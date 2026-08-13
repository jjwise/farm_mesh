# Irrigation Pod Tracker

Implementation v1 for a multi-hop irrigation pod tracking system with:

- **Firmware profiles** on Heltec Wireless Tracker:
  - `ENDPOINT_POD`
  - `RELAY_FIXED`
  - `GATEWAY_CENTRAL`
- **MQTT ingestion worker** with QoS 1 and idempotent PostgreSQL writes.
- **Backend API** (FastAPI) for line registry, history, snapshot, interpolation.
- **Web map UI** for timeline/history and coverage heatmap.
- **Self-hosted stack** with Mosquitto TLS, PostgreSQL, Caddy HTTPS, API and web UI.

## Repository structure

- `src/firmware/`: firmware runtime and role-specific logic
- `include/project_config.h`: compile-time defaults for node identity and gateway uplink
- `platformio.ini`: PlatformIO environments for each firmware profile
- `backend/`: FastAPI service and interpolation logic
- `web/`: static frontend map UI
- `deploy/`: hardened Docker Compose deployment for a home server
- `docs/meshtastic_integration_notes.md`: where to plug real Meshtastic transport
- `meshtastic_overlay/`: isolated module scaffold to port into Meshtastic fork

## Firmware build targets

```bash
pio run -e endpoint_pod
pio run -e relay_fixed
pio run -e gateway_central
```

## Notes

- Mesh transport currently uses a dedicated abstraction in `src/firmware/mesh_transport.*`.
  Hook Meshtastic module internals there to preserve backend/web contracts unchanged.
- Gateway uplink uses verified TLS and QoS 1; `msg_id` is also unique in PostgreSQL for application-level idempotence.
- `GET /v1/line/{line_id}/snapshot` computes pod interpolation using `pod_count` + `pod_spacing_m`.
- For clean fork maintenance, prefer porting logic from this repo into `meshtastic_overlay/src/modules/irrigation/*`.

## Recommended self-hosted architecture

```text
Endpoint pods --LoRa--> Meshtastic gateway --MQTT/TLS:8883--> Mosquitto
                                                              |
                                                      MQTT worker (QoS 1)
                                                              |
                                                         PostgreSQL
                                                              |
Internet --HTTPS:443--> Caddy --private network--> FastAPI + static web UI
```

Only MQTT/TLS and HTTPS are exposed by the Compose stack. PostgreSQL, FastAPI,
and MQTT port 1883 remain on a private Docker network. See
`deploy/README.md` for bootstrap, DNS, certificate, firewall and backup steps.
