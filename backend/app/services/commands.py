"""Safe MQTT command construction and one-shot publication."""

import hashlib
import hmac
import json
import re
import ssl
import uuid
from datetime import datetime, timedelta, timezone

import paho.mqtt.client as mqtt

from app.config import settings
from app.schemas import NodeCommandRequest

TOPIC_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
MINIMUM_HMAC_KEY_LENGTH = 32


def validate_topic_segment(value: str, field_name: str) -> None:
    if TOPIC_SEGMENT_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} is not a safe MQTT topic segment")


def _length_prefixed(value: str) -> str:
    return f"{len(value)}:{value}|"


def command_signature(payload: dict[str, str | int], hmac_key: str) -> str:
    """Sign the fixed command fields with a 128-bit HMAC-SHA256 tag."""

    if len(hmac_key) < MINIMUM_HMAC_KEY_LENGTH:
        raise RuntimeError("command HMAC key must contain at least 32 characters")
    canonical = (
        "v1|"
        + _length_prefixed(str(payload["i"]))
        + _length_prefixed(str(payload["r"]))
        + f"{payload['a']}|{payload['x']}|{payload['z']}|"
        + f"{int(payload.get('w', 0))}|{int(payload.get('d', 0))}|{int(payload.get('u', 0))}"
    )
    return hmac.new(hmac_key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def build_command_contract(
    farm_id: str,
    tracker_id: str,
    command_id: str,
    request: NodeCommandRequest,
    now: datetime | None = None,
    hmac_key: str | None = None,
) -> tuple[str, str, datetime]:
    """Build the compact, expiring, non-retained mesh command contract."""

    validate_topic_segment(farm_id, "farm_id")
    validate_topic_segment(tracker_id, "tracker_id")
    issued_at = now or datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(seconds=settings.command_ttl_seconds)
    payload: dict[str, str | int] = {
        "k": "C",
        "i": command_id,
        "r": tracker_id,
        "a": "V" if request.action == "SET_VALVE" else "I",
        "x": int(issued_at.timestamp() * 1000),
        "z": int(expires_at.timestamp() * 1000),
    }
    if request.action == "SET_VALVE":
        payload["w"] = 1 if request.valve_open else 0
        if request.valve_open:
            payload["d"] = int(request.duration_sec or 0)
    else:
        payload["u"] = int(request.position_interval_sec or 0)
    payload["s"] = command_signature(
        payload,
        settings.resolved_command_hmac_key if hmac_key is None else hmac_key,
    )

    topic = f"farm/{farm_id}/nodes/{tracker_id}/commands"
    return topic, json.dumps(payload, separators=(",", ":")), expires_at


def publish_command(topic: str, payload_json: str) -> None:
    """Publish one QoS command and wait until the broker accepted it."""

    if not settings.mqtt_host:
        raise RuntimeError("MQTT host is not configured")

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{settings.mqtt_client_id}-api-{uuid.uuid4().hex[:8]}",
        clean_session=True,
        protocol=mqtt.MQTTv311,
    )
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.resolved_mqtt_password)
    if settings.mqtt_tls:
        client.tls_set(
            ca_certs=settings.mqtt_ca_file or None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )

    try:
        client.connect(settings.mqtt_host, settings.mqtt_port, settings.mqtt_keepalive_seconds)
        client.loop_start()
        result = client.publish(
            topic,
            payload_json,
            qos=settings.mqtt_command_qos,
            retain=False,
        )
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish returned {result.rc}")
        result.wait_for_publish(timeout=settings.mqtt_publish_timeout_seconds)
        if not result.is_published():
            raise TimeoutError("MQTT command publish timed out")
    finally:
        client.disconnect()
        client.loop_stop()
