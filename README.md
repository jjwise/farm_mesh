# Irrigation Pod Tracker

Implementation v1 for a multi-hop irrigation pod tracking system with:

- **Firmware profiles** on Heltec Wireless Tracker:
  - `ENDPOINT_POD`
  - `BASIC_TRACKER`
  - `VALVE_ACTUATOR`
  - `RELAY_FIXED`
  - `GATEWAY_CENTRAL`
- **MQTT worker** with QoS 1, idempotent PostgreSQL writes, and command retries.
- **Backend API** (FastAPI) for nodes, commands, line registry, history, snapshot, and interpolation.
- **Unified web map** with profile filters/sorting, pod heat layer, tracker settings, and valve controls.
- **Self-hosted stack** with Mosquitto TLS, PostgreSQL, Caddy HTTPS, API and web UI.

## Repository structure

- `../meshtastic_fork/`: source of truth for every deployed firmware profile.
- `backend/`: FastAPI, PostgreSQL models, MQTT ingestion, and command outbox.
- `web/`: unified static map and role-specific controls.
- `deploy/`: hardened Docker Compose deployment for a home server.
- `src/firmware/` and `meshtastic_overlay/`: legacy prototypes; do not deploy them.

## Firmware build targets

```bash
cd ../meshtastic_fork
pio run -e hwt_tracker
pio run -e hwt_valve
pio run -e hwt_gw
```

## Notes

- Gateway uplink uses verified TLS and QoS 1; `msg_id` is unique in PostgreSQL for application-level idempotence.
- Commands are non-retained, expire after a short TTL, and are retried until an ACK/rejection or expiry.
- Valve opening requires valid node time and a bounded duration; the node closes automatically.
- GPIO4 on the Heltec profile drives only a protected logic-level MOSFET/driver input, never a solenoid directly.
- `GET /v1/line/{line_id}/snapshot` computes pod interpolation using `pod_count` + `pod_spacing_m`.

## Recommended self-hosted architecture

```text
Pods / trackers / valves <--LoRa--> Meshtastic gateway <--MQTT/TLS:8883--> Mosquitto
                                                                           |
                                                          telemetry + command worker
                                                                           |
                                                                      PostgreSQL
                                                                           |
Internet --HTTPS:443--> Caddy --private network--> FastAPI + static web UI
```

Only MQTT/TLS and HTTPS are exposed by the Compose stack. PostgreSQL, FastAPI,
and MQTT port 1883 remain on a private Docker network. See
`deploy/README.md` for bootstrap, DNS, certificate, firewall and backup steps.
