/*
 * Lab 4 — 類比讀取（analogRead）
 * 讀電位器（可變電阻）的電壓，印出 0–1023 的數值與換算電壓。
 * 接線：電位器兩端接 5V 與 GND，中間（滑動端）接 A0。
 */
void setup() {
  Serial.begin(9600);
}
void loop() {
  int v = analogRead(A0);          // 0..1023（10-bit ADC）
  float volt = v * 5.0 / 1023.0;
  Serial.print(v);
  Serial.print("  ");
  Serial.print(volt, 2);
  Serial.println(" V");
  delay(200);
}
