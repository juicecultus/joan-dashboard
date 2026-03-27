#!/usr/bin/env python3
"""Send a batch of CLI commands to the Joan device and capture responses."""

import sys
import time

import serial

PORT = "/dev/cu.usbserial-A507MY5N"
BAUD = 115200
TIMEOUT_PER_CMD = 2.0  # seconds to wait for response after each command

COMMANDS = [
    "fw_version_get",
    "fw_checksum_get",
    "uuid_get",
    "system_conf_get",
    "display_conf_get",
    "conn_type_list",
    "conn_type_get",
    "feat_get",
    "log_config_get",
    "status_get",
    "battery_conf_get",
    "uptime",
    "cli_version_get",
    "gtin_get",
    "cc3100_fw_version",
    "cc3100_mac_address",
    "ipv4_conf_get",
    "wifi_conf_get",
    "wifi_mac_conf_get",
    "eth_conf_get",
    "encryption_config_get",
    "conn_retry_get",
    "conn_state_get",
    "server_tcp_get",
    "server_hb_get",
    "border_get",
    "bq24023_mode_get",
    "get_sw_wd",
    "certs_config_get",
    "max17135_dump",
]


def drain(ser: serial.Serial, timeout: float = 0.3) -> str:
    """Read all available data until silence for `timeout` seconds."""
    buf = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = ser.read(4096)
        if chunk:
            buf += chunk
            deadline = time.time() + timeout  # reset on new data
        else:
            time.sleep(0.02)
    return buf.decode("utf-8", errors="replace")


def send_cmd(ser: serial.Serial, cmd: str, timeout: float = TIMEOUT_PER_CMD) -> str:
    """Send a command and return the response text."""
    ser.reset_input_buffer()
    ser.write((cmd + "\r\n").encode("utf-8"))
    ser.flush()
    return drain(ser, timeout=timeout)


def main() -> int:
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

    # Drain any buffered output first
    print("[drain] clearing buffer...")
    initial = drain(ser, timeout=1.0)
    if initial.strip():
        print(initial)

    # Send a bare CR to get a clean prompt
    ser.write(b"\r\n")
    ser.flush()
    time.sleep(0.3)
    drain(ser, timeout=0.3)

    log_lines = []
    for cmd in COMMANDS:
        print(f"\n{'='*60}")
        print(f">>> {cmd}")
        print('='*60)
        resp = send_cmd(ser, cmd)
        print(resp)
        log_lines.append(f">>> {cmd}\n{resp}\n")

    ser.close()

    # Write log
    log_path = "logs/joan-query.log"
    import os
    os.makedirs("logs", exist_ok=True)
    with open(log_path, "w") as f:
        f.write("\n".join(log_lines))
    print(f"\n[done] Log saved to {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
