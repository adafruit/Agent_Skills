#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Shared pytest configuration for I2C validation tests."""


def pytest_addoption(parser):
    parser.addoption(
        "--use-output-files",
        action="store_true",
        default=False,
        help="Compare pre-captured .out.txt files instead of running on hardware.",
    )
    parser.addoption(
        "--arduino-port",
        default="/dev/ttyUSB0",
        help="Serial port for the Arduino board (default: /dev/ttyUSB0).",
    )
    parser.addoption(
        "--arduino-fqbn",
        default="arduino:avr:uno",
        help="Arduino Fully Qualified Board Name (default: arduino:avr:uno).",
    )
    parser.addoption(
        "--circuitpython-port",
        default="/dev/ttyACM0",
        help="Serial port for the CircuitPython device (default: /dev/ttyACM0).",
    )
    parser.addoption(
        "--circuitpython-path",
        default="/media/timc/CIRCUITPY/",
        help="Mount path for the CIRCUITPY drive (default: /media/timc/CIRCUITPY/).",
    )
    parser.addoption(
        "--duration",
        type=float,
        default=30.0,
        help="Max seconds to wait for serial output (default: 30).",
    )
