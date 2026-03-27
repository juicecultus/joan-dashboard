#!/usr/bin/env python3
"""Proxy that PATCHES the bootloader status packet to report old FW version.

Goal: trick the real server into thinking we have outdated firmware,
so it sends an ACK + firmware data instead of a NACK.

Status packet layout (88 bytes):
  Offset 36-39: FW major  (uint32 LE)
  Offset 40-43: FW minor  (uint32 LE)
  Offset 44-47: FW revision (uint32 LE)
"""

import datetime
import os
import socket
import struct
import sys
import threading

HOST = "0.0.0.0"
PORT = 11113
REAL_SERVER = "we3.gw.getjoan.com"
REAL_PORT = 11113
LOG_DIR = "logs"

# Fake old firmware version to report
FAKE_FW_MAJOR = 1
FAKE_FW_MINOR = 0
FAKE_FW_REV = 0


def ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")


def patch_status(data: bytes) -> bytes:
    """Patch FW version fields in the 88-byte status packet."""
    if len(data) < 48:
        return data
    patched = bytearray(data)
    struct.pack_into("<I", patched, 36, FAKE_FW_MAJOR)
    struct.pack_into("<I", patched, 40, FAKE_FW_MINOR)
    struct.pack_into("<I", patched, 44, FAKE_FW_REV)
    # Also zero out the FW CRC so server doesn't match current FW
    struct.pack_into("<I", patched, 8, 0x00000000)
    return bytes(patched)


def handle_client(conn: socket.socket, addr: tuple, log_f) -> None:
    log_f.write(f"\n{'='*70}\n")
    log_f.write(f"[{ts()}] CONNECTION from {addr}\n")
    log_f.flush()

    try:
        conn.settimeout(5.0)
        # Read from Joan
        data = conn.recv(4096)
        if not data:
            log_f.write(f"[{ts()}] No data received, closing\n")
            conn.close()
            return

        log_f.write(f"[{ts()}] Joan -> Proxy: {len(data)} bytes\n")
        log_f.write(f"  hex: {data.hex()}\n")
        log_f.flush()
        print(f"[{ts()}] Joan -> {len(data)} bytes")

        # Patch the status packet
        patched = patch_status(data)
        log_f.write(f"[{ts()}] PATCHED status (FW {FAKE_FW_MAJOR}.{FAKE_FW_MINOR}.{FAKE_FW_REV}, CRC=0)\n")
        log_f.write(f"  hex: {patched.hex()}\n")
        log_f.flush()
        print(f"[{ts()}] Patched FW version -> {FAKE_FW_MAJOR}.{FAKE_FW_MINOR}.{FAKE_FW_REV}")

        # Connect to real server
        upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream.settimeout(30.0)
        try:
            upstream.connect((REAL_SERVER, REAL_PORT))
        except Exception as e:
            log_f.write(f"[{ts()}] UPSTREAM CONNECT FAILED: {e}\n")
            conn.close()
            return

        log_f.write(f"[{ts()}] Connected to upstream {REAL_SERVER}:{REAL_PORT}\n")

        # Forward PATCHED data to real server
        upstream.sendall(patched)
        log_f.write(f"[{ts()}] Forwarded {len(patched)} patched bytes to upstream\n")
        log_f.flush()

        # Read ALL upstream response data — could be large if firmware is included
        upstream_resp = b""
        chunk_count = 0
        while True:
            try:
                chunk = upstream.recv(65536)
                if not chunk:
                    log_f.write(f"[{ts()}] Upstream closed connection\n")
                    break
                chunk_count += 1
                upstream_resp += chunk
                log_f.write(f"[{ts()}] Upstream chunk #{chunk_count}: {len(chunk)} bytes (total: {len(upstream_resp)})\n")
                log_f.write(f"  hex[0:64]: {chunk[:64].hex()}\n")
                log_f.flush()
                print(f"[{ts()}] Upstream chunk #{chunk_count}: {len(chunk)} bytes (total: {len(upstream_resp)})")

                # Forward to Joan immediately
                conn.sendall(chunk)
                log_f.write(f"[{ts()}] Forwarded chunk to Joan\n")
            except socket.timeout:
                log_f.write(f"[{ts()}] Upstream read timeout (done)\n")
                break

        log_f.write(f"[{ts()}] Total upstream response: {len(upstream_resp)} bytes in {chunk_count} chunks\n")
        if upstream_resp:
            # Log first 256 bytes in detail
            log_f.write(f"  FIRST 256 bytes: {upstream_resp[:256].hex()}\n")
            if len(upstream_resp) > 256:
                log_f.write(f"  LAST 64 bytes:  {upstream_resp[-64:].hex()}\n")
        log_f.flush()

        upstream.close()

        # Check for follow-up from Joan after receiving server response
        followup_data = b""
        for _ in range(10):
            try:
                more = conn.recv(65536)
                if more:
                    followup_data += more
                    log_f.write(f"[{ts()}] Joan follow-up: {len(more)} bytes\n")
                    log_f.write(f"  hex[0:64]: {more[:64].hex()}\n")
                    log_f.flush()
                    print(f"[{ts()}] Joan follow-up: {len(more)} bytes")
                else:
                    break
            except socket.timeout:
                break

        if followup_data:
            log_f.write(f"[{ts()}] Total Joan follow-up: {len(followup_data)} bytes\n")

    except Exception as e:
        log_f.write(f"[{ts()}] ERROR: {e}\n")
        import traceback
        log_f.write(traceback.format_exc())
    finally:
        log_f.write(f"[{ts()}] CONNECTION CLOSED\n")
        log_f.flush()
        conn.close()


def main() -> int:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(LOG_DIR, f"joan-proxy-patch-{ts_str}.txt")

    print(f"[proxy-patch] {HOST}:{PORT} -> {REAL_SERVER}:{REAL_PORT}")
    print(f"[proxy-patch] Patching FW to {FAKE_FW_MAJOR}.{FAKE_FW_MINOR}.{FAKE_FW_REV}")
    print(f"[proxy-patch] Log: {log_path}")

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
                t = threading.Thread(target=handle_client, args=(conn, addr, log_f), daemon=True)
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
