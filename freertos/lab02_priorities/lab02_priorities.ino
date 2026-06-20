/*
 * Lab 2 — 優先權與搶佔（preemption）
 * 高優先權 task 一旦就緒就會搶佔 CPU。觀察序列埠訊息密度差異。
 * 重點：xTaskCreate 的 uxPriority 參數（數字越大越優先）。
 */
#include <Arduino_FreeRTOS.h>

void TaskHigh(void *pvParameters) {
  for (;;) {
    Serial.println(F("[HIGH] working"));
    vTaskDelay(pdMS_TO_TICKS(200));   // 讓出，否則低優先 task 永遠搶不到
  }
}

void TaskLow(void *pvParameters) {
  for (;;) {
    Serial.println(F("    [low] working"));
    vTaskDelay(pdMS_TO_TICKS(500));
  }
}

void setup() {
  Serial.begin(9600);
  // 優先權：HIGH = 2，LOW = 1
  xTaskCreate(TaskHigh, "High", 192, NULL, 2, NULL);
  xTaskCreate(TaskLow,  "Low",  192, NULL, 1, NULL);
}

void loop() {}
