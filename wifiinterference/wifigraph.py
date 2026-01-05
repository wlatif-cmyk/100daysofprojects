import json, time
import serial
import matplotlib.pyplot as plt

PORT = "COM4"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)
ser.reset_input_buffer()

plt.ion()
fig, ax = plt.subplots()
channels = list(range(1,14))
bars = ax.bar(channels, [0]*13)

ax.set_title("ESP32-S3 Wi-Fi Channel Interference")
ax.set_xlabel("Channel")
ax.set_ylabel("Interference Score")
ax.set_xticks(channels)

while True:
    line = ser.readline().decode(errors="ignore").strip()
    if not line:
        continue

    try:
        msg = json.loads(line)
    except:
        continue

    if msg.get("event") != "scan":
        continue

    weights = msg["weight"]

    maxy = 1
    for i, v in enumerate(weights):
        bars[i].set_height(v)
        maxy = max(maxy, v)

    ax.set_ylim(0, maxy * 1.2)
    fig.canvas.draw()
    fig.canvas.flush_events()
