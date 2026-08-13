# Endpoint Pod V2 Spec

## Scope

This document defines the `ENDPOINT_POD` firmware behavior for irrigation pod
tracking when the real requirement is to know where the pods were left for
irrigation, not to reconstruct the full path during movement.

This spec applies to the Heltec Wireless Tracker endpoint role only.

## Core decisions

- Endpoint pods may sleep deeply.
- Endpoint pods are not treated as critical backbone routers.
- Endpoint pods may relay traffic only while awake.
- Fixed relays and the central gateway remain always-on.
- Intermediate movement points are ignored.
- `heartbeat` is published every `12 h`.
- After movement, publish as soon as GNSS fix is stable.
- Republish `5 min` later as a settle confirmation.
- If no GNSS fix is obtained after movement, publish
  `motion_detected_no_fix` with the last known point marked `stale=true`.
- `heading` is only trusted after the pod has stopped and stabilized.
- IMU temperature is ignored for now.
- `battery_mv` is always included in outbound endpoint events.

## Hardware assumptions

- MCU/radio/GNSS platform: Heltec Wireless Tracker V1.1
- IMU + magnetometer: `ICM-20948`
- IMU interface: `I2C`
- Wake source: `ICM-20948` motion interrupt
- GNSS remains the source of final position and UTC resync

## Important board note

Do not use `GPIO45` or `GPIO46` for the `ICM-20948` interrupt on the Heltec
Wireless Tracker variant. In the current board definition they are already used
 for I2C:

- `GPIO45 = SDA`
- `GPIO46 = SCL`

The interrupt pin must remain configurable and be assigned later.

## Behavioral goal

The endpoint should tell the system:

- the pod was moved
- the pod ended up here
- the pod is still here five minutes later
- the pod has not checked in for too long if only stale position is available

The endpoint should not attempt to provide a full breadcrumb trail during
movement.

## State machine

### `SLEEP_STATIONARY`

Deep sleep baseline state.

Wake sources:

- timer wake for `heartbeat`
- `ICM-20948` motion interrupt

Behavior:

- radio unavailable while sleeping
- no relay responsibility while sleeping

### `WAKE_HEARTBEAT`

Timer-based wake for periodic check-in.

Behavior:

- power up required rails
- bring up GNSS
- obtain a short GNSS fix attempt
- read battery voltage
- if fix becomes valid and stable, publish `heartbeat`
- otherwise publish `heartbeat_no_fix` with `stale=true`
- return to sleep

### `WAKE_MOTION`

Wake on IMU interrupt.

Behavior:

- record that movement has started
- do not publish immediately
- do not send intermediate points

### `WAIT_SETTLE`

Movement is considered ongoing until the pod is quiet long enough.

Defaults:

- motion start threshold: `0.2 g`
- motion end: `120 s` without movement

Behavior:

- ignore intermediate GNSS points
- keep the node awake
- wait until the pod is stationary long enough to trust the final state

### `ACQUIRE_FINAL_FIX`

After settle, obtain the final position.

Behavior:

- attempt GNSS until stable fix or timeout
- read battery voltage
- read heading from the `ICM-20948` only after settle

Outcomes:

- stable fix: go to `PUBLISH_FINAL`
- timeout without fix: go to `PUBLISH_MOTION_NO_FIX`

### `PUBLISH_FINAL`

Publish final stable post-move position.

Event:

- `publish_reason = POST_MOVE_FIX`

Behavior:

- include final stable GNSS point
- include `heading_deg` only if `heading_valid=true`
- include `battery_mv`
- arm a delayed confirmation for `5 min`

### `SETTLE_CONFIRM`

Republish after five minutes if the pod is still stationary.

Event:

- `publish_reason = SETTLE_CONFIRM`

Behavior:

- re-read battery voltage
- optionally re-check GNSS fix quality
- re-read heading if available
- publish confirmation
- return to sleep

### `PUBLISH_MOTION_NO_FIX`

Movement occurred, but GNSS never became stable in time.

Event:

- `publish_reason = MOTION_DETECTED_NO_FIX`

Behavior:

- publish last known good location
- set `stale=true`
- set `fix=false`
- include `battery_mv`
- set `heading_valid=false`
- return to sleep

## Timing defaults

- `heartbeat_interval_sec = 43200`
- `settle_confirm_delay_sec = 300`
- `motion_start_threshold_g = 0.2`
- `motion_end_quiet_sec = 120`
- `gnss_fix_timeout_sec = 600`

The GNSS timeout remains configurable, but `10 min` is the recommended starting
default.

## Stable fix definition

The endpoint should only trust a final point when:

- GNSS fix is valid
- speed is near zero
- the pod is already in `WAIT_SETTLE` complete state
- `HDOP` is under a configurable threshold
- the fix remains acceptable for `2-3` consecutive samples

Recommended initial rule:

- `hdop <= 2.5`
- `3` consecutive acceptable fixes

## Heading policy

Heading is a post-settle signal only.

Rules:

- never trust heading during movement
- do not publish heading immediately on motion wake
- compute heading only after the pod is stationary
- publish `heading_deg` only if `heading_valid=true`

Calibration status:

- magnetometer calibration is still TBD
- until calibration exists, heading may be computed internally but should be
  treated conservatively

Recommended v1.1 behavior:

- keep the field in the event contract
- allow `heading_valid=false`
- do not block position publish if heading is unavailable

## Time policy

The ESP32 RTC is sufficient to maintain wake intervals such as `12 h`, but it
is not an authoritative long-term UTC source.

Rules:

- use RTC/deep sleep timers for scheduling
- use GNSS to refresh UTC quality whenever a valid fix is available
- if waking without GNSS fix, timestamps may be based on RTC-derived time but
  should be considered lower quality

Recommended field:

- `time_quality = RTC | GNSS`

## Battery policy

`battery_mv` is required on every outbound endpoint event.

For the Heltec Wireless Tracker V1.1, reuse the board-level battery measurement
path before introducing custom calibration:

- `BATTERY_PIN = 1`
- `ADC_CTRL = 2`
- `ADC_MULTIPLIER = 4.9 * 1.045`

## Event types

Logical endpoint event types:

- `HEARTBEAT`
- `HEARTBEAT_NO_FIX`
- `POST_MOVE_FIX`
- `SETTLE_CONFIRM`
- `MOTION_DETECTED_NO_FIX`

## Event payload

Logical fields required in endpoint-originated events:

- `msg_id`
- `ts_utc_ms`
- `tracker_id`
- `line_id`
- `endpoint_role`
- `publish_reason`
- `lat`
- `long`
- `fix`
- `stale`
- `heading_deg`
- `heading_valid`
- `battery_mv`
- `hop_count`
- `time_quality`

Notes:

- `lat/long` may carry the last known position when `stale=true`
- `heading_deg` should be omitted or ignored when `heading_valid=false`

## Mesh transport expectations

For endpoint pods:

- while awake, they may relay traffic
- while sleeping, they are unavailable to the mesh
- therefore they must never be treated as required routing infrastructure

Routing must rely on:

- `RELAY_FIXED`
- `GATEWAY_CENTRAL`

not on sleeping endpoints.

## ICM-20948 integration expectations

Recommended library:

- `SparkFun ICM-20948 Arduino Library`

Required use:

- motion interrupt wake
- accelerometer-based motion thresholding
- magnetometer-backed heading after settle

Deferred:

- production-quality magnetometer calibration workflow
- temperature export

## Implementation notes

### Overlay/fork changes expected

1. Add `ICM-20948` dependency and wrapper isolated inside the irrigation overlay.
2. Add endpoint sleep/wake state machine distinct from gateway/relay behavior.
3. Add configurable `imu_interrupt_pin`.
4. Add wake reason handling:
   - timer
   - motion interrupt
5. Add final-fix acquisition logic.
6. Add stale fallback event when GNSS timeout expires.
7. Add delayed `5 min` settle confirmation publish.
8. Add battery measurement into endpoint event build path.
9. Add heading computation with `heading_valid`.
10. Keep mesh payload compact over LoRa.

### Non-goals for this iteration

- continuous path tracking while moving
- ambient temperature reporting
- mandatory heading calibration workflow before all other endpoint work
- using endpoint pods as always-available relays

## Risks

- GNSS timeout too short may overproduce `stale` events
- GNSS timeout too long may hurt battery life
- uncalibrated magnetometer may make heading misleading
- incorrect interrupt pin selection may break wake behavior
- relying on RTC-only timestamps too long without GNSS resync may drift UTC

## Recommended next implementation sequence

1. Add endpoint sleep/wake state machine skeleton.
2. Integrate `ICM-20948` motion interrupt wake.
3. Add movement settle logic.
4. Add post-settle GNSS final-fix publish.
5. Add stale fallback publish.
6. Add `5 min` settle confirmation.
7. Add battery measurement to outbound payload.
8. Add heading computation with conservative `heading_valid`.
