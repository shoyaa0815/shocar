void fw() {
  digitalWrite(motorL_F, HIGH);
  digitalWrite(motorR_F, HIGH);
}

void bw() {
  digitalWrite(motorL_B, HIGH);
  digitalWrite(motorR_B, HIGH);
}

void tr() {
  digitalWrite(motorL_B, HIGH);
  digitalWrite(motorR_B, LOW);
}

void tl() {
  digitalWrite(motorL_B, LOW);
  digitalWrite(motorR_B, HIGH);
}

void stop() {
  digitalWrite(motorL_F, LOW);
  digitalWrite(motorR_F, LOW);

  digitalWrite(motorL_B, LOW);
  digitalWrite(motorR_B, LOW);
}