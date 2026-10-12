void forward() {
  digitalWrite(motorL_F, HIGH);
  digitalWrite(motorR_F, HIGH);
}

void backward() {
  digitalWrite(motorL_B, HIGH);
  digitalWrite(motorR_B, HIGH);
}

void turnright() {
  digitalWrite(motorL_B, HIGH);
  digitalWrite(motorR_B, LOW);
}

void turnleft() {
  digitalWrite(motorL_B, LOW);
  digitalWrite(motorR_B, HIGH);
}
