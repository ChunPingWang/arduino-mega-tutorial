# 新手 Labs 驗證紀錄

驗證環境：實機 **Arduino Mega（ATmega1280）**，`/dev/ttyUSB0`，序列埠 9600。
編譯／燒錄：`arduino-cli ... -b arduino:avr:mega:cpu=atmega1280`（AVR 核心 1.8.8）。

| Lab | 編譯 | 燒錄 | 執行驗證 | 說明 |
|---|---|---|---|---|
| lab01_blink | ✅ 1460B | ✅ | ⚠️ 需目視 | 無序列輸出，須看 pin 13 LED |
| lab02_serial_hello | ✅ 1944B | ✅ | ✅ 已驗證 | 序列每秒 `Hello Arduino Mega!` |
| lab03_button | ✅ 1442B | ✅ | ⚠️ 需按鈕 | 須接 pin2 按鈕並目視 LED |
| lab04_analog_read | ✅ 3748B | ✅ | ✅ 已驗證 | 序列印出讀值與電壓 |
| lab05_pwm_breathing | ✅ 1898B | ✅ | ⚠️ 需目視 | 須接 pin9 LED 看呼吸效果 |
| lab06_serial_bridge | ✅ 2068B | ✅ | ⚠️ 需外接裝置 | 須在 Serial1(18/19) 接裝置 |

## 已實測的執行證據

**lab02_serial_hello**：

```
Hello Arduino Mega!
Hello Arduino Mega!
Hello Arduino Mega!
```

**lab04_analog_read**（A0 浮接時的讀值，轉動電位器會變化）：

```
419  2.05 V
402  1.96 V
396  1.94 V
```

## 無法自動驗證者：標註與測試方法

本機只能讀 USB 序列埠，無法讀取 LED 電位、按下實體按鈕或外接第二裝置，
因此以下各項已編譯並燒錄成功，但「行為」需依下列方式人工驗證：

- **lab01_blink（需目視）**：pin 13 內建 LED 應每 0.5 秒閃一次。
- **lab03_button（需按鈕）**：按鈕一腳接 pin 2、另一腳接 GND；按下時 pin 13 LED 亮，放開即滅。
- **lab05_pwm_breathing（需目視）**：LED 經 220Ω 接 pin 9；應看到由暗漸亮再漸暗的呼吸效果。
- **lab06_serial_bridge（需外接裝置）**：在 TX1=18 / RX1=19 接另一片 Arduino 或藍牙模組；
  從電腦序列埠輸入的字會送到該裝置，裝置回傳的字會顯示在電腦上。
  *快速測法*：把 pin 18(TX1) 與 pin 19(RX1) 用杜邦線直接短接做迴路（loopback），
  則從 USB 打字會原封不動回顯，即證明橋接路徑正常。

## 還原開發板

實測後，板子已**還原回原本的「循序點燈」韌體**（備份於 `analysis/sketch_backup.hex`）。
如需再次還原：

```bash
avrdude -c arduino -p atmega1280 -P /dev/ttyUSB0 -b 57600 \
  -U flash:w:analysis/sketch_backup.hex:i
```
