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

void sr() {
  digitalWrite(motorF_L, HIGH);
  digitalWrite(motorB_R, HIGH);
}

void sl() {
  digitalWrite(motorB_L, HIGH);
  digitalWrite(motorF_R, HIGH);
}

void stopMotor() {
  digitalWrite(motorF_L, LOW);
  digitalWrite(motorF_R, LOW);

  digitalWrite(motorB_L, LOW);
  digitalWrite(motorB_R, LOW);
}
