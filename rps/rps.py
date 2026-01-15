import cv2
import numpy as np
import mediapipe as mp
import random
import time
import math

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# ---------- Helpers ----------
def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def finger_extended(lm, tip_id, pip_id):
    # For index/middle/ring/pinky: tip higher than PIP in image coords (y smaller means higher)
    return lm[tip_id][1] < lm[pip_id][1]

def classify_rps(lm):
    """
    lm: list of 21 (x,y) pixel coords
    Returns: "rock" | "paper" | "scissors" | "unknown"
    """
    # Landmark indices
    # Thumb: tip 4, ip 3, mcp 2
    # Index: tip 8, pip 6
    # Middle: tip 12, pip 10
    # Ring: tip 16, pip 14
    # Pinky: tip 20, pip 18

    idx = finger_extended(lm, 8, 6)
    mid = finger_extended(lm, 12, 10)
    ring = finger_extended(lm, 16, 14)
    pinky = finger_extended(lm, 20, 18)

    # Thumb: use distance tip(4) to palm(0) vs thumb mcp(2) to palm(0) as rough "open" heuristic
    thumb_open = dist(lm[4], lm[0]) > dist(lm[2], lm[0]) * 1.15

    extended_count = sum([idx, mid, ring, pinky])

    # Rules (simple + works well):
    # Paper: 4 fingers extended (thumb ignored)
    if extended_count == 4:
        return "paper"

    # Scissors: index + middle extended, ring + pinky not
    if idx and mid and (not ring) and (not pinky):
        return "scissors"

    # Rock: none of the 4 fingers extended (fist). thumb can be either.
    if extended_count == 0:
        return "rock"

    return "unknown"

def decide_winner(user, comp):
    if user == comp:
        return "tie"
    if (user == "rock" and comp == "scissors") or \
       (user == "scissors" and comp == "paper") or \
       (user == "paper" and comp == "rock"):
        return "win"
    return "lose"

# ---------- UI drawing ----------
def draw_panel(img, lines, x=10, y=10, line_h=28):
    for i, text in enumerate(lines):
        cv2.putText(img, text, (x, y + i * line_h),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)

def draw_badge(img, text, pos=(10, 420)):
    cv2.rectangle(img, (pos[0]-5, pos[1]-30), (pos[0]+260, pos[1]+10), (0, 0, 0), -1)
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)

# ---------- Main ----------
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam.")
        return

    # Game state
    user_score = 0
    comp_score = 0
    last_result = "Press SPACE to play a round"
    locked_user_move = None
    locked_comp_move = None
    last_lock_time = 0

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    ) as hands:

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = hands.process(rgb)

            user_move = "no hand"

            if res.multi_hand_landmarks:
                hand_lms = res.multi_hand_landmarks[0]
                lm = []
                for p in hand_lms.landmark:
                    lm.append((int(p.x * w), int(p.y * h)))

                mp_draw.draw_landmarks(frame, hand_lms, mp_hands.HAND_CONNECTIONS)

                guess = classify_rps(lm)
                user_move = guess

            # Instructions + state
            lines = [
                f"Your move (live): {user_move}",
                f"Locked round: {locked_user_move or '-'} vs {locked_comp_move or '-'}",
                f"Score: You {user_score}  -  {comp_score} CPU",
                f"Result: {last_result}",
                "Controls: SPACE=lock round | R=reset | Q=quit"
            ]
            draw_panel(frame, lines)

            # If a round was locked recently, show a badge for a moment
            if locked_user_move and (time.time() - last_lock_time < 1.5):
                draw_badge(frame, f"LOCKED: {locked_user_move.upper()} vs {locked_comp_move.upper()}")

            cv2.imshow("RPS - MediaPipe", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break

            if key == ord('r'):
                user_score = 0
                comp_score = 0
                last_result = "Reset! Press SPACE to play."
                locked_user_move = None
                locked_comp_move = None

            if key == 32:  # SPACE
                # Only lock if we have a valid move
                if user_move in ["rock", "paper", "scissors"]:
                    comp_move = random.choice(["rock", "paper", "scissors"])
                    outcome = decide_winner(user_move, comp_move)

                    locked_user_move = user_move
                    locked_comp_move = comp_move
                    last_lock_time = time.time()

                    if outcome == "win":
                        user_score += 1
                        last_result = "You WIN!"
                    elif outcome == "lose":
                        comp_score += 1
                        last_result = "You LOSE!"
                    else:
                        last_result = "TIE!"

                else:
                    last_result = "Show a clear ROCK / PAPER / SCISSORS, then press SPACE."

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
