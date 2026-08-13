#include "mqtt_uplink.h"

namespace {
constexpr unsigned long k_wifi_retry_ms = 10000;
constexpr unsigned long k_mqtt_retry_ms = 5000;
}  // namespace

MqttUplink::MqttUplink()
    : mqtt_client_(secure_client_), last_wifi_attempt_ms_(0), last_mqtt_attempt_ms_(0) {}

bool MqttUplink::begin(const NodeConfig &config) {
  config_ = config;
  WiFi.mode(WIFI_STA);
  secure_client_.setInsecure();

  if (config_.mqtt_host.isEmpty()) {
    Serial.println("[mqtt] mqtt host is empty; gateway uplink disabled");
    return false;
  }

  mqtt_client_.setServer(config_.mqtt_host.c_str(), config_.mqtt_port);
  return true;
}

void MqttUplink::loop() {
  if (!ensure_wifi_connected()) {
    return;
  }
  ensure_mqtt_connected();
  mqtt_client_.loop();
}

bool MqttUplink::publish_payload(const String &topic, const String &payload, uint8_t qos_level) {
  (void)qos_level;
  if (!ensure_wifi_connected()) {
    return false;
  }
  if (!ensure_mqtt_connected()) {
    return false;
  }

  // PubSubClient supports QoS 0 publish; idempotent msg_id in backend handles duplicates.
  const bool published = mqtt_client_.publish(topic.c_str(), payload.c_str(), false);
  if (!published) {
    Serial.println("[mqtt] publish failed");
  }
  return published;
}

bool MqttUplink::is_connected() {
  return mqtt_client_.connected();
}

bool MqttUplink::ensure_wifi_connected() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  if (millis() - last_wifi_attempt_ms_ < k_wifi_retry_ms) {
    return false;
  }
  last_wifi_attempt_ms_ = millis();

  if (config_.wifi_ssid.isEmpty()) {
    Serial.println("[wifi] wifi ssid not configured");
    return false;
  }

  Serial.printf("[wifi] connecting to ssid=%s\n", config_.wifi_ssid.c_str());
  WiFi.begin(config_.wifi_ssid.c_str(), config_.wifi_password.c_str());
  return false;
}

bool MqttUplink::ensure_mqtt_connected() {
  if (mqtt_client_.connected()) {
    return true;
  }

  if (millis() - last_mqtt_attempt_ms_ < k_mqtt_retry_ms) {
    return false;
  }
  last_mqtt_attempt_ms_ = millis();

  Serial.printf("[mqtt] connecting host=%s port=%u\n", config_.mqtt_host.c_str(), config_.mqtt_port);
  const bool connected = mqtt_client_.connect(
      config_.mqtt_client_id.c_str(), config_.mqtt_username.c_str(), config_.mqtt_password.c_str());

  if (!connected) {
    Serial.printf("[mqtt] connect failed rc=%d\n", mqtt_client_.state());
  }
  return connected;
}
