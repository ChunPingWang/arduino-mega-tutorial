/*
 * Lab 2 — 序列埠印出 Hello（Serial）
 * 透過 USB 序列埠每秒印一行字到電腦。監看鮑率設 9600。
 */
void setup() {
  Serial.begin(9600);
}
void loop() {
  Serial.println("Hello Arduino Mega!");
  delay(1000);
}
