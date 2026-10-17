#include <WebServer.h>
#include <ArduinoJson.h>

WebServer server(80);

void inputCommand() {
  JsonDocument data;

  deserializeJson(data, server.arg("plain"));
  String command = data["command"] | "stop";

  stopMotor();

  
  if (command == "forward") {
    fw();
  }
  else if (command == "backward") {
    bw();
  }
  else if (command == "left") {
    tl();
  }
  else if (command == "right") {
    tr();
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
}
