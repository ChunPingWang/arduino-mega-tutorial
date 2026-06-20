# Arduino Mega 板子檢測方法

本文件記錄如何在 Linux 上檢測一塊連接到電腦的 Arduino Mega 板子：包含辨識硬體、確認晶片型號、讀取保險絲（fuse），以及監看序列埠（Serial）輸出的完整流程與指令。

> 本次實測的板子為 **原版 Arduino Mega（ATmega1280）**，採用 FTDI FT232R 作為 USB 轉序列晶片。

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
