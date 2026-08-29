"""Database engine and session setup."""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


database_url = settings.resolved_database_url
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True, future=True)
session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def initialize_schema() -> None:
    """Create tables and apply the small idempotent migration set."""

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        tracker_columns = {column["name"] for column in inspect(connection).get_columns("trackers")}
        if "node_profile" not in tracker_columns:
            connection.execute(
                text(
                    "ALTER TABLE trackers ADD COLUMN node_profile "
                    "VARCHAR(64) NOT NULL DEFAULT 'ENDPOINT_POD'"
                )
            )
            connection.execute(
                text(
                    "UPDATE trackers SET node_profile = CASE "
                    "WHEN UPPER(endpoint_role) = 'RELAY_FIXED' THEN 'RELAY_FIXED' "
                    "WHEN UPPER(endpoint_role) = 'GATEWAY_CENTRAL' THEN 'GATEWAY_CENTRAL' "
                    "ELSE 'ENDPOINT_POD' END"
                )
            )


def get_db():
    """Yield a SQLAlchemy session per request."""

    db = session_local()
    try:
        yield db
    finally:
        db.close()
