#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Pytest script to run CircuitPython hardware tests found in hw_tests/.

Discovers every .py file in hw_tests/, runs each one on a connected
CircuitPython device via circuitpython_runner.py, captures the serial
output, and asserts that all PASS:/FAIL: sub-test markers show no failures.

Can also be run against pre-captured output files (*.out.txt) by using
the ``--use-output-files`` flag.

Usage:
    pytest test_hw_circuitpython.py -v
    pytest test_hw_circuitpython.py -v --use-output-files
    pytest test_hw_circuitpython.py -v --circuitpython-port /dev/ttyACM0
    pytest test_hw_circuitpython.py -v --circuitpython-port /dev/ttyACM0 --duration 90
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
HW_TESTS_DIR = BASE_DIR / "hw_tests"
CIRCUITPYTHON_RUNNER = BASE_DIR / "circuitpython_runner.py"


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

# Match pass/fail result lines across two conventions used in hw_tests:
#   Convention A (tests 00-11):  "PASS: description"  /  "FAIL: description"
#   Convention B (test 12):      "description: OK"    /  "FAIL: description"
# Summary lines ("ALL TESTS PASSED", "SOME TESTS FAILED") are intentionally excluded.
_PASS_RE = re.compile(r"(^\s*PASS:|:\s*OK\s*$)")
_FAIL_RE = re.compile(r"^\s*FAIL:")


def parse_hw_test_results(output: str) -> Tuple[List[str], List[str], bool]:
    """Parse hw_test output into (passed_lines, failed_lines, completed).

    Returns:
        passed_lines: list of lines whose content reports a sub-test PASS
        failed_lines: list of lines whose content reports a sub-test FAIL
        completed:    True if the ``~~END~~`` sentinel was found in the output
    """
    passed: List[str] = []
    failed: List[str] = []
    completed = False
    for line in output.splitlines():
        stripped = line.strip()
        if stripped == "~~END~~":
            completed = True
        elif _PASS_RE.match(stripped):
            passed.append(stripped)
        elif _FAIL_RE.match(stripped):
            failed.append(stripped)
    return passed, failed, completed


# ---------------------------------------------------------------------------
# Test discovery
# ---------------------------------------------------------------------------

def discover_hw_tests() -> List[Tuple[str, Path]]:
    """Return (test_name, script_path) for every .py file in hw_tests/."""
    tests: List[Tuple[str, Path]] = []
    if HW_TESTS_DIR.exists():
        for f in sorted(HW_TESTS_DIR.glob("*.py")):
            tests.append((f.stem, f))
    return tests


def discover_hw_test_output_files() -> List[Tuple[str, Path]]:
    """Return (test_name, output_path) for every *.out.txt in hw_tests/."""
    tests: List[Tuple[str, Path]] = []
    if HW_TESTS_DIR.exists():
        for f in sorted(HW_TESTS_DIR.glob("*.out.txt")):
            name = f.name.replace(".out.txt", "")
            tests.append((name, f))
    return tests


# ---------------------------------------------------------------------------
# Runner – copy script to device and capture serial output
# ---------------------------------------------------------------------------

def run_circuitpython(script: Path, port: str, cp_path: str, duration: float) -> str:
    """Copy *script* to CIRCUITPY and return the captured serial output."""
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
# pytest hooks
# ---------------------------------------------------------------------------

def pytest_generate_tests(metafunc):
    """Dynamically parametrize ``test_hw`` based on discovered hw_test files."""
    if "test_name" in metafunc.fixturenames:
        use_output_files = metafunc.config.getoption("--use-output-files")
        if use_output_files:
            tests = discover_hw_test_output_files()
        else:
            tests = discover_hw_tests()
        ids = [t[0] for t in tests]
        metafunc.parametrize("test_name,test_path", tests, ids=ids)


# ---------------------------------------------------------------------------
# Parametrized test
# ---------------------------------------------------------------------------

def test_hw(test_name, test_path, request):
    """Run a hw_test script on CircuitPython and assert all sub-tests pass."""
    use_output_files = request.config.getoption("--use-output-files")

    if use_output_files:
        output = test_path.read_text()
    else:
        cp_port = request.config.getoption("--circuitpython-port")
        cp_path = request.config.getoption("--circuitpython-path")
        duration = request.config.getoption("--duration")
        output = run_circuitpython(test_path, cp_port, cp_path, duration)

    passed, failed, completed = parse_hw_test_results(output)

    assert completed, (
        f"Test '{test_name}' did not complete (~~END~~ marker not found).\n"
        f"Raw output:\n{output}"
    )

    assert len(passed) + len(failed) > 0, (
        f"No PASS:/FAIL: results found in output for '{test_name}'.\n"
        f"Raw output:\n{output}"
    )

    assert len(failed) == 0, (
        f"Test '{test_name}' had {len(failed)} failure(s):\n"
        + "\n".join(f"  {line}" for line in failed)
        + f"\n\nAll results ({len(passed)} passed, {len(failed)} failed):\n"
        + "\n".join(f"  {line}" for line in passed + failed)
        + f"\n\nFull output:\n{output}"
    )
