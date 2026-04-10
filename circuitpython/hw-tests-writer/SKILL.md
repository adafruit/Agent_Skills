# Writing CircuitPython Hardware Tests from Arduino Hardware Tests

This skill covers converting Arduino `.ino` hardware test sketches into
CircuitPython `.py` scripts that run on a CircuitPython device and produce
output compatible with `test_hw_circuitpython.py` from the `hw-tests-runner`
skill.

---

## 1. File Layout and Naming

- Place all CircuitPython hardware test scripts in a single flat directory
  (e.g. `circuitpython_hw_tests/` or `hw_tests/`).
- One test per `.py` file. Name files with a two-digit numeric prefix and a
  short snake_case descriptor:
  ```
  00_lux.py
  01_mode.py
  02_cdr.py
  03_integration_time.py
  04_interrupt.py
  05_threshold.py
  ```
- The numeric prefix controls execution order and keeps filenames sorted
  logically.

---

## 2. Output Format

The test runner (`test_hw_circuitpython.py`) parses serial output with two
regex patterns and one sentinel:

| Pattern | Regex | Example |
|---------|-------|---------|
| Pass (Convention A) | `^\s*PASS:` | `PASS: Sensor found` |
| Pass (Convention B) | `:\s*OK\s*$` | `Upper 10.0 -> 11.25: OK` |
| Fail | `^\s*FAIL:` | `FAIL: Sensor found` |
| Completion sentinel | exact match `~~END~~` | `~~END~~` |

Rules:
- Every sub-test **must** print exactly one `PASS:` or `FAIL:` line.
- The script **must** print `~~END~~` when finished, whether it passed or
  failed. This lets the `circuitpython_runner` return early instead of
  waiting for the full duration timeout.
- Summary lines like `ALL TESTS PASSED` are fine for human readability but
  are ignored by the parser.
- Informational `print()` lines (raw values, debug info) are fine as long as
  they don't accidentally match the pass/fail regexes.

---

## 3. Script Structure (Template)

Every test script should follow this skeleton:

```python
# SPDX-FileCopyrightText: 2026 Your Name for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Hardware test: <one-line description of what this tests>.
"""

import time
import board
import busio
import adafruit_yourdriver

passed = 0
failed = 0


def test(name, condition):
    global passed, failed
    if condition:
        print(f"PASS: {name}")
        passed += 1
    else:
        print(f"FAIL: {name}")
        failed += 1


try:
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_yourdriver.YourDriver(i2c)
    test("Sensor found", True)

    # --- Test sections go here ---

    print()
    print(f"=== Summary: {passed} passed, {failed} failed ===")
    print("ALL TESTS PASSED" if passed > 0 and failed == 0 else "SOME TESTS FAILED")

except Exception as e:
    print(f"FAIL: Unhandled exception: {e}")

print("~~END~~")
```

Key points:
- The `try/except` ensures `~~END~~` is always printed even if the driver
  fails to initialize or an unexpected error occurs.
- The `test()` helper keeps pass/fail formatting consistent.
- `~~END~~` is **outside** the try/except so it runs unconditionally.

---

## 4. Translation Reference: Arduino to CircuitPython

### 4.1 Initialization

| Arduino | CircuitPython |
|---------|---------------|
| `#include <Wire.h>` | `import board, busio` |
| `Wire.begin()` | `i2c = busio.I2C(board.SCL, board.SDA)` |
| `Adafruit_SENSOR sensor;` | `sensor = adafruit_driver.Driver(i2c)` |
| `sensor.begin()` returns bool | Constructor raises `RuntimeError` on failure; wrap in try/except |

### 4.2 Timing

| Arduino | CircuitPython |
|---------|---------------|
| `delay(ms)` | `time.sleep(seconds)` — note the unit change |
| `millis()` | `time.monotonic()` — returns float seconds |
| Elapsed: `millis() - start` (ms) | `time.monotonic() - start` (seconds) |

When converting timing thresholds from Arduino (milliseconds) to
CircuitPython (seconds), divide by 1000. For example, an Arduino check like
`manualTime >= 400 && manualTime <= 1500` becomes
`0.4 <= manual_time <= 1.5`.

### 4.3 Serial Output

| Arduino | CircuitPython |
|---------|---------------|
| `Serial.begin(115200)` | Not needed; `print()` goes to serial automatically |
| `Serial.println(F("text"))` | `print("text")` |
| `Serial.print(value); Serial.println();` | `print(f"{value}")` |
| `while (!Serial) delay(10);` | Not needed in CircuitPython |

### 4.4 GPIO / Digital I/O

| Arduino | CircuitPython |
|---------|---------------|
| `#define INT_PIN 2` | `INT_PIN = board.D2` |
| `pinMode(pin, INPUT_PULLUP)` | `pin = digitalio.DigitalInOut(board.D2)` then `pin.direction = digitalio.Direction.INPUT` and `pin.pull = digitalio.Pull.UP` |
| `digitalRead(pin)` returns `HIGH`/`LOW` | `pin.value` returns `True`/`False` |
| N/A (automatic cleanup) | `pin.deinit()` when done (good practice) |

### 4.5 NaN Checks

| Arduino | CircuitPython |
|---------|---------------|
| `isnan(value)` | `value != value` (NaN is the only float that is not equal to itself) or `import math; math.isnan(value)` |

### 4.6 Properties vs Methods

Arduino Adafruit drivers typically use getter/setter methods. CircuitPython
drivers use Python properties. Map them accordingly:

| Arduino | CircuitPython |
|---------|---------------|
| `sensor.readLux()` | `sensor.lux` |
| `sensor.setMode(MODE_X)` | `sensor.mode = Mode.X` |
| `sensor.getMode()` | `sensor.mode` |
| `sensor.enableInterrupt(true)` | `sensor.interrupt_enabled = True` |
| `sensor.isInterruptEnabled()` | `sensor.interrupt_enabled` |
| `sensor.setUpperThreshold(val)` | `sensor.upper_threshold = val` |
| `sensor.getUpperThreshold()` | `sensor.upper_threshold` |

### 4.7 Enum / Constant Values

Arduino uses `#define` or `enum` constants like `MAX44009_MODE_CONTINUOUS`.
CircuitPython drivers use CV (constant-value) classes:

| Arduino | CircuitPython |
|---------|---------------|
| `MAX44009_MODE_CONTINUOUS` | `Mode.CONTINUOUS` |
| `MAX44009_INTEGRATION_800MS` | `IntegrationTime.MS_800` |

Import these from the driver module:
```python
from adafruit_yourdriver import Mode, IntegrationTime
```

### 4.8 Raw Register Access

Sometimes tests need to read raw registers to verify hardware behavior
(e.g., that a config bit actually changed the ADC encoding). In Arduino this
is done with `Adafruit_BusIO_Register`. In CircuitPython, use the driver
object's underlying `i2c_device`:

```python
import struct

def read_raw_register(sensor, reg_addr, num_bytes):
    """Read raw bytes from a register via the driver's I2C device."""
    buf = bytearray(num_bytes)
    with sensor.i2c_device as i2c:
        i2c.write_then_readinto(bytes([reg_addr]), buf)
    return buf

# Example: read 16-bit big-endian value from register 0x03
raw = struct.unpack(">H", read_raw_register(sensor, 0x03, 2))[0]
```

### 4.9 Arduino `setup()` / `loop()` Structure

Arduino sketches split into `setup()` (runs once) and `loop()` (runs
forever). Hardware tests typically do all work in `setup()` and leave
`loop()` empty. In CircuitPython, just write the test as top-level code —
there is no setup/loop distinction.

The Arduino `while (1) delay(10);` halt-on-error pattern becomes a
try/except at the top level, or simply printing `FAIL:` and falling through.

---

## 5. Timing-Sensitive Tests

Some tests measure how long the sensor takes to update (e.g., verifying that
different integration times produce different measurement rates). These
require special care:

1. **Use `time.monotonic()`** for elapsed time measurement, not
   `time.time()`.
2. **Units are seconds** (float), not milliseconds.
3. **Poll in a tight loop** with a small `time.sleep()` (1-2ms) between
   reads to avoid flooding the I2C bus.
4. **Use median-of-N** (typically 3 runs) for stability — timing on
   microcontrollers can be noisy.
5. **Allow wide tolerances** — CircuitPython's I2C overhead and garbage
   collector pauses add latency compared to Arduino. If the Arduino test
   checks `< 50ms`, the CircuitPython test may need `< 100ms`.
6. **Settle time**: after changing a sensor configuration, sleep long enough
   for the sensor to complete at least one measurement cycle before starting
   to measure timing.

---

## 6. Common Pitfalls

- **Forgetting `~~END~~`**: If the script crashes before printing `~~END~~`,
  the runner waits for the full duration timeout. The try/except/`~~END~~`
  pattern prevents this.
- **Accidental regex matches**: Don't print lines starting with `PASS:` or
  `FAIL:` unless they are actual test results. Debug output like
  `"PASS through filter: 42"` would be miscounted.
- **Delay units**: Arduino `delay()` takes milliseconds; `time.sleep()` takes
  seconds. This is the most common conversion bug.
- **Boolean comparisons**: Arduino `digitalRead()` returns `HIGH` (1) or
  `LOW` (0). CircuitPython `pin.value` returns `True`/`False`. Compare
  accordingly.
- **Missing deinit**: CircuitPython pins should be `deinit()`ed when no
  longer needed, especially in test scripts that may be run repeatedly.
- **I2C bus locking**: When doing raw register reads via `with sensor.i2c_device as i2c:`,
  the bus is locked for the duration of the `with` block. Keep these blocks
  short.
- **No `goto`**: Arduino tests sometimes use `goto summary;` for early exit
  on init failure. In CircuitPython, the try/except structure handles this
  naturally — any exception skips to the except block, then `~~END~~` prints.

---

## 7. Checklist

Before considering a conversion complete:

- [ ] File has a two-digit numeric prefix and descriptive name
- [ ] SPDX license header is present
- [ ] Module docstring describes what the test verifies
- [ ] `test()` helper uses `PASS:` / `FAIL:` format
- [ ] All test logic is inside a `try/except`
- [ ] `~~END~~` is printed unconditionally at the end (outside try/except)
- [ ] All Arduino `delay(ms)` converted to `time.sleep(seconds)`
- [ ] All Arduino method calls mapped to CircuitPython properties
- [ ] All Arduino constants mapped to CircuitPython CV class values
- [ ] Timing thresholds adjusted for CircuitPython overhead if needed
- [ ] GPIO pins are `deinit()`ed after use
- [ ] Sensor state is restored to defaults at end of test
- [ ] No lines accidentally match `PASS:` or `FAIL:` regex patterns
- [ ] Test can be run standalone on a CircuitPython device as `code.py`
