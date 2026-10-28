#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm(0x40);

void servo1(int angle) {
  angle = constrain(angle, 0, 180);

  int pulse = map(angle, 0, 180, 1000, 2000);

  pwm.writeMicroseconds(0, pulse);
}

void setServo() {
  Wire.begin(21, 22);
  Serial.println("wire ok");

  if (!pwm.begin()) {
    Serial.println("ไม่เจอ PCA9685");
    while (true) {
      delay(1000);
    }
  }

  pwm.setPWMFreq(50);
  delay(10);

  // servo1(0);
}
