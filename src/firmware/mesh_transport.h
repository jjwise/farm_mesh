#pragma once

#include <Arduino.h>

#include "node_config.h"
#include "telemetry_event.h"

class MeshTransport {
 public:
  MeshTransport();
  bool begin(const NodeConfig &config);
  void loop();
  bool publish_telemetry(const TelemetryEvent &event, uint8_t hop_limit);
  bool receive_telemetry(TelemetryEvent &event);

 private:
  NodeConfig config_;
  String rx_line_buffer_;
};

