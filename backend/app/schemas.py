"""Pydantic schemas for request/response contracts."""

from pydantic import BaseModel, ConfigDict, Field


class LineConfigUpsert(BaseModel):
    """Request payload for creating/updating a line config."""

    line_id: str
    name: str = ""
    pod_count: int = Field(default=0, ge=0)
    pod_spacing_m: float = Field(default=0.0, ge=0)


class LineSummary(BaseModel):
    """Line metadata and interpolation settings."""

    line_id: str
    name: str
    pod_count: int
    pod_spacing_m: float


class TelemetryEventIn(BaseModel):
    """Incoming telemetry payload from gateway."""

    model_config = ConfigDict(extra="forbid")

    msg_id: str
    ts_utc_ms: int = Field(ge=0)
    device_ts_utc_ms: int | None = Field(default=None, ge=0)
    farm_id: str = "farm_01"
    tracker_id: str
    line_id: str
    endpoint_role: str
    publish_reason: str = "HEARTBEAT"
    lat: float
    long: float
    hdop: float = 0.0
    speed_mps: float = 0.0
    heading_deg: float = 0.0
    heading_valid: bool = False
    motion_state: str = "STATIONARY"
    battery_mv: int = 0
    fix: bool = False
    stale: bool = False
    time_quality: str = "UNKNOWN"
    hop_count: int = Field(default=0, ge=0)
    mqtt_topic: str = ""


class IngestTelemetryRequest(BaseModel):
    """Batch telemetry ingestion payload."""

    events: list[TelemetryEventIn]


class IngestTelemetryResponse(BaseModel):
    """Batch ingestion status."""

    inserted: int
    duplicates: int


class HistoryPoint(BaseModel):
    """Telemetry entry returned by history endpoint."""

    msg_id: str
    ts_utc_ms: int
    received_at_utc_ms: int
    farm_id: str
    tracker_id: str
    line_id: str
    endpoint_role: str
    publish_reason: str
    lat: float
    long: float
    hdop: float
    speed_mps: float
    heading_deg: float
    heading_valid: bool
    motion_state: str
    battery_mv: int
    fix: bool
    stale: bool
    time_quality: str
    hop_count: int


class SnapshotEndpoint(BaseModel):
    """Snapshot position for one endpoint."""

    endpoint_role: str
    tracker_id: str
    ts_utc_ms: int
    publish_reason: str
    lat: float
    long: float
    heading_deg: float
    heading_valid: bool
    speed_mps: float
    motion_state: str
    battery_mv: int
    fix: bool
    stale: bool
    time_quality: str
    hop_count: int


class PodPoint(BaseModel):
    """Interpolated pod point."""

    pod_index: int
    lat: float
    long: float
    compressed: bool


class SnapshotResponse(BaseModel):
    """Line snapshot at a given timestamp."""

    line_id: str
    at_utc_ms: int
    endpoint_a: SnapshotEndpoint | None
    endpoint_b: SnapshotEndpoint | None
    pods: list[PodPoint]
    compressed: bool
