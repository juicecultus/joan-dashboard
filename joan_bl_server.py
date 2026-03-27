#!/usr/bin/env python3
"""Joan bootloader update server.

Receives the 88-byte status packet from the bootloader, sends a configurable
response, and logs everything. Used to reverse-engineer the update protocol.

Modes:
  --mode nack    Try simple NACK-like responses (short packets)
  --mode ack     Try ACK-like responses (signal "update available")
  --mode proxy   Forward to real Joan server and capture the response
  --mode echo    Just echo back the received packet
"""

import argparse
import datetime
import os
import socket
import struct
import sys
import threading
import time

HOST = "0.0.0.0"
PORT = 11113
REAL_SERVER = "we3.gw.getjoan.com"
REAL_PORT = 11113
LOG_DIR = "logs"


def ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")


def hex_dump(data: bytes, prefix: str = "  ") -> str:
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{prefix}{i:04x}: {hex_part:<48s} {ascii_part}")
    return "\n".join(lines)


def handle_nack(conn: socket.socket, data: bytes, response_idx: int) -> None:
    """Try various NACK-like responses."""
    responses = [
        # Index 0: Single byte 0x00
        (b"\x00", "single byte 0x00"),
        # Index 1: Single byte 0x01
        (b"\x01", "single byte 0x01"),
        # Index 2: Single byte 0x02
        (b"\x02", "single byte 0x02"),
        # Index 3: 4-byte response type=2, NACK
        (b"\x02\x00\x00\x00", "4-byte: type=2 zeros"),
        # Index 4: 4-byte all zeros
        (b"\x00\x00\x00\x00", "4-byte: all zeros"),
        # Index 5: 8-byte with type=2 and NACK flag
        (b"\x02\x00\x00\x04\x00\x00\x00\x00", "8-byte: type=2, len=4, zeros"),
        # Index 6: PV2-style NACK — type=2, flags, no data
        (struct.pack("<BBHI", 0x02, 0x00, 0x0000, 0), "PV2-style NACK"),
        # Index 7: Just the number 0 as uint32
        (struct.pack("<I", 0), "uint32 zero"),
        # Index 8: Packet header only — type 2, length 0
        (b"\x02\x00\x00\x00", "pkt type=2 len=0"),
    ]

    idx = response_idx % len(responses)
    resp_data, desc = responses[idx]
    print(f"[{ts()}] Sending NACK response #{idx}: {desc}")
    print(f"  hex: {resp_data.hex()}")
    conn.sendall(resp_data)


def handle_ack(conn: socket.socket, data: bytes) -> None:
    """Send an ACK-like response signaling 'update available'."""
    # Try: type=2, some kind of ACK flag, then firmware metadata
    # This is speculative — we'll iterate based on bootloader response
    resp = struct.pack("<BBHI", 0x02, 0x01, 0x0000, 0)
    print(f"[{ts()}] Sending ACK response: {resp.hex()}")
    conn.sendall(resp)

    # Wait for bootloader to request firmware data
    time.sleep(0.5)
    try:
        conn.settimeout(10.0)
        more = conn.recv(4096)
        if more:
            print(f"[{ts()}] Bootloader sent {len(more)} more bytes after ACK:")
            print(hex_dump(more))
    except socket.timeout:
        print(f"[{ts()}] No further data from bootloader after ACK")


def handle_proxy(conn: socket.socket, data: bytes) -> None:
    """Forward to real Joan server and capture the response."""
    print(f"[{ts()}] Proxying to {REAL_SERVER}:{REAL_PORT}")
    try:
        upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream.settimeout(15.0)
        upstream.connect((REAL_SERVER, REAL_PORT))
        print(f"[{ts()}] Connected to upstream, forwarding {len(data)} bytes")
        upstream.sendall(data)

        # Capture response
        resp = b""
        while True:
            try:
                chunk = upstream.recv(4096)
                if not chunk:
                    break
                resp += chunk
                print(f"[{ts()}] Upstream sent {len(chunk)} bytes:")
                print(hex_dump(chunk))
                # Forward to bootloader
                conn.sendall(chunk)
            except socket.timeout:
                break

        upstream.close()
        print(f"[{ts()}] Total upstream response: {len(resp)} bytes")
        if resp:
            print(f"  full hex: {resp.hex()}")

    except Exception as e:
        print(f"[{ts()}] Proxy error: {e}")


def handle_client(conn: socket.socket, addr: tuple, mode: str, log_path: str,
                  response_idx: int) -> None:
    print(f"\n[{ts()}] === Connection from {addr} ===")
    all_rx = b""
    try:
        conn.settimeout(5.0)
        # Read initial packet
        data = conn.recv(4096)
        if data:
            all_rx += data
            print(f"[{ts()}] Received {len(data)} bytes:")
            print(hex_dump(data))

            with open(log_path, "ab") as f:
                f.write(f"\n[{ts()}] RX {len(data)} from {addr}\n".encode())
                f.write(data)
                f.write(b"\n")

            if mode == "nack":
                handle_nack(conn, data, response_idx)
            elif mode == "ack":
                handle_ack(conn, data)
            elif mode == "proxy":
                handle_proxy(conn, data)
            elif mode == "echo":
                conn.sendall(data)
                print(f"[{ts()}] Echoed {len(data)} bytes back")

            # Wait and read any follow-up
            time.sleep(2.0)
            try:
                more = conn.recv(4096)
                if more:
                    all_rx += more
                    print(f"[{ts()}] Follow-up {len(more)} bytes:")
                    print(hex_dump(more))
            except socket.timeout:
                pass

    except socket.timeout:
        print(f"[{ts()}] Timeout reading from {addr}")
    except Exception as e:
        print(f"[{ts()}] Error: {e}")
    finally:
        print(f"[{ts()}] Connection closed ({len(all_rx)} bytes total)")
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="nack", choices=["nack", "ack", "proxy", "echo"])
    ap.add_argument("--response-idx", type=int, default=0,
                    help="For nack mode: which response variant to try (0-8)")
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args()

    os.makedirs(LOG_DIR, exist_ok=True)
    ts_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(LOG_DIR, f"joan-blserver-{ts_str}.bin")

    print(f"[server] Mode: {args.mode}")
    print(f"[server] Listening on {HOST}:{args.port}")
    print(f"[server] Log: {log_path}")
    if args.mode == "nack":
        print(f"[server] Response index: {args.response_idx}")
    print()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((HOST, args.port))
    except OSError as e:
        print(f"[FAIL] Cannot bind to port {args.port}: {e}")
        return 1

    sock.listen(5)
    sock.settimeout(1.0)

    conn_count = 0
    try:
        while True:
            try:
                conn, addr = sock.accept()
                t = threading.Thread(
                    target=handle_client,
                    args=(conn, addr, args.mode, log_path, args.response_idx + conn_count),
                    daemon=True,
                )
                t.start()
                conn_count += 1
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("\n[exit]")
    finally:
        sock.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
