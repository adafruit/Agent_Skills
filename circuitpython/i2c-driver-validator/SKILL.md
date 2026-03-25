---
name: i2c-driver-validator
description: Write and run I2C driver validation tests that compare Arduino and CircuitPython I2C transactions for a given sensor/breakout. Use when validating that an Arduino driver and a CircuitPython driver produce equivalent I2C bus traffic for chip ID reads and all configuration register set/get operations.
license: MIT
metadata:
  version: "1.0"
  requires: ["python3", "pytest", "pyserial", "arduino-cli", "circuitpython device", "arduino device"]
---

# I2C Driver Validator Skill

This skill guides you through writing paired Arduino/CircuitPython test programs that exercise a sensor driver's chip ID and configuration registers, then compares the resulting I2C bus transactions to verify both drivers behave equivalently.

## When to Use This Skill

Use this skill when you need to:
- Validate that an Arduino driver and CircuitPython driver produce equivalent I2C traffic
- Test chip ID readback for a sensor breakout
- Test all valid values for each configuration register (range, data rate, mode, etc.)
- Catch driver-level differences in initialization sequences or register access patterns

## Requirements

- An Arduino board with the sensor breakout wired via I2C
- A CircuitPython board with the same type of sensor breakout wired via I2C
- Both boards connected to the host machine via USB
- `arduino-cli` installed and configured with the appropriate board core
- The Arduino driver library installed (e.g., via `arduino-cli lib install`)
- The CircuitPython driver library installed on the CIRCUITPY device
- The `adafruit_debug_i2c` library installed on the CIRCUITPY device
- Python 3 with `pytest` and `pyserial` in the virtual environment
- The Arduino driver must be compiled with `-DDEBUG_SERIAL=Serial` to enable I2C debug output from Adafruit BusIO

## Overview

The validation framework consists of:

1. **Paired test programs** — For each test, an Arduino sketch and a CircuitPython script that perform the same logical operations (init, set config, read back)
2. **Runner scripts** — `arduino_runner.py` compiles/uploads/captures Arduino serial output; `circuitpython_runner.py` copies code to CIRCUITPY and captures serial output
3. **Test harness** — `test_i2c_validation.py` (pytest) discovers test pairs, runs both, parses I2C debug lines, and asserts the transaction sequences match

The test harness auto-discovers pairs by matching names: an Arduino sketch directory `arduino_tests/XX_name/XX_name.ino` pairs with `circuitpython_tests/XX_name.py`.

## Step 1: Set Up the Test Directory Structure

Create a test directory for the sensor under your workspace. Copy the framework scripts from this skill's `scripts/` directory.

```
<sensor>_tests/
├── arduino_tests/          # Arduino sketch directories go here
├── circuitpython_tests/    # CircuitPython scripts go here
├── arduino_runner.py       # Copied from scripts/arduino_runner.py
├── circuitpython_runner.py # Copied from scripts/circuitpython_runner.py
├── test_i2c_validation.py  # Copied from scripts/test_i2c_validation.py
└── conftest.py             # Copied from scripts/conftest.py
```

## Step 2: Identify What to Test

Before writing tests, examine both the Arduino and CircuitPython driver source code. Identify:

1. **Chip ID register** — The WHO_AM_I or device ID register and its expected value
2. **Configuration registers** — All registers exposed by the driver with setter/getter methods or properties
3. **Valid values for each register** — The enum or constant values each configuration accepts

For each configuration property, plan a test that sets every valid value and reads it back.

### Typical test list for a sensor:

| Test | What it covers |
|------|---------------|
| `00_chipid` | Initialize sensor, verify chip ID, power down |
| `01_set_<config1>` | Set each valid value for config property 1 with readback verification |
| `02_set_<config2>` | Set each valid value for config property 2 with readback verification |
| ... | One test per configuration register/property |

## Step 3: Write the Arduino Test Sketch

Create a directory `arduino_tests/XX_name/` containing `XX_name.ino`.

### Template — Chip ID Test

```cpp
#include "<DriverLibrary>.h"
#include <Wire.h>

DriverClass sensor = DriverClass();

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  // Pre-reset: force sensor to known default state via raw I2C
  // before the library initializes with debug logging.
  // Write the reset value to the appropriate register.
  Wire.begin();
  Wire.beginTransmission(SENSOR_I2C_ADDRESS);
  Wire.write(RESET_REGISTER);
  Wire.write(RESET_VALUE);
  Wire.endTransmission();
  delay(20);

  Serial.println(F("Sensor Chip ID Test"));

  if (!sensor.begin_I2C()) {
    Serial.println(F("Failed to find sensor"));
    while (1) { delay(10); }
  }

  Serial.println(F("Sensor found!"));

  sensor.setOperationMode(POWER_DOWN_MODE);
  Serial.println("~~END~~");
}

void loop() { delay(10); }
```

### Template — Configuration Register Test

```cpp
#include "<DriverLibrary>.h"
#include <Wire.h>

DriverClass sensor = DriverClass();

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  // Pre-reset (see above)
  Wire.begin();
  Wire.beginTransmission(SENSOR_I2C_ADDRESS);
  Wire.write(RESET_REGISTER);
  Wire.write(RESET_VALUE);
  Wire.endTransmission();
  delay(20);

  Serial.println(F("Sensor Set <Config> Test"));

  if (!sensor.begin_I2C()) {
    Serial.println(F("Failed to find sensor"));
    while (1) { delay(10); }
  }

  Serial.println(F("Sensor found!"));

  // For each valid value:
  sensor.setConfig(VALUE_1);
  if (sensor.getConfig() == VALUE_1) {
    Serial.println(F("PASS: Config set to Value1"));
  } else {
    Serial.println(F("FAIL: Config readback mismatch for Value1"));
  }

  sensor.setConfig(VALUE_2);
  if (sensor.getConfig() == VALUE_2) {
    Serial.println(F("PASS: Config set to Value2"));
  } else {
    Serial.println(F("FAIL: Config readback mismatch for Value2"));
  }

  // ... repeat for all valid values ...

  sensor.setOperationMode(POWER_DOWN_MODE);
  Serial.println("~~END~~");
}

void loop() { delay(10); }
```

### Key Arduino patterns:
- Always include `<Wire.h>` for the pre-reset
- Use `Serial.begin(115200)` and `while (!Serial)` for reliable startup
- Print `PASS:` or `FAIL:` for each readback verification
- Always print `~~END~~` as the final line — the runner uses this as a sentinel to stop capturing
- End with power-down mode to leave the sensor in a known low-power state

## Step 4: Write the CircuitPython Test Script

Create `circuitpython_tests/XX_name.py`.

### Template — Chip ID Test

```python
# SPDX-FileCopyrightText: 2026 Your Name
# SPDX-License-Identifier: MIT

import time
import board
from adafruit_debug_i2c import DebugI2C
from driver_library import SensorClass, OperationMode

# Pre-reset: force sensor to known default state
# using a throwaway driver instance on the unwrapped I2C bus.
i2c = board.I2C()
reset_instance = SensorClass(i2c)
reset_instance.reset()
reset_instance = None
del reset_instance

debug_i2c = DebugI2C(i2c)
sensor = SensorClass(debug_i2c)

print("Sensor Chip ID Test")
print("Sensor found!")

sensor.operation_mode = OperationMode.POWER_DOWN
print("~~END~~")
```

### Template — Configuration Register Test

```python
# SPDX-FileCopyrightText: 2026 Your Name
# SPDX-License-Identifier: MIT

import time
import board
from adafruit_debug_i2c import DebugI2C
from driver_library import SensorClass, OperationMode, ConfigEnum

# Pre-reset
i2c = board.I2C()
reset_instance = SensorClass(i2c)
reset_instance.reset()
reset_instance = None
del reset_instance

debug_i2c = DebugI2C(i2c)
sensor = SensorClass(debug_i2c)

print("Sensor Set <Config> Test")
print("Sensor found!")

sensor.config = ConfigEnum.VALUE_1
assert sensor.config == ConfigEnum.VALUE_1, f"FAIL: Config readback mismatch for Value1 (got {sensor.config})"
print("PASS: Config set to Value1")

sensor.config = ConfigEnum.VALUE_2
assert sensor.config == ConfigEnum.VALUE_2, f"FAIL: Config readback mismatch for Value2 (got {sensor.config})"
print("PASS: Config set to Value2")

# ... repeat for all valid values ...

sensor.operation_mode = OperationMode.POWER_DOWN
print("~~END~~")
```

### Key CircuitPython patterns:
- **Pre-reset uses a throwaway driver instance** on the unwrapped `board.I2C()`, NOT raw `i2c.writeto()` calls. Raw bus writes may fail with `ETIMEDOUT` on some CircuitPython boards. The throwaway instance handles I2C addressing and retries through the driver's own I2C device management.
- `DebugI2C` wraps the I2C bus to produce debug output — only create it **after** the pre-reset so reset transactions are not logged
- Use `assert` with descriptive messages for readback verification
- Always print `~~END~~` as the final sentinel line

## Step 5: The Pre-Reset Pattern (Critical)

Both Arduino and CircuitPython tests **must** force the sensor into a known default state before the debug-logged initialization begins. Without this, residual register values from previous test runs cause mismatches in the read-modify-write sequences during `reset()`.

### Why it's needed

Both driver libraries use a **read-modify-write** pattern to set the soft-reset bit. If the sensor's control register has leftover bits from a previous run (e.g., range was set to 16G), the read phase returns a different value on each platform (because each has its own independent sensor), causing different write values even though the end result (sensor reset) is identical.

### Arduino pre-reset

```cpp
Wire.begin();
Wire.beginTransmission(SENSOR_I2C_ADDRESS);
Wire.write(RESET_REGISTER);    // e.g., 0x21 for LIS3MDL CTRL_REG2
Wire.write(RESET_BIT_VALUE);   // e.g., 0x04 for the SOFT_RST bit
Wire.endTransmission();
delay(20);
```

This uses raw `Wire` calls which are **not** captured by the Adafruit BusIO debug logging, so they don't appear in the transaction trace.

### CircuitPython pre-reset

```python
i2c = board.I2C()
reset_instance = SensorClass(i2c)
reset_instance.reset()
reset_instance = None
del reset_instance
```

This creates a throwaway driver instance on the **unwrapped** `board.I2C()` bus (not `DebugI2C`), so its transactions are not logged. The instance is then deleted before creating the real debug-wrapped instance.

**Important:** Do NOT use raw `i2c.writeto()` for the pre-reset. On some CircuitPython boards, raw bus writes to the sensor address fail with `OSError: [Errno 116] ETIMEDOUT`. Using a driver instance avoids this because the driver's `I2CDevice` handles addressing properly.

## Step 6: Run the Tests

From inside the `<sensor>_tests/` directory:

```bash
# Run all tests on hardware with default ports
pytest test_i2c_validation.py -v

# Specify ports and board type
pytest test_i2c_validation.py -v \
  --arduino-port /dev/ttyUSB0 \
  --arduino-fqbn arduino:avr:uno \
  --circuitpython-port /dev/ttyACM0 \
  --circuitpython-path /media/timc/CIRCUITPY/

# Run a single test
pytest test_i2c_validation.py -v -k "01_set_range"

# Increase timeout for slow tests
pytest test_i2c_validation.py -v --duration 60
```

The Arduino sketches are compiled with `-DDEBUG_SERIAL=Serial` by default (set in `arduino_runner.py`), which enables I2C debug output from the Adafruit BusIO library. CircuitPython gets equivalent debug output from the `adafruit_debug_i2c` wrapper.

## Step 7: Evaluate Test Output and Diagnose Common Issues

When a test fails, the output shows a side-by-side transaction comparison with ✓/✗ markers. Here's how to diagnose the most common failure patterns:

### Issue 1: Different read values during reset (residual register state)

**Symptom:** Mismatch in the first few transactions after chip ID check, during the reset read-modify-write. One side reads `0x00` while the other reads a non-zero value.

```
   3  I2CREAD @ 0x1C :: 0x60                         I2CREAD @ 0x1C :: 0x00                         ✗
   4  I2CWRITE @ 0x1C :: 0x21, 0x64                  I2CWRITE @ 0x1C :: 0x21, 0x04                  ✗
```

**Cause:** The sensor retains register values from previous test runs. Since the Arduino and CircuitPython boards have separate sensor chips, they may start with different residual state.

**Fix:** Add the pre-reset pattern (Step 5) to both tests. This forces both sensors to default state before the debug-logged initialization.

### Issue 2: One side has extra read-modify-write transactions (redundant register writes)

**Symptom:** Transactions shift out of alignment partway through. One side has extra read/write pairs that write the same value back (no actual change).

```
   5  I2CWRITE @ 0x1C :: 0x21                        I2CWRITE @ 0x1C :: 0x20                        ✗
```

**Cause:** The drivers' initialization sequences differ. Common examples:
- **Arduino reads back a register after reset** (e.g., calling `getRange()` inside `reset()`) while CircuitPython doesn't
- **CircuitPython sets a property redundantly** — e.g., the `data_rate` setter internally sets `performance_mode`, but `__init__` already set `performance_mode` explicitly right before, causing duplicate register writes

**Diagnosis:** Map each transaction to a register address using the datasheet. Identify which extra read-modify-write sequences one side has. Trace through both drivers' `__init__`/`_init` code to find where the extra calls originate.

**This is a real driver difference** — it represents a finding about how the two drivers diverge. It may or may not need fixing depending on whether the extra transactions are functionally meaningful.

### Issue 3: Timing-dependent register values (transient hardware states)

**Symptom:** A single READ transaction differs despite the surrounding writes being identical. The differing values are both "valid" states for that register.

```
  33  I2CREAD @ 0x1C :: 0x03                         I2CREAD @ 0x1C :: 0x01                         ✗
```

**Cause:** Some sensor modes trigger automatic hardware state transitions. For example, the LIS3MDL's SINGLE measurement mode (0x01) automatically transitions to POWER_DOWN (0x03) after the measurement completes. If one platform reads the register faster than the other, it catches a different phase of the transition.

**Fix:** Add a small delay (e.g., `delay(100)` / `time.sleep(0.1)`) in **both** tests after setting the transient mode, before the next operation. This ensures the hardware transition completes on both platforms before proceeding. The delay must be added to both Arduino and CircuitPython tests so the resulting transaction sequences remain aligned.

### Issue 4: Transaction count mismatch (missing or extra transactions)

**Symptom:** One side has `<missing>` entries at the end of the diff.

```
  25  <missing>                                      I2CWRITE @ 0x1C :: 0x22, 0x00                  ✗
```

**Cause:** The drivers perform different numbers of register operations. This is usually a combination of Issue 2 (redundant writes in one driver). Count the operations each driver performs and trace through the source to understand why.

### General diagnosis approach:

1. **Find the first ✗ line** — everything before it matched, so the divergence starts there
2. **Look up the register address** — the first byte in an I2CWRITE is the register address. Check the datasheet or driver header to identify which register is involved
3. **Determine the operation type** — Is it a read-modify-write (WRITE addr → READ → WRITE addr,value)? A direct write? A readback?
4. **Trace through both drivers' source code** — follow the init sequence and the specific setter/getter being tested to find where the operations diverge
5. **Categorize the issue** — residual state (fix with pre-reset), redundant writes (driver difference finding), timing (fix with delay), or a genuine bug

## Tips and Best Practices

1. **Number tests with a two-digit prefix** (`00_`, `01_`, `02_`, ...) so they run in a predictable order
2. **Start with `00_chipid`** — it validates basic connectivity and chip identification before testing configuration
3. **One configuration register per test** — keeps tests focused and failures easy to diagnose
4. **Always verify readback** — after setting each value, read it back and assert/check it matches. This validates the getter independently of the I2C transaction comparison
5. **Print PASS/FAIL for each value** — makes it easy to spot which specific value caused a readback failure in the serial output
6. **End every test with power-down mode** — leaves the sensor in a known low-power state for the next test
7. **End every test with `~~END~~`** — the runner scripts use this sentinel to stop capturing output
8. **Consult the sensor datasheet** for register addresses, bit field layouts, and any auto-transition behaviors that might need delays
9. **Check both drivers' source code** before writing tests to understand their init sequences and identify potential divergence points
10. **When a test fails, examine the serial output** (not just the transaction diff) to check for `FAIL:` lines indicating readback mismatches independent of the I2C comparison
