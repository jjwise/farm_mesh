# Meshtastic Irrigation Overlay

This folder contains an isolated irrigation module scaffold designed to be
ported into a Meshtastic firmware fork.

Goals:

- Keep irrigation logic distinct from Meshtastic core internals.
- Minimize fork maintenance cost by limiting core hooks.
- Preserve backend/web payload contracts already implemented in this repo.

This overlay is not wired into the local PlatformIO app build. It is a
portable patchset workspace for your Meshtastic fork.

## Folder layout

- `src/modules/irrigation/`: isolated irrigation module source files
- `docs/IRRIGATION_PATCHSET.md`: exact hook points and patch strategy
- `docs/PORTING_MAP.md`: mapping from local prototype files to overlay files
- `docs/ENDPOINT_POD_V2_SPEC.md`: endpoint sleep/wake, motion, GNSS, and payload behavior

## Suggested usage

1. Fork Meshtastic firmware.
2. Copy `src/modules/irrigation/` and `src/modules/IrrigationOverlayModule.*`
   into your fork under `src/modules/`.
3. Apply hook changes listed in `docs/IRRIGATION_PATCHSET.md`.
4. Build and test each profile incrementally (`hwt_ep`, `hwt_relay`, `hwt_gw`).

## Secure gateway configuration

The gateway refuses a TLS connection when no trusted CA is compiled in. Keep
credentials in `IrrigationGatewaySecrets.generated.h`, never in PlatformIO
configuration. The self-hosted deployment provides a generator:

```text
deploy/scripts/render_firmware_secrets.py
```

The generated header supplies the Wi-Fi credentials, broker DNS name, port
8883, MQTT credentials, and public CA. The MQTT uplink uses a persistent
session and QoS 1; the gateway backlog is only popped after `PUBACK`.

## Config persistence

The overlay now includes `src/modules/irrigation/IrrigationConfigStore.*`, which
persists irrigation-specific settings in `/irrigation.cfg` on LittleFS.

Recommended precedence in the fork wrapper:

1. `make_default_irrigation_config()`
2. persisted `/irrigation.cfg`
3. build-time overrides for first bootstrap / controlled test runs
4. runtime-derived values such as `tracker_id`
