#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Pytest script to validate I2C transaction matching between Arduino and
CircuitPython programs.

Discovers test pairs by matching base names in arduino_tests/ and
circuitpython_tests/ directories. Runs both programs on their respective
devices, captures serial output, parses I2C debug lines, and asserts the
transaction sequences are identical.

Can also be run against pre-captured output files (*.out.txt) by using
the ``--use-output-files`` flag.

Usage:
    pytest test_i2c_validation.py -v
    pytest test_i2c_validation.py -v --use-output-files
    pytest test_i2c_validation.py -v --arduino-port /dev/ttyUSB0 --circuitpython-port /dev/ttyACM0
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ARDUINO_TESTS_DIR = BASE_DIR / "arduino_tests"
CIRCUITPYTHON_TESTS_DIR = BASE_DIR / "circuitpython_tests"
ARDUINO_RUNNER = BASE_DIR / "arduino_runner.py"
CIRCUITPYTHON_RUNNER = BASE_DIR / "circuitpython_runner.py"


# ---------------------------------------------------------------------------
# I2C transaction model & parsing
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class I2CTransaction:
    """A single I2C bus transaction (read or write)."""
    operation: str  # "WRITE" or "READ"
    address: int
    data: Tuple[int, ...]

    def __str__(self) -> str:
        data_hex = ", ".join(f"0x{b:02X}" for b in self.data)
        return f"I2C{self.operation} @ 0x{self.address:02X} :: {data_hex}"


# Regex that captures: I2CWRITE or I2CREAD, address, and the byte payload.
# Works for both Arduino and CircuitPython debug output.
_I2C_LINE_RE = re.compile(
    r"I2C(WRITE|READ)\s+@\s+(0x[0-9A-Fa-f]+)\s*::\s*(.*)"
)


def _parse_data_bytes(raw: str) -> Tuple[int, ...]:
    """Parse the data portion of an I2C debug line into a tuple of ints.

    Handles both Arduino style (trailing commas, ``STOP`` token) and
    CircuitPython style (clean comma-separated hex values).
    """
    # Remove the STOP marker that Arduino output may contain
    cleaned = raw.replace("STOP", "").strip()
    # Strip any trailing commas / whitespace
    cleaned = cleaned.rstrip(", \t")
    if not cleaned:
        return ()
    parts = [p.strip().rstrip(",") for p in cleaned.split(",") if p.strip().rstrip(",")]
    result: list[int] = []
    for part in parts:
        part = part.strip()
        if part:
            result.append(int(part, 16))
    return tuple(result)


def parse_i2c_transactions(serial_output: str) -> List[I2CTransaction]:
    """Extract an ordered list of I2C transactions from serial output text."""
    transactions: List[I2CTransaction] = []
    for line in serial_output.splitlines():
        m = _I2C_LINE_RE.search(line)
        if m:
            operation = m.group(1).upper()  # "WRITE" or "READ"
            address = int(m.group(2), 16)
            data = _parse_data_bytes(m.group(3))
            transactions.append(I2CTransaction(operation=operation, address=address, data=data))
    return transactions


# ---------------------------------------------------------------------------
# Test-pair discovery
# ---------------------------------------------------------------------------

def discover_test_pairs() -> List[Tuple[str, Path, Path]]:
    """Return a list of (test_name, arduino_sketch_dir, circuitpython_script)
    for every matching pair found in the test directories."""
    pairs: List[Tuple[str, Path, Path]] = []

    # Build a map of CircuitPython tests keyed by base name (without extension)
    cp_tests = {}
    if CIRCUITPYTHON_TESTS_DIR.exists():
        for f in sorted(CIRCUITPYTHON_TESTS_DIR.glob("*.py")):
            cp_tests[f.stem] = f

    # Look for matching Arduino sketch directories
    if ARDUINO_TESTS_DIR.exists():
        for d in sorted(ARDUINO_TESTS_DIR.iterdir()):
            if d.is_dir() and d.name in cp_tests:
                # The .ino file is expected to be named <dir_name>.ino inside the dir
                ino_file = d / f"{d.name}.ino"
                if ino_file.exists():
                    pairs.append((d.name, d, cp_tests[d.name]))

    return pairs


def discover_output_file_pairs() -> List[Tuple[str, Path, Path]]:
    """Return a list of (test_name, arduino_output, circuitpython_output)
    for every matching pair of pre-captured .out.txt files."""
    pairs: List[Tuple[str, Path, Path]] = []

    cp_outputs = {}
    if CIRCUITPYTHON_TESTS_DIR.exists():
        for f in sorted(CIRCUITPYTHON_TESTS_DIR.glob("*.out.txt")):
            # e.g.  00_chipid.out.txt  →  stem = "00_chipid.out", we want "00_chipid"
            name = f.name.replace(".out.txt", "")
            cp_outputs[name] = f

    if ARDUINO_TESTS_DIR.exists():
        for f in sorted(ARDUINO_TESTS_DIR.glob("*.out.txt")):
            name = f.name.replace(".out.txt", "")
            if name in cp_outputs:
                pairs.append((name, f, cp_outputs[name]))

    return pairs


# ---------------------------------------------------------------------------
# Runners – capture serial output from devices
# ---------------------------------------------------------------------------

def run_arduino(sketch_dir: Path, port: str, fqbn: str, duration: float) -> str:
    """Compile, upload, and capture serial output from an Arduino sketch."""
    cmd = [
        sys.executable, str(ARDUINO_RUNNER),
        str(sketch_dir),
        "--port", port,
        "--fqbn", fqbn,
        "--duration", str(duration),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 120)
    # Combine stdout; the runner prints serial output to stdout
    output = result.stdout
    if result.returncode != 0:
        raise RuntimeError(
            f"Arduino runner failed (exit {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return output


def run_circuitpython(script: Path, port: str, cp_path: str, duration: float) -> str:
    """Copy script to CIRCUITPY and capture serial output."""
    cmd = [
        sys.executable, str(CIRCUITPYTHON_RUNNER),
        str(script),
        "--port", port,
        "--path", cp_path,
        "--duration", str(duration),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 60)
    output = result.stdout
    if result.returncode != 0:
        raise RuntimeError(
            f"CircuitPython runner failed (exit {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return output


# ---------------------------------------------------------------------------
# Comparison helper
# ---------------------------------------------------------------------------

def format_transaction_diff(
    arduino_txns: List[I2CTransaction],
    cp_txns: List[I2CTransaction],
) -> str:
    """Build a human-readable diff of two transaction lists."""
    lines: List[str] = []
    max_len = max(len(arduino_txns), len(cp_txns))
    lines.append(f"{'#':>4}  {'Arduino':<45}  {'CircuitPython':<45}  Match")
    lines.append("-" * 110)
    for i in range(max_len):
        a = str(arduino_txns[i]) if i < len(arduino_txns) else "<missing>"
        c = str(cp_txns[i]) if i < len(cp_txns) else "<missing>"
        match = "✓" if i < len(arduino_txns) and i < len(cp_txns) and arduino_txns[i] == cp_txns[i] else "✗"
        lines.append(f"{i:>4}  {a:<45}  {c:<45}  {match}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parametrized test
# ---------------------------------------------------------------------------

def _get_test_ids_and_params(use_output_files: bool):
    """Helper used at collection time to build the parametrize list."""
    if use_output_files:
        return discover_output_file_pairs()
    else:
        return discover_test_pairs()


def pytest_generate_tests(metafunc):
    """Dynamically parametrize the ``test_i2c_match`` test based on discovered
    test pairs and the ``--use-output-files`` flag."""
    if "test_name" in metafunc.fixturenames:
        use_output_files = metafunc.config.getoption("--use-output-files")
        pairs = _get_test_ids_and_params(use_output_files)
        ids = [p[0] for p in pairs]
        metafunc.parametrize("test_name,arduino_path,circuitpython_path", pairs, ids=ids)


def test_i2c_match(test_name, arduino_path, circuitpython_path, request):
    """Validate that I2C transactions from Arduino and CircuitPython match."""
    use_output_files = request.config.getoption("--use-output-files")

    if use_output_files:
        # Read pre-captured output files
        arduino_output = arduino_path.read_text()
        cp_output = circuitpython_path.read_text()
    else:
        # Run on actual hardware
        arduino_port = request.config.getoption("--arduino-port")
        arduino_fqbn = request.config.getoption("--arduino-fqbn")
        cp_port = request.config.getoption("--circuitpython-port")
        cp_path = request.config.getoption("--circuitpython-path")
        duration = request.config.getoption("--duration")

        arduino_output = run_arduino(arduino_path, arduino_port, arduino_fqbn, duration)
        cp_output = run_circuitpython(circuitpython_path, cp_port, cp_path, duration)

    # Parse I2C transactions from both outputs
    arduino_txns = parse_i2c_transactions(arduino_output)
    cp_txns = parse_i2c_transactions(cp_output)

    # Must have found at least one transaction in each
    assert len(arduino_txns) > 0, (
        f"No I2C transactions found in Arduino output for test '{test_name}'.\n"
        f"Raw output:\n{arduino_output}"
    )
    assert len(cp_txns) > 0, (
        f"No I2C transactions found in CircuitPython output for test '{test_name}'.\n"
        f"Raw output:\n{cp_output}"
    )

    # Compare
    diff = format_transaction_diff(arduino_txns, cp_txns)
    assert arduino_txns == cp_txns, (
        f"I2C transaction mismatch for test '{test_name}'!\n\n{diff}"
    )
