#include "mesh_transport.h"

MeshTransport::MeshTransport() : rx_line_buffer_("") {}

bool MeshTransport::begin(const NodeConfig &config) {
  config_ = config;
  Serial.printf(
      "[mesh] profile=%s line_id=%s default_hop=%u max_hop=%u\n",
      node_profile_to_string(config_.node_profile),
      config_.line_id.c_str(),
      config_.default_hop_limit,
      config_.max_hop_override);
  return true;
}

void MeshTransport::loop() {}

bool MeshTransport::publish_telemetry(const TelemetryEvent &event, uint8_t hop_limit) {
  String payload_json;
  if (!telemetry_to_json(event, payload_json)) {
    return false;
  }
  Serial.printf("MESH_TX:hop=%u payload=%s\n", hop_limit, payload_json.c_str());
  return true;
}

bool MeshTransport::receive_telemetry(TelemetryEvent &event) {
  while (Serial.available() > 0) {
    const char input_char = static_cast<char>(Serial.read());
    if (input_char == '\r') {
      continue;
    }
    if (input_char != '\n') {
      rx_line_buffer_ += input_char;
      continue;
    }

    String line = rx_line_buffer_;
    rx_line_buffer_ = "";
    line.trim();
    if (!line.startsWith("MESH_RX:")) {
      continue;
    }

    const String payload_json = line.substring(8);
    if (telemetry_from_json(payload_json, event)) {
      return true;
    }
  }
  return false;
}
