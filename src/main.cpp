#include "firmware/app_runtime.h"

AppRuntime app_runtime;

void setup() {
  app_runtime.setup();
}

void loop() {
  app_runtime.loop();
}
