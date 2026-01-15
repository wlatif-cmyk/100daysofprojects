import cv2
import mediapipe as mp
import numpy as np
import random
import time

# Setup
W, H = 960, 540
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.6)

# Game state
paddle_w, paddle_h = 160, 18
paddle_y = H - 60
paddle_x = W // 2

ball_r = 14
ball_x, ball_y = W // 2, H // 2
ball_vx, ball_vy = 260, -260

score = 0
game_over = False
last_time = time.time()

def reset_ball():
    global ball_x, ball_y, ball_vx, ball_vy
    ball_x, ball_y = W // 2, H // 2
    ball_vx = random.choice([-1, 1]) * random.uniform(220, 300)
    ball_vy = -random.uniform(220, 320)

# --------- Loop ---------
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    now = time.time()
    dt = now - last_time
    last_time = now

    # Slight dark overlay (makes shapes pop)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (W, H), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)

    # ----- Hand tracking for paddle -----
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = hands.process(rgb)

    if res.multi_hand_landmarks:
        lm = res.multi_hand_landmarks[0].landmark
        # Use wrist x position to control paddle
        wrist_x = int(lm[0].x * W)
        paddle_x = np.clip(wrist_x, paddle_w // 2, W - paddle_w // 2)

    # ----- Update ball -----
    if not game_over:
        ball_x += ball_vx * dt
        ball_y += ball_vy * dt

        # Wall bounce
        if ball_x - ball_r < 0:
            ball_x = ball_r
            ball_vx *= -1
        if ball_x + ball_r > W:
            ball_x = W - ball_r
            ball_vx *= -1
        if ball_y - ball_r < 0:
            ball_y = ball_r
            ball_vy *= -1

        # Paddle bounce
        paddle_left = paddle_x - paddle_w // 2
        paddle_right = paddle_x + paddle_w // 2
        paddle_top = paddle_y - paddle_h // 2
        paddle_bottom = paddle_y + paddle_h // 2

        if (paddle_left <= ball_x <= paddle_right and
            paddle_top <= ball_y + ball_r <= paddle_bottom and
            ball_vy > 0):

            ball_y = paddle_top - ball_r
            ball_vy *= -1
            score += 1

            # Add tiny "english" based on hit position
            hit = (ball_x - paddle_x) / (paddle_w / 2)
            ball_vx += hit * 120

        # Miss = game over
        if ball_y - ball_r > H:
            game_over = True

    # ----- Draw paddle -----
    cv2.rectangle(
        frame,
        (int(paddle_x - paddle_w//2), int(paddle_y - paddle_h//2)),
        (int(paddle_x + paddle_w//2), int(paddle_y + paddle_h//2)),
        (255, 255, 255),
        -1
    )

    # ----- Draw ball -----
    cv2.circle(frame, (int(ball_x), int(ball_y)), ball_r, (255, 255, 255), -1)

    # ----- HUD -----
    cv2.putText(frame, f"Score: {score}", (20, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

    if game_over:
        cv2.putText(frame, "GAME OVER", (W//2 - 170, H//2 - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
        cv2.putText(frame, "Press R to restart", (W//2 - 190, H//2 + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)

    cv2.imshow("Hand Pong (ESC to quit)", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break
    if key in [ord('r'), ord('R')]:
        score = 0
        game_over = False
        reset_ball()

cap.release()
cv2.destroyAllWindows()
