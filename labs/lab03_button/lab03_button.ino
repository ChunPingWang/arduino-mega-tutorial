/*
 * Lab 3 — 按鈕讀取（digitalRead）
 * 讀取按鈕狀態並用內建 LED 顯示。
 * 接線：按鈕一腳接 pin 2，另一腳接 GND（內建上拉，按下為 LOW）。
 */
const int BTN = 2, LED = 13;
void setup() {
  pinMode(BTN, INPUT_PULLUP);
  pinMode(LED, OUTPUT);
}
void loop() {
  bool pressed = (digitalRead(BTN) == LOW);
  digitalWrite(LED, pressed ? HIGH : LOW);
}
