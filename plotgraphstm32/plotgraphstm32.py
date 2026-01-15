import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

PORT = "COM8"      
BAUD = 115200
N = 500            

ser = serial.Serial(PORT, BAUD, timeout=1)
data = deque([0]*N, maxlen=N)

fig, ax = plt.subplots()
line, = ax.plot(list(data))
ax.set_ylim(0, 4095)
ax.set_title("STM32 ADC (Potentiometer)")
ax.set_xlabel("Sample")
ax.set_ylabel("ADC value (0-4095)")

def update(frame):
    # read a few lines per frame for smoother plot
    for _ in range(50):
        s = ser.readline().decode(errors="ignore").strip()
        if s.isdigit():
            data.append(int(s))
    line.set_ydata(list(data))
    return line,

ani = animation.FuncAnimation(fig, update, interval=30, blit=True)
plt.show()
