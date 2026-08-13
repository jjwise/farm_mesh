#pragma once

#include <Arduino.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "node_config.h"

class MqttUplink {
 public:
  MqttUplink();
  bool begin(const NodeConfig &config);
  void loop();
  bool publish_payload(const String &topic, const String &payload, uint8_t qos_level);
  bool is_connected();

 private:
  bool ensure_wifi_connected();
  bool ensure_mqtt_connected();

  NodeConfig config_;
  WiFiClientSecure secure_client_;
  PubSubClient mqtt_client_;
  unsigned long last_wifi_attempt_ms_;
  unsigned long last_mqtt_attempt_ms_;
};
