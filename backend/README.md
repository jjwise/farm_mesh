# Backend

FastAPI service for line/snapshot/history views, plus a separate MQTT ingestion
worker. PostgreSQL is recommended for deployment; SQLite remains convenient
for local tests.

## Run

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment variables

Use `.env` in `backend/` with `IRRIGATION_` prefix:

```env
IRRIGATION_DATABASE_URL=sqlite:///./irrigation_tracker.db
IRRIGATION_API_TOKEN=change-me-token
IRRIGATION_SNAPSHOT_WINDOW_SECONDS=30
IRRIGATION_MAX_HISTORY_POINTS=10000
IRRIGATION_ADMIN_TOKEN=change-me-admin-token
IRRIGATION_MQTT_HOST=localhost
IRRIGATION_MQTT_PORT=1883
IRRIGATION_MQTT_USERNAME=irrigation-backend
IRRIGATION_MQTT_PASSWORD=change-me
IRRIGATION_MQTT_TOPIC=farm/+/lines/+/trackers/+/telemetry
```

Run the MQTT worker separately:

```bash
python -m app.mqtt_worker
```

## Main endpoints

- `POST /v1/ingest/telemetry`
- `POST /v1/lines`
- `GET /v1/lines`
- `GET /v1/line/{line_id}/snapshot?at=...`
- `GET /v1/line/{line_id}/history?from=...&to=...`

`POST /v1/lines` requires `x-admin-token`. HTTP ingestion remains available
for diagnostics and requires `x-api-token`; the production path is MQTT.

The worker accepts the compact firmware keys (`i`, `t`, `r`, `l`, etc.),
checks that tracker and line identifiers agree with the MQTT topic, and commits
the event before acknowledging QoS 1. Invalid pre-2020 device timestamps are
preserved as `device_ts_utc_ms`, while the effective event time falls back to
the server receive time.

Schema creation still uses SQLAlchemy `create_all`. It is suitable for a new
deployment, but it does not migrate an existing database. Export any existing
SQLite data before switching to PostgreSQL.
