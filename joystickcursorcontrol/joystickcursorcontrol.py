import time
import serial
from pynput.mouse import Controller, Button

PORT = "COM4"
BAUD = 115200

mouse = Controller()

# Tuning
SPEED = 0.015   # higher = faster cursor
POWER = 1.6     # >1 makes center less sensitive, edges more sensitive
MAX_STEP = 30   # clamp per update so it doesn't jump

last_sw = 0

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def shape(v):
    """Nonlinear response curve for smoother control."""
    sign = -1 if v < 0 else 1
    v = abs(v)
    return sign * (v ** POWER)

def main():
    global last_sw
    print(f"Opening serial: {PORT} @ {BAUD}")
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        # Let ESP32 reset and start sending
        time.sleep(2.0)
        ser.reset_input_buffer()

        print("Running. Ctrl+C to stop.")
        while True:
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue

            # Expect: dx,dy,sw
            parts = line.split(",")
            if len(parts) != 3:
                continue

            try:
                dx = int(parts[0])
                dy = int(parts[1])
                sw = int(parts[2])
            except ValueError:
                continue

            # Convert dx/dy into pixel movement
            # (dy is usually inverted for natural feel; flip if needed)
            mx = int(clamp(shape(dx) * SPEED, -MAX_STEP, MAX_STEP))
            my = int(clamp(shape(dy) * SPEED, -MAX_STEP, MAX_STEP))

            if mx != 0 or my != 0:
                mouse.move(mx, my)

            # Click on press edge (0 -> 1)
            if sw == 1 and last_sw == 0:
                mouse.click(Button.left, 1)

            last_sw = sw

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
