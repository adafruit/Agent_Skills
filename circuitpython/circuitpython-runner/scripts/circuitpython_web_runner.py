#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import argparse
import os
import sys
import time

import websocket
import logging
import base64
from circup.backends import WebBackend
import shutil


def send_ctrl(ws: websocket.WebSocket, char: str) -> None:
    ws.send(char.encode("utf-8"))



def wait_for_prompt(ws: websocket.WebSocket, timeout: float = 10.0) -> bool:
    buffer = ""
    end_time = time.monotonic() + timeout
    while time.monotonic() < end_time:
        send_ctrl(ws, "\x03")
        start = time.monotonic()
        while time.monotonic() - start < 0.5:
            data = ws.recv()
            buffer += data
            if ">>>" in buffer:
                return True
            else:
                send_ctrl(ws, "\x03")
            time.sleep(0.05)
    return False


def read_for_duration(ws: websocket.WebSocket, duration: float = 10.0) -> None:
    end_time = time.monotonic() + duration
    buffer = ""
    started = False
    marker = "code.py output:"
    line_buffer = ""
    while time.monotonic() < end_time:

        data = ws.recv()
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
                        line_buffer += remaining
            else:
                print(data, end="", flush=True)
                line_buffer += data

            # Check each complete line in line_buffer for the end sentinel
            while "\n" in line_buffer:
                line, line_buffer = line_buffer.split("\n", 1)
                if line.strip() == "~~END~~":
                    return



def main() -> None:
    parser = argparse.ArgumentParser(description="Copy a python code file to the CIRCUITPY drive, run it and "
                                                 "read output from the CircuitPython device over serial.")
    parser.add_argument('filename', help="The code file to run on the CircuitPython device."
                                         "Will be copied to CIRCUITPY/code.py")
    parser.add_argument("--port", default="80", help="HTTP port to connect to")
    parser.add_argument("--host", default=f"circuitpython.local", help="URL to CircuitPython web workflow.")
    parser.add_argument("--password", default="", help="Password for CircuitPython web workflow, it is set in "
                                           "settings.toml file on the device..")
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Seconds to listen for output running the program.",
    )
    args = parser.parse_args()

    ws = websocket.WebSocket()
    auth_slug = base64.b64encode(f":{args.password}".encode('utf-8'))
    ws.connect(f"ws://{args.host}/cp/serial/", header=[f"Authorization: Basic {auth_slug.decode('utf-8')}"])


    if not wait_for_prompt(ws):
        raise RuntimeError("Did not receive >>> prompt from device")

    shutil.copyfile(args.filename, "/tmp/code.py")

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)
    web_backend = WebBackend(args.host, args.port, args.password, logger, timeout=args.duration)
    web_backend.upload_file("/tmp/code.py", "/")
    time.sleep(3)

    send_ctrl(ws, "\x04")
    read_for_duration(ws, args.duration)


if __name__ == "__main__":
    main()
