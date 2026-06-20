/*
 * Lab 5 — PWM 呼吸燈（analogWrite）
 * 用 PWM 讓 LED 由暗到亮漸變（呼吸效果）。
 * 接線：LED 經 220Ω 電阻接 pin 9（PWM 腳），另一端接 GND。
 */
const int LED = 9;               // 必須是 PWM 腳（~ 記號）
void setup() {
  pinMode(LED, OUTPUT);
}
void loop() {
  for (int b = 0; b <= 255; b++) { analogWrite(LED, b); delay(5); }
  for (int b = 255; b >= 0; b--) { analogWrite(LED, b); delay(5); }
}
