"""Tests for the compact firmware MQTT contract."""

from datetime import datetime, timezone

import pytest

from app.mqtt_codec import InvalidMqttMessage, normalize_mqtt_message


def test_normalize_compact_payload() -> None:
    event = normalize_mqtt_message(
        "farm/farm_01/lines/line_01/trackers/node_ABCD/telemetry",
        (
            b'{"i":"node_ABCD-1780000000000-1","t":1780000000000,'
            b'"r":"node_ABCD","l":"line_01","e":"ENDPOINT_A","n":"ENDPOINT_POD","p":"P",'
            b'"a":-43.5321,"o":172.6362,"m":"S","f":1,"s":0,'
            b'"d":91.2,"v":1,"b":4010,"q":"G","h":3}'
        ),
    )

    assert event.farm_id == "farm_01"
    assert event.publish_reason == "POST_MOVE_FIX"
    assert event.motion_state == "STATIONARY"
    assert event.heading_valid is True
    assert event.time_quality == "GNSS"
    assert event.ts_utc_ms == 1780000000000
    assert event.node_profile == "ENDPOINT_POD"


def test_normalize_valve_ack_state() -> None:
    event = normalize_mqtt_message(
        "farm/farm_01/lines/infrastructure/trackers/node_VALVE/telemetry",
        (
            b'{"i":"ack-1","t":1780000000000,"r":"node_VALVE","l":"infrastructure",'
            b'"e":"VALVE","n":"VALVE_ACTUATOR","p":"A","a":-43.5,"o":172.6,'
            b'"f":1,"c":"command-1","w":1}'
        ),
    )

    assert event.node_profile == "VALVE_ACTUATOR"
    assert event.publish_reason == "COMMAND_ACK"
    assert event.command_id == "command-1"
    assert event.command_status == "ACKED"
    assert event.valve_open is True


def test_invalid_device_time_uses_receive_time() -> None:
    received_at = datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc)
    event = normalize_mqtt_message(
        "farm/farm_01/lines/line_01/trackers/node_ABCD/telemetry",
        (
            b'{"i":"old-firmware-1","t":12345,"r":"node_ABCD","l":"line_01",'
            b'"e":"ENDPOINT_A","a":-43.5,"o":172.6,"f":1}'
        ),
        received_at=received_at,
    )

    assert event.device_ts_utc_ms == 12345
    assert event.ts_utc_ms == int(received_at.timestamp() * 1000)
    assert event.time_quality == "UNKNOWN"


def test_topic_payload_identity_mismatch_is_rejected() -> None:
    with pytest.raises(InvalidMqttMessage, match="identifiers do not match"):
        normalize_mqtt_message(
            "farm/farm_01/lines/line_01/trackers/node_ABCD/telemetry",
            b'{"i":"bad-1","r":"other-node","l":"line_01","e":"ENDPOINT_A"}',
        )
