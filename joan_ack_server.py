#!/usr/bin/env python3
"""Joan bootloader ACK test server.

Sends an ACK response (flag=0 instead of NACK flag=1) to the bootloader's
88-byte status packet, then captures whatever the bootloader sends next.

NACK (real server): 02 00 00 f0  01 00 00 00  00 00 00 00  00 00 00 00
ACK  (our test):    02 00 00 f0  00 00 00 00  00 00 00 00  00 00 00 00

The goal is to discover what the bootloader sends after receiving ACK
(presumably firmware chunk requests or readiness signal).
"""

import datetime
import os
import socket
import struct
import sys
import threading
import time

HOST = "0.0.0.0"
PORT = 11113
LOG_DIR = "logs"

# The ACK response: same header as NACK but with flag=0
ACK_RESPONSE = bytes.fromhex("020000f0000000000000000000000000")
NACK_RESPONSE = bytes.fromhex("020000f0010000000000000000000000")


def ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")


def handle_client(conn: socket.socket, addr: tuple, log_f, send_ack: bool) -> None:
    log_f.write(f"\n{'='*70}\n")
    log_f.write(f"[{ts()}] CONNECTION from {addr}\n")
    log_f.flush()
    print(f"\n[{ts()}] === Connection from {addr} ===")

    all_rx = b""
    try:
        conn.settimeout(3.0)

        # Read initial packet
        data = conn.recv(4096)
        if not data:
            conn.close()
            return

        all_rx += data
        pkt_type = data[0] if data else 0
        log_f.write(f"[{ts()}] RX {len(data)} bytes (type=0x{pkt_type:02X})\n")
        log_f.write(f"  hex: {data.hex()}\n")
        log_f.flush()
        print(f"[{ts()}] RX {len(data)} bytes (type=0x{pkt_type:02X}): {data[:16].hex()}...")

        # Only send ACK to type 0x02 (bootloader) packets
        if pkt_type == 0x02 and len(data) == 88:
            if send_ack:
                print(f"[{ts()}] >>> Sending ACK (flag=0) to bootloader")
                log_f.write(f"[{ts()}] TX ACK: {ACK_RESPONSE.hex()}\n")
                conn.sendall(ACK_RESPONSE)
            else:
                print(f"[{ts()}] >>> Sending NACK (flag=1) to bootloader")
                log_f.write(f"[{ts()}] TX NACK: {NACK_RESPONSE.hex()}\n")
                conn.sendall(NACK_RESPONSE)
            log_f.flush()

            # Now capture EVERYTHING the bootloader sends next
            print(f"[{ts()}] Waiting for bootloader response (up to 30s)...")
            conn.settimeout(2.0)
            capture_start = time.time()
            while time.time() - capture_start < 30:
                try:
                    chunk = conn.recv(4096)
                    if not chunk:
                        print(f"[{ts()}] Connection closed by bootloader")
                        break
                    all_rx += chunk
                    log_f.write(f"[{ts()}] RX {len(chunk)} bytes\n")
                    log_f.write(f"  hex: {chunk.hex()}\n")
                    log_f.flush()
                    print(f"[{ts()}] RX {len(chunk)} bytes: {chunk[:32].hex()}...")

                    # Try to decode as text
                    try:
                        text = chunk.decode("ascii")
                        if all(32 <= ord(c) < 127 or c in "\r\n\t" for c in text):
                            print(f"  ascii: {text!r}")
                    except Exception:
                        pass

                except socket.timeout:
                    continue
                except ConnectionResetError:
                    print(f"[{ts()}] Connection reset by bootloader")
                    break

        elif pkt_type == 0x03:
            # App packet — send NACK equivalent (or just close)
            print(f"[{ts()}] App packet (type=0x03), sending NACK")
            log_f.write(f"[{ts()}] App packet, sending NACK\n")
            conn.sendall(NACK_RESPONSE)

        else:
            print(f"[{ts()}] Unknown packet type 0x{pkt_type:02X}, {len(data)} bytes")
            log_f.write(f"[{ts()}] Unknown packet\n")

    except Exception as e:
        log_f.write(f"[{ts()}] ERROR: {e}\n")
        print(f"[{ts()}] ERROR: {e}")
    finally:
        log_f.write(f"[{ts()}] Total RX: {len(all_rx)} bytes\n")
        if all_rx:
            log_f.write(f"  FULL HEX: {all_rx.hex()}\n")
        log_f.write(f"[{ts()}] CONNECTION CLOSED\n")
        log_f.flush()
        print(f"[{ts()}] Total RX: {len(all_rx)} bytes")
        conn.close()


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--nack", action="store_true", help="Send NACK instead of ACK (for verification)")
    args = ap.parse_args()

    send_ack = not args.nack

    os.makedirs(LOG_DIR, exist_ok=True)
    ts_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    mode_str = "ack" if send_ack else "nack"
    log_path = os.path.join(LOG_DIR, f"joan-{mode_str}test-{ts_str}.txt")

    print(f"[server] Mode: {'ACK' if send_ack else 'NACK'}")
    print(f"[server] Listening on {HOST}:{PORT}")
    print(f"[server] Log: {log_path}")

    log_f = open(log_path, "w")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(5)
    sock.settimeout(1.0)

    try:
        while True:
            try:
                conn, addr = sock.accept()
                t = threading.Thread(
                    target=handle_client,
                    args=(conn, addr, log_f, send_ack),
                    daemon=True,
                )
                t.start()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("\n[exit]")
    finally:
        sock.close()
        log_f.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
