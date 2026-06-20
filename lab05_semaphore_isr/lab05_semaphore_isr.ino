/*
 * Lab 5 — 中斷喚醒 task（Binary Semaphore + ISR）
 * 按鈕（pin 2 = INT0）按下時，ISR 用 binary semaphore 喚醒一個 task 去處理。
 * 把耗時工作搬出中斷，是即時系統的標準做法。
 * 重點：xSemaphoreCreateBinary / xSemaphoreGiveFromISR / portYIELD_FROM_ISR。
 *
 * 接線：按鈕一腳接 pin 2，另一腳接 GND（使用內建上拉，按下為 LOW）。
 */
#include <Arduino_FreeRTOS.h>
#include <semphr.h>

SemaphoreHandle_t xButtonSem;
const uint8_t BTN = 2;

void onButtonISR() {
  BaseType_t xHigherPriorityTaskWoken = pdFALSE;
  // 在 ISR 裡只做這件事：喚醒等待的 task
  xSemaphoreGiveFromISR(xButtonSem, &xHigherPriorityTaskWoken);
  // 若喚醒了更高優先權的 task，立刻切換過去
  if (xHigherPriorityTaskWoken) taskYIELD();
}

void TaskHandleButton(void *pvParameters) {
  for (;;) {
    // 平時睡著，被中斷 give 之後才醒來
    if (xSemaphoreTake(xButtonSem, portMAX_DELAY) == pdTRUE) {
      Serial.println(F("Button pressed!"));
      vTaskDelay(pdMS_TO_TICKS(200));   // 簡單去彈跳
    }
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(BTN, INPUT_PULLUP);
  xButtonSem = xSemaphoreCreateBinary();
  attachInterrupt(digitalPinToInterrupt(BTN), onButtonISR, FALLING);
  xTaskCreate(TaskHandleButton, "Btn", 192, NULL, 2, NULL);
}

void loop() {}
