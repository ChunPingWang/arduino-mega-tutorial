/*
 * Lab 4 — 互斥鎖（Mutex）保護共享資源
 * 兩個 task 都要用 Serial。用 mutex 確保訊息不交錯。
 * 重點：xSemaphoreCreateMutex / xSemaphoreTake / xSemaphoreGive。
 *
 * 試試看：把 take/give 註解掉，會看到兩個 task 的訊息互相打斷、變亂碼。
 */
#include <Arduino_FreeRTOS.h>
#include <semphr.h>

SemaphoreHandle_t xSerialMutex;

void printSafely(const __FlashStringHelper *who, int n) {
  xSemaphoreTake(xSerialMutex, portMAX_DELAY);   // 取得鎖
  Serial.print(who);
  Serial.print(F(" count="));
  Serial.println(n);
  xSemaphoreGive(xSerialMutex);                   // 釋放鎖
}

void TaskA(void *pvParameters) {
  int n = 0;
  for (;;) { printSafely(F("TaskA"), n++); vTaskDelay(pdMS_TO_TICKS(300)); }
}

void TaskB(void *pvParameters) {
  int n = 0;
  for (;;) { printSafely(F("TaskB"), n++); vTaskDelay(pdMS_TO_TICKS(370)); }
}

void setup() {
  Serial.begin(9600);
  xSerialMutex = xSemaphoreCreateMutex();
  xTaskCreate(TaskA, "A", 192, NULL, 1, NULL);
  xTaskCreate(TaskB, "B", 192, NULL, 1, NULL);
}

void loop() {}
