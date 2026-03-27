import argparse
import datetime
import os
import queue
import re
import sys
import threading
import time

import serial


PROMPT_RE = re.compile(r"(^|\n)\s*>\s*$", re.MULTILINE)


def _now_ts() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def _safe_decode(b: bytes) -> str:
    return b.decode("utf-8", errors="replace")


def _reader_thread(ser: serial.Serial, out_q: queue.Queue[bytes], stop_evt: threading.Event) -> None:
    while not stop_evt.is_set():
        try:
            b = ser.read(4096)
            if b:
                out_q.put(b)
            else:
                time.sleep(0.01)
        except Exception as e:
            out_q.put(f"\n[serial read error] {e}\n".encode("utf-8", errors="replace"))
            time.sleep(0.2)


def probe_baud(port: str, baud_rates: list[int], probe_seconds: float = 1.2) -> int | None:
    for baud in baud_rates:
        try:
            ser = serial.Serial(
                port,
                baudrate=baud,
                timeout=0,
                write_timeout=0.5,
                rtscts=False,
                dsrdtr=False,
            )
        except Exception:
            continue

        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # Try to elicit prompt.
            ser.write(b"\r\nhelp\r\n")
            ser.flush()

            start = time.time()
            buf = b""
            while time.time() - start < probe_seconds:
                b = ser.read(4096)
                if b:
                    buf += b
                    if b">" in buf or b"help" in buf or PROMPT_RE.search(_safe_decode(buf)):
                        return baud
                time.sleep(0.02)
        finally:
            try:
                ser.close()
            except Exception:
                pass

    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/cu.usbserial-A507MY5N")
    ap.add_argument("--baud", type=int, default=0, help="0 enables baud probing")
    ap.add_argument(
        "--probe",
        default="115200,57600,38400,19200,9600",
        help="Comma-separated baud rates to try when --baud=0",
    )
    ap.add_argument("--log", default="", help="Path to a log file (defaults to ./logs/<ts>.log)")
    ap.add_argument("--no-timestamp", action="store_true")
    args = ap.parse_args()

    port = args.port
    baud = args.baud

    if baud == 0:
        baud_rates = [int(x.strip()) for x in args.probe.split(",") if x.strip()]
        print(f"[probe] Probing {port} with baud rates: {baud_rates}")
        baud = probe_baud(port, baud_rates)
        if baud is None:
            print("[probe] Failed to detect baud rate. Try specifying --baud explicitly.")
            return 2
        print(f"[probe] Detected baud: {baud}")

    log_path = args.log
    if not log_path:
        os.makedirs("logs", exist_ok=True)
        log_path = os.path.join("logs", f"joan-{_now_ts()}.log")

    print(f"[open] {port} @ {baud}")
    print(f"[log]  {log_path}")
    print("[hint] Type commands and press Enter. Ctrl-C to exit.")

    try:
        ser = serial.Serial(
            port,
            baudrate=baud,
            timeout=0,
            write_timeout=1.0,
            rtscts=False,
            dsrdtr=False,
        )
    except Exception as e:
        print(f"[open] Failed: {e}")
        return 1

    out_q: queue.Queue[bytes] = queue.Queue()
    stop_evt = threading.Event()
    t = threading.Thread(target=_reader_thread, args=(ser, out_q, stop_evt), daemon=True)
    t.start()

    try:
        with open(log_path, "ab", buffering=0) as lf:
            last_print = ""
            while True:
                # Drain device output.
                drained = False
                while True:
                    try:
                        b = out_q.get_nowait()
                    except queue.Empty:
                        break

                    drained = True
                    s = _safe_decode(b)
                    if args.no_timestamp:
                        sys.stdout.write(s)
                        sys.stdout.flush()
                        lf.write(b)
                    else:
                        # Timestamp each chunk, but avoid spamming timestamps mid-line.
                        ts = datetime.datetime.now().strftime("%H:%M:%S")
                        if last_print.endswith("\n") or not last_print:
                            prefix = f"[{ts}] "
                        else:
                            prefix = ""
                        sys.stdout.write(prefix + s)
                        sys.stdout.flush()
                        lf.write(prefix.encode("utf-8") + b)
                    last_print = s

                # Read user input if no device data is streaming.
                if not drained:
                    r, _, _ = select_select([sys.stdin], 0.05)
                    if r:
                        line = sys.stdin.readline()
                        if not line:
                            time.sleep(0.05)
                            continue
                        if not line.endswith("\n"):
                            line += "\n"
                        ser.write(line.replace("\n", "\r\n").encode("utf-8", errors="replace"))
                        ser.flush()
    except KeyboardInterrupt:
        print("\n[exit]")
    finally:
        stop_evt.set()
        try:
            ser.close()
        except Exception:
            pass

    return 0


def select_select(rlist, timeout: float):
    # macOS stdin select works; wrapped for testability.
    import select

    return select.select(rlist, [], [], timeout)


if __name__ == "__main__":
    raise SystemExit(main())
