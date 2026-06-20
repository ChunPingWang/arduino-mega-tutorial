# Arduino Mega × FreeRTOS 新手實驗

這個分支（branch `freertos`）收錄一系列 **FreeRTOS** 入門實驗，讓初學者在 Arduino Mega
（本教學實測為 ATmega1280）上學會「多工（multitasking）」的觀念：task、延遲、優先權、
佇列（queue）、互斥鎖（mutex）與訊號量（semaphore）。

> 為什麼用 Mega 學 FreeRTOS？Mega 腳位多、4 組硬體序列埠，方便同時觀察多個 task 的行為。
> 但要注意 **ATmega1280 只有 8 KB SRAM**，task 數量與 stack 大小要省著用。

---

## 0. 什麼是 FreeRTOS？（一分鐘版）

平常的 Arduino 程式只有一個 `loop()`，所有事情得排隊輪流做。
**FreeRTOS** 是一個小型即時作業系統，讓你把程式拆成多個 **task（任務）**，
由排程器（scheduler）依**優先權**自動切換，看起來像「同時」在跑。

| 傳統 Arduino | FreeRTOS |
|---|---|
| 一個 `loop()` 包山包海 | 多個獨立 `task`，各做各的 |
| `delay()` 會卡住全部 | `vTaskDelay()` 只讓出該 task，別人照跑 |
| 自己用 `millis()` 排程 | 排程器幫你切換 |

---

## 1. 安裝 FreeRTOS 函式庫

本系列使用 Phillip Stevens 維護的 **Arduino_FreeRTOS**（專為 AVR 移植）。

**Arduino IDE：**
`工具 → 管理程式庫 → 搜尋 "FreeRTOS" → 安裝 "FreeRTOS by Phillip Stevens"`

**arduino-cli：**

```bash
arduino-cli lib install "FreeRTOS"
```

關鍵觀念：**安裝後不需要自己呼叫 `vTaskStartScheduler()`**。
這個函式庫會在 `setup()` 結束後自動啟動排程器；你只要在 `setup()` 裡用
`xTaskCreate()` 建立 task，然後把 `loop()` 留空即可（`loop()` 會變成 idle task）。

---

## 2. 上傳方式（與主分支相同）

```bash
# 1280 板（本教學實測板）
arduino-cli compile -b arduino:avr:mega:cpu=atmega1280 lab01_two_tasks
arduino-cli upload  -b arduino:avr:mega:cpu=atmega1280 -p /dev/ttyUSB0 lab01_two_tasks

# 2560 板改成 cpu=atmega2560
```

序列埠監看一律用 **9600**（本系列範例的 `Serial.begin(9600)`）：

```bash
arduino-cli monitor -p /dev/ttyUSB0 -c baudrate=9600
```

---

## 實驗總覽

| Lab | 主題 | 學到的 FreeRTOS API |
|---|---|---|
| [Lab 1](lab01_two_tasks/) | 兩個獨立閃爍 task | `xTaskCreate`, `vTaskDelay` |
| [Lab 2](lab02_priorities/) | 優先權與搶佔 | task priority, `taskYIELD` |
| [Lab 3](lab03_queue/) | 用佇列在 task 間傳資料 | `xQueueCreate/Send/Receive` |
| [Lab 4](lab04_mutex/) | 用互斥鎖保護共享資源 | `xSemaphoreCreateMutex`, `Take/Give` |
| [Lab 5](lab05_semaphore_isr/) | 中斷喚醒 task | binary semaphore, `...FromISR` |

每個 Lab 資料夾內都有可直接上傳的 `.ino`，下面是各 Lab 的重點說明。

---

### Lab 1 — 兩個獨立閃爍 task

**目標**：建立兩個 task，分別讓內建 LED（pin 13）與另一顆 LED（pin 12）以**不同頻率**閃爍。
體會「兩件事同時在做」。

**重點**：
- `xTaskCreate(fn, "名稱", stack字數, 參數, 優先權, handle)`
- `vTaskDelay(pdMS_TO_TICKS(ms))`：只讓出自己，**不會卡住另一個 task**。

**預期結果**：兩顆 LED 各自以不同節奏閃爍，互不影響。
若你改用一般 `delay()`，就會發現另一個 task 被卡住——這正是 `vTaskDelay` 的價值。

---

### Lab 2 — 優先權與搶佔（preemption）

**目標**：建立高、低優先權兩個 task，觀察高優先權 task 如何「搶佔」CPU。

**重點**：
- `xTaskCreate` 最後第二個參數是**優先權**（數字越大越高）。
- 高優先權 task 只要就緒（ready），排程器會立刻切過去執行。
- `taskYIELD()` 主動讓出 CPU。

**預期結果**：序列埠會看到高優先權 task 的訊息明顯較密集／優先出現。

---

### Lab 3 — 佇列（Queue）傳資料

**目標**：一個「生產者」task 每秒讀一次類比值（A0），透過 **queue** 丟給「消費者」task 印出。
這是 task 間傳資料**最安全**的方式。

**重點**：
- `xQueueCreate(長度, 每筆大小)`
- `xQueueSend(q, &data, 等待時間)` / `xQueueReceive(q, &buf, 等待時間)`
- 消費者用 `portMAX_DELAY` 等待，沒資料時自動睡著、不浪費 CPU。

**預期結果**：序列埠每秒印出一筆 A0 的讀值，且生產與消費完全解耦。

---

### Lab 4 — 互斥鎖（Mutex）保護共享資源

**目標**：兩個 task 都要印字到同一個 `Serial`。不加保護時訊息會交錯亂掉；
用 **mutex** 確保一次只有一個 task 在用 Serial。

**重點**：
- `xSemaphoreCreateMutex()`
- 用前 `xSemaphoreTake(mutex, portMAX_DELAY)`，用完 `xSemaphoreGive(mutex)`。

**預期結果**：加上 mutex 後，兩個 task 的整行訊息不再彼此打斷／交錯。

---

### Lab 5 — 中斷喚醒 task（Binary Semaphore + ISR）

**目標**：按鈕按下時觸發外部中斷，中斷裡用 **binary semaphore** 喚醒一個 task 去處理
（把耗時工作搬出中斷，是即時系統的標準做法）。

**重點**：
- `xSemaphoreCreateBinary()`
- 中斷服務常式（ISR）裡用 `xSemaphoreGiveFromISR(sem, &xHigherPriorityTaskWoken)`。
- task 端 `xSemaphoreTake(sem, portMAX_DELAY)` 平時睡著，被中斷喚醒才動作。

**接線**：按鈕一腳接 pin 2（Mega 的外部中斷腳 INT0），另一腳接 GND。

**預期結果**：每按一次按鈕，序列埠就印出一行「Button pressed!」，且中斷本身極短。

---

## 常見問題

- **程式一上傳就當機／重開機**：多半是 **stack 不夠**。AVR 的 stack 單位是「字（word）」，
  會用到 `Serial`／`sprintf` 的 task 建議 `stack ≥ 128`。
- **SRAM 不足**：ATmega1280 只有 8 KB。task 越多、stack 越大越吃 RAM，
  編譯時留意 IDE 顯示的 RAM 使用率。
- **`vTaskDelay(0)`**：不會延遲，只會讓出一次 CPU；要延遲請用 `pdMS_TO_TICKS(ms)`。
- **tick 解析度**：本函式庫預設 tick 約 15 ms，太短的延遲會被進位。
