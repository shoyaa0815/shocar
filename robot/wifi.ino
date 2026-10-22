#include <WiFi.h>
#include "robot_config.h"

void set_wifi() {
  WiFi.begin(wifi_name, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print("wait ");
  }

  Serial.println("connect wifi");
  Serial.println(WiFi.localIP());
}