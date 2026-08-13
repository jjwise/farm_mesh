#include "telemetry_event.h"

#include <ArduinoJson.h>

String motion_state_to_string(MotionState motion_state) {
  switch (motion_state) {
    case MotionState::MOVING:
      return "MOVING";
    case MotionState::STATIONARY:
    default:
      return "STATIONARY";
  }
}

MotionState motion_state_from_string(const String &value) {
  if (value == "MOVING") {
    return MotionState::MOVING;
  }
  return MotionState::STATIONARY;
}

bool telemetry_to_json(const TelemetryEvent &event, String &output_json) {
  JsonDocument json_doc;
  json_doc["msg_id"] = event.msg_id;
  json_doc["ts_utc_ms"] = event.ts_utc_ms;
  json_doc["tracker_id"] = event.tracker_id;
  json_doc["line_id"] = event.line_id;
  json_doc["endpoint_role"] = event.endpoint_role;
  json_doc["lat"] = event.lat;
  json_doc["long"] = event.lon;
  json_doc["hdop"] = event.hdop;
  json_doc["speed_mps"] = event.speed_mps;
  json_doc["heading_deg"] = event.heading_deg;
  json_doc["motion_state"] = motion_state_to_string(event.motion_state);
  json_doc["battery_mv"] = event.battery_mv;
  json_doc["fix"] = event.fix;
  json_doc["hop_count"] = event.hop_count;

  const size_t written = serializeJson(json_doc, output_json);
  return written > 0;
}

bool telemetry_from_json(const String &payload_json, TelemetryEvent &event) {
  JsonDocument json_doc;
  DeserializationError parse_error = deserializeJson(json_doc, payload_json);
  if (parse_error) {
    return false;
  }

  event.msg_id = json_doc["msg_id"] | "";
  event.ts_utc_ms = json_doc["ts_utc_ms"] | 0;
  event.tracker_id = json_doc["tracker_id"] | "";
  event.line_id = json_doc["line_id"] | "";
  event.endpoint_role = json_doc["endpoint_role"] | "";
  event.lat = json_doc["lat"] | 0.0;
  if (json_doc["long"].isNull()) {
    event.lon = json_doc["lon"] | 0.0;
  } else {
    event.lon = json_doc["long"] | 0.0;
  }
  event.hdop = json_doc["hdop"] | 0.0f;
  event.speed_mps = json_doc["speed_mps"] | 0.0f;
  event.heading_deg = json_doc["heading_deg"] | 0.0f;
  event.motion_state = motion_state_from_string(json_doc["motion_state"] | "STATIONARY");
  event.battery_mv = json_doc["battery_mv"] | 0;
  event.fix = json_doc["fix"] | false;
  event.hop_count = json_doc["hop_count"] | 0;
  return true;
}

String build_mqtt_topic(const String &farm_id, const String &line_id, const String &tracker_id) {
  return "farm/" + farm_id + "/lines/" + line_id + "/trackers/" + tracker_id + "/telemetry";
}

TelemetryEvent build_empty_event(const NodeConfig &config) {
  TelemetryEvent event;
  event.msg_id = "";
  event.ts_utc_ms = 0;
  event.tracker_id = config.tracker_id;
  event.line_id = config.line_id;
  event.endpoint_role = config.endpoint_role;
  event.lat = 0.0;
  event.lon = 0.0;
  event.hdop = 0.0f;
  event.speed_mps = 0.0f;
  event.heading_deg = 0.0f;
  event.motion_state = MotionState::STATIONARY;
  event.battery_mv = 0;
  event.fix = false;
  event.hop_count = 0;
  return event;
}

