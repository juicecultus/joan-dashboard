#!/usr/bin/env python3
"""Redirect a Joan device from getjoan.com to a local VSS server.

Connects via the FTDI USB UART serial console (Micro-USB port) and uses
CLI commands to change the server address, save to flash, and reboot.

Usage:
    pip install pyserial
    python joan_redirect_and_reboot.py

Original factory settings (to restore if needed):
    server_tcp_set we3.gw.getjoan.com 11113
"""

import sys
import time

import serial

# ── Configuration ──────────────────────────────────────────────────
# Serial port: macOS = /dev/cu.usbserial-*, Linux = /dev/ttyUSB0
PORT = "/dev/cu.usbserial-A507MY5N"
BAUD = 115200

# Your VSS server's IP address and port
LOCAL_IP = "192.168.1.100"   # ← change this to your Pi / VSS host IP
LOCAL_PORT = "11113"


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


def send_cmd(ser: serial.Serial, cmd: str, wait: float = 2.0) -> str:
    ser.reset_input_buffer()
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()
    return drain(ser, timeout=wait)


def main() -> int:
    print(f"[open] {PORT} @ {BAUD}")
    try:
        ser = serial.Serial(
            PORT, baudrate=BAUD, timeout=0, write_timeout=1.0,
            rtscts=False, dsrdtr=False,
        )
    except Exception as e:
        print(f"[FAIL] {e}")
        return 1

    # Drain
    drain(ser, timeout=1.0)
    ser.write(b"\r\n")
    ser.flush()
    time.sleep(0.3)
    drain(ser, timeout=0.3)

    # Step 1: Show current settings
    print("\n--- Current server settings ---")
    resp = send_cmd(ser, "server_tcp_get")
    print(resp)

    resp = send_cmd(ser, "encryption_config_get")
    print(resp)

    # Step 2: Redirect server to our local IP
    print(f"\n--- Redirecting server to {LOCAL_IP}:{LOCAL_PORT} ---")
    resp = send_cmd(ser, f"server_tcp_set {LOCAL_IP} {LOCAL_PORT}")
    print(resp)

    # Step 3: Disable encryption so we can read the protocol
    print("\n--- Disabling outbound encryption ---")
    resp = send_cmd(ser, "encryption_mode_set 0")
    print(resp)

    # Step 4: Verify new settings
    print("\n--- Verifying new settings ---")
    resp = send_cmd(ser, "server_tcp_get")
    print(resp)

    resp = send_cmd(ser, "encryption_config_get")
    print(resp)

    # Step 5: Save to flash
    print("\n--- Saving settings to flash ---")
    resp = send_cmd(ser, "flash_save")
    print(resp)

    # Step 6: Reboot
    print("\n--- Rebooting device ---")
    print("[IMPORTANT] Make sure joan_capture_server.py is running on port 11113!")
    resp = send_cmd(ser, "reboot", wait=1.0)
    print(resp)

    # Capture boot output for 30s
    print("\n--- Capturing boot output (30s) ---")
    start = time.time()
    while time.time() - start < 30:
        chunk = ser.read(4096)
        if chunk:
            sys.stdout.write(chunk.decode("utf-8", errors="replace"))
            sys.stdout.flush()
        else:
            time.sleep(0.01)

    ser.close()
    print("\n[done]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
