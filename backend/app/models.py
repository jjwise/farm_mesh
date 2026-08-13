"""SQLAlchemy models for lines, trackers, and telemetry."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now() -> datetime:
    """Return timezone-aware UTC now."""

    return datetime.now(timezone.utc)


class LineModel(Base):
    """Line configuration used for interpolation and grouping."""

    __tablename__ = "lines"

    id = Column(Integer, primary_key=True, index=True)
    line_id = Column(String(128), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False, default="")
    pod_count = Column(Integer, nullable=False, default=0)
    pod_spacing_m = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    trackers = relationship("TrackerModel", back_populates="line", cascade="all, delete-orphan")


class TrackerModel(Base):
    """Metadata for a tracker node."""

    __tablename__ = "trackers"

    id = Column(Integer, primary_key=True, index=True)
    tracker_id = Column(String(128), unique=True, index=True, nullable=False)
    line_id = Column(String(128), ForeignKey("lines.line_id"), index=True, nullable=False)
    endpoint_role = Column(String(64), nullable=False, default="")
    node_profile = Column(String(64), nullable=False, default="")
    default_hop_limit = Column(Integer, nullable=False, default=3)
    max_hop_override = Column(Integer, nullable=False, default=5)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    line = relationship("LineModel", back_populates="trackers")


class TelemetryEventModel(Base):
    """Raw telemetry event from mesh/gateway ingestion."""

    __tablename__ = "telemetry_events"

    id = Column(Integer, primary_key=True, index=True)
    msg_id = Column(String(256), unique=True, index=True, nullable=False)
    ts_utc = Column(DateTime(timezone=True), index=True, nullable=False)
    device_ts_utc_ms = Column(BigInteger, nullable=True)
    received_at = Column(DateTime(timezone=True), index=True, nullable=False, default=utc_now)
    farm_id = Column(String(128), index=True, nullable=False, default="farm_01")
    tracker_id = Column(String(128), index=True, nullable=False)
    line_id = Column(String(128), index=True, nullable=False)
    endpoint_role = Column(String(64), index=True, nullable=False)
    publish_reason = Column(String(64), index=True, nullable=False, default="HEARTBEAT")
    lat = Column(Float, nullable=False)
    long = Column("long", Float, nullable=False)
    hdop = Column(Float, nullable=False, default=0.0)
    speed_mps = Column(Float, nullable=False, default=0.0)
    heading_deg = Column(Float, nullable=False, default=0.0)
    heading_valid = Column(Boolean, nullable=False, default=False)
    motion_state = Column(String(32), nullable=False, default="STATIONARY")
    battery_mv = Column(Integer, nullable=False, default=0)
    fix = Column(Boolean, nullable=False, default=False)
    stale = Column(Boolean, nullable=False, default=False)
    time_quality = Column(String(32), nullable=False, default="UNKNOWN")
    hop_count = Column(Integer, nullable=False, default=0)
    mqtt_topic = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
