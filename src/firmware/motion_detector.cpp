#include "motion_detector.h"

#include <Arduino.h>

namespace {
constexpr float k_accel_threshold_g = 0.06f;
constexpr float k_speed_threshold_mps = 0.40f;
constexpr float k_heading_threshold_deg = 12.0f;
constexpr unsigned long k_motion_hold_ms = 120000;
}  // namespace

MotionDetector::MotionDetector()
    : motion_state_(MotionState::STATIONARY), transition_to_moving_(false), last_motion_ms_(0) {}

void MotionDetector::update(float accel_rms_g, float gps_speed_mps, float heading_delta_deg, bool gps_fix) {
  transition_to_moving_ = false;

  const bool accel_motion = accel_rms_g >= k_accel_threshold_g;
  const bool speed_motion = gps_fix && gps_speed_mps >= k_speed_threshold_mps;
  const bool heading_motion = gps_fix && gps_speed_mps > 0.2f && heading_delta_deg >= k_heading_threshold_deg;
  const bool motion_now = accel_motion || speed_motion || heading_motion;

  if (motion_now) {
    last_motion_ms_ = millis();
    if (motion_state_ != MotionState::MOVING) {
      motion_state_ = MotionState::MOVING;
      transition_to_moving_ = true;
    }
    return;
  }

  if (motion_state_ == MotionState::MOVING && millis() - last_motion_ms_ > k_motion_hold_ms) {
    motion_state_ = MotionState::STATIONARY;
  }
}

MotionState MotionDetector::motion_state() const {
  return motion_state_;
}

bool MotionDetector::transition_to_moving() const {
  return transition_to_moving_;
}

