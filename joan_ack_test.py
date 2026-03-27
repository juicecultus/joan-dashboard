#!/usr/bin/env python3
"""Test different ACK response values against the Joan bootloader.

Runs a TCP server with a configurable ACK response, reboots the Joan,
and captures the UART output to see what the bootloader says.

Usage:
  python joan_ack_test.py --flag 0          # flag=0, no extra fields
  python joan_ack_test.py --flag 0 --size 365488  # flag=0 + firmware size
  python joan_ack_test.py --flag 2          # flag=2
  python joan_ack_test.py --hex 020000f000000000305905000000000  # raw hex
"""

import argparse
import socket
import struct
import sys
import threading
import time

import serial

SERIAL_PORT = "/dev/cu.usbserial-A507MY5N"
SERIAL_BAUD = 115200
TCP_PORT = 11113


def build_response(flag: int, fw_size: int = 0, fw_crc: int = 0,
                    extra: bytes = b"") -> bytes:
    header = b"\x02\x00\x00\xf0"
    return header + struct.pack("<III", flag, fw_size, fw_crc) + extra


def tcp_server(response: bytes, result: dict, stop_evt: threading.Event) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", TCP_PORT))
    sock.listen(5)
    sock.settimeout(1.0)

    while not stop_evt.is_set():
        try:
            conn, addr = sock.accept()
        except socket.timeout:
            continue

        try:
            conn.settimeout(5.0)
            data = conn.recv(4096)
            if data and len(data) == 88 and data[0] == 0x02:
                print(f"  [tcp] BL connected, sending {len(response)} bytes: {response.hex()}")
                conn.sendall(response)

                # Capture any follow-up
                time.sleep(1.0)
                try:
                    more = conn.recv(4096)
                    if more:
                        result["follow_up"] = more.hex()
                        print(f"  [tcp] BL sent {len(more)} more bytes: {more[:32].hex()}...")
                except Exception:
                    pass
            elif data and data[0] == 0x03:
                # App packet, ignore
                pass
        except Exception as e:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    sock.close()


def reboot_and_capture(timeout: float = 30.0) -> str:
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0, write_timeout=1.0,
                        rtscts=False, dsrdtr=False)
    time.sleep(0.3)
    ser.read(65536)
    ser.write(b"\r\n")
    ser.flush()
    time.sleep(0.3)
    ser.read(65536)
    ser.reset_input_buffer()
    ser.write(b"reboot\r\n")
    ser.flush()

    buf = ""
    start = time.time()
    while time.time() - start < timeout:
        chunk = ser.read(4096)
        if chunk:
            t = chunk.decode("utf-8", errors="replace")
            buf += t
        else:
            time.sleep(0.01)
        # Stop early once we see BL result
        if "BL failed" in buf or "BL success" in buf or "Firmware update" in buf:
            time.sleep(2)
            chunk = ser.read(65536)
            if chunk:
                buf += chunk.decode("utf-8", errors="replace")
            break

    ser.close()
    return buf


def extract_bl_result(uart_output: str) -> str:
    """Extract the bootloader result line from UART output."""
    lines = uart_output.split("\n")
    for line in lines:
        line = line.strip()
        if "Start BL" in line:
            continue
        if any(kw in line for kw in ["NACK", "ACK", "ack_nack", "header",
                                      "BL failed", "BL success", "firmware",
                                      "Firmware", "received", "Receiving",
                                      "timeout", "invalid", "update",
                                      "download", "flash", "chunk"]):
            yield line


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--flag", type=int, default=None)
    ap.add_argument("--size", type=int, default=0)
    ap.add_argument("--crc", type=int, default=0)
    ap.add_argument("--hex", default=None, help="Raw hex response to send")
    ap.add_argument("--flags", default=None,
                    help="Comma-separated list of flag values to test in sequence")
    args = ap.parse_args()

    if args.flags:
        flag_values = [int(x.strip(), 0) for x in args.flags.split(",")]
    elif args.flag is not None:
        flag_values = [args.flag]
    elif args.hex:
        flag_values = [None]
    else:
        # Default: test common values
        flag_values = [0, 2, 3, 0xFF, 0xFFFFFFFF]

    for i, flag_val in enumerate(flag_values):
        if args.hex:
            response = bytes.fromhex(args.hex)
            desc = f"raw hex: {args.hex}"
        else:
            response = build_response(flag_val, args.size, args.crc)
            desc = f"flag={flag_val} (0x{flag_val:X}), size={args.size}, crc={args.crc}"

        print(f"\n{'='*60}")
        print(f"TEST {i+1}/{len(flag_values)}: {desc}")
        print(f"  Response hex: {response.hex()}")
        print("=" * 60)

        # Start TCP server
        result = {}
        stop_evt = threading.Event()
        tcp_thread = threading.Thread(target=tcp_server,
                                      args=(response, result, stop_evt), daemon=True)
        tcp_thread.start()
        time.sleep(0.5)

        # Reboot and capture UART
        uart = reboot_and_capture(timeout=25)

        # Stop TCP server
        stop_evt.set()
        time.sleep(1)

        # Show results
        print(f"\n--- BL Result ---")
        found_any = False
        for line in extract_bl_result(uart):
            print(f"  {line}")
            found_any = True
        if not found_any:
            print("  (no relevant BL output found)")

        if result.get("follow_up"):
            print(f"  Follow-up data from BL: {result['follow_up']}")

        # Brief pause between tests
        if i < len(flag_values) - 1:
            print("\n  Waiting 5s before next test...")
            time.sleep(5)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
