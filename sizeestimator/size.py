import cv2
import mediapipe as mp
import serial
import time
import numpy as np
import pyautogui

# Try to import brightness library safely
try:
    import screen_brightness_control as sbc
    BRIGHTNESS_AVAILABLE = True
except ImportError:
    print("[WARN] screen_brightness_control not installed. Brightness control will be disabled.")
    BRIGHTNESS_AVAILABLE = False

# CONFIG 
SERIAL_PORT = "COM3"   
BAUD_RATE = 9600

CLOSE_TOGGLE_CM = 5.0      # hand closer than this = toggle ON/OFF
TOGGLE_COOLDOWN = 1.0      # seconds between toggles

ANGLE_TRIGGER = 2.5        # radians of twist to trigger (~140 deg)
GESTURE_COOLDOWN = 0.8     # seconds between volume gesture triggers

# BRIGHTNESS CONFIG
BRIGHTNESS_COOLDOWN = 0.4  # seconds between brightness changes

# VOLUME 
def change_volume(delta):
    if delta > 0:
        pyautogui.press("volumeup")
        print("[INFO] Volume UP")
    elif delta < 0:
        pyautogui.press("volumedown")
        print("[INFO] Volume DOWN")

# BRIGHTNESS 
def set_brightness_level_from_fingers(finger_count):
    """
    Map 0–5 fingers to brightness:
      0 -> 0%
      1 -> 20%
      2 -> 40%
      3 -> 60%
      4 -> 80%
      5 -> 100%
    """
    if not BRIGHTNESS_AVAILABLE:
        print(f"[INFO] (Fake) set brightness for {finger_count} fingers (brightness lib not installed)")
        return

    # clamp 0..5 just in case
    finger_count = max(0, min(5, finger_count))

    if finger_count == 0:
        target = 0
    else:
        target = int((finger_count / 5) * 100)

    try:
        sbc.set_brightness(target, display=0)
        print(f"[INFO] Brightness set to {target}% for {finger_count} fingers")
    except Exception as e:
        print("[WARN] Could not change brightness:", e)

# SERIAL
def open_serial(port, baud_rate):
    try:
        ser = serial.Serial(port, baud_rate, timeout=0.1)
        time.sleep(2)
        print(f"[INFO] Serial connected on {port}")
        return ser
    except Exception as e:
        print("[WARN] Could not open serial:", e)
        return None

def read_distance_cm(ser):
    if ser is None or not ser.in_waiting:
        return None
    try:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line or line == "NaN":
            return None
        return float(line)
    except:
        return None

# MAIN
mp_hands = mp.solutions.hands

def count_fingers(lm, handedness_label):
    """
    Count how many fingers are up using Mediapipe landmarks.
    lm: landmarks list
    handedness_label: 'Left' or 'Right'
    """
    fingers = []

    # Indices for each fingertip and corresponding joint
    tip_ids = [4, 8, 12, 16, 20]

    # Thumb
    # Use x comparison because thumb bends sideways
    if handedness_label == "Right":
        # Right hand: thumb is open if tip is to the left of IP joint (x smaller)
        if lm.landmark[tip_ids[0]].x < lm.landmark[tip_ids[0] - 1].x:
            fingers.append(1)
        else:
            fingers.append(0)
    else:
        # Left hand: thumb is open if tip is to the right of IP joint (x larger)
        if lm.landmark[tip_ids[0]].x > lm.landmark[tip_ids[0] - 1].x:
            fingers.append(1)
        else:
            fingers.append(0)

    # Other four fingers: compare y of tip and PIP joint
    for i in range(1, 5):
        # If tip is above joint (smaller y), finger is up
        if lm.landmark[tip_ids[i]].y < lm.landmark[tip_ids[i] - 2].y:
            fingers.append(1)
        else:
            fingers.append(0)

    return sum(fingers)

def main():
    ser = open_serial(SERIAL_PORT, BAUD_RATE)

    cap = cv2.VideoCapture(0)   # if this fails, try 1 or 2
    if not cap.isOpened():
        print("[ERROR] Could not open camera (try changing VideoCapture index to 1 or 2)")
        return

    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5
    )

    last_angle = None
    cumulative_angle = 0.0
    last_gesture_time = 0.0

    features_enabled = True
    last_distance = None

    was_close = False
    last_toggle_time = 0.0

    # brightness state
    last_finger_count = None
    last_brightness_time = 0.0

    # MODE: "volume" or "brightness"
    mode = "volume"  # start in volume mode

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read from camera")
            break

        h, w = frame.shape[:2]
        now = time.time()

        # ULTRASONIC TOGGLE
        d = read_distance_cm(ser)
        if d is not None:
            last_distance = d
            close_now = d < CLOSE_TOGGLE_CM

            if close_now and not was_close and (now - last_toggle_time > TOGGLE_COOLDOWN):
                features_enabled = not features_enabled
                last_toggle_time = now
                print(f"[INFO] Features toggled to: {features_enabled}")

            was_close = close_now

        # HAND TRACKING
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        fingertip_angle = None
        brightness_text = ""
        volume_text = ""
        fingers_up = None

        if result.multi_hand_landmarks:
            lm = result.multi_hand_landmarks[0]

            # handedness info (Left or Right)
            handedness_label = "Right"
            if result.multi_handedness:
                handedness_label = result.multi_handedness[0].classification[0].label

            # fingertip (index) for twist angle
            x_tip = lm.landmark[8].x * w
            y_tip = lm.landmark[8].y * h

            # hand center reference
            x_wrist = lm.landmark[0].x * w
            y_wrist = lm.landmark[0].y * h
            x_mcp = lm.landmark[9].x * w
            y_mcp = lm.landmark[9].y * h
            cx = (x_wrist + x_mcp) / 2.0
            cy = (y_wrist + y_mcp) / 2.0

            dx = x_tip - cx
            dy = y_tip - cy
            fingertip_angle = np.arctan2(dy, dx)

            # draw markers
            cv2.circle(frame, (int(x_tip), int(y_tip)), 8, (0, 255, 0), -1)
            cv2.circle(frame, (int(cx), int(cy)), 6, (0, 200, 255), -1)
            cv2.line(frame, (int(cx), int(cy)), (int(x_tip), int(y_tip)),
                     (0, 255, 255), 2)

            # --- FINGER COUNT FOR BRIGHTNESS ---
            fingers_up = count_fingers(lm, handedness_label)

        # --- VOLUME: twist gesture (only in VOLUME mode) ---
        if features_enabled and mode == "volume" and fingertip_angle is not None:
            if last_angle is not None:
                diff = fingertip_angle - last_angle
                if diff > np.pi:
                    diff -= 2 * np.pi
                if diff < -np.pi:
                    diff += 2 * np.pi
                cumulative_angle += diff
            last_angle = fingertip_angle
        else:
            last_angle = None
            cumulative_angle = 0.0

        if features_enabled and mode == "volume" and abs(cumulative_angle) > ANGLE_TRIGGER:
            if (now - last_gesture_time) > GESTURE_COOLDOWN:
                if cumulative_angle > 0:
                    change_volume(+1)
                    volume_text = "Volume UP"
                else:
                    change_volume(-1)
                    volume_text = "Volume DOWN"

                last_gesture_time = now

            cumulative_angle = 0.0
            last_angle = None

        # --- BRIGHTNESS: based on number of fingers up (only in BRIGHTNESS mode) ---
        if features_enabled and mode == "brightness" and fingers_up is not None:
            # change brightness only when finger count changes and cooldown passed
            if (last_finger_count is None or fingers_up != last_finger_count) and \
               (now - last_brightness_time) > BRIGHTNESS_COOLDOWN:

                set_brightness_level_from_fingers(fingers_up)
                last_brightness_time = now
                last_finger_count = fingers_up

                if fingers_up == 0:
                    brightness_text = "Brightness: 0% (0 fingers)"
                else:
                    level = int((fingers_up / 5) * 100)
                    brightness_text = f"Brightness: {level}% ({fingers_up} fingers)"

        # TEXT OVERLAY  
        status = "ENABLED" if features_enabled else "DISABLED"
        status_color = (0, 255, 0) if features_enabled else (0, 0, 255)

        cv2.putText(frame, f"Status: {status}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        # show mode
        cv2.putText(frame, f"Mode: {mode.upper()} (F7 to toggle)",
                    (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 255), 2)

        if last_distance:
            cv2.putText(frame, f"Sensor: {last_distance:.1f} cm",
                        (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.putText(frame, "Touch sensor (close) to toggle ON/OFF",
                    (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        if volume_text:
            cv2.putText(frame, volume_text,
                        (10, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        if brightness_text:
            cv2.putText(frame, brightness_text,
                        (10, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        if cumulative_angle != 0.0 and mode == "volume":
            cv2.putText(frame, f"Angle: {cumulative_angle:.2f}",
                        (10, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        if fingers_up is not None:
            cv2.putText(frame, f"Fingers up: {fingers_up}",
                        (10, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 2)

        cv2.imshow("Gesture Volume & Brightness Control (Toggle)", frame)
        key = cv2.waitKey(1) & 0xFF

        # Quit
        if key == ord('q'):
            break

        # Toggle mode with F7 (usually keycode 118)
        if key == ord('='):  # using 'q' as toggle button
            if mode == "volume":
                mode = "brightness"
            else:
                mode = "volume"
            print(f"[INFO] Mode switched to: {mode.upper()}")
            # small delay to avoid bouncing
            time.sleep(0.15)

    cap.release()
    if ser:
        ser.close()
    hands.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
