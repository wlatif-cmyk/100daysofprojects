import cv2
import mediapipe as mp
import serial
import time
import math

#CONFIG
ARDUINO_PORT = "COM3"
BAUD_RATE = 9600

MIN_DIST = 0.02   # fingers very close (in normalized units)
MAX_DIST = 0.30   # fingers far apart

#SERIAL SETUP
try:
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # give Arduino time to reset
    print(f"Connected to Arduino on {ARDUINO_PORT}")
except Exception as e:
    print("Could not open serial port. Check ARDUINO_PORT.")
    print(e)
    ser = None

# ==== MEDIAPIPE HANDS SETUP ====
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

cap = cv2.VideoCapture(0)  # 0 = default camera

def map_value(x, in_min, in_max, out_min, out_max):
    # Clamp
    if x < in_min:
        x = in_min
    if x > in_max:
        x = in_max
    # Linear map
    return out_min + (out_max - out_min) * (x - in_min) / (in_max - in_min)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Flip for selfie view (optional)
    frame = cv2.flip(frame, 1)

    # Convert to RGB for MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    brightness = 0
    info_text = "No hand"

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]

        # Thumb tip = landmark 4, index tip = landmark 8
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]

        # Landmarks are normalized (0-1)
        dx = thumb_tip.x - index_tip.x
        dy = thumb_tip.y - index_tip.y
        distance = math.sqrt(dx*dx + dy*dy)

        # Map distance to brightness:
        # fingers close (MIN_DIST) -> 255 (bright)
        # fingers far (MAX_DIST) -> 0 (dim)
        brightness = int(map_value(distance, MIN_DIST, MAX_DIST, 255, 0))
        brightness = max(0, min(255, brightness))

        info_text = f"dist={distance:.3f}  brightness={brightness}"

        # Draw landmarks and a line between thumb & index
        h, w, _ = frame.shape
        thumb_px = (int(thumb_tip.x * w), int(thumb_tip.y * h))
        index_px = (int(index_tip.x * w), int(index_tip.y * h))
        cv2.line(frame, thumb_px, index_px, (255, 255, 255), 2)
        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    # Send brightness to Arduino (if serial is open)
    if ser is not None:
        try:
            ser.write(f"{brightness}\n".encode())
        except Exception as e:
            print("Serial write error:", e)

    # Put text on the frame
    cv2.putText(frame, info_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow("Thumb-Index LED Control", frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
if ser is not None:
    ser.close()
