#pragma once

/**
 * Project-level configuration defaults.
 *
 * Override these values at build time using `build_flags` in `platformio.ini`.
 * Keep credentials out of version control for real deployments.
 */

#ifndef PROJECT_FARM_ID
#define PROJECT_FARM_ID "farm_demo"
#endif

#ifndef PROJECT_LINE_ID
#define PROJECT_LINE_ID "line_demo_01"
#endif

#ifndef PROJECT_TRACKER_ID
#define PROJECT_TRACKER_ID "tracker_demo"
#endif

#ifndef PROJECT_ENDPOINT_ROLE
#define PROJECT_ENDPOINT_ROLE "ENDPOINT_A"
#endif

#ifndef PROJECT_WIFI_SSID
#define PROJECT_WIFI_SSID ""
#endif

#ifndef PROJECT_WIFI_PASSWORD
#define PROJECT_WIFI_PASSWORD ""
#endif

#ifndef PROJECT_MQTT_HOST
#define PROJECT_MQTT_HOST ""
#endif

#ifndef PROJECT_MQTT_PORT
#define PROJECT_MQTT_PORT 8883
#endif

#ifndef PROJECT_MQTT_USERNAME
#define PROJECT_MQTT_USERNAME ""
#endif

#ifndef PROJECT_MQTT_PASSWORD
#define PROJECT_MQTT_PASSWORD ""
#endif

#ifndef PROJECT_STATIONARY_INTERVAL_SEC
#define PROJECT_STATIONARY_INTERVAL_SEC 3600
#endif

#ifndef PROJECT_MOVING_INTERVAL_SEC
#define PROJECT_MOVING_INTERVAL_SEC 10
#endif

#ifndef PROJECT_MOVING_HOLD_SEC
#define PROJECT_MOVING_HOLD_SEC 120
#endif

#ifndef PROJECT_GATEWAY_BUFFER_MAX_RECORDS
#define PROJECT_GATEWAY_BUFFER_MAX_RECORDS 12000
#endif
