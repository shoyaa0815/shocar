const int motorF_L = 13;
const int motorF_R = 14;

const int motorB_L = 26;
const int motorB_R = 27;

const int button = 25;

bool start = false;

void setup() {
  pinMode(motorF_L, OUTPUT);
  pinMode(motorF_R, OUTPUT);

  pinMode(motorB_L, OUTPUT);
  pinMode(motorB_R, OUTPUT);

  pinMode(button, INPUT_PULLUP);

  stopMotor();

  setServo();
  
  Serial.begin(115200);
  set_wifi();

  startRemote();

}

void loop() {
  if(digitalRead(button) == 0) {
    start = true;
  }

  if(start) {
    loopRemote();
  }
}