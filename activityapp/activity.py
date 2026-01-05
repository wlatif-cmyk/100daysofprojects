import time
import math
import serial
import cv2
import mediapipe as mp

PORT = "COM3"     
BAUD = 115200

mp_pose = mp.solutions.pose

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def compute_motion_score(prev_pts, pts):
    """Returns a motion value roughly 0..1 based on landmark movement."""
    if prev_pts is None or pts is None:
        return 0.0
    s = 0.0
    for i in range(len(pts)):
        s += dist(prev_pts[i], pts[i])
    s /= len(pts)
    return s  

def motion_to_score(motion):
    """
    Map motion magnitude to 0..100.
    Tune these if needed.
    """
    low = 0.0015   # below this = basically still
    high = 0.015   # above this = very active
    x = (motion - low) / (high - low)
    return int(clamp(x, 0.0, 1.0) * 100)

def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    print("Connected to", PORT)

    cap = None
    pose = mp_pose.Pose(model_complexity=1, enable_segmentation=False)

    running = False
    prev_pts = None
    avg_sum = 0
    avg_count = 0

    last_tick = time.time()
    smooth_score = 0.0

    def start_session():
        nonlocal running, cap, prev_pts, avg_sum, avg_count, smooth_score
        if cap is None:
            cap = cv2.VideoCapture(0)
        prev_pts = None
        avg_sum = 0
        avg_count = 0
        smooth_score = 0.0
        running = True
        print("Session STARTED")

    def stop_session():
        nonlocal running, avg_sum, avg_count
        running = False
        avg = int(avg_sum / avg_count) if avg_count > 0 else 0
        print("Session STOPPED. Avg score:", avg)
        ser.write(f"SCORE:{avg}\n".encode("utf-8"))

    while True:
        # to read arduino commands
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
        except Exception:
            line = ""

        if line == "START" and not running:
            start_session()
        elif line == "STOP" and running:
            stop_session()

        # to run scoring loop only while running python app
        if running:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = pose.process(frame_rgb)

            pts = None
            present = False

            if res.pose_landmarks:
                present = True
                # uses subset of landmarks to keep stable
                use_ids = [0, 11, 12, 23, 24, 15, 16]  # nose, shoulders, hips, wrists
                pts = []
                for idx in use_ids:
                    lm = res.pose_landmarks.landmark[idx]
                    pts.append((lm.x, lm.y))

            motion = compute_motion_score(prev_pts, pts) if present else 0.0
            prev_pts = pts if present else None

            raw_score = motion_to_score(motion) if present else 0

            # Smooth it so it's not jumpy
            smooth_score = 0.85 * smooth_score + 0.15 * raw_score

            # Count toward average ~10x/sec
            now = time.time()
            if now - last_tick >= 0.10:
                last_tick = now
                avg_sum += int(smooth_score)
                avg_count += 1

            # Optional preview window (press Q to quit)
            cv2.putText(frame, f"Score: {int(smooth_score)}/100", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
            cv2.imshow("Activity Score", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            time.sleep(0.05)

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()
    ser.close()

if __name__ == "__main__":
    main()
