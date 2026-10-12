const int motorL_F = 10;
const int motorR_F = 11;

const int motorL_B = 12;
const int motorR_B = 13;

const int motorR_arm = 14;
const int motorL_arm = 15;

void setup() {
  pinMode(motorL_F, OUTPUT);
  pinMode(motorR_F, OUTPUT);

  pinMode(motorL_B, OUTPUT);
  pinMode(motorR_B, OUTPUT);

  pinMode(motorR_arm, OUTPUT);
  pinMode(motorL_arm, OUTPUT);

}

void loop() {
  forward();
}
