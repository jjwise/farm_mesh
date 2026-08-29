"""Tests for safe server-to-node command contracts."""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import NodeCommandRequest
from app.services.commands import build_command_contract

TEST_HMAC_KEY = "0123456789abcdef0123456789abcdef"


def test_valve_open_requires_duration() -> None:
    with pytest.raises(ValidationError, match="duration_sec"):
        NodeCommandRequest(action="SET_VALVE", valve_open=True)


def test_build_compact_expiring_valve_command() -> None:
    request = NodeCommandRequest(action="SET_VALVE", valve_open=True, duration_sec=300)
    now = datetime(2026, 8, 24, 1, 2, 3, tzinfo=timezone.utc)
    topic, payload_json, expires_at = build_command_contract(
        farm_id="farm_01",
        tracker_id="node_VALVE",
        command_id="command-1",
        request=request,
        now=now,
        hmac_key=TEST_HMAC_KEY,
    )
    payload = json.loads(payload_json)

    assert topic == "farm/farm_01/nodes/node_VALVE/commands"
    assert payload["k"] == "C"
    assert payload["a"] == "V"
    assert payload["w"] == 1
    assert payload["d"] == 300
    assert payload["z"] > payload["x"]
    assert payload["s"] == "c4fab546ae46acb2ed2123493431e5ff"
    assert expires_at > now


def test_tracker_interval_contract() -> None:
    request = NodeCommandRequest(action="SET_POSITION_INTERVAL", position_interval_sec=1800)
    _, payload_json, _ = build_command_contract(
        farm_id="farm_01",
        tracker_id="node_TRACKER",
        command_id="command-2",
        request=request,
        hmac_key=TEST_HMAC_KEY,
    )
    payload = json.loads(payload_json)

    assert payload["a"] == "I"
    assert payload["u"] == 1800
    assert "w" not in payload


def test_command_rejects_fields_for_another_action() -> None:
    with pytest.raises(ValidationError, match="valve fields"):
        NodeCommandRequest(
            action="SET_POSITION_INTERVAL",
            position_interval_sec=900,
            valve_open=False,
        )


def test_command_topic_segments_cannot_escape_the_node_namespace() -> None:
    request = NodeCommandRequest(action="SET_POSITION_INTERVAL", position_interval_sec=900)
    with pytest.raises(ValueError, match="farm_id"):
        build_command_contract(
            farm_id="farm/other",
            tracker_id="node_TRACKER",
            command_id="command-3",
            request=request,
            hmac_key=TEST_HMAC_KEY,
        )


def test_command_requires_a_strong_hmac_key() -> None:
    request = NodeCommandRequest(action="SET_VALVE", valve_open=False)
    with pytest.raises(RuntimeError, match="at least 32"):
        build_command_contract(
            farm_id="farm_01",
            tracker_id="node_VALVE",
            command_id="command-4",
            request=request,
            hmac_key="short",
        )
