"""Unified node registry, history, and role-specific commands."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.lines import parse_datetime_input, require_admin_token, to_epoch_ms, to_history_point
from app.config import settings
from app.database import get_db
from app.models import NodeCommandModel, NodeStateModel, TelemetryEventModel, TrackerModel
from app.schemas import HistoryPoint, NodeCommandRequest, NodeCommandResponse, NodeSummary
from app.services.commands import build_command_contract, publish_command

router = APIRouter(prefix="/v1", tags=["nodes"])


def command_response(command: NodeCommandModel) -> NodeCommandResponse:
    return NodeCommandResponse(
        command_id=command.command_id,
        tracker_id=command.tracker_id,
        action=command.action,
        status=command.status,
        created_at_utc_ms=to_epoch_ms(command.created_at),
        expires_at_utc_ms=to_epoch_ms(command.expires_at),
        sent_at_utc_ms=to_epoch_ms(command.sent_at) if command.sent_at else None,
        acknowledged_at_utc_ms=to_epoch_ms(command.acknowledged_at) if command.acknowledged_at else None,
        error_message=command.error_message,
    )


@router.get("/nodes", response_model=list[NodeSummary])
def get_nodes(
    profile: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
) -> list[NodeSummary]:
    """Return all known nodes with latest telemetry and confirmed state."""

    query = db.query(TrackerModel)
    if profile:
        query = query.filter(TrackerModel.node_profile == profile.upper())
    trackers = query.order_by(TrackerModel.tracker_id.asc()).all()
    result: list[NodeSummary] = []
    for tracker in trackers:
        latest = (
            db.query(TelemetryEventModel)
            .filter(TelemetryEventModel.tracker_id == tracker.tracker_id)
            .order_by(TelemetryEventModel.ts_utc.desc(), TelemetryEventModel.id.desc())
            .first()
        )
        latest_position = (
            db.query(TelemetryEventModel)
            .filter(
                TelemetryEventModel.tracker_id == tracker.tracker_id,
                or_(TelemetryEventModel.lat != 0, TelemetryEventModel.long != 0),
            )
            .order_by(TelemetryEventModel.ts_utc.desc(), TelemetryEventModel.id.desc())
            .first()
        )
        state_row = db.query(NodeStateModel).filter(NodeStateModel.tracker_id == tracker.tracker_id).one_or_none()
        result.append(
            NodeSummary(
                tracker_id=tracker.tracker_id,
                farm_id=latest.farm_id if latest else "farm_01",
                line_id=tracker.line_id,
                endpoint_role=tracker.endpoint_role,
                node_profile=tracker.node_profile,
                last_seen_utc_ms=to_epoch_ms(latest.received_at) if latest else None,
                lat=latest_position.lat if latest_position else None,
                long=latest_position.long if latest_position else None,
                battery_mv=latest.battery_mv if latest else None,
                fix=latest_position.fix if latest_position else None,
                stale=latest_position.stale if latest_position else None,
                valve_open=state_row.valve_open if state_row else None,
                position_interval_sec=state_row.position_interval_sec if state_row else None,
                last_command_id=state_row.last_command_id if state_row else "",
                last_command_status=state_row.last_command_status if state_row else "",
            )
        )
    return result


@router.get("/nodes/{tracker_id}/history", response_model=list[HistoryPoint])
def get_node_history(
    tracker_id: str,
    from_value: Annotated[str | None, Query(alias="from")] = None,
    to_value: Annotated[str | None, Query(alias="to")] = None,
    db: Session = Depends(get_db),
) -> list[HistoryPoint]:
    now_utc = datetime.now(timezone.utc)
    from_utc = parse_datetime_input(from_value, now_utc - timedelta(hours=24))
    to_utc = parse_datetime_input(to_value, now_utc)
    if from_utc > to_utc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'from' must be earlier than 'to'")
    rows = (
        db.query(TelemetryEventModel)
        .filter(
            TelemetryEventModel.tracker_id == tracker_id,
            TelemetryEventModel.ts_utc >= from_utc,
            TelemetryEventModel.ts_utc <= to_utc,
        )
        .order_by(TelemetryEventModel.ts_utc.asc())
        .limit(settings.max_history_points)
        .all()
    )
    return [to_history_point(row) for row in rows]


@router.post(
    "/nodes/{tracker_id}/commands",
    response_model=NodeCommandResponse,
    dependencies=[Depends(require_admin_token)],
)
def create_node_command(
    tracker_id: str,
    request: NodeCommandRequest,
    db: Session = Depends(get_db),
) -> NodeCommandResponse:
    """Persist and publish an expiring command; reported state changes only on acknowledgement."""

    tracker = db.query(TrackerModel).filter(TrackerModel.tracker_id == tracker_id).one_or_none()
    if tracker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="node not found")
    expected_profile = "VALVE_ACTUATOR" if request.action == "SET_VALVE" else "BASIC_TRACKER"
    if tracker.node_profile != expected_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{request.action} is not supported by {tracker.node_profile}",
        )

    command_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    latest = (
        db.query(TelemetryEventModel)
        .filter(TelemetryEventModel.tracker_id == tracker_id)
        .order_by(TelemetryEventModel.received_at.desc())
        .first()
    )
    farm_id = latest.farm_id if latest else "farm_01"
    try:
        topic, payload_json, expires_at = build_command_contract(
            farm_id=farm_id,
            tracker_id=tracker_id,
            command_id=command_id,
            request=request,
            now=now,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="node has an invalid MQTT identifier",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="command authentication is not configured",
        ) from exc
    command = NodeCommandModel(
        command_id=command_id,
        farm_id=farm_id,
        tracker_id=tracker_id,
        action=request.action,
        payload_json=payload_json,
        status="PENDING",
        created_at=now,
        expires_at=expires_at,
    )
    db.add(command)
    db.commit()

    state_row = db.query(NodeStateModel).filter(NodeStateModel.tracker_id == tracker_id).one_or_none()
    if state_row is None:
        state_row = NodeStateModel(tracker_id=tracker_id)
        db.add(state_row)
    state_row.last_command_id = command_id
    try:
        publish_command(topic, payload_json)
        command.status = "SENT"
        command.sent_at = datetime.now(timezone.utc)
        state_row.last_command_status = "SENT"
        db.commit()
        db.refresh(command)
        return command_response(command)
    except Exception as exc:
        command.status = "FAILED"
        command.error_message = str(exc)[:500]
        state_row.last_command_status = "FAILED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"command_id": command_id, "error": "MQTT command delivery failed"},
        ) from exc


@router.get("/nodes/{tracker_id}/commands/{command_id}", response_model=NodeCommandResponse)
def get_node_command(tracker_id: str, command_id: str, db: Session = Depends(get_db)) -> NodeCommandResponse:
    command = (
        db.query(NodeCommandModel)
        .filter(NodeCommandModel.tracker_id == tracker_id, NodeCommandModel.command_id == command_id)
        .one_or_none()
    )
    if command is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="command not found")
    expires_at = command.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if command.status == "SENT" and expires_at < datetime.now(timezone.utc):
        command.status = "EXPIRED"
        db.commit()
    return command_response(command)
