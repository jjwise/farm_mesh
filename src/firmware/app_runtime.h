#pragma once

#include "mesh_transport.h"
#include "motion_detector.h"
#include "mqtt_uplink.h"
#include "node_config.h"
#include "ring_buffer_store.h"
#include "sensor_adapters.h"
#include "telemetry_event.h"

class AppRuntime {
 public:
  AppRuntime();
  void setup();
  void loop();

 private:
  void loop_endpoint();
  void loop_relay();
  void loop_gateway();
  uint8_t compute_hop_limit(const SensorSample &sample) const;
  TelemetryEvent build_event_from_sample(const SensorSample &sample);
  bool flush_gateway_backlog(size_t max_messages);
  static uint64_t get_runtime_timestamp_ms();

  NodeConfig config_;
  MeshTransport mesh_transport_;
  SensorAdapters sensor_adapters_;
  MotionDetector motion_detector_;
  RingBufferStore ring_buffer_store_;
  MqttUplink mqtt_uplink_;
  unsigned long last_endpoint_publish_ms_;
  unsigned long last_relay_heartbeat_ms_;
  unsigned long last_gateway_flush_ms_;
  float last_heading_deg_;
  uint32_t event_sequence_;
};

