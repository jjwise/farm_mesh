#pragma once

#include <Arduino.h>

#include "node_config.h"

struct TelemetryEvent {
  String msg_id;
  uint64_t ts_utc_ms;
  String tracker_id;
  String line_id;
  String endpoint_role;
  double lat;
  double lon;
  float hdop;
  float speed_mps;
  float heading_deg;
  MotionState motion_state;
  uint16_t battery_mv;
  bool fix;
  uint8_t hop_count;
};

String motion_state_to_string(MotionState motion_state);
MotionState motion_state_from_string(const String &value);
bool telemetry_to_json(const TelemetryEvent &event, String &output_json);
bool telemetry_from_json(const String &payload_json, TelemetryEvent &event);
String build_mqtt_topic(const String &farm_id, const String &line_id, const String &tracker_id);
TelemetryEvent build_empty_event(const NodeConfig &config);

