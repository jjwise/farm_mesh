#include "sensor_adapters.h"

#include <Arduino.h>

SensorAdapters::SensorAdapters()
    : start_ms_(0), simulated_heading_(90.0f), simulated_latitude_(-33.865143), simulated_longitude_(151.2099) {}

bool SensorAdapters::begin(const NodeConfig &config) {
  config_ = config;
  start_ms_ = millis();
  return true;
}

SensorSample SensorAdapters::read_sample() {
  const unsigned long elapsed_sec = (millis() - start_ms_) / 1000UL;

  // Simulation profile: movement bursts to exercise motion-based telemetry.
  const bool is_moving_window = (elapsed_sec % 900UL) < 120UL;
  const float speed_mps = is_moving_window ? 0.85f : 0.02f;
  const float accel_rms_g = is_moving_window ? 0.09f : 0.01f;
  const bool gps_fix = true;
  const float hdop = is_moving_window ? 1.2f : 0.9f;

  if (is_moving_window) {
    simulated_heading_ += 0.7f;
    if (simulated_heading_ >= 360.0f) {
      simulated_heading_ -= 360.0f;
    }
    simulated_latitude_ += 0.0000025;
    simulated_longitude_ += 0.0000010;
  }

  SensorSample sample;
  sample.gps_fix = gps_fix;
  sample.latitude = simulated_latitude_;
  sample.longitude = simulated_longitude_;
  sample.hdop = hdop;
  sample.speed_mps = speed_mps;
  sample.heading_deg = simulated_heading_;
  sample.accel_rms_g = accel_rms_g;
  sample.battery_mv = static_cast<uint16_t>(3900 - ((elapsed_sec / 3600UL) % 300UL));
  return sample;
}

