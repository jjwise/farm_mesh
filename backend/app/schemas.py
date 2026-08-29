"""Pydantic schemas for request/response contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    node_profile: str = "ENDPOINT_POD"
    publish_reason: str = "HEARTBEAT"
    lat: float = Field(ge=-90, le=90)
    long: float = Field(ge=-180, le=180)
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
    command_id: str = ""
    valve_open: bool | None = None
    position_interval_sec: int | None = Field(default=None, ge=60, le=86400)
    command_status: str = ""


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


class NodeSummary(BaseModel):
    """Current map and role-specific state for one mesh node."""

    tracker_id: str
    farm_id: str
    line_id: str
    endpoint_role: str
    node_profile: str
    last_seen_utc_ms: int | None
    lat: float | None
    long: float | None
    battery_mv: int | None
    fix: bool | None
    stale: bool | None
    valve_open: bool | None
    position_interval_sec: int | None
    last_command_id: str
    last_command_status: str


class NodeCommandRequest(BaseModel):
    """Validated server-to-node command."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["SET_VALVE", "SET_POSITION_INTERVAL"]
    valve_open: bool | None = None
    duration_sec: int | None = Field(default=None, ge=1, le=3600)
    position_interval_sec: int | None = Field(default=None, ge=60, le=86400)

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.action == "SET_VALVE":
            if self.valve_open is None:
                raise ValueError("valve_open is required for SET_VALVE")
            if self.position_interval_sec is not None:
                raise ValueError("position_interval_sec is not valid for SET_VALVE")
            if self.valve_open and self.duration_sec is None:
                raise ValueError("duration_sec is required when opening a valve")
            if not self.valve_open:
                self.duration_sec = None
        else:
            if self.position_interval_sec is None:
                raise ValueError("position_interval_sec is required for SET_POSITION_INTERVAL")
            if self.valve_open is not None or self.duration_sec is not None:
                raise ValueError("valve fields are not valid for SET_POSITION_INTERVAL")
        return self


class NodeCommandResponse(BaseModel):
    """Command delivery and acknowledgement status."""

    command_id: str
    tracker_id: str
    action: str
    status: str
    created_at_utc_ms: int
    expires_at_utc_ms: int
    sent_at_utc_ms: int | None
    acknowledged_at_utc_ms: int | None
    error_message: str


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
