# FreeRTOS Labs 驗證紀錄

驗證環境：實機 **Arduino Mega（ATmega1280）**，`/dev/ttyUSB0`，序列埠 9600。
編譯：`arduino-cli compile -b arduino:avr:mega:cpu=atmega1280`，
函式庫 FreeRTOS 11.1.0，AVR 核心 1.8.8。

| Lab | 編譯 | 燒錄 | 執行驗證 | 說明 |
|---|---|---|---|---|
| lab01_two_tasks | ✅ 7738B | ✅ | ⚠️ 需目視 | 無序列輸出，須看 LED |
| lab02_priorities | ✅ 8208B | ✅ | ✅ 已驗證 | 序列實測 `[HIGH]` 約為 `[low]` 的 2.5 倍 |
| lab03_queue | ✅ 9454B | ✅ | ✅ 已驗證 | 序列每秒一筆 `A0 = NNN` |
| lab04_mutex | ✅ 10444B | ✅ | ✅ 已驗證 | 序列行不交錯，mutex 生效 |
| lab05_semaphore_isr | ✅ 10480B | ✅ | ⚠️ 需按鈕 | 無按鈕時正確靜默（task 阻塞中） |

## 已實測的執行證據

**lab02_priorities**（證明 FreeRTOS 多工 + 優先權在實機運作）：

```
[HIGH] working
    [low] working
[HIGH] working
[HIGH] working
    [low] working
[HIGH] working
...
```
`[HIGH]`（延遲 200ms）出現頻率約為 `[low]`（延遲 500ms）的 2.5 倍，與設計相符。

**lab03_queue**：

```
A0 = 434
A0 = 400
A0 = 389
```
生產者每秒讀 A0 → queue → 消費者印出，解耦正常。

**lab04_mutex**：

```
TaskA count=0
TaskB count=0
TaskA count=1
TaskB count=1
```
兩 task 共用 Serial，整行不被打斷，mutex 保護成功。

## 無法自動驗證者：標註與測試方法

- **lab01_two_tasks（需目視）**：本機無法讀取 LED 電位。
  *測試方法*：pin 13 內建 LED 應以 100ms、pin 12 外接 LED 應以 350ms 各自閃爍，
  兩者頻率不同且互不影響，即代表兩 task 並行成功。

- **lab05_semaphore_isr（需實體按鈕）**：本機無法按下實體按鈕。
  已驗證「無輸入時正確靜默」（task 阻塞於 `xSemaphoreTake`，未空轉）。
  *測試方法*：按鈕一腳接 pin 2、另一腳接 GND；每按一次，序列埠應印出一行
  `Button pressed!`。

## 還原開發板

實測後，板子目前載有最後燒錄的 lab。原本的「循序點燈」韌體已備份於
`analysis/sketch_backup.hex`（主分支），可用以下指令還原：

```bash
avrdude -c arduino -p atmega1280 -P /dev/ttyUSB0 -b 57600 \
  -U flash:w:analysis/sketch_backup.hex:i
```
