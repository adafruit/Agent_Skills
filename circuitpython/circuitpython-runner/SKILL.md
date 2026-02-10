---
name: circuitpython-runner
description: Run CircuitPython code on a connected CircuitPython device and read the output. Use when testing CircuitPython code, debugging hardware interactions, or working with microcontrollers.
license: MIT
metadata:
  version: "1.0"
  requires: ["python3", "circuitpython device"]
---

# CircuitPython Runner Skill

This skill enables you to run CircuitPython code on a connected CircuitPython device and capture the output.

## When to Use This Skill

Use this skill when you need to:
- Test CircuitPython code on actual hardware
- Debug sensor readings or hardware interactions
- Prototype microcontroller applications
- Verify CircuitPython library functionality
- Run code that requires physical hardware (displays, sensors, LEDs, etc.)

## Requirements

- A CircuitPython-compatible device connected and mounted
- Python 3 installed on the host system
- pyserial installed inside the python virtual environment
- The `circuitpython_run_and_read_output.py` script available in the skills scripts/ directory

## How It Works

The CircuitPython device appears as a USB drive. After you save code to `code.py` on the device, run the helper script to execute the code on the CircuitPython device and capture serial output.

## Usage Instructions

### Step 1: Write the CircuitPython Code

Save your CircuitPython code to `code.py` on the CircuitPython device. 

**Example:**
```python
# Simple blink example
import time
import board
import digitalio

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

for i in range(5):
    led.value = True
    print(f"LED ON - iteration {i+1}")
    time.sleep(0.5)
    led.value = False
    print(f"LED OFF - iteration {i+1}")
    time.sleep(0.5)

print("Done!")
```

### Step 2: Run the Output Reader Script

After saving the code, immediately run the `circuitpython_run_and_read_output.py` script to execute the code and capture the device's output:

```bash
python3 circuitpython_run_and_read_output.py
```

The script will:
1. Connect to the CircuitPython device's serial port
2. Run the code by issuing ctrl+C and ctrl+D inputs
3. Capture and display all printed output
4. Return after 10 seconds or the time specified by the --duration argument

## Complete Workflow Example

```bash
# 1. Save your code to the device
cat > /path/to/CIRCUITPY/code.py << 'EOF'
import time
print("Hello from CircuitPython!")
for i in range(3):
    print(f"Count: {i}")
    time.sleep(1)
print("Goodbye!")
EOF

# 2. Run the output reader
python3 circuitpython_run_and_read_output.py
```

## Common Patterns

### Sensor Reading
```python
import board
import adafruit_dht

dht = adafruit_dht.DHT22(board.D4)
try:
    temperature = dht.temperature
    humidity = dht.humidity
    print(f"Temp: {temperature}°C, Humidity: {humidity}%")
except RuntimeError as e:
    print(f"Error reading sensor: {e}")
```

### I2C Device Communication
```python
import board
import busio

i2c = busio.I2C(board.SCL, board.SDA)
while not i2c.try_lock():
    pass

print("I2C devices found:", [hex(addr) for addr in i2c.scan()])
i2c.unlock()
```

### NeoPixel Control
```python
import board
import neopixel

pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3)
pixels[0] = (255, 0, 0)  # Red
print("NeoPixel set to red")
```

## Tips and Best Practices

1. **Always include print statements** - The output reader captures printed text, so add informative print statements to track execution
2. **Handle errors gracefully** - Use try-except blocks to catch and report errors without crashing
3. **Keep code concise** - CircuitPython devices have limited memory; keep your test code focused
4. **Add delays when needed** - Some hardware operations need time to complete; use `time.sleep()` appropriately
5. **Import only what you need** - Minimize imports to reduce memory usage

## Common Edge Cases

- **Device not mounted**: If `CIRCUITPY/` is not accessible, as the user to check that the device is properly connected and recognized by the system
- **Permission errors**: You may need appropriate permissions to write to the mounted device path
- **Code syntax errors**: If the code has syntax errors, the device will display an error message that the script should capture
- **Infinite loops**: If your code contains an infinite loop without output, the reader script may timeout
- **Import errors**: If libraries are missing from the device, you'll see ImportError messages in the output

## Troubleshooting

**No output received**: 
- Ask the user to verify the device is connected and mounted
- Check that the serial port is accessible
- Ensure your code contains print statements

**Script timeouts**:
- The output reader has a --duration argument to control the timeout length
- Ensure your CircuitPython code completes in a reasonable time
- Add a final print statement to signal completion