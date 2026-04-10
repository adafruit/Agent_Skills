# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT


def pytest_addoption(parser):
    parser.addoption(
        "--use-output-files",
        action="store_true",
        default=False,
        help="Use pre-captured *.out.txt files instead of running on hardware.",
    )
    parser.addoption(
        "--circuitpython-port",
        default="/dev/ttyACM0",
        help="Serial port for the CircuitPython device (default: /dev/ttyACM0).",
    )
    parser.addoption(
        "--circuitpython-path",
        default="/media/timc/CIRCUITPY/",
        help="Mount path of the CIRCUITPY drive (default: /media/timc/CIRCUITPY/).",
    )
    parser.addoption(
        "--arduino-port",
        default="/dev/ttyUSB0",
        help="Serial port for the Arduino device (default: /dev/ttyUSB0).",
    )
    parser.addoption(
        "--arduino-fqbn",
        default="arduino:avr:uno",
        help="Arduino FQBN string (default: arduino:avr:uno).",
    )
    parser.addoption(
        "--duration",
        type=float,
        default=60.0,
        help="Seconds to wait for each test to finish (default: 60).",
    )
