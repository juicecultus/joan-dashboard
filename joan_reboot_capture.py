#!/usr/bin/env python3
"""Send 'reboot' to the Joan device and capture all boot output.

Strategy:
1. Open serial, drain buffered data
2. Send 'reboot' command
3. Immediately start capturing all output for 30 seconds
4. During capture, periodically send break/newline/space to try to
   interrupt a bootloader 'press any key' prompt
5. Save everything to a timestamped log file
"""

import datetime
import os
import sys
import time

import serial

PORT = "/dev/cu.usbserial-A507MY5N"
BAUD = 115200
CAPTURE_SECONDS = 30


def drain(ser: serial.Serial, timeout: float = 0.5) -> bytes:
    buf = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = ser.read(4096)
        if chunk:
            buf += chunk
            deadline = time.time() + timeout
        else:
            time.sleep(0.01)
    return buf


def main() -> int:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs("logs", exist_ok=True)
    log_path = f"logs/joan-reboot-{ts}.log"

    print(f"[open] {PORT} @ {BAUD}")
    try:
        ser = serial.Serial(
            PORT,
            baudrate=BAUD,
            timeout=0,
            write_timeout=1.0,
            rtscts=False,
            dsrdtr=False,
        )
    except Exception as e:
        print(f"[FAIL] {e}")
        return 1

    # Drain any buffered output
    print("[drain] clearing buffer...")
    pre = drain(ser, timeout=1.0)
    if pre:
        print(pre.decode("utf-8", errors="replace"))

    # Send reboot
    print("[send] reboot")
    ser.write(b"reboot\r\n")
    ser.flush()

    # Capture boot output
    print(f"[capture] Recording for {CAPTURE_SECONDS}s...")
    print(f"[capture] Will also send interrupts (Enter/Space/Ctrl-C) to catch bootloader")
    print("=" * 60)

    all_data = b""
    start = time.time()
    last_interrupt = start
    interrupt_interval = 0.5  # send interrupt every 0.5s for first 10s
    interrupt_chars = [b"\r\n", b" ", b"\x03", b"\x1b", b"x"]

    interrupt_idx = 0
    while time.time() - start < CAPTURE_SECONDS:
        chunk = ser.read(4096)
        if chunk:
            all_data += chunk
            text = chunk.decode("utf-8", errors="replace")
            sys.stdout.write(text)
            sys.stdout.flush()

        now = time.time()
        elapsed = now - start

        # Send interrupts for the first 15 seconds
        if elapsed < 15 and now - last_interrupt >= interrupt_interval:
            c = interrupt_chars[interrupt_idx % len(interrupt_chars)]
            try:
                ser.write(c)
                ser.flush()
            except Exception:
                pass
            interrupt_idx += 1
            last_interrupt = now

        if not chunk:
            time.sleep(0.01)

    print("\n" + "=" * 60)

    # Also try toggling DTR/RTS in case bootloader needs it
    print("[try] Toggling DTR/RTS...")
    for _ in range(3):
        ser.dtr = False
        ser.rts = False
        time.sleep(0.1)
        ser.dtr = True
        ser.rts = True
        time.sleep(0.1)
        chunk = ser.read(4096)
        if chunk:
            all_data += chunk
            print(chunk.decode("utf-8", errors="replace"))

    ser.close()

    # Save log
    with open(log_path, "wb") as f:
        f.write(all_data)

    print(f"\n[done] Captured {len(all_data)} bytes → {log_path}")

    # Quick analysis
    text = all_data.decode("utf-8", errors="replace").lower()
    keywords = ["boot", "u-boot", "bl>", "bootloader", "dfu", "flash", "enter",
                "press", "hit any key", "loading", "jump", "firmware", "update"]
    found = [k for k in keywords if k in text]
    if found:
        print(f"[analysis] Found bootloader-related keywords: {found}")
    else:
        print("[analysis] No obvious bootloader keywords found in capture")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
