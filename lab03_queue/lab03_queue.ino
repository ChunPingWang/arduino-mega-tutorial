/*
 * Lab 3 — 佇列（Queue）在 task 間傳資料
 * 生產者每秒讀一次 A0，透過 queue 傳給消費者印出。
 * 重點：xQueueCreate / xQueueSend / xQueueReceive（task 間最安全的傳資料方式）。
 */
#include <Arduino_FreeRTOS.h>
#include <queue.h>

QueueHandle_t xQueue;   // 佇列：存放 A0 的讀值（int）

void TaskProducer(void *pvParameters) {
  for (;;) {
    int value = analogRead(A0);
    xQueueSend(xQueue, &value, portMAX_DELAY);   // 滿了就等
    vTaskDelay(pdMS_TO_TICKS(1000));
  }
}

void TaskConsumer(void *pvParameters) {
  int received;
  for (;;) {
    // 沒資料就睡著（不浪費 CPU），有資料才醒來
    if (xQueueReceive(xQueue, &received, portMAX_DELAY) == pdPASS) {
      Serial.print(F("A0 = "));
      Serial.println(received);
    }
  }
}

void setup() {
  Serial.begin(9600);
  xQueue = xQueueCreate(5, sizeof(int));   // 長度 5、每筆 sizeof(int)
  if (xQueue != NULL) {
    xTaskCreate(TaskProducer, "Prod", 128, NULL, 1, NULL);
    xTaskCreate(TaskConsumer, "Cons", 192, NULL, 2, NULL);
  }
}

void loop() {}
