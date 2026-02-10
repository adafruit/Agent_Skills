#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import argparse
import time
import serial


def send_ctrl(ser: serial.Serial, char: str) -> None:
    ser.write(char.encode("utf-8"))
    ser.flush()


def wait_for_prompt(ser: serial.Serial, timeout: float = 10.0) -> bool:
    buffer = ""
    end_time = time.monotonic() + timeout
    while time.monotonic() < end_time:
        send_ctrl(ser, "\x03")
        start = time.monotonic()
        while time.monotonic() - start < 0.5:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
                buffer += data
                if ">>>" in buffer:
                    return True
            time.sleep(0.05)
    return False


def read_for_duration(ser: serial.Serial, duration: float = 10.0) -> None:
    end_time = time.monotonic() + duration
    buffer = ""
    started = False
    marker = "code.py output:"
    while time.monotonic() < end_time:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
            if data:
                if not started:
                    buffer += data
                    marker_index = buffer.find(marker)
                    if marker_index != -1:
                        started = True
                        start_pos = marker_index + len(marker)
                        remaining = buffer[start_pos:]
                        if remaining:
                            print(remaining, end="", flush=True)
                else:
                    print(data, end="", flush=True)
        else:
            time.sleep(0.05)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run code.py and read output from CircuitPython device.")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Serial port to open.")
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Seconds to listen for output after sending Ctrl+D.",
    )
    args = parser.parse_args()

    with serial.Serial(args.port, baudrate=115200, timeout=0) as ser:
        if not wait_for_prompt(ser):
            raise RuntimeError("Did not receive >>> prompt from device")
        send_ctrl(ser, "\x04")
        read_for_duration(ser, args.duration)


if __name__ == "__main__":
    main()
