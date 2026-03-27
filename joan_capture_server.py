#!/usr/bin/env python3
"""TCP server that captures what the Joan bootloader sends during 'Start BL'.

Listens on the same port the Joan expects (11113) and logs all received data.
Also tries echoing back various responses to see what the bootloader expects.
"""

import datetime
import os
import socket
import sys
import threading
import time

HOST = "0.0.0.0"
PORT = 11113
LOG_DIR = "logs"


def handle_client(conn: socket.socket, addr: tuple, log_path: str) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")
    print(f"[{ts}] Connection from {addr}")

    all_data = b""
    try:
        conn.settimeout(1.0)
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                ts = datetime.datetime.now().strftime("%H:%M:%S.%f")
                all_data += data
                print(f"[{ts}] Received {len(data)} bytes from {addr}:")
                print(f"  hex: {data.hex()}")
                try:
                    text = data.decode("utf-8", errors="replace")
                    printable = all(32 <= ord(c) < 127 or c in "\r\n\t" for c in text)
                    if printable:
                        print(f"  ascii: {text!r}")
                except Exception:
                    pass

                # Log raw bytes
                with open(log_path, "ab") as f:
                    f.write(f"[{ts}] RX {len(data)} bytes\n".encode())
                    f.write(data)
                    f.write(b"\n---\n")

            except socket.timeout:
                continue
            except Exception as e:
                print(f"[error] {e}")
                break

    except Exception as e:
        print(f"[error] {e}")
    finally:
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")
        print(f"[{ts}] Connection closed from {addr}")
        print(f"[{ts}] Total received: {len(all_data)} bytes")
        if all_data:
            print(f"  Full hex dump: {all_data.hex()}")
        conn.close()


def main() -> int:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(LOG_DIR, f"joan-server-{ts}.bin")

    print(f"[server] Listening on {HOST}:{PORT}")
    print(f"[server] Log: {log_path}")
    print(f"[server] Ctrl-C to stop\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((HOST, PORT))
    except OSError as e:
        print(f"[FAIL] Cannot bind to port {PORT}: {e}")
        print("[hint] Try: sudo lsof -i :11113")
        return 1

    sock.listen(5)
    sock.settimeout(1.0)

    try:
        while True:
            try:
                conn, addr = sock.accept()
                t = threading.Thread(target=handle_client, args=(conn, addr, log_path), daemon=True)
                t.start()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("\n[exit]")
    finally:
        sock.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
