"""Read and configuration endpoints for lines and telemetry history."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from dateutil import parser as date_parser
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import LineModel, TelemetryEventModel
from app.schemas import HistoryPoint, LineConfigUpsert, LineSummary, SnapshotEndpoint, SnapshotResponse
from app.services.interpolation import interpolate_pods

router = APIRouter(prefix="/v1", tags=["lines"])


def require_admin_token(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    """Protect configuration mutations even when the API is reached without Caddy."""

    expected_token = settings.resolved_admin_token
    if not expected_token:
        return
    if x_admin_token is None or not secrets.compare_digest(x_admin_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid x-admin-token",
        )


def to_epoch_ms(value: datetime) -> int:
    """Convert datetime to unix epoch milliseconds."""

    return int(value.timestamp() * 1000)


def parse_datetime_input(value: str | None, default_value: datetime) -> datetime:
    """Parse ISO datetime; fallback to default when value is empty."""

    if not value:
        return default_value

    parsed = date_parser.parse(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_history_point(model: TelemetryEventModel) -> HistoryPoint:
    """Serialize database row to history response."""

    return HistoryPoint(
        msg_id=model.msg_id,
        ts_utc_ms=to_epoch_ms(model.ts_utc),
        received_at_utc_ms=to_epoch_ms(model.received_at),
        farm_id=model.farm_id,
        tracker_id=model.tracker_id,
        line_id=model.line_id,
        endpoint_role=model.endpoint_role,
        publish_reason=model.publish_reason,
        lat=model.lat,
        long=model.long,
        hdop=model.hdop,
        speed_mps=model.speed_mps,
        heading_deg=model.heading_deg,
        heading_valid=model.heading_valid,
        motion_state=model.motion_state,
        battery_mv=model.battery_mv,
        fix=model.fix,
        stale=model.stale,
        time_quality=model.time_quality,
        hop_count=model.hop_count,
    )


def find_closest_endpoint_event(
    db: Session,
    line_id: str,
    endpoint_role: str,
    at_utc: datetime,
    window_seconds: int,
) -> TelemetryEventModel | None:
    """Find nearest endpoint telemetry in the target window, fallback to latest before at_utc."""

    window_start = at_utc - timedelta(seconds=window_seconds)
    window_end = at_utc + timedelta(seconds=window_seconds)
    candidates = (
        db.query(TelemetryEventModel)
        .filter(
            TelemetryEventModel.line_id == line_id,
            TelemetryEventModel.endpoint_role == endpoint_role,
            TelemetryEventModel.ts_utc >= window_start,
            TelemetryEventModel.ts_utc <= window_end,
        )
        .all()
    )
    if candidates:
        return min(candidates, key=lambda item: abs((item.ts_utc - at_utc).total_seconds()))

    return (
        db.query(TelemetryEventModel)
        .filter(
            TelemetryEventModel.line_id == line_id,
            TelemetryEventModel.endpoint_role == endpoint_role,
            TelemetryEventModel.ts_utc <= at_utc,
        )
        .order_by(TelemetryEventModel.ts_utc.desc())
        .first()
    )


@router.post("/lines", response_model=LineSummary, dependencies=[Depends(require_admin_token)])
def upsert_line_config(payload: LineConfigUpsert, db: Session = Depends(get_db)) -> LineSummary:
    """Create or update line interpolation settings."""

    line = db.query(LineModel).filter(LineModel.line_id == payload.line_id).one_or_none()
    if line is None:
        line = LineModel(line_id=payload.line_id)
        db.add(line)

    line.name = payload.name
    line.pod_count = payload.pod_count
    line.pod_spacing_m = payload.pod_spacing_m
    db.commit()
    db.refresh(line)

    return LineSummary(
        line_id=line.line_id,
        name=line.name,
        pod_count=line.pod_count,
        pod_spacing_m=line.pod_spacing_m,
    )


@router.get("/lines", response_model=list[LineSummary])
def get_lines(db: Session = Depends(get_db)) -> list[LineSummary]:
    """Return all configured lines."""

    lines = db.query(LineModel).order_by(LineModel.line_id.asc()).all()
    return [
        LineSummary(
            line_id=line.line_id,
            name=line.name,
            pod_count=line.pod_count,
            pod_spacing_m=line.pod_spacing_m,
        )
        for line in lines
    ]


@router.get("/line/{line_id}/history", response_model=list[HistoryPoint])
def get_line_history(
    line_id: str,
    from_value: Annotated[str | None, Query(alias="from")] = None,
    to_value: Annotated[str | None, Query(alias="to")] = None,
    db: Session = Depends(get_db),
) -> list[HistoryPoint]:
    """Return historical telemetry in a time window."""

    now_utc = datetime.now(timezone.utc)
    from_utc = parse_datetime_input(from_value, now_utc - timedelta(hours=24))
    to_utc = parse_datetime_input(to_value, now_utc)

    if from_utc > to_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'from' must be earlier than 'to'",
        )

    rows = (
        db.query(TelemetryEventModel)
        .filter(
            TelemetryEventModel.line_id == line_id,
            TelemetryEventModel.ts_utc >= from_utc,
            TelemetryEventModel.ts_utc <= to_utc,
        )
        .order_by(TelemetryEventModel.ts_utc.asc())
        .limit(settings.max_history_points)
        .all()
    )
    return [to_history_point(row) for row in rows]


@router.get("/line/{line_id}/snapshot", response_model=SnapshotResponse)
def get_line_snapshot(
    line_id: str,
    at: str | None = None,
    db: Session = Depends(get_db),
) -> SnapshotResponse:
    """Return nearest endpoint positions and interpolated pod positions for a timestamp."""

    line = db.query(LineModel).filter(LineModel.line_id == line_id).one_or_none()
    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="line not found")

    at_utc = parse_datetime_input(at, datetime.now(timezone.utc))
    endpoint_a = find_closest_endpoint_event(
        db=db,
        line_id=line_id,
        endpoint_role="ENDPOINT_A",
        at_utc=at_utc,
        window_seconds=settings.snapshot_window_seconds,
    )
    endpoint_b = find_closest_endpoint_event(
        db=db,
        line_id=line_id,
        endpoint_role="ENDPOINT_B",
        at_utc=at_utc,
        window_seconds=settings.snapshot_window_seconds,
    )

    endpoint_a_response = None
    endpoint_b_response = None
    if endpoint_a is not None:
        endpoint_a_response = SnapshotEndpoint(
            endpoint_role=endpoint_a.endpoint_role,
            tracker_id=endpoint_a.tracker_id,
            ts_utc_ms=to_epoch_ms(endpoint_a.ts_utc),
            publish_reason=endpoint_a.publish_reason,
            lat=endpoint_a.lat,
            long=endpoint_a.long,
            heading_deg=endpoint_a.heading_deg,
            heading_valid=endpoint_a.heading_valid,
            speed_mps=endpoint_a.speed_mps,
            motion_state=endpoint_a.motion_state,
            battery_mv=endpoint_a.battery_mv,
            fix=endpoint_a.fix,
            stale=endpoint_a.stale,
            time_quality=endpoint_a.time_quality,
            hop_count=endpoint_a.hop_count,
        )
    if endpoint_b is not None:
        endpoint_b_response = SnapshotEndpoint(
            endpoint_role=endpoint_b.endpoint_role,
            tracker_id=endpoint_b.tracker_id,
            ts_utc_ms=to_epoch_ms(endpoint_b.ts_utc),
            publish_reason=endpoint_b.publish_reason,
            lat=endpoint_b.lat,
            long=endpoint_b.long,
            heading_deg=endpoint_b.heading_deg,
            heading_valid=endpoint_b.heading_valid,
            speed_mps=endpoint_b.speed_mps,
            motion_state=endpoint_b.motion_state,
            battery_mv=endpoint_b.battery_mv,
            fix=endpoint_b.fix,
            stale=endpoint_b.stale,
            time_quality=endpoint_b.time_quality,
            hop_count=endpoint_b.hop_count,
        )

    pods = []
    compressed = False
    if endpoint_a is not None and endpoint_b is not None and line.pod_count > 0:
        pods, compressed = interpolate_pods(
            lat_a=endpoint_a.lat,
            long_a=endpoint_a.long,
            lat_b=endpoint_b.lat,
            long_b=endpoint_b.long,
            pod_count=line.pod_count,
            pod_spacing_m=line.pod_spacing_m,
        )

    return SnapshotResponse(
        line_id=line_id,
        at_utc_ms=to_epoch_ms(at_utc),
        endpoint_a=endpoint_a_response,
        endpoint_b=endpoint_b_response,
        pods=pods,
        compressed=compressed,
    )
