#include <WiFi.h>

const char*ssid = "wifi name";
const char*password = "password";

void set_wifi() {
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print("wait ");
  }

  Serial.println("connect wifi");
  Serial.println(WiFi.localIP());
}