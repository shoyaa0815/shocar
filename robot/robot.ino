const int motorF_L = 13;
const int motorF_R = 14;

const int motorB_L = 26;
const int motorB_R = 27;

const int button1 = 25;
const int button2 = 33;


bool start = false;

void setup() {
  Serial.begin(115200);

  pinMode(motorF_L, OUTPUT);
  pinMode(motorF_R, OUTPUT);
  pinMode(motorB_L, OUTPUT);
  pinMode(motorB_R, OUTPUT);

  pinMode(button1, INPUT_PULLUP);
  pinMode(button2, INPUT_PULLUP);

  stopMotor();
  setServo();
  set_wifi();
  startRemote();

}

void loop() {
  // if(digitalRead(button) == 0) {
  //   start = true;
  // }

  // if(start) {
  //   loopRemote();
  // }

  loopRemote();

  if(digitalRead(button1) == 0) {
    servo1(180);
  }else if (digitalRead(button2) == 0) {
    servo1(0);
  }
}
