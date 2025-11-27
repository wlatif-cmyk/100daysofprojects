import cv2
import mediapipe as mp
import serial
import time

# COM port of Arduino
arduino = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

while True:
    success, img = cap.read()
    if not success:
        break

    h, w, _ = img.shape  # height, width of camera frame

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    if results.multi_hand_landmarks:
        for hand in results.multi_hand_landmarks:

            # Index finger tip landmark (landmark #8)
            x = hand.landmark[8].x  # normalized 0.0 - 1.0  
            pixel_x = int(x * w)    # convert to actual pixel location

            # Draw landmarks
            mp_draw.draw_landmarks(img, hand, mp_hands.HAND_CONNECTIONS)

            # Visual guide
            cv2.line(img, (w//2, 0), (w//2, h), (255,255,255), 2)
            cv2.circle(img, (pixel_x, 200), 10, (0,255,0), cv2.FILLED)

            # left side
            if pixel_x < w // 2:
                arduino.write(b'L\n')
                cv2.putText(img, "LEFT SIDE", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

            # right side
            else:
                arduino.write(b'R\n')
                cv2.putText(img, "RIGHT SIDE", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    else:
        # If no hand, send neutral
        arduino.write(b'N\n')
        cv2.putText(img, "NO HAND", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

    cv2.imshow("Hand Left/Right Detection", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
arduino.close()
cv2.destroyAllWindows()
