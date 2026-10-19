#include <ESP32Servo.h>

Servo servo1;
Servo servo2;
Servo servo3;
Servo servo4;

void setServo() {
  servo1.attach(16);
  servo2.attach(17);
  servo3.attach(18);
  servo4.attach(19);

}