#include <WebServer.h>
#include <ArduinoJson.h>

WebServer server(80);
unsigned long lastCommandTime = 0;

void inputCommand() {
  JsonDocument data;

  deserializeJson(data, server.arg("plain"));
  String command = data["command"] | "stop";

  stopMotor();

  
  if (command == "forward") {
    lastCommandTime = millis();
    fw();
  }
  else if (command == "backward") {
    lastCommandTime = millis();
    bw();
  }
  else if (command == "left") {
    lastCommandTime = millis();
    sl();
  }
  else if (command == "right") {
    lastCommandTime = millis();
    sr();
  }
  else {
    stopMotor();
  }

  server.send(200, "text/plain", command);
}

void startRemote() {
  server.on("/command", HTTP_POST, inputCommand);
  server.begin();
}

void loopRemote() {
  server.handleClient();
  if (millis() - lastCommandTime >= 500) {
    stopMotor();
  }
}
