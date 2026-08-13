#include "node_config.h"

#include "project_config.h"

#ifndef PROJECT_DEFAULT_HOP_LIMIT
#define PROJECT_DEFAULT_HOP_LIMIT 3
#endif

#ifndef PROJECT_MAX_HOP_OVERRIDE
#define PROJECT_MAX_HOP_OVERRIDE 5
#endif

static NodeProfile get_build_profile() {
#if defined(NODE_PROFILE_RELAY_FIXED)
  return NodeProfile::RELAY_FIXED;
#elif defined(NODE_PROFILE_GATEWAY_CENTRAL)
  return NodeProfile::GATEWAY_CENTRAL;
#else
  return NodeProfile::ENDPOINT_POD;
#endif
}

NodeConfig load_node_config() {
  NodeConfig config;
  config.farm_id = PROJECT_FARM_ID;
  config.line_id = PROJECT_LINE_ID;
  config.tracker_id = PROJECT_TRACKER_ID;
  config.endpoint_role = PROJECT_ENDPOINT_ROLE;
  config.node_profile = get_build_profile();
  config.default_hop_limit = static_cast<uint8_t>(PROJECT_DEFAULT_HOP_LIMIT);
  config.max_hop_override = static_cast<uint8_t>(PROJECT_MAX_HOP_OVERRIDE);
  config.stationary_interval_sec = static_cast<uint32_t>(PROJECT_STATIONARY_INTERVAL_SEC);
  config.moving_interval_sec = static_cast<uint32_t>(PROJECT_MOVING_INTERVAL_SEC);
  config.moving_hold_sec = static_cast<uint32_t>(PROJECT_MOVING_HOLD_SEC);
  config.wifi_ssid = PROJECT_WIFI_SSID;
  config.wifi_password = PROJECT_WIFI_PASSWORD;
  config.mqtt_host = PROJECT_MQTT_HOST;
  config.mqtt_port = static_cast<uint16_t>(PROJECT_MQTT_PORT);
  config.mqtt_username = PROJECT_MQTT_USERNAME;
  config.mqtt_password = PROJECT_MQTT_PASSWORD;
  config.mqtt_client_id = config.tracker_id + "_gateway";
  config.gateway_buffer_max_records = static_cast<uint16_t>(PROJECT_GATEWAY_BUFFER_MAX_RECORDS);
  return config;
}

const char *node_profile_to_string(NodeProfile node_profile) {
  switch (node_profile) {
    case NodeProfile::ENDPOINT_POD:
      return "ENDPOINT_POD";
    case NodeProfile::RELAY_FIXED:
      return "RELAY_FIXED";
    case NodeProfile::GATEWAY_CENTRAL:
      return "GATEWAY_CENTRAL";
    default:
      return "UNKNOWN";
  }
}

bool is_endpoint_profile(NodeProfile node_profile) {
  return node_profile == NodeProfile::ENDPOINT_POD;
}

bool is_gateway_profile(NodeProfile node_profile) {
  return node_profile == NodeProfile::GATEWAY_CENTRAL;
}

