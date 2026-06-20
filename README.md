# Arduino Mega 板子檢測方法

本文件記錄如何在 Linux 上檢測一塊連接到電腦的 Arduino Mega 板子：包含辨識硬體、確認晶片型號、讀取保險絲（fuse），以及監看序列埠（Serial）輸出的完整流程與指令。

> 本次實測的板子為 **原版 Arduino Mega（ATmega1280）**，採用 FTDI FT232R 作為 USB 轉序列晶片。

> 📌 **分支說明**：本 `main` 分支放的是基礎教學（板子檢測、Flash 韌體分析、版本差異、
> 以及 blink／序列埠／按鈕／類比／PWM 等基礎 Labs）。
> 想學多工（task、queue、mutex、semaphore）請切到 **`freertos` 分支**，那裡有 FreeRTOS 進階實驗。

---

## 0. 環境需求

- Linux 系統（本文以 Fedora 為例）
- `avrdude`（燒錄／讀取 AVR 晶片）
- `python3`（用於監看序列埠）
- 對序列埠裝置（`/dev/ttyUSB0`）的讀寫權限

---

## 1. 辨識 USB 硬體

先確認板子是用哪一顆 USB 轉序列晶片，這決定了後續要用的通訊協定與鮑率（baud rate）。

```bash
# 列出 USB 裝置，過濾常見的 Arduino／序列晶片
lsusb | grep -i -E "arduino|atmel|ftdi|ch340|serial|2341|1a86"
```

常見對應關係：

| USB ID | 晶片 | 常見板子 |
|---|---|---|
| `2341:xxxx` | ATmega16U2 | 原版 Arduino Uno / Mega 2560 |
| `0403:6001` | FTDI FT232R | 原版 Arduino Mega 1280 / 舊版相容板 |
| `1a86:7523` | CH340 | 相容板（clone） |

本次實測結果：

```
Bus 003 Device 007: ID 0403:6001 Future Technology Devices International, Ltd FT232 Serial (UART) IC
```

→ 是 **FTDI 晶片**，代表這是 FTDI 架構的 Mega 板。

---

## 2. 找出序列埠裝置節點

```bash
# 列出有穩定名稱的序列裝置
ls -l /dev/serial/by-id/

# 直接找 ttyUSB / ttyACM 節點
ls /dev/tty* | grep -E "ttyUSB|ttyACM"
```

本次結果：

```
usb-FTDI_FT232R_USB_UART_A600edEX-if00-port0 -> ../../ttyUSB0
```

→ 裝置節點為 **`/dev/ttyUSB0`**。

> 提示：FTDI 板會是 `ttyUSB*`；具備 16U2 的原生 USB 板（如 Mega 2560）通常是 `ttyACM*`。

---

## 3. 取得序列埠存取權限

序列埠通常屬於 `root:dialout`，權限為 `crw-rw----`。若使用者不在 `dialout` 群組，將無法存取。

```bash
# 確認權限與群組
ls -l /dev/ttyUSB0
id -Gn        # 看看有沒有 dialout
```

授權方式二擇一：

```bash
# 方法 A：暫時授權（重新插拔後失效，適合臨時檢測）
sudo chmod a+rw /dev/ttyUSB0

# 方法 B：永久授權（需登出再登入才生效，建議做法）
sudo usermod -aG dialout $USER
```

---

## 4. 確認晶片型號（讀取 signature）

不同 Mega 用不同的 bootloader 協定與鮑率，需要逐一嘗試：

| 板子 | programmer | 鮑率 | 對應指令參數 |
|---|---|---|---|
| Mega 2560（16U2） | `wiring` | 115200 | `-c wiring -p atmega2560 -b 115200` |
| Mega 1280（FTDI） | `arduino`（STK500v1） | 57600 | `-c arduino -p atmega1280 -b 57600` |

實測「**Mega 1280 + FTDI**」可成功同步的指令：

```bash
avrdude -c arduino -p atmega1280 -P /dev/ttyUSB0 -b 57600 -v
```

成功時會看到 device signature：

```
Device signature = 1E 97 03 (ATmega1280)
```

Signature 對照表：

| Signature | 晶片 |
|---|---|
| `1E 97 03` | ATmega1280 |
| `1E 98 01` | ATmega2560 |
| `1E 95 0F` | ATmega328P（Uno） |

> 注意：若用錯協定（例如 FTDI 板硬套 `wiring`/115200），會出現 `stk500v2_getsync() failed` 的 timeout，這代表**協定／鮑率不對**，並非板子壞掉。

---

## 5. 讀取保險絲與 lock bit（唯讀）

```bash
avrdude -c arduino -p atmega1280 -P /dev/ttyUSB0 -b 57600 \
  -U signature:r:-:h \
  -U lfuse:r:-:h -U hfuse:r:-:h -U efuse:r:-:h -U lock:r:-:h
```

> ⚠️ **限制**：透過 Arduino bootloader 只能讀取 signature／flash／EEPROM，**讀不到真正的 fuse 值**（會回傳 `0x00`）。若要讀正確的 fuse，需改用 ISP 燒錄器（接 6-pin ICSP 排針）。

---

## 6. 監看序列埠輸出（看板子在做什麼）

開啟序列埠會觸發 DTR 重置，板子會重新啟動，因此可以捕捉到開機時的輸出。
但**鮑率未知**，需逐一嘗試常見值並判斷哪個鮑率輸出的是「可讀文字」。

### 6.1 用 stty + 讀取做鮑率掃描

```bash
for baud in 9600 115200 57600 38400 19200 4800; do
  stty -F /dev/ttyUSB0 $baud raw -echo
  timeout 3 head -c 4096 /dev/ttyUSB0 > cap_$baud.bin
  echo "baud=$baud bytes=$(wc -c < cap_$baud.bin)"
done
```

### 6.2 用 Python 強制 DTR 重置並監聽

當單純開啟無法觸發重置時，可用 ioctl 主動送出 DTR 重置脈衝再監聽：

```python
import os, time, fcntl, termios, struct, select
PORT = "/dev/ttyUSB0"; TIOCM_DTR = 0x002
baud, secs = 115200, 8
B = {9600: termios.B9600, 57600: termios.B57600, 115200: termios.B115200}

fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd)
a[0] = termios.IGNPAR; a[1] = 0; a[3] = 0
a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
a[4] = a[5] = B[baud]
termios.tcsetattr(fd, termios.TCSANOW, a)

# DTR 重置脈衝
fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack('I', TIOCM_DTR)); time.sleep(0.15)
fcntl.ioctl(fd, termios.TIOCMBIC, struct.pack('I', TIOCM_DTR)); time.sleep(0.05)

buf = bytearray(); end = time.time() + secs
while time.time() < end:
    r, _, _ = select.select([fd], [], [], 0.3)
    if r:
        try: buf += os.read(fd, 4096)
        except OSError: pass
os.close(fd)
print(len(buf), "bytes:", bytes(buf[:200]))
```

### 6.3 判讀結果

- **有可讀文字** → 該鮑率正確，即可看到板子實際輸出。
- **完全沒有資料（0 bytes）** → 代表載入的程式**沒有透過 USB 序列埠（UART0）輸出**。
  這不一定是故障，可能是：
  - 程式只驅動 LED／繼電器／馬達／伺服等輸出，不做 `Serial.print`
  - 程式只讀感測器並就地動作，不輸出記錄
  - 程式用的是其他序列埠（`Serial1/2/3`，腳位 14–19）或 I²C／SPI，USB 看不到
  - 是最簡單的程式（如 Blink）或沒有有意義的程式

> 本次實測：在所有常見鮑率下都收到 **0 bytes**，連送出 `?`、`help`、`AT` 等指令也無回應，
> 但 bootloader 能正常同步 → 結論是**該程式不透過 USB 序列埠通訊**。

---

## 7. 進一步：把程式從 Flash 讀出來分析（選用）

若序列埠看不出板子在做什麼，可把 flash 內容讀出再分析字串／反組譯（唯讀、安全）：

```bash
# 讀出 flash 到 hex 檔
avrdude -c arduino -p atmega1280 -P /dev/ttyUSB0 -b 57600 \
  -U flash:r:sketch_backup.hex:i

# 從中找出可讀字串（常能看出用了哪些函式庫／功能）
avr-objcopy -I ihex sketch_backup.hex -O binary sketch_backup.bin
strings sketch_backup.bin
```

---

## 8. Flash 程式實際分析範例

本次把整顆 128 KB flash 讀出後做的分析，示範如何在「沒有任何可讀字串」的情況下，
仍能判斷板子在做什麼。

### 8.1 量測實際用量

```bash
# 將 hex 轉為 binary（系統若無 avr-objcopy，可用一般 objcopy）
objcopy -I ihex sketch_backup.hex -O binary sketch_backup.bin

# 統計非 0xFF（已燒錄）位元組、找出程式最高位址
python3 -c "b=open('sketch_backup.bin','rb').read(); \
print('used', sum(1 for x in b if x!=0xFF), 'of', len(b))"
```

實測結果：

| 區段 | 內容 | 大小 |
|---|---|---|
| 應用程式 `0x00000–0x01307` | 使用者 sketch | 約 4.8 KB |
| Bootloader `0x1F000–0x1FF15` | ATmegaBOOT | 約 3.7 KB |
| 其餘 | 未燒錄（`0xFF`） | — |

整顆 flash 只用了 **約 6%**。唯一可讀字串位於 bootloader 區：
`ATmegaBOOT / Arduino Mega - (C) Arduino LLC - 090930`（日期 2009-09-30），
應用程式區則**完全沒有可讀字串**（與序列埠靜默的觀察一致）。

### 8.2 解析中斷向量表（關鍵技巧）

沒有字串時，可解析 **中斷向量表（interrupt vector table）** 來推斷用到哪些周邊。
ATmega1280 的向量表在 flash 開頭，共 57 個項目、每個 4 bytes（一道 `jmp`）。
未使用的中斷會全部指向同一個「bad interrupt」位址；指向**獨立位址**的才是真正啟用的。

```bash
# 解析向量表，列出有安裝真正處理常式的中斷
python3 parse_vectors.py   # 見 analysis/ 目錄
```

實測啟用的中斷：

| 中斷向量 | 意義 |
|---|---|
| `TIMER0_OVF` | Arduino 核心的 `millis()` / `delay()` 計時器（每個 sketch 都有） |
| `USART0_RX` | Serial（USB）接收中斷 |
| `USART1_RX` | Serial1 接收中斷 |
| `USART2_RX` | Serial2 接收中斷 |
| `USART3_RX` | Serial3 接收中斷 |

### 8.3 向量表的初步推測（後被反組譯推翻）

僅看向量表，會以為「四個 USART RX 都啟用 → 是多埠序列橋接」。
**但這是誤判**：Arduino Mega 核心把 `Serial / Serial1 / Serial2 / Serial3` 都宣告為全域物件，
四個 RX ISR 在連結階段一律會被連進來、向量自然都是非預設值——**即使程式只用到 `Serial`**。
所以「向量非預設」只代表 ISR 被連結，不代表 `begin()` 真的被呼叫。

> 教訓：向量表能縮小範圍，但要 **100% 確認邏輯，必須反組譯**。

### 8.4 反組譯確認真正邏輯

本環境無 `avr-objdump`，因此自製了一支極簡 AVR 反組譯器
（`analysis/avr_dis.py`，先用向量表的 `jmp` 驗證正確性）。從 `RESET` 一路追：

```
RESET(0x206) → C 執行期初始化 → call main()(0xBB0)
main: call init() → call setup()(0x2AC) → for(;;) loop()(0x260)
```

反組譯 `setup()` 與 `loop()` 並比對輔助函式後還原出的程式碼：

```c
void setup() {
  for (int p = 2; p < 54; p++) pinMode(p, OUTPUT);  // 腳位 2..53 設為輸出
  Serial.begin(9600);                               // 有開，但從未使用
}
void loop() {
  for (int p = 2; p < 54; p++) {
    digitalWrite(p, HIGH);   // 0x4DA = digitalWrite（用 lpm 查 PROGMEM 腳位表）
    delay(400);              // 0x384 = delay（cli 後讀 timer0_millis @ 0x0212）
    digitalWrite(p, LOW);
  }
}
```

迴圈邊界直接來自 `.data` 初始值（flash `0x0D42`）：起點 `[0x200]=2`、數量 `[0x202]=0x34=52`。

**真正結論**：這是一支 **循序點燈（running light）的輸出測試** ——
把腳位 2–53 依序點亮 400ms 再熄滅，逐一輪巡 52 支腳。
`Serial.begin(9600)` 只是開了埠卻從未 `print`，正好解釋了序列埠為何全程靜默。

> 重點方法論：**字串 → 向量表 → 反組譯**，由淺入深。本案例正是最佳教材：
> 向量表給了「四埠橋接」的**假象**，唯有反組譯才揭露它其實是「循序點燈測試」。
> 結論可疑時，務必往下一層（反組譯）求證，不要停在推測。

---

## 9. 新版 Arduino Mega 有什麼不同？

本次實測的是最早期的 **Mega 1280**。市面上「新版」一般指 **Mega 2560**（尤其是 R3）。
主要差異如下：

### 9.1 核心晶片：ATmega1280 → ATmega2560

| 項目 | Mega 1280（舊） | Mega 2560（新） |
|---|---|---|
| Flash | 128 KB | **256 KB** |
| SRAM | 8 KB | 8 KB（相同） |
| EEPROM | 4 KB | 4 KB（相同） |
| Signature | `1E 97 03` | `1E 98 01` |
| 數位 / 類比腳位 | 54 / 16 | 54 / 16（相同） |

→ 最大實質差異是 **flash 加倍到 256 KB**，可放更大的程式。

### 9.2 USB 轉序列晶片：FTDI → ATmega8U2 / 16U2

| 版本 | USB 晶片 | 裝置節點 |
|---|---|---|
| Mega 1280 / 早期 | FTDI FT232RL | `/dev/ttyUSB*` |
| Mega 2560 R1 / R2 | ATmega8U2 | `/dev/ttyACM*` |
| Mega 2560 R3 | **ATmega16U2** | `/dev/ttyACM*` |

→ 新版改用 Atmel 自家 MCU 做 USB（原生 USB CDC），不再依賴 FTDI 驅動；
16U2 韌體可重刷，能模擬鍵盤／滑鼠等 USB 裝置。

### 9.3 Bootloader 協定與鮑率

| 版本 | programmer | 鮑率 | avrdude 參數 |
|---|---|---|---|
| Mega 1280（舊） | STK500v1（`arduino`） | **57600** | `-c arduino -p atmega1280 -b 57600` |
| Mega 2560（新） | STK500v2（`wiring`） | **115200** | `-c wiring -p atmega2560 -b 115200` |

→ 這也是為什麼本次一開始用 `wiring`/115200 會 timeout：協定與鮑率對新版才正確。

### 9.4 R3 改版的接腳新增

Mega 2560 **R3** 相對於更早版本，額外新增：

- **SDA / SCL** 兩支 I²C 專用腳（移到 AREF 旁，與 Uno R3 對齊，方便 shield 共用）
- **IOREF** 腳：讓 shield 偵測板子工作電壓（5V / 3.3V）
- 多一支 **GND** 與一支保留腳
- 改良的自動重置（auto-reset）電路

### 9.5 一句話總結

> 新版（Mega 2560 R3）相對舊版（Mega 1280）：**flash 加倍（256 KB）、USB 改用可重刷的
> 16U2（走 `ttyACM`、原生 USB）、bootloader 改為 `wiring`/115200、並新增 SDA/SCL 與 IOREF 腳**；
> CPU 速度、腳位數量、SRAM/EEPROM 容量則維持不變。

---

## 10. 新手實驗（Labs）

以下實驗專為初學者設計，由淺入深。每個實驗都包含：**目標 → 接線 → 程式碼 → 上傳 → 預期結果**。

### 上傳前準備

**用 Arduino IDE：**

1. `工具 → 開發板 → Arduino AVR Boards → Arduino Mega or Mega 2560`
2. 本次實測是舊版 1280，需設定 `工具 → 處理器 → ATmega1280`（2560 板則選 ATmega2560）
3. `工具 → 連接埠 → /dev/ttyUSB0`
4. 按上傳（→）

**用 arduino-cli（命令列）：**

```bash
# 安裝後先抓核心
arduino-cli core install arduino:avr

# 編譯 + 上傳（1280 板用此 FQBN；2560 板改 cpu=atmega2560）
arduino-cli compile -b arduino:avr:mega:cpu=atmega1280 lab01_blink
arduino-cli upload  -b arduino:avr:mega:cpu=atmega1280 -p /dev/ttyUSB0 lab01_blink
```

> 註：序列埠監看的鮑率由程式中的 `Serial.begin(n)` 決定，與上傳鮑率（1280 為 57600）無關。

---

### Lab 1 — 內建 LED 閃爍（Blink）

**目標**：點亮並閃爍板上內建 LED（接在 pin 13）。不需任何外接零件。

```cpp
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);   // Mega 的 LED_BUILTIN = 13
}
void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
  delay(500);
}
```

**預期結果**：板上 L 燈每 0.5 秒閃一次。改 `delay` 數值可變快或變慢。

---

### Lab 2 — 序列埠印出 Hello（Serial）

**目標**：透過 USB 序列埠印字到電腦。學會 `Serial.print` 與序列埠監看。

```cpp
void setup() {
  Serial.begin(9600);
}
void loop() {
  Serial.println("Hello Arduino Mega!");
  delay(1000);
}
```

**上傳後**用以下任一方式監看（鮑率設 9600）：

```bash
arduino-cli monitor -p /dev/ttyUSB0 -c baudrate=9600
# 或本文件第 6 節的 Python 監聽腳本
```

**預期結果**：每秒出現一行 `Hello Arduino Mega!`。

---

### Lab 3 — 按鈕讀取（digitalRead）

**目標**：讀取按鈕狀態並用內建 LED 顯示。

**接線**：按鈕一腳接 pin 2，另一腳接 GND（使用內建上拉電阻，按下為 LOW）。

```cpp
const int BTN = 2, LED = 13;
void setup() {
  pinMode(BTN, INPUT_PULLUP);
  pinMode(LED, OUTPUT);
}
void loop() {
  bool pressed = (digitalRead(BTN) == LOW);
  digitalWrite(LED, pressed ? HIGH : LOW);
}
```

**預期結果**：按住按鈕時 LED 亮，放開即滅。

---

### Lab 4 — 類比讀取（analogRead）

**目標**：讀電位器（可變電阻）的電壓，印出 0–1023 的數值。

**接線**：電位器兩端接 5V 與 GND，中間（滑動端）接 A0。

```cpp
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
```

**預期結果**：轉動電位器，序列埠數值在 0–1023、電壓在 0–5V 之間變化。

---

### Lab 5 — PWM 呼吸燈（analogWrite）

**目標**：用 PWM 讓 LED 由暗到亮漸變（呼吸效果）。

**接線**：LED 經 220Ω 電阻接 pin 9（Mega 的 PWM 腳之一），另一端接 GND。

```cpp
const int LED = 9;               // 必須是 PWM 腳（~ 記號）
void setup() {
  pinMode(LED, OUTPUT);
}
void loop() {
  for (int b = 0; b <= 255; b++) { analogWrite(LED, b); delay(5); }
  for (int b = 255; b >= 0; b--) { analogWrite(LED, b); delay(5); }
}
```

**預期結果**：LED 平滑地由暗變亮再變暗，像呼吸一樣。

---

### Lab 6 — 多序列埠橋接（Serial1，Mega 專屬）

**目標**：體驗 Mega 才有的 **第二組硬體序列埠**（共 4 組）。把 USB 收到的字轉送到 Serial1，反之亦然——這就是「序列橋接」的基本寫法（注意：第 8 節實測的板子**並非**橋接，而是循序點燈）。

**接線**：外接裝置（如另一片 Arduino 或藍牙模組）接 Mega 的 **TX1=18 / RX1=19**。

```cpp
void setup() {
  Serial.begin(9600);    // USB
  Serial1.begin(9600);   // 第二組 UART（腳位 18/19）
}
void loop() {
  if (Serial.available())  Serial1.write(Serial.read());  // USB -> 裝置
  if (Serial1.available()) Serial.write(Serial1.read());  // 裝置 -> USB
}
```

**預期結果**：從電腦序列埠輸入的字會送到接在 Serial1 的裝置；裝置回傳的字會顯示在電腦上。

> 進階：Mega 還有 `Serial2`（16/17）與 `Serial3`（14/15）。把四個都 `begin()` 起來，
> 即可做出「四埠序列閘道」。（提醒：第 8 節向量表一度誤判實測板子是這種閘道，
> 反組譯後才確認其實只是循序點燈——詳見 8.3／8.4。）

---

## 附錄：本次實測板子摘要

| 項目 | 值 |
|---|---|
| 板子 | 原版 Arduino Mega（ATmega1280） |
| MCU | ATmega1280, 8-bit AVR @ 16 MHz |
| Signature | `1E 97 03` |
| USB 晶片 | FTDI FT232R（`0403:6001`，序號 `A600edEX`） |
| 裝置節點 | `/dev/ttyUSB0` |
| Bootloader | STK500v1（`arduino`）@ 57600 baud |
| Flash / SRAM / EEPROM | 128 KB / 8 KB / 4 KB |
| 數位 I/O | 54 腳（15 路 PWM） |
| 類比輸入 | 16 路（10-bit ADC） |
| 硬體序列埠 | 4 組（Serial, Serial1–3） |
| 序列埠輸出狀態 | 靜默（程式未透過 USB 序列埠通訊） |
