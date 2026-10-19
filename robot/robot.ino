const int motorF_L = 13;
const int motorF_R = 14;

const int motorB_L = 26;
const int motorB_R = 27;

void setup() {
  stopMotor();
  setServo();
  
  Serial.begin(115200);
  set_wifi();

  pinMode(motorF_L, OUTPUT);
  pinMode(motorF_R, OUTPUT);

  pinMode(motorB_L, OUTPUT);
  pinMode(motorB_R, OUTPUT);

  startRemote();

}

void loop() {
  loopRemote();
}