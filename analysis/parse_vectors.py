#!/usr/bin/env python3
"""解析 ATmega1280 的中斷向量表，列出有安裝真正處理常式的中斷。

用法:
    objcopy -I ihex sketch_backup.hex -O binary sketch_backup.bin
    python3 parse_vectors.py [sketch_backup.bin]

原理:
    ATmega1280 的向量表在 flash 開頭，57 個項目、每個 4 bytes（一道 jmp/rjmp）。
    未使用的中斷全部指向同一個 "bad interrupt" 位址；指向獨立位址的才是真正啟用的。
"""
import sys
from collections import Counter

NAMES = ["RESET","INT0","INT1","INT2","INT3","INT4","INT5","INT6","INT7",
    "PCINT0","PCINT1","PCINT2","WDT","TIMER2_COMPA","TIMER2_COMPB","TIMER2_OVF",
    "TIMER1_CAPT","TIMER1_COMPA","TIMER1_COMPB","TIMER1_COMPC","TIMER1_OVF",
    "TIMER0_COMPA","TIMER0_COMPB","TIMER0_OVF","SPI_STC","USART0_RX","USART0_UDRE",
    "USART0_TX","ANALOG_COMP","ADC","EE_READY","TIMER3_CAPT","TIMER3_COMPA",
    "TIMER3_COMPB","TIMER3_COMPC","TIMER3_OVF","USART1_RX","USART1_UDRE","USART1_TX",
    "TWI","SPM_READY","TIMER4_CAPT","TIMER4_COMPA","TIMER4_COMPB","TIMER4_COMPC",
    "TIMER4_OVF","TIMER5_CAPT","TIMER5_COMPA","TIMER5_COMPB","TIMER5_COMPC","TIMER5_OVF",
    "USART2_RX","USART2_UDRE","USART2_TX","USART3_RX","USART3_UDRE","USART3_TX"]


def target(b, i):
    """回傳第 i*4 位元組處 jmp/rjmp 的目標（byte 位址），無法解析則 None。"""
    w1 = b[i] | b[i + 1] << 8
    w2 = b[i + 2] | b[i + 3] << 8
    if (w1 & 0xFE0E) == 0x940C:            # jmp (32-bit)
        return w2 * 2
    if (w1 & 0xF000) == 0xC000:            # rjmp (relative)
        off = w1 & 0x0FFF
        if off >= 0x800:
            off -= 0x1000
        return i + 2 + off * 2
    return None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "sketch_backup.bin"
    b = open(path, "rb").read()
    targets = {nm: target(b, n * 4) for n, nm in enumerate(NAMES)}

    counts = Counter(v for v in targets.values() if v is not None)
    bad = counts.most_common(1)[0][0]
    print(f"default/bad-ISR handler @ 0x{bad:05X} (shared by {counts[bad]} vectors)\n")
    print("啟用的中斷（安裝了獨立處理常式）:")
    for nm, t in targets.items():
        if t is not None and t != bad and nm != "RESET":
            print(f"  {nm:14s} -> 0x{t:05X}")
    print(f"\nRESET -> 0x{targets['RESET']:05X}")


if __name__ == "__main__":
    main()
