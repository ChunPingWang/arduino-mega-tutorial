/*
 * Lab 6 — 多序列埠橋接（Serial1，Mega 專屬）
 * 把 USB 收到的字轉送到 Serial1，反之亦然。體驗 Mega 的第二組硬體序列埠。
 * 接線：外接裝置（另一片 Arduino 或藍牙模組）接 Mega 的 TX1=18 / RX1=19。
 */
void setup() {
  Serial.begin(9600);    // USB
  Serial1.begin(9600);   // 第二組 UART（腳位 18/19）
}
void loop() {
  if (Serial.available())  Serial1.write(Serial.read());  // USB -> 裝置
  if (Serial1.available()) Serial.write(Serial1.read());  // 裝置 -> USB
}
