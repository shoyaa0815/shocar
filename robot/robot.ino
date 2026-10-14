const int motorL_F = 26;
const int motorR_F = 27;

const int motorL_B = 13;
const int motorR_B = 14;

void setup() {
  pinMode(motorL_F, OUTPUT);
  pinMode(motorR_F, OUTPUT);

  pinMode(motorL_B, OUTPUT);
  pinMode(motorR_B, OUTPUT);

}

void loop() {
  fw();
}
