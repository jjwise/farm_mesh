"""Tests for role-specific state and command acknowledgements."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import NodeCommandModel, NodeStateModel, TrackerModel
from app.schemas import TelemetryEventIn
from app.services.ingestion import ingest_event


def test_valve_ack_updates_confirmed_state_and_command() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    session.add(
        NodeCommandModel(
            command_id="command-1",
            farm_id="farm_01",
            tracker_id="node_VALVE",
            action="SET_VALVE",
            payload_json="{}",
            status="SENT",
            created_at=now,
            expires_at=now + timedelta(minutes=2),
        )
    )
    session.commit()

    event = TelemetryEventIn(
        msg_id="ack-1",
        ts_utc_ms=int(now.timestamp() * 1000),
        farm_id="farm_01",
        tracker_id="node_VALVE",
        line_id="infrastructure",
        endpoint_role="VALVE",
        node_profile="VALVE_ACTUATOR",
        publish_reason="COMMAND_ACK",
        lat=-43.5,
        long=172.6,
        fix=True,
        command_id="command-1",
        command_status="ACKED",
        valve_open=True,
    )

    assert ingest_event(session, event) is True
    state = session.query(NodeStateModel).filter_by(tracker_id="node_VALVE").one()
    tracker = session.query(TrackerModel).filter_by(tracker_id="node_VALVE").one()
    assert state.valve_open is True
    assert state.last_command_status == "ACKED"
    assert tracker.node_profile == "VALVE_ACTUATOR"
    assert session.query(NodeCommandModel).filter_by(command_id="command-1").one().status == "ACKED"
    session.close()

def test_node_summary_keeps_last_nonzero_position_after_positionless_ack() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    position = TelemetryEventIn(
        msg_id="position-1",
        ts_utc_ms=int(now.timestamp() * 1000),
        farm_id="farm_01",
        tracker_id="node_VALVE",
        line_id="infrastructure",
        endpoint_role="VALVE",
        node_profile="VALVE_ACTUATOR",
        publish_reason="VALVE_STATE",
        lat=-43.5,
        long=172.6,
        fix=True,
    )
    ack = TelemetryEventIn(
        msg_id="ack-without-position",
        ts_utc_ms=int((now + timedelta(seconds=1)).timestamp() * 1000),
        farm_id="farm_01",
        tracker_id="node_VALVE",
        line_id="infrastructure",
        endpoint_role="VALVE",
        node_profile="VALVE_ACTUATOR",
        publish_reason="COMMAND_ACK",
        lat=0,
        long=0,
        fix=False,
        command_id="close-1",
        command_status="ACKED",
        valve_open=False,
    )
    assert ingest_event(session, position) is True
    assert ingest_event(session, ack) is True

    from app.api.nodes import get_nodes

    summary = get_nodes(db=session)[0]
    assert summary.lat == -43.5
    assert summary.long == 172.6
    assert summary.valve_open is False
    session.close()
