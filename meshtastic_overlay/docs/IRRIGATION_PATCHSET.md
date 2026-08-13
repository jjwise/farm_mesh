# IRRIGATION_PATCHSET

This document defines a minimal-change integration plan for adding irrigation
features to a Meshtastic firmware fork while keeping the changes distinct from
core mesh logic.

## Integration policy

1. All irrigation business logic lives under:
   - `src/modules/irrigation/*`
2. Core Meshtastic files are touched only for module registration and packet
   callback hooks.
3. Standard Meshtastic position packets remain untouched for app compatibility.
4. Extended irrigation telemetry is sent on an application port.

## Core hook categories

Exact filenames vary by Meshtastic release. Apply hooks by role below.

1. Module registration hook:
   - Register `IrrigationModule` in module startup/registry path.
   - Current fork hook point: `src/modules/Modules.cpp`.
2. RX hook:
   - Route incoming irrigation port packets into `IrrigationModule::on_packet_rx`.
3. TX hook:
   - Allow `IrrigationModule` to emit irrigation telemetry through existing send
     path (no custom radio stack).
4. Tick hook:
   - Call `IrrigationModule::tick(now_ms)` from scheduler/loop.
5. Config hook:
   - Use the isolated `IrrigationConfigStore` first.
   - Load `defaults -> /irrigation.cfg -> build overrides -> runtime derived`.
   - Keep Meshtastic native config unchanged in v1.

## Commit strategy

Keep each stage in a dedicated commit:

1. `scaffold`: add `src/modules/irrigation/*` with no active behavior.
2. `codec`: add packet encode/decode and port wiring.
3. `motion`: add movement detector and publish cadence logic.
4. `gateway`: add queue + MQTT uplink implementation.
5. `routing`: apply hop defaults (`3`) and border override (`5`) for irrigation packets.
6. `docs`: update operations docs and patchset notes.

## Profiles

Use compile-time profile flags:

- `IRRIGATION_PROFILE_ENDPOINT_POD`
- `IRRIGATION_PROFILE_RELAY_FIXED`
- `IRRIGATION_PROFILE_GATEWAY_CENTRAL`

### Known working build environments (Heltec Wireless Tracker v1.1)

- `heltec-wireless-tracker` (generic irrigation-enabled)
- `hwt_ep` (endpoint profile)
- `hwt_relay` (relay profile)
- `hwt_gw` (gateway profile + MQTT uplink flag)

Build examples:

- `platformio run -e hwt_ep`
- `platformio run -e hwt_relay`
- `platformio run -e hwt_gw`

## Config bootstrap

The isolated irrigation config is stored in:

- `/irrigation.cfg`

Suggested wrapper behavior:

1. Build baseline with `make_default_irrigation_config()`.
2. Merge persisted values from `IrrigationConfigStore::load(...)`.
3. Apply compile-time overrides such as:
   - `IRRIGATION_FARM_ID`
   - `IRRIGATION_LINE_ID`
   - `IRRIGATION_ENDPOINT_ROLE`
   - `IRRIGATION_WIFI_SSID`
   - `IRRIGATION_WIFI_PASSWORD`
   - `IRRIGATION_MQTT_HOST`
   - `IRRIGATION_MQTT_PORT`
   - `IRRIGATION_MQTT_USERNAME`
   - `IRRIGATION_MQTT_PASSWORD`
4. Derive runtime-only values such as `tracker_id`.
5. Call `save_if_changed(...)` so the bootstrap config survives reboot.

Windows note:

- If toolchain reports `CreateProcess` or `lto-wrapper` failures, disable LTO in
  the target env (`build_unflags = -flto`, `build_flags += -fno-lto`).

## Contracts to preserve

Payload fields:

- `msg_id`
- `ts_utc_ms`
- `tracker_id`
- `line_id`
- `endpoint_role`
- `lat`
- `long`
- `hdop`
- `speed_mps`
- `heading_deg`
- `motion_state`
- `battery_mv`
- `fix`
- `hop_count`

MQTT topic:

- `farm/{farm_id}/lines/{line_id}/trackers/{tracker_id}/telemetry`

## Operational constraints

1. Stationary telemetry interval: `3600s`.
2. Moving telemetry interval: `10s`.
3. Moving hold: `120s`.
4. Default hop: `3`.
5. Max override hop: `5`.
6. Gateway buffer target: `24-72h` using ring queue.
