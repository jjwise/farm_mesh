# Meshtastic Integration Notes

The firmware now exposes a clear integration seam:

- `src/firmware/mesh_transport.h`
- `src/firmware/mesh_transport.cpp`

Current behavior uses serial-based stubs:

- `publish_telemetry()` writes `MESH_TX:...` logs.
- `receive_telemetry()` reads `MESH_RX:{json}` lines from serial input.

This allows end-to-end API/web validation immediately while keeping payload and topic contracts stable.

## Replace stub with Meshtastic module internals

1. Map `publish_telemetry()` to Meshtastic packet send path.
2. Map `receive_telemetry()` to Meshtastic receive callback/queue.
3. Preserve payload fields and message `msg_id`.
4. Keep hop policy inputs:
   - `default_hop_limit`
   - `max_hop_override`
5. Keep endpoint role semantics:
   - `ENDPOINT_A`, `ENDPOINT_B`, `RELAY_FIXED`, `GATEWAY_CENTRAL`

## Compatibility target

- Continue emitting standard position packets for official Meshtastic app compatibility.
- Send extended telemetry on a dedicated app port for backend analytics.

