# Porting Map

Map of current prototype files to Meshtastic overlay module files.

## Source mapping

1. `src/firmware/telemetry_event.*`
   - `src/modules/irrigation/IrrigationPacketCodec.*`
   - `src/modules/irrigation/IrrigationTypes.h`

2. `src/firmware/motion_detector.*`
   - `src/modules/irrigation/IrrigationMotionDetector.*`

3. `src/firmware/ring_buffer_store.*`
   - `src/modules/irrigation/IrrigationGatewayStore.*`

4. `src/firmware/mqtt_uplink.*`
   - `src/modules/irrigation/IrrigationMqttUplink.*`

5. `src/firmware/app_runtime.*`
   - `src/modules/irrigation/IrrigationModule.*`

6. Meshtastic module wrapper
   - `src/modules/IrrigationOverlayModule.*`
   - Registered in `src/modules/Modules.cpp`

## Notes

- `src/firmware/mesh_transport.*` is a local stub transport. In Meshtastic fork,
  replace this role with module TX/RX hooks to existing packet paths.
- Keep all irrigation files in one module directory to reduce merge conflicts.
