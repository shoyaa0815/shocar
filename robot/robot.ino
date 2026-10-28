const int motorF_L = 13;
const int motorF_R = 14;

const int motorB_L = 26;
const int motorB_R = 27;

const int button = 25;

bool start = false;

void setup() {
  Serial.begin(115200);
  Serial.println("boot");

  pinMode(motorF_L, OUTPUT);
  pinMode(motorF_R, OUTPUT);

  pinMode(motorB_L, OUTPUT);
  pinMode(motorB_R, OUTPUT);

  pinMode(button, INPUT_PULLUP);

  stopMotor();
  Serial.println("motor ok");

  setServo();
  Serial.println("servo ok");

  // set_wifi();

  // startRemote();

}

void loop() {
  // if(digitalRead(button) == 0) {
  //   start = true;
  // }

  // if(start) {
  //   loopRemote();
  // }

  // loopRemote();

  servo1(60);    // ไป 60 องศา
  Serial.println("60");
  delay(1000);   // รอ 1 วินาที

  servo1(120);   // ไป 120 องศา
  Serial.println("120");
  delay(1000);

}