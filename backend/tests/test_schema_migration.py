"""Regression tests for upgrades of an already-populated database."""

from sqlalchemy import create_engine, inspect, text

from app import database


def test_initialize_schema_adds_node_profile_to_legacy_trackers(monkeypatch) -> None:
    legacy_engine = create_engine("sqlite:///:memory:")
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE trackers ("
                "id INTEGER PRIMARY KEY, "
                "tracker_id VARCHAR(128) NOT NULL, "
                "line_id VARCHAR(128) NOT NULL, "
                "endpoint_role VARCHAR(64) NOT NULL, "
                "default_hop_limit INTEGER NOT NULL DEFAULT 3, "
                "max_hop_override INTEGER NOT NULL DEFAULT 5, "
                "created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO trackers "
                "(tracker_id, line_id, endpoint_role, created_at) "
                "VALUES ('node-old', 'line-1', 'ENDPOINT_A', CURRENT_TIMESTAMP)"
            )
        )

    monkeypatch.setattr(database, "engine", legacy_engine)
    database.initialize_schema()
    database.initialize_schema()

    columns = {column["name"] for column in inspect(legacy_engine).get_columns("trackers")}
    assert "node_profile" in columns
    with legacy_engine.connect() as connection:
        profile = connection.execute(
            text("SELECT node_profile FROM trackers WHERE tracker_id = 'node-old'")
        ).scalar_one()
    assert profile == "ENDPOINT_POD"
