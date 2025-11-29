import cv2
import mediapipe as mp
import serial
import time

arduino = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)  # let Arduino reset

# MediaPipe Hands setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

last_state = None  # 'OPEN' or 'CLOSE'

def count_fingers(hand_landmarks, img_height, img_width):
    """
    Returns how many fingers are 'up'.
    Uses simple rule: fingertip y < pip y (for all but thumb).
    """
    # Landmarks index:
    # 8 - index tip, 6 - index pip
    # 12 - middle tip, 10 - middle pip
    # 16 - ring tip, 14 - ring pip
    # 20 - pinky tip, 18 - pinky pip
    tips_ids = [8, 12, 16, 20]
    pip_ids  = [6, 10, 14, 18]

    fingers_up = 0
    for tip, pip in zip(tips_ids, pip_ids):
        tip_y = hand_landmarks.landmark[tip].y
        pip_y = hand_landmarks.landmark[pip].y

        # In image coords: smaller y = higher on the screen
        if tip_y < pip_y:
            fingers_up += 1

    return fingers_up

while True:
    success, img = cap.read()
    if not success:
        break

    h, w, _ = img.shape

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    state_text = "NO HAND"
    color = (0, 0, 255)

    if results.multi_hand_landmarks:
        for hand in results.multi_hand_landmarks:
            # Draw the landmarks
            mp_draw.draw_landmarks(img, hand, mp_hands.HAND_CONNECTIONS)

            fingers_up = count_fingers(hand, h, w)

            # Simple logic:
            # 3 or more fingers -> open hand
            # 1 or fewer fingers -> closed hand
            if fingers_up >= 3:
                current_state = 'OPEN'
            elif fingers_up <= 1:
                current_state = 'CLOSE'
            else:
                current_state = None  # in-between / ignore

            if current_state is not None and current_state != last_state:
                if current_state == 'OPEN':
                    arduino.write(b'O\n')
                elif current_state == 'CLOSE':
                    arduino.write(b'C\n')
                last_state = current_state

            if current_state == 'OPEN':
                state_text = "HAND OPEN"
                color = (0, 255, 0)
            elif current_state == 'CLOSE':
                state_text = "HAND CLOSED"
                color = (0, 255, 255)
            else:
                state_text = "HAND MID"
                color = (255, 255, 0)

            # Show how many fingers it thinks are up
            cv2.putText(img, f"Fingers: {fingers_up}", (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.putText(img, state_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    cv2.imshow("Hand Open/Close -> Servo", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
arduino.close()
cv2.destroyAllWindows()
