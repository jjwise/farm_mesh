#include "app_runtime.h"

#include <cmath>

namespace {
constexpr unsigned long k_loop_delay_ms = 250;
constexpr unsigned long k_relay_heartbeat_interval_ms = 300000;
constexpr unsigned long k_gateway_flush_interval_ms = 2000;
constexpr float k_border_hop_hdop_threshold = 3.5f;
}  // namespace

AppRuntime::AppRuntime()
    : last_endpoint_publish_ms_(0),
      last_relay_heartbeat_ms_(0),
      last_gateway_flush_ms_(0),
      last_heading_deg_(0.0f),
      event_sequence_(0) {}

void AppRuntime::setup() {
  Serial.begin(115200);
  delay(1500);

  config_ = load_node_config();
  Serial.printf(
      "[boot] profile=%s tracker_id=%s line_id=%s role=%s\n",
      node_profile_to_string(config_.node_profile),
      config_.tracker_id.c_str(),
      config_.line_id.c_str(),
      config_.endpoint_role.c_str());

  mesh_transport_.begin(config_);

  if (is_endpoint_profile(config_.node_profile)) {
    sensor_adapters_.begin(config_);
  }

  if (is_gateway_profile(config_.node_profile)) {
    ring_buffer_store_.begin("/gateway_queue.log", config_.gateway_buffer_max_records);
    mqtt_uplink_.begin(config_);
  }
}

void AppRuntime::loop() {
  switch (config_.node_profile) {
    case NodeProfile::ENDPOINT_POD:
      loop_endpoint();
      break;
    case NodeProfile::RELAY_FIXED:
      loop_relay();
      break;
    case NodeProfile::GATEWAY_CENTRAL:
      loop_gateway();
      break;
  }
  delay(k_loop_delay_ms);
}

void AppRuntime::loop_endpoint() {
  SensorSample sample = sensor_adapters_.read_sample();
  const float heading_delta_deg = fabsf(sample.heading_deg - last_heading_deg_);
  last_heading_deg_ = sample.heading_deg;

  motion_detector_.update(sample.accel_rms_g, sample.speed_mps, heading_delta_deg, sample.gps_fix);
  const MotionState current_state = motion_detector_.motion_state();
  const uint32_t interval_sec =
      current_state == MotionState::MOVING ? config_.moving_interval_sec : config_.stationary_interval_sec;

  const bool due_by_interval =
      last_endpoint_publish_ms_ == 0 || millis() - last_endpoint_publish_ms_ >= interval_sec * 1000UL;
  const bool due_by_transition = motion_detector_.transition_to_moving();
  if (!due_by_interval && !due_by_transition) {
    return;
  }

  TelemetryEvent event = build_event_from_sample(sample);
  event.motion_state = current_state;
  event.hop_count = compute_hop_limit(sample);
  if (mesh_transport_.publish_telemetry(event, event.hop_count)) {
    last_endpoint_publish_ms_ = millis();
  }
}

void AppRuntime::loop_relay() {
  mesh_transport_.loop();
  if (millis() - last_relay_heartbeat_ms_ < k_relay_heartbeat_interval_ms) {
    return;
  }
  last_relay_heartbeat_ms_ = millis();
  Serial.printf(
      "[relay] alive tracker_id=%s default_hop=%u max_hop=%u\n",
      config_.tracker_id.c_str(),
      config_.default_hop_limit,
      config_.max_hop_override);
}

void AppRuntime::loop_gateway() {
  mesh_transport_.loop();
  mqtt_uplink_.loop();

  TelemetryEvent incoming_event;
  while (mesh_transport_.receive_telemetry(incoming_event)) {
    String payload_json;
    if (telemetry_to_json(incoming_event, payload_json)) {
      ring_buffer_store_.append(payload_json);
      Serial.printf(
          "[gateway] queued msg_id=%s queue_size=%u\n",
          incoming_event.msg_id.c_str(),
          static_cast<unsigned int>(ring_buffer_store_.size()));
    }
  }

  if (millis() - last_gateway_flush_ms_ < k_gateway_flush_interval_ms) {
    return;
  }
  last_gateway_flush_ms_ = millis();
  flush_gateway_backlog(20);
}

uint8_t AppRuntime::compute_hop_limit(const SensorSample &sample) const {
  if (!sample.gps_fix || sample.hdop > k_border_hop_hdop_threshold) {
    return config_.max_hop_override;
  }
  return config_.default_hop_limit;
}

TelemetryEvent AppRuntime::build_event_from_sample(const SensorSample &sample) {
  TelemetryEvent event = build_empty_event(config_);
  event.ts_utc_ms = get_runtime_timestamp_ms();
  event.lat = sample.latitude;
  event.lon = sample.longitude;
  event.hdop = sample.hdop;
  event.speed_mps = sample.speed_mps;
  event.heading_deg = sample.heading_deg;
  event.battery_mv = sample.battery_mv;
  event.fix = sample.gps_fix;
  event.msg_id = config_.tracker_id + "-" + String(event.ts_utc_ms) + "-" + String(event_sequence_++);
  return event;
}

bool AppRuntime::flush_gateway_backlog(size_t max_messages) {
  if (!mqtt_uplink_.is_connected()) {
    return false;
  }

  size_t sent_count = 0;
  while (sent_count < max_messages) {
    String payload_json;
    if (!ring_buffer_store_.peek_next(payload_json)) {
      break;
    }

    TelemetryEvent queued_event;
    if (!telemetry_from_json(payload_json, queued_event)) {
      ring_buffer_store_.pop_next();
      continue;
    }

    const String topic = build_mqtt_topic(config_.farm_id, queued_event.line_id, queued_event.tracker_id);
    const bool sent = mqtt_uplink_.publish_payload(topic, payload_json, 1);
    if (!sent) {
      break;
    }
    ring_buffer_store_.pop_next();
    sent_count++;
  }

  if (sent_count > 0) {
    Serial.printf(
        "[gateway] flushed=%u pending=%u\n",
        static_cast<unsigned int>(sent_count),
        static_cast<unsigned int>(ring_buffer_store_.size()));
  }
  return sent_count > 0;
}

uint64_t AppRuntime::get_runtime_timestamp_ms() {
  return static_cast<uint64_t>(millis());
}
