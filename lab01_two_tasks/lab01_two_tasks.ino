/*
 * Lab 1 — 兩個獨立閃爍 task
 * 兩個 task 各自用不同頻率閃 LED，互不影響。
 * 重點：xTaskCreate、vTaskDelay（只讓出自己，不卡別人）。
 */
#include <Arduino_FreeRTOS.h>

void TaskBlink13(void *pvParameters) {   // 內建 LED，週期 200ms
  pinMode(13, OUTPUT);
  for (;;) {
    digitalWrite(13, HIGH);
    vTaskDelay(pdMS_TO_TICKS(100));
    digitalWrite(13, LOW);
    vTaskDelay(pdMS_TO_TICKS(100));
  }
}

void TaskBlink12(void *pvParameters) {   // 外接 LED，週期 700ms
  pinMode(12, OUTPUT);
  for (;;) {
    digitalWrite(12, HIGH);
    vTaskDelay(pdMS_TO_TICKS(350));
    digitalWrite(12, LOW);
    vTaskDelay(pdMS_TO_TICKS(350));
  }
}

void setup() {
  // 在 setup() 建立 task；排程器會在 setup() 結束後自動啟動。
  xTaskCreate(TaskBlink13, "Blink13", 128, NULL, 1, NULL);
  xTaskCreate(TaskBlink12, "Blink12", 128, NULL, 1, NULL);
}

void loop() {
  // 留空：loop() 會變成 idle task。
}
