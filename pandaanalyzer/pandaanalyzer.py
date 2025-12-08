import cv2
import numpy as np
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os
import webbrowser
from collections import deque


# spotify api key
SPOTIPY_CLIENT_ID = "108d8cd20c4c4dee96bd4c3dc6ae4716"
SPOTIPY_CLIENT_SECRET = "ea132174cd20417e9f7b08c2956a2ae4"
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_USERNAME = "n3ox8xs7vi8smcg9f7xoatr1o"

#            CONFIG CONSTANTS
SCOPE = "user-modify-playback-state user-read-playback-state"

DETECTION_THRESHOLD = 2        # Higher = harder to detect 
TRIGGER_COOLDOWN = 15           # Seconds between song plays
SCAN_LINE_SPEED = 80            # Speed of scan animation

SMOOTHING_WINDOW = 12           # How many frames to average
REQUIRED_CONSECUTIVE_FRAMES = 3 # How many stable frames needed

# spotify auth 
sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SCOPE,
        username=SPOTIFY_USERNAME,
        open_browser=True
    )
)

#spotify playback 

def play_panda_song():
    """Play 'Panda' by Desiigner and open Spotify UI."""
    results = sp.search(q="track:Panda artist:Desiigner", type="track", limit=1)
    tracks = results.get("tracks", {}).get("items", [])

    if not tracks:
        print("Could not find 'Panda'.")
        return

    track = tracks[0]
    track_uri = track["uri"]
    track_url = track["external_urls"]["spotify"]

    devices = sp.devices().get("devices", [])
    if not devices:
        print("No active Spotify devices. Opening Spotify UI instead.")
        open_spotify_ui(track_uri, track_url)
        return

    device_id = devices[0]["id"]

    print("🎵 Playing 'Panda' by Desiigner!")
    sp.start_playback(device_id=device_id, uris=[track_uri])

    open_spotify_ui(track_uri, track_url)


def open_spotify_ui(track_uri, track_url):
    """Try to switch to Spotify app or open in browser."""
    try:
        os.startfile(track_uri)  # Windows/macOS Spotify URI
    except Exception:
        webbrowser.open(track_url)

#panda detection 
def setup_panda_reference(path="panda_ref.png"):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError("Could not load panda_ref.png")

    orb = cv2.ORB_create(nfeatures=1500)
    kp, des = orb.detectAndCompute(img, None)

    if des is None or len(des) == 0:
        raise ValueError("Bad reference image. Use clear photo of your REAL panda plush.")

    return img, kp, des, orb


def detect_panda_in_frame(frame, panda_des, orb):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    kp2, des2 = orb.detectAndCompute(gray, None)

    if des2 is None or len(des2) == 0:
        return 0  # no features = no matches

    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = bf.knnMatch(panda_des, des2, k=2)

    good = []
    for pair in matches:
        if len(pair) != 2:
            continue
        m, n = pair

        #strict ratio test
        if m.distance < 0.55 * n.distance:
            good.append(m)

    return len(good)

#scanning hud/green line animation
def draw_scanning_overlay(frame, score, detected):
    h, w, _ = frame.shape
    t = time.time()

    # Moving scan line
    line_y = int((t * SCAN_LINE_SPEED) % h)
    cv2.line(frame, (0, line_y), (w, line_y), (0, 255, 0), 2)

    # Animated scanning text
    dots = int(t * 3) % 4
    scan_text = "SCANNING" + "." * dots
    cv2.putText(frame, scan_text, (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    # Status text
    if detected:
        txt = f"PANDA DETECTED!!!  smooth_score={score}"
        cv2.putText(frame, txt, (30, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
    else:
        txt = f"Looking... smooth_score={score}"
        cv2.putText(frame, txt, (30, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    return frame

#main loop
def main():
    try:
        _, _, panda_des, orb = setup_panda_reference("panda_ref.png")
        print("✔ panda_ref.png loaded.")
    except Exception as e:
        print("Error:", e)
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Webcam error.")
        return

    last_trigger_time = 0
    scores_window = deque(maxlen=SMOOTHING_WINDOW)
    consecutive = 0

    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        raw_score = detect_panda_in_frame(frame, panda_des, orb)

        # Smooth score
        scores_window.append(raw_score)
        smooth_score = int(sum(scores_window) / len(scores_window))

        # Stable detection decision
        detected = smooth_score >= DETECTION_THRESHOLD

        if detected:
            consecutive += 1
        else:
            consecutive = 0

        # Draw HUD
        frame = draw_scanning_overlay(frame, smooth_score, detected)

        # Trigger after stable detection
        if consecutive >= REQUIRED_CONSECUTIVE_FRAMES:
            now = time.time()
            if now - last_trigger_time > TRIGGER_COOLDOWN:
                print(f"🎯 PANDA DETECTED! raw={raw_score}, smooth={smooth_score}")
                play_panda_song()
                last_trigger_time = now
            consecutive = 0  # reset

        cv2.imshow("🐼 Panda Scanner", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()