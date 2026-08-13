#pragma once

#include "node_config.h"

class MotionDetector {
 public:
  MotionDetector();
  void update(float accel_rms_g, float gps_speed_mps, float heading_delta_deg, bool gps_fix);
  MotionState motion_state() const;
  bool transition_to_moving() const;

 private:
  MotionState motion_state_;
  bool transition_to_moving_;
  unsigned long last_motion_ms_;
};

