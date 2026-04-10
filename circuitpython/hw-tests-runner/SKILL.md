# Running CircuitPython Hardware Tests

A pytest-based framework for running functional hardware tests on a CircuitPython device and reporting pass/fail results per test script.

---

## Repository layout

```
<driver-repo>/
├── hw_tests/                    # One .py script per hardware test
│   ├── 00_als_neopixel.py
│   ├── 01_proximity_servo.py
│   └── ...
├── circuitpython_runner.py      # Copies code.py to CIRCUITPY, reads serial output
├── conftest.py                  # Registers shared pytest CLI options
└── test_hw_circuitpython.py     # Pytest script – discovers and runs all hw_tests
```

---

## How it works

1. **Discovery** – `test_hw_circuitpython.py` scans `hw_tests/` for `*.py` files (sorted by filename) and creates one parametrized pytest test per file: `test_hw[<stem>]`.
2. **Execution** – Each script is copied to the CIRCUITPY drive as `code.py` via `circuitpython_runner.py`, which then reads serial output until the `~~END~~` sentinel is received or the duration timeout elapses.
3. **Parsing** – The output is scanned for result lines:
   - **Pass** – lines matching `PASS: …` or ending in `: OK`
   - **Fail** – lines matching `FAIL: …`
4. **Assertions** – The test fails in pytest if:
   - `~~END~~` was never received (script crashed or timed out)
   - No `PASS:`/`FAIL:` result lines were found at all
   - One or more `FAIL:` lines were present

---

## Running the tests

### Prerequisites

- CircuitPython device connected via USB
- CIRCUITPY drive mounted (default: `/media/<user>/CIRCUITPY/`)
- Serial port available (default: `/dev/ttyACM0`)
- Python environment with `pytest` and `pyserial` installed

### Basic run (live hardware)

```bash
pytest test_hw_circuitpython.py -v
```

### Specify port and mount path

```bash
pytest test_hw_circuitpython.py -v \
    --circuitpython-port /dev/ttyACM0 \
    --circuitpython-path /media/user/CIRCUITPY/
```

### Increase timeout for slow tests

```bash
pytest test_hw_circuitpython.py -v --duration 120
```

### Run a single test by name

```bash
pytest test_hw_circuitpython.py -v -k 12_interrupt_pin
```

### Run against pre-captured output files

Save output from a real run as `hw_tests/<name>.out.txt`, then replay offline:

```bash
pytest test_hw_circuitpython.py -v --use-output-files
```

---

## CLI options reference

| Option | Default | Description |
|---|---|---|
| `--circuitpython-port` | `/dev/ttyACM0` | Serial port of the CircuitPython device |
| `--circuitpython-path` | `/media/timc/CIRCUITPY/` | Mount path of the CIRCUITPY drive |
| `--duration` | `60.0` | Seconds to wait for each test to complete |
| `--use-output-files` | `False` | Read `hw_tests/*.out.txt` instead of running on hardware |

Options are registered in `conftest.py` and apply to all test files in the repository.

---

## Adapting to a different driver

To reuse this framework for a different CircuitPython driver:

1. Copy `circuitpython_runner.py`, `conftest.py`, and `test_hw_circuitpython.py` into the new driver repo (no changes needed).
2. Create an `hw_tests/` directory and populate it with test scripts following the conventions above.
3. Update the `--circuitpython-path` default in `conftest.py` if the CIRCUITPY mount path differs on the target machine.
4. Run `pytest test_hw_circuitpython.py -v`.
