/*
 * Lab 1 — 內建 LED 閃爍（Blink）
 * 點亮並閃爍板上內建 LED（pin 13）。不需任何外接零件。
 */
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);   // Mega 的 LED_BUILTIN = 13
}
void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
  delay(500);
}
