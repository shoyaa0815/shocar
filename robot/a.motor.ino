void fw() {
  digitalWrite(motorF_L, HIGH);
  digitalWrite(motorF_R, HIGH);

  digitalWrite(motorB_L, LOW);
  digitalWrite(motorB_R, LOW);
}

void bw() {
  digitalWrite(motorB_L, HIGH);
  digitalWrite(motorB_R, HIGH);

  digitalWrite(motorF_L, LOW);
  digitalWrite(motorF_R, LOW);

}

void tr() {
  digitalWrite(motorF_L, HIGH);
  delay(300);
  digitalWrite(motorB_R, HIGH);
  delay(300);
}

void tl() {
  digitalWrite(motorB_L, HIGH);
  delay(300);
  digitalWrite(motorF_R, HIGH);
  delay(300);
}

void stopMotor() {
  digitalWrite(motorF_L, LOW);
  digitalWrite(motorF_R, LOW);

  digitalWrite(motorB_L, LOW);
  digitalWrite(motorB_R, LOW);
}
