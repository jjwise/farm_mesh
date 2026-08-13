"""Shared idempotent telemetry ingestion used by HTTP and MQTT."""

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import LineModel, TelemetryEventModel, TrackerModel
from app.schemas import TelemetryEventIn


def ensure_line(db: Session, line_id: str) -> LineModel:
    """Create a line row when unknown and return it."""

    line = db.query(LineModel).filter(LineModel.line_id == line_id).one_or_none()
    if line is not None:
        return line

    line = LineModel(line_id=line_id, name=line_id, pod_count=0, pod_spacing_m=0.0)
    db.add(line)
    db.flush()
    return line


def ensure_tracker(db: Session, event: TelemetryEventIn) -> TrackerModel:
    """Create or update tracker metadata from an event."""

    tracker = db.query(TrackerModel).filter(TrackerModel.tracker_id == event.tracker_id).one_or_none()
    if tracker is not None:
        if tracker.line_id != event.line_id:
            tracker.line_id = event.line_id
        tracker.endpoint_role = event.endpoint_role.upper()
        return tracker

    endpoint_role = event.endpoint_role.upper()
    node_profile = "ENDPOINT_POD"
    if endpoint_role == "RELAY_FIXED":
        node_profile = "RELAY_FIXED"
    elif endpoint_role == "GATEWAY_CENTRAL":
        node_profile = "GATEWAY_CENTRAL"

    tracker = TrackerModel(
        tracker_id=event.tracker_id,
        line_id=event.line_id,
        endpoint_role=endpoint_role,
        node_profile=node_profile,
        default_hop_limit=3,
        max_hop_override=5,
    )
    db.add(tracker)
    db.flush()
    return tracker


def ingest_event(db: Session, event: TelemetryEventIn) -> bool:
    """Insert one event. Return False when msg_id already exists."""

    ensure_line(db, event.line_id)
    ensure_tracker(db, event)

    model = TelemetryEventModel(
        msg_id=event.msg_id,
        ts_utc=datetime.fromtimestamp(event.ts_utc_ms / 1000.0, tz=timezone.utc),
        device_ts_utc_ms=event.device_ts_utc_ms,
        farm_id=event.farm_id,
        tracker_id=event.tracker_id,
        line_id=event.line_id,
        endpoint_role=event.endpoint_role.upper(),
        publish_reason=event.publish_reason.upper(),
        lat=event.lat,
        long=event.long,
        hdop=event.hdop,
        speed_mps=event.speed_mps,
        heading_deg=event.heading_deg,
        heading_valid=event.heading_valid,
        motion_state=event.motion_state.upper(),
        battery_mv=event.battery_mv,
        fix=event.fix,
        stale=event.stale,
        time_quality=event.time_quality.upper(),
        hop_count=event.hop_count,
        mqtt_topic=event.mqtt_topic,
    )
    db.add(model)
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False
