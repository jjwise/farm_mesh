"""Optional HTTP ingestion endpoint for diagnostics and migration."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import IngestTelemetryRequest, IngestTelemetryResponse
from app.services.ingestion import ingest_event

router = APIRouter(prefix="/v1", tags=["ingest"])


def require_ingest_token(x_api_token: Annotated[str | None, Header()] = None) -> None:
    """Validate ingestion token header when configured."""

    expected_token = settings.resolved_api_token
    if not expected_token:
        return
    if x_api_token is None or not secrets.compare_digest(x_api_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid x-api-token",
        )


@router.post(
    "/ingest/telemetry",
    response_model=IngestTelemetryResponse,
    dependencies=[Depends(require_ingest_token)],
)
def ingest_telemetry(payload: IngestTelemetryRequest, db: Session = Depends(get_db)) -> IngestTelemetryResponse:
    """Ingest telemetry events with idempotence on msg_id."""

    inserted = 0
    duplicates = 0

    for event in payload.events:
        if ingest_event(db, event):
            inserted += 1
        else:
            duplicates += 1

    return IngestTelemetryResponse(inserted=inserted, duplicates=duplicates)
