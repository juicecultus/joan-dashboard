#!/usr/bin/env python3
"""Clean proxy that logs BOTH directions to a text file.

Sits between Joan bootloader and real Joan server, capturing everything.
"""

import datetime
import os
import socket
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


def handle_client(conn: socket.socket, addr: tuple, log_f) -> None:
    log_f.write(f"\n{'='*70}\n")
    log_f.write(f"[{ts()}] CONNECTION from {addr}\n")
    log_f.flush()

    try:
        conn.settimeout(3.0)
        # Read from Joan
        data = conn.recv(4096)
        if not data:
            log_f.write(f"[{ts()}] No data received, closing\n")
            conn.close()
            return

        log_f.write(f"[{ts()}] Joan -> Proxy: {len(data)} bytes\n")
        log_f.write(f"  hex: {data.hex()}\n")
        log_f.flush()
        print(f"[{ts()}] Joan ({addr[1]}) -> {len(data)} bytes: {data[:20].hex()}...")

        # Connect to real server
        upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream.settimeout(20.0)
        try:
            upstream.connect((REAL_SERVER, REAL_PORT))
        except Exception as e:
            log_f.write(f"[{ts()}] UPSTREAM CONNECT FAILED: {e}\n")
            conn.close()
            return

        log_f.write(f"[{ts()}] Connected to upstream {REAL_SERVER}:{REAL_PORT}\n")

        # Forward Joan's data to real server
        upstream.sendall(data)
        log_f.write(f"[{ts()}] Forwarded {len(data)} bytes to upstream\n")
        log_f.flush()

        # Read upstream response
        upstream_resp = b""
        while True:
            try:
                chunk = upstream.recv(4096)
                if not chunk:
                    break
                upstream_resp += chunk
                log_f.write(f"[{ts()}] Upstream -> Proxy: {len(chunk)} bytes\n")
                log_f.write(f"  hex: {chunk.hex()}\n")
                log_f.flush()
                print(f"[{ts()}] Upstream -> {len(chunk)} bytes: {chunk[:20].hex()}...")

                # Forward to Joan immediately
                conn.sendall(chunk)
                log_f.write(f"[{ts()}] Forwarded {len(chunk)} bytes to Joan\n")
            except socket.timeout:
                log_f.write(f"[{ts()}] Upstream read timeout (done)\n")
                break

        log_f.write(f"[{ts()}] Total upstream response: {len(upstream_resp)} bytes\n")
        if upstream_resp:
            log_f.write(f"  FULL HEX: {upstream_resp.hex()}\n")
        log_f.flush()

        upstream.close()

        # Check for follow-up from Joan
        try:
            more = conn.recv(4096)
            if more:
                log_f.write(f"[{ts()}] Joan follow-up: {len(more)} bytes\n")
                log_f.write(f"  hex: {more.hex()}\n")
        except socket.timeout:
            pass

    except Exception as e:
        log_f.write(f"[{ts()}] ERROR: {e}\n")
    finally:
        log_f.write(f"[{ts()}] CONNECTION CLOSED\n")
        log_f.flush()
        conn.close()


def main() -> int:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(LOG_DIR, f"joan-proxy-{ts_str}.txt")

    print(f"[proxy] {HOST}:{PORT} -> {REAL_SERVER}:{REAL_PORT}")
    print(f"[proxy] Log: {log_path}")

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
