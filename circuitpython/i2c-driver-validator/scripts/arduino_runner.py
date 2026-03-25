#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import argparse
import subprocess
import sys
import time
import serial


def compile_sketch(sketch_path: str, fqbn: str, extra_flags: str) -> None:
    """Compile the Arduino sketch using arduino-cli."""
    cmd = [
        "arduino-cli", "compile",
        "--fqbn", fqbn,
        "--build-property", f'build.extra_flags="{extra_flags}"',
        sketch_path,
    ]
    print(f"Compiling: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Compilation failed (exit code {result.returncode})")
    print("Compilation successful.")


def upload_sketch(sketch_path: str, port: str, fqbn: str) -> None:
    """Upload the compiled sketch to the Arduino board."""
    cmd = [
        "arduino-cli", "upload",
        "-p", port,
        "--fqbn", fqbn,
        sketch_path,
    ]
    print(f"Uploading: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Upload failed (exit code {result.returncode})")
    print("Upload successful.")


def read_for_duration(ser: serial.Serial, duration: float = 10.0) -> None:
    """Read serial output from the Arduino for the given duration or until the
    end sentinel ``~~END~~`` is received on its own line."""
    end_time = time.monotonic() + duration
    line_buffer = ""
    while time.monotonic() < end_time:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
            if data:
                print(data, end="", flush=True)
                line_buffer += data

                # Check each complete line for the end sentinel
                while "\n" in line_buffer:
                    line, line_buffer = line_buffer.split("\n", 1)
                    if line.strip() == "~~END~~":
                        return
        else:
            time.sleep(0.05)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile and flash an Arduino sketch, then read serial output."
    )
    parser.add_argument(
        "sketch",
        help="Path to the Arduino sketch directory (or .ino file).",
    )
    parser.add_argument(
        "--port",
        default="/dev/ttyUSB0",
        help="Serial port for upload and monitoring (default: /dev/ttyUSB0).",
    )
    parser.add_argument(
        "--fqbn",
        default="arduino:avr:uno",
        help="Fully Qualified Board Name (default: arduino:avr:uno).",
    )
    parser.add_argument(
        "--extra-flags",
        default="-DDEBUG_SERIAL=Serial",
        help='Extra compiler flags (default: "-DDEBUG_SERIAL=Serial").',
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=115200,
        help="Serial baud rate (default: 115200).",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Seconds to listen for serial output after flashing (default: 10).",
    )
    parser.add_argument(
        "--boot-delay",
        type=float,
        default=0.0,
        help="Seconds to wait after upload for the board to reset (default: 0).",
    )
    args = parser.parse_args()

    # --- Compile ---
    compile_sketch(args.sketch, args.fqbn, args.extra_flags)

    # --- Upload / Flash ---
    upload_sketch(args.sketch, args.port, args.fqbn)

    # Give the board time to reset after flashing
    print(f"Waiting {args.boot_delay}s for board to reset...")
    time.sleep(args.boot_delay)

    # --- Read serial output ---
    print(f"Reading serial on {args.port} at {args.baud} baud for up to {args.duration}s...")
    print(f"~~BEGIN SERIAL OUTPUT~~\n")
    with serial.Serial(args.port, baudrate=args.baud, timeout=0) as ser:
        read_for_duration(ser, args.duration)


if __name__ == "__main__":
    main()
