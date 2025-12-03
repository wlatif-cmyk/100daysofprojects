import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time

# don't insta-kill if mouse hits corner
pyautogui.FAILSAFE = False

# ------------- CONFIG -------------

CAM_INDEX = 0       # change to 1/2 if needed

# cursor smoothing (0 = raw, 1 = snail)
CURSOR_SMOOTHING = 0.5
CURSOR_DEADZONE_PX = 3   # ignore tiny jitters smaller than this (pixels)

# "push" click detection
PUSH_Z_DELTA = 0.08      # how big a forward move counts as a push
CLICK_COOLDOWN = 0.25    # seconds between clicks

# scroll tuning (scroll mode: 1 finger up = up, 2 = down)
SCROLL_AMOUNT = 120      # how much each scroll pulse moves
SCROLL_COOLDOWN = 0.08   # seconds between scroll pulses

# ---------------------------------

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

screen_w, screen_h = pyautogui.size()


def count_fingers(lm, handedness_label):
    """
    Very chill finger counter:
      0 -> fist
      1, 2, 3, 4, 5 -> that many fingers up
    Good enough for scroll mode.
    """
    fingers = []
    tips = [4, 8, 12, 16, 20]  # thumb, index, middle, ring, pinky

    # thumb goes sideways
    if handedness_label == "Right":
        fingers.append(1 if lm.landmark[tips[0]].x < lm.landmark[tips[0] - 1].x else 0)
    else:
        fingers.append(1 if lm.landmark[tips[0]].x > lm.landmark[tips[0] - 1].x else 0)

    # other fingers: tip above PIP joint = up
    for i in range(1, 5):
        fingers.append(1 if lm.landmark[tips[i]].y < lm.landmark[tips[i] - 2].y else 0)

    return sum(fingers)


def main():
    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        print("[ERROR] Camera didn't start. Try CAM_INDEX = 1 or 2.")
        return

    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

    # smoothed cursor
    mouse_x, mouse_y = pyautogui.position()
    filtered_fx, filtered_fy = None, None  # filtered (0–1) finger coords

    # click via push
    last_index_z = None
    last_click_time = 0.0

    # scroll mode state
    last_scroll_time = 0.0

    # mode: pointer or scroll
    mode = "pointer"

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Camera feed died, exiting.")
            break

        # mirror so it feels natural
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        gesture_text = ""

        if result.multi_hand_landmarks:
            lm = result.multi_hand_landmarks[0]

            # left/right hand — helps thumb logic for finger counting
            handedness_label = "Right"
            if result.multi_handedness:
                handedness_label = result.multi_handedness[0].classification[0].label

            # draw the hand so you know it's tracking
            mp_drawing.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)

            # index fingertip position and depth
            idx_landmark = lm.landmark[8]
            idx_tip = np.array([idx_landmark.x, idx_landmark.y])
            idx_z = idx_landmark.z  # depth, smaller = closer to camera

            # ---------- CURSOR SMOOTHING (always based on index tip) ----------

            if filtered_fx is None:
                filtered_fx, filtered_fy = idx_tip[0], idx_tip[1]
            else:
                filtered_fx = filtered_fx + CURSOR_SMOOTHING * (idx_tip[0] - filtered_fx)
                filtered_fy = filtered_fy + CURSOR_SMOOTHING * (idx_tip[1] - filtered_fy)

            target_x = filtered_fx * screen_w
            target_y = filtered_fy * screen_h

            dx = target_x - mouse_x
            dy = target_y - mouse_y
            dist = (dx * dx + dy * dy) ** 0.5

            if dist > CURSOR_DEADZONE_PX and mode == "pointer":
                mouse_x, mouse_y = target_x, target_y
                pyautogui.moveTo(mouse_x, mouse_y)

            # ---------- FINGER COUNT (for scroll mode) ----------
            fingers_up = count_fingers(lm, handedness_label)
            now = time.time()

            # ---------- POINTER MODE: push to click ----------
            if mode == "pointer":
                if last_index_z is not None:
                    # positive dz means finger moved toward camera (z got smaller)
                    dz = last_index_z - idx_z
                    if dz > PUSH_Z_DELTA and (now - last_click_time) > CLICK_COOLDOWN:
                        pyautogui.click()
                        last_click_time = now
                        gesture_text = "Click"

            # remember depth for next frame
            last_index_z = idx_z

            # ---------- SCROLL MODE: 1 finger up = up, 2 = down ----------
            if mode == "scroll":
                if (now - last_scroll_time) > SCROLL_COOLDOWN:
                    if fingers_up == 1:
                        pyautogui.scroll(SCROLL_AMOUNT)
                        last_scroll_time = now
                        gesture_text = "Scroll up"
                    elif fingers_up == 2:
                        pyautogui.scroll(-SCROLL_AMOUNT)
                        last_scroll_time = now
                        gesture_text = "Scroll down"

        else:
            # no hand: chill everything
            filtered_fx = filtered_fy = None
            last_index_z = None

        # ---------- UI TEXT ----------
        mode_text = f"Mode: {mode.upper()}   (= to toggle)"
        cv2.putText(frame, mode_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 255, 255), 2)

        if gesture_text:
            cv2.putText(frame, gesture_text, (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.putText(frame, "q = quit", (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)

        cv2.imshow("Virtual Mouse - Push Click & Finger Scroll", frame)
        key = cv2.waitKey(1) & 0xFF

        # quit
        if key == ord('q'):
            break

        # mode toggle
        if key == ord('='):
            mode = "scroll" if mode == "pointer" else "pointer"
            print(f"[INFO] Mode switched to {mode.upper()}")
            time.sleep(0.15)

    cap.release()
    cv2.destroyAllWindows()
    hands.close()


if __name__ == "__main__":
    main()
