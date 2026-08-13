#pragma once

#include "node_config.h"

struct SensorSample {
  bool gps_fix;
  double latitude;
  double longitude;
  float hdop;
  float speed_mps;
  float heading_deg;
  float accel_rms_g;
  uint16_t battery_mv;
};

class SensorAdapters {
 public:
  SensorAdapters();
  bool begin(const NodeConfig &config);
  SensorSample read_sample();

 private:
  NodeConfig config_;
  unsigned long start_ms_;
  float simulated_heading_;
  double simulated_latitude_;
  double simulated_longitude_;
};

