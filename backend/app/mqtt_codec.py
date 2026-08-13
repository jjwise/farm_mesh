"""Validation and normalization for compact irrigation MQTT messages."""

import json
import re
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.schemas import TelemetryEventIn

TOPIC_PATTERN = re.compile(
    r"^farm/(?P<farm_id>[^/]+)/lines/(?P<line_id>[^/]+)/"
    r"trackers/(?P<tracker_id>[^/]+)/telemetry$"
)
MIN_VALID_EPOCH_MS = 1_577_836_800_000  # 2020-01-01T00:00:00Z

PUBLISH_REASONS = {
    "H": "HEARTBEAT",
    "N": "HEARTBEAT_NO_FIX",
    "P": "POST_MOVE_FIX",
    "C": "SETTLE_CONFIRM",
    "X": "MOTION_DETECTED_NO_FIX",
}
MOTION_STATES = {"M": "MOVING", "S": "STATIONARY"}
TIME_QUALITIES = {"G": "GNSS", "R": "RTC", "U": "UNKNOWN"}


class InvalidMqttMessage(ValueError):
    """Raised when a topic/payload pair violates the telemetry contract."""


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def normalize_mqtt_message(
    topic: str,
    payload: bytes,
    received_at: datetime | None = None,
) -> TelemetryEventIn:
    """Convert compact or verbose firmware JSON into the canonical API schema."""

    match = TOPIC_PATTERN.fullmatch(topic)
    if match is None:
        raise InvalidMqttMessage("topic does not match irrigation telemetry contract")

    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidMqttMessage("payload is not valid UTF-8 JSON") from exc
    if not isinstance(raw, dict):
        raise InvalidMqttMessage("payload must be a JSON object")

    topic_values = match.groupdict()
    tracker_id = str(raw.get("r", raw.get("tracker_id", "")))
    line_id = str(raw.get("l", raw.get("line_id", "")))
    if tracker_id != topic_values["tracker_id"] or line_id != topic_values["line_id"]:
        raise InvalidMqttMessage("topic and payload identifiers do not match")

    received_at = received_at or datetime.now(timezone.utc)
    received_ms = int(received_at.timestamp() * 1000)
    device_ts = int(raw.get("t", raw.get("ts_utc_ms", 0)) or 0)
    effective_ts = device_ts if device_ts >= MIN_VALID_EPOCH_MS else received_ms
    time_quality = TIME_QUALITIES.get(
        str(raw.get("q", raw.get("time_quality", "U"))).upper(),
        str(raw.get("time_quality", "UNKNOWN")).upper(),
    )
    if device_ts < MIN_VALID_EPOCH_MS:
        time_quality = "UNKNOWN"

    data = {
        "msg_id": str(raw.get("i", raw.get("msg_id", ""))),
        "ts_utc_ms": effective_ts,
        "device_ts_utc_ms": device_ts or None,
        "farm_id": topic_values["farm_id"],
        "tracker_id": tracker_id,
        "line_id": line_id,
        "endpoint_role": str(raw.get("e", raw.get("endpoint_role", ""))).upper(),
        "publish_reason": PUBLISH_REASONS.get(
            str(raw.get("p", raw.get("publish_reason", "H"))).upper(),
            str(raw.get("publish_reason", "HEARTBEAT")).upper(),
        ),
        "lat": float(raw.get("a", raw.get("lat", 0.0))),
        "long": float(raw.get("o", raw.get("long", raw.get("lon", 0.0)))),
        "hdop": float(raw.get("hdop", 0.0)),
        "speed_mps": float(raw.get("speed_mps", 0.0)),
        "heading_deg": float(raw.get("d", raw.get("heading_deg", 0.0))),
        "heading_valid": _bool_value(raw.get("v", raw.get("heading_valid", False))),
        "motion_state": MOTION_STATES.get(
            str(raw.get("m", raw.get("motion_state", "S"))).upper(),
            str(raw.get("motion_state", "STATIONARY")).upper(),
        ),
        "battery_mv": int(raw.get("b", raw.get("battery_mv", 0)) or 0),
        "fix": _bool_value(raw.get("f", raw.get("fix", False))),
        "stale": _bool_value(raw.get("s", raw.get("stale", False))),
        "time_quality": time_quality,
        "hop_count": int(raw.get("h", raw.get("hop_count", 0)) or 0),
        "mqtt_topic": topic,
    }
    if not data["msg_id"] or not data["endpoint_role"]:
        raise InvalidMqttMessage("msg_id and endpoint_role are required")

    try:
        return TelemetryEventIn.model_validate(data)
    except (ValidationError, TypeError, ValueError) as exc:
        raise InvalidMqttMessage(f"payload validation failed: {exc}") from exc
