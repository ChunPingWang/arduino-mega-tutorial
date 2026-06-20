#!/usr/bin/env python3
"""Minimal AVR disassembler — enough to read Arduino sketch logic.

用法: python3 avr_dis.py sketch_backup.bin <start_byte> <end_byte>
位址以 byte 表示（AVR 指令位址習慣用 word，本工具顯示 byte 與 word 兩者）。

涵蓋 Arduino sketch 常見指令；無法辨識者顯示為 .dw 0xXXXX。
ATmega1280 擴充 I/O 暫存器以名稱標註（UDRn / UCSRnA 等）。
"""
import sys

# ATmega1280 重要暫存器（data-space 位址）
SFR = {
    0xC0: "UCSR0A", 0xC1: "UCSR0B", 0xC2: "UCSR0C", 0xC6: "UDR0",
    0xC8: "UCSR1A", 0xC9: "UCSR1B", 0xCA: "UCSR1C", 0xCE: "UDR1",
    0xD0: "UCSR2A", 0xD1: "UCSR2B", 0xD2: "UCSR2C", 0xD6: "UDR2",
    0x130: "UCSR3A", 0x131: "UCSR3B", 0x132: "UCSR3C", 0x136: "UDR3",
}
def sfr(a): return SFR.get(a, f"0x{a:04X}")


def sext(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def disasm_word(w, w2, addr_word):
    """回傳 (text, words_consumed)."""
    # 32-bit 指令先處理
    if (w & 0xFE0E) == 0x940C:  # JMP
        k = ((w >> 4 & 0x1F) << 17) | ((w & 1) << 16) | w2
        return f"jmp  0x{k*2:05X}", 2
    if (w & 0xFE0E) == 0x940E:  # CALL
        k = ((w >> 4 & 0x1F) << 17) | ((w & 1) << 16) | w2
        return f"call 0x{k*2:05X}", 2
    if (w & 0xFE0F) == 0x9000:  # LDS Rd,k
        d = (w >> 4) & 0x1F
        return f"lds  r{d}, {sfr(w2)}", 2
    if (w & 0xFE0F) == 0x9200:  # STS k,Rr
        d = (w >> 4) & 0x1F
        return f"sts  {sfr(w2)}, r{d}", 2

    # 16-bit
    if w == 0x0000: return "nop", 1
    if w == 0x9508: return "ret", 1
    if w == 0x9518: return "reti", 1
    if w == 0x9409: return "ijmp", 1
    if w == 0x9509: return "icall", 1
    if w == 0x9478: return "sei", 1
    if w == 0x94F8: return "cli", 1

    if (w & 0xF000) == 0xC000:  # RJMP
        return f"rjmp 0x{(addr_word+1+sext(w&0xFFF,12))*2:05X}", 1
    if (w & 0xF000) == 0xD000:  # RCALL
        return f"rcall 0x{(addr_word+1+sext(w&0xFFF,12))*2:05X}", 1
    if (w & 0xF000) == 0xE000:  # LDI
        d = ((w >> 4) & 0xF) + 16
        k = ((w >> 4) & 0xF0) | (w & 0xF)
        return f"ldi  r{d}, 0x{k:02X}", 1
    if (w & 0xF000) == 0x3000:  # CPI
        d = ((w >> 4) & 0xF) + 16
        k = ((w >> 4) & 0xF0) | (w & 0xF)
        return f"cpi  r{d}, 0x{k:02X}", 1
    for op, mn in ((0x4000, "sbci"), (0x5000, "subi"), (0x6000, "ori"), (0x7000, "andi")):
        if (w & 0xF000) == op:
            d = ((w >> 4) & 0xF) + 16
            k = ((w >> 4) & 0xF0) | (w & 0xF)
            return f"{mn} r{d}, 0x{k:02X}", 1

    # branches BRBS/BRBC
    if (w & 0xFC00) == 0xF000 or (w & 0xFC00) == 0xF400:
        s = w & 7
        k = sext((w >> 3) & 0x7F, 7)
        set_ = (w & 0x0400) == 0
        names = {0: "cs/lo", 1: "eq", 2: "mi", 3: "vs", 4: "lt", 5: "hs", 6: "ts", 7: "ie"}
        names_c = {0: "cc/sh", 1: "ne", 2: "pl", 3: "vc", 4: "ge", 5: "tc", 6: "tc", 7: "id"}
        mn = "br" + (names[s] if set_ else names_c[s])
        return f"{mn} 0x{(addr_word+1+k)*2:05X}", 1

    # register-register ALU (6-bit opcode, d/r 5-bit)
    def dr():
        d = (w >> 4) & 0x1F
        r = ((w >> 5) & 0x10) | (w & 0xF)
        return d, r
    rr_ops = {0x1C00: "adc", 0x0C00: "add", 0x2000: "and", 0x1400: "cp",
              0x0400: "cpc", 0x1000: "cpse", 0x2400: "eor", 0x2C00: "mov",
              0x2800: "or", 0x0800: "sbc", 0x1800: "sub", 0x9C00: "mul"}
    for op, mn in rr_ops.items():
        if (w & 0xFC00) == op:
            d, r = dr()
            if mn == "eor" and d == r: return f"clr  r{d}", 1
            if mn == "add" and d == r: return f"lsl  r{d}", 1
            return f"{mn}  r{d}, r{r}", 1

    if (w & 0xFF00) == 0x0100:  # MOVW
        return f"movw r{((w>>4)&0xF)*2}, r{(w&0xF)*2}", 1
    if (w & 0xFF00) == 0x9600:  # ADIW
        d = ((w >> 4) & 3) * 2 + 24
        k = ((w >> 2) & 0x30) | (w & 0xF)
        return f"adiw r{d}, 0x{k:02X}", 1
    if (w & 0xFF00) == 0x9700:  # SBIW
        d = ((w >> 4) & 3) * 2 + 24
        k = ((w >> 2) & 0x30) | (w & 0xF)
        return f"sbiw r{d}, 0x{k:02X}", 1

    # IN / OUT
    if (w & 0xF800) == 0xB000:
        d = (w >> 4) & 0x1F
        a = ((w >> 5) & 0x30) | (w & 0xF)
        return f"in   r{d}, 0x{a:02X}", 1
    if (w & 0xF800) == 0xB800:
        d = (w >> 4) & 0x1F
        a = ((w >> 5) & 0x30) | (w & 0xF)
        return f"out  0x{a:02X}, r{d}", 1

    # PUSH/POP
    if (w & 0xFE0F) == 0x920F: return f"push r{(w>>4)&0x1F}", 1
    if (w & 0xFE0F) == 0x900F: return f"pop  r{(w>>4)&0x1F}", 1

    # single-reg ops
    sr = {0x9400: "com", 0x9401: "neg", 0x9403: "inc", 0x940A: "dec",
          0x9405: "asr", 0x9406: "lsr", 0x9407: "ror", 0x9402: "swap"}
    for code, mn in sr.items():
        if (w & 0xFE0F) == code:
            return f"{mn}  r{(w>>4)&0x1F}", 1

    # SBIC/SBIS/SBI/CBI (I/O bit)
    if (w & 0xFF00) == 0x9800: return f"cbi  0x{(w>>3)&0x1F:02X}, {w&7}", 1
    if (w & 0xFF00) == 0x9A00: return f"sbi  0x{(w>>3)&0x1F:02X}, {w&7}", 1
    if (w & 0xFF00) == 0x9900: return f"sbic 0x{(w>>3)&0x1F:02X}, {w&7}", 1
    if (w & 0xFF00) == 0x9B00: return f"sbis 0x{(w>>3)&0x1F:02X}, {w&7}", 1
    # SBRC/SBRS (reg bit)
    if (w & 0xFE08) == 0xFC00: return f"sbrc r{(w>>4)&0x1F}, {w&7}", 1
    if (w & 0xFE08) == 0xFE00: return f"sbrs r{(w>>4)&0x1F}, {w&7}", 1

    # LD/ST X,Y,Z (subset) + LDD/STD
    if (w & 0xFE0F) == 0x900C: return f"ld   r{(w>>4)&0x1F}, X", 1
    if (w & 0xFE0F) == 0x900D: return f"ld   r{(w>>4)&0x1F}, X+", 1
    if (w & 0xFE0F) == 0x900E: return f"ld   r{(w>>4)&0x1F}, -X", 1
    if (w & 0xFE0F) == 0x8008: return f"ld   r{(w>>4)&0x1F}, Y", 1
    if (w & 0xFE0F) == 0x9009: return f"ld   r{(w>>4)&0x1F}, Y+", 1
    if (w & 0xFE0F) == 0x8000: return f"ld   r{(w>>4)&0x1F}, Z", 1
    if (w & 0xFE0F) == 0x9001: return f"ld   r{(w>>4)&0x1F}, Z+", 1
    if (w & 0xFE0F) == 0x920C: return f"st   X, r{(w>>4)&0x1F}", 1
    if (w & 0xFE0F) == 0x920D: return f"st   X+, r{(w>>4)&0x1F}", 1
    if (w & 0xFE0F) == 0x8208: return f"st   Y, r{(w>>4)&0x1F}", 1
    if (w & 0xFE0F) == 0x9209: return f"st   Y+, r{(w>>4)&0x1F}", 1
    if (w & 0xFE0F) == 0x8200: return f"st   Z, r{(w>>4)&0x1F}", 1
    if (w & 0xFE0F) == 0x9201: return f"st   Z+, r{(w>>4)&0x1F}", 1
    # LDD/STD with displacement (Y=bit3 clear/set pattern)
    if (w & 0xD208) == 0x8008:  # LDD Rd, Y+q
        d = (w >> 4) & 0x1F
        q = (w & 7) | ((w >> 7) & 0x18) | ((w >> 8) & 0x20)
        return f"ldd  r{d}, Y+{q}", 1
    if (w & 0xD208) == 0x8000:  # LDD Rd, Z+q
        d = (w >> 4) & 0x1F
        q = (w & 7) | ((w >> 7) & 0x18) | ((w >> 8) & 0x20)
        return f"ldd  r{d}, Z+{q}", 1
    if (w & 0xD208) == 0x8208:  # STD Y+q, Rr
        d = (w >> 4) & 0x1F
        q = (w & 7) | ((w >> 7) & 0x18) | ((w >> 8) & 0x20)
        return f"std  Y+{q}, r{d}", 1
    if (w & 0xD208) == 0x8200:  # STD Z+q, Rr
        d = (w >> 4) & 0x1F
        q = (w & 7) | ((w >> 7) & 0x18) | ((w >> 8) & 0x20)
        return f"std  Z+{q}, r{d}", 1

    return f".dw  0x{w:04X}", 1


def main():
    path, start, end = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0)
    b = open(path, "rb").read()
    i = start
    while i < end:
        aw = i // 2
        w = b[i] | b[i + 1] << 8
        w2 = (b[i + 2] | b[i + 3] << 8) if i + 3 < len(b) else 0
        text, n = disasm_word(w, w2, aw)
        raw = " ".join(f"{b[i+k]:02x}" for k in range(n * 2))
        print(f"  {i:05X} ({aw:04X}):  {raw:<12}  {text}")
        i += n * 2


if __name__ == "__main__":
    main()
