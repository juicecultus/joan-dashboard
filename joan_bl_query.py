#!/usr/bin/env python3
"""Reboot the Joan, catch the bootloader 'bl>' prompt, and send commands."""

import datetime
import os
import sys
import time

import serial

PORT = "/dev/cu.usbserial-A507MY5N"
BAUD = 115200

BL_COMMANDS = [
    "help",
    "?",
    "version",
    "info",
    "status",
    "list",
]


def drain(ser: serial.Serial, timeout: float = 0.5) -> str:
    buf = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = ser.read(4096)
        if chunk:
            buf += chunk
            deadline = time.time() + timeout
        else:
            time.sleep(0.01)
    return buf.decode("utf-8", errors="replace")


def wait_for(ser: serial.Serial, marker: str, timeout: float = 15.0) -> tuple[bool, str]:
    """Wait for a specific string to appear in serial output."""
    buf = ""
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = ser.read(4096)
        if chunk:
            text = chunk.decode("utf-8", errors="replace")
            buf += text
            sys.stdout.write(text)
            sys.stdout.flush()
            if marker in buf:
                return True, buf
        else:
            time.sleep(0.01)
    return False, buf


def send_and_read(ser: serial.Serial, cmd: str, wait: float = 2.0) -> str:
    """Send a command and read response."""
    ser.reset_input_buffer()
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()
    return drain(ser, timeout=wait)


def main() -> int:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs("logs", exist_ok=True)
    log_path = f"logs/joan-bl-{ts}.log"

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

    all_output = ""

    # Drain buffered output thoroughly
    print("[drain] clearing buffer (3s)...")
    pre = drain(ser, timeout=3.0)
    if pre.strip():
        sys.stdout.write(pre[-200:] + "\n")  # show tail only
    all_output += pre

    # Send bare CR to get a clean prompt
    ser.write(b"\r\n")
    ser.flush()
    time.sleep(0.5)
    prompt_check = drain(ser, timeout=0.5)
    all_output += prompt_check

    # Now send reboot as a clean command
    print("[send] reboot")
    ser.reset_input_buffer()
    ser.write(b"reboot\r\n")
    ser.flush()

    # Wait for bootloader CLI to start, then poke it
    print("[wait] Waiting for 'CLI USB task started' (up to 15s)...")
    found_cli, buf = wait_for(ser, "CLI USB task started", timeout=15.0)
    all_output += buf

    if not found_cli:
        print("\n[FAIL] Did not see bootloader CLI startup")
        with open(log_path, "w") as f:
            f.write(all_output)
        ser.close()
        return 1

    print("\n[OK] Bootloader CLI detected! Sending CR to get prompt...")
    time.sleep(0.3)

    # Send CR to trigger bl> prompt
    ser.write(b"\r\n")
    ser.flush()

    found_bl, buf2 = wait_for(ser, "bl>", timeout=5.0)
    all_output += buf2

    if not found_bl:
        print("\n[WARN] Did not see 'bl>' but will try commands anyway")

    print("\n[OK] Sending commands to bootloader...")

    # Try each command at the bl> prompt
    for cmd in BL_COMMANDS:
        print(f"\n{'='*60}")
        print(f"bl>>> {cmd}")
        print("=" * 60)
        resp = send_and_read(ser, cmd, wait=3.0)
        print(resp)
        all_output += f"\nbl>>> {cmd}\n{resp}\n"

    # Let device finish booting
    print("\n[wait] Letting device continue boot (20s)...")
    more = drain(ser, timeout=20.0)
    print(more)
    all_output += more

    ser.close()

    with open(log_path, "w") as f:
        f.write(all_output)
    print(f"\n[done] Full capture → {log_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
