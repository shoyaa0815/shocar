void fw() {
  digitalWrite(motorF_L, 1);
  digitalWrite(motorF_R, 1);

  digitalWrite(motorB_L, 0);
  digitalWrite(motorB_R, 0);
}

void bw() {
  digitalWrite(motorB_L, 1);
  digitalWrite(motorB_R, 1);

  digitalWrite(motorF_L, 0);
  digitalWrite(motorF_R, 0);

}

void sr() {
  digitalWrite(motorF_L, 1);
  digitalWrite(motorB_R, 1);
}

void sl() {
  digitalWrite(motorB_L, 1);
  digitalWrite(motorF_R, 1);
}

void stopMotor() {
  digitalWrite(motorF_L, 0);
  digitalWrite(motorF_R, 0);

  digitalWrite(motorB_L, 0);
  digitalWrite(motorB_R, 0);
}
