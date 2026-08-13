#pragma once

#include <Arduino.h>

enum class NodeProfile {
  ENDPOINT_POD,
  RELAY_FIXED,
  GATEWAY_CENTRAL
};

enum class MotionState {
  STATIONARY,
  MOVING
};

struct NodeConfig {
  String farm_id;
  String line_id;
  String tracker_id;
  String endpoint_role;
  NodeProfile node_profile;
  uint8_t default_hop_limit;
  uint8_t max_hop_override;
  uint32_t stationary_interval_sec;
  uint32_t moving_interval_sec;
  uint32_t moving_hold_sec;
  String wifi_ssid;
  String wifi_password;
  String mqtt_host;
  uint16_t mqtt_port;
  String mqtt_username;
  String mqtt_password;
  String mqtt_client_id;
  uint16_t gateway_buffer_max_records;
};

NodeConfig load_node_config();
const char *node_profile_to_string(NodeProfile node_profile);
bool is_endpoint_profile(NodeProfile node_profile);
bool is_gateway_profile(NodeProfile node_profile);

