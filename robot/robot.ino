const int motorF_L = 26;
const int motorF_R = 27;

const int motorB_L = 13;
const int motorB_R = 14;

void setup() {
  Serial.begin(115200);
  Serial.println("test code");
  set_wifi();

  pinMode(motorF_L, OUTPUT);
  pinMode(motorF_R, OUTPUT);

  pinMode(motorB_L, OUTPUT);
  pinMode(motorB_R, OUTPUT);

  stopMotor();
  startRemote();

}

void loop() {
  loopRemote();
}