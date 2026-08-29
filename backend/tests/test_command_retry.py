"""Tests for command outbox expiry and retry bookkeeping."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import NodeCommandModel, NodeStateModel
from app import mqtt_worker


class DisconnectedClient:
    def is_connected(self) -> bool:
        return False


def test_retry_worker_expires_unacknowledged_command(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    now = datetime.now(timezone.utc)

    db = sessions()
    db.add(
        NodeCommandModel(
            command_id="expired-1",
            farm_id="farm_01",
            tracker_id="node_VALVE",
            action="SET_VALVE",
            payload_json="{}",
            status="SENT",
            created_at=now - timedelta(minutes=3),
            expires_at=now - timedelta(minutes=1),
            sent_at=now - timedelta(minutes=2),
        )
    )
    db.add(
        NodeStateModel(
            tracker_id="node_VALVE",
            last_command_id="expired-1",
            last_command_status="SENT",
        )
    )
    db.commit()
    db.close()

    monkeypatch.setattr(mqtt_worker, "session_local", sessions)
    mqtt_worker.retry_node_commands(DisconnectedClient())

    db = sessions()
    assert db.query(NodeCommandModel).one().status == "EXPIRED"
    assert db.query(NodeStateModel).one().last_command_status == "EXPIRED"
    db.close()
