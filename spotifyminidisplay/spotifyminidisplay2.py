"""
Spotify -> ESP32 bridge + command server

Does 2 jobs:
1) Poll Spotify "currently playing" and POST JSON to:
      http://ESP32_IP/spotify
2) Expose Flask endpoints (for ESP32 buttons):
      POST /next
      POST /prev
      POST /pause   (toggle)
      POST /seek?delta_ms=10000  (or -10000)

Install:
  pip install spotipy flask requests

Run:
  python spotify_bridge.py

If you ever change scopes, delete .spotify_token_cache first.
"""

import time
import threading
import requests
import spotipy
from flask import Flask, request
from spotipy.oauth2 import SpotifyOAuth

# ===== EDIT THESE =====
ESP32_IP = "192.168.5.253"  # ESP32 receiver
SPOTIFY_CLIENT_ID = "334ba8eca86141bd885e1186ed796b43"
SPOTIFY_CLIENT_SECRET = "3863da09caa441dc845b6941b524b6b2"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
# ======================

SCOPE = "user-read-currently-playing user-read-playback-state user-modify-playback-state"

app = Flask(__name__)

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=SCOPE,
    open_browser=True,
    cache_path=".spotify_token_cache",
))

def post_to_esp32(payload: dict) -> None:
    url = f"http://{ESP32_IP}/spotify"
    try:
        r = requests.post(url, json=payload, timeout=6)
        if r.status_code != 200:
            print("ESP32 HTTP error:", r.status_code, r.text)
    except Exception as e:
        print("ESP32 post failed:", e)

def now_playing_loop():
    print("Now-playing loop started.")
    last_sent = None
    last_track_id = None

    while True:
        try:
            data = sp.current_user_playing_track()

            if not data or not data.get("item"):
                payload = {
                    "title": "Not playing",
                    "artist": "",
                    "progress_ms": 0,
                    "duration_ms": 1,
                    "is_playing": False,
                }
                post_to_esp32(payload)
                time.sleep(2)
                continue

            item = data["item"]
            is_playing = bool(data.get("is_playing", False))

            title = item.get("name", "Unknown")
            artists = ", ".join(a.get("name", "") for a in item.get("artists", [])) or "Unknown"

            progress_ms = int(data.get("progress_ms") or 0)
            duration_ms = int(item.get("duration_ms") or 1)

            track_id = item.get("id")
            if track_id and track_id != last_track_id:
                print(f"Now playing: {title} — {artists}")
                last_track_id = track_id

            payload = {
                "title": title,
                "artist": artists,
                "progress_ms": progress_ms,
                "duration_ms": duration_ms,
                "is_playing": is_playing,
            }

            # reduce spam: only send when second tick changes or state changes
            key = (title, artists, progress_ms // 1000, duration_ms, is_playing)
            if key != last_sent:
                post_to_esp32(payload)
                last_sent = key

            time.sleep(1.5)

        except Exception as e:
            print("Now-playing error:", e)
            time.sleep(2)

def _no_active_device_hint(e: Exception):
    msg = str(e)
    if "No active device" in msg or "NO_ACTIVE_DEVICE" in msg:
        print("Spotify: No active device.")
        print("Fix: start playing on your laptop or select a device in Spotify Connect.")

@app.post("/next")
def cmd_next():
    print("CMD: NEXT (from ESP32)")
    try:
        sp.next_track()
    except Exception as e:
        print("NEXT failed:", e)
        _no_active_device_hint(e)
        return "error", 500
    return "ok"

@app.post("/prev")
def cmd_prev():
    print("CMD: PREV (from ESP32)")
    try:
        sp.previous_track()
    except Exception as e:
        print("PREV failed:", e)
        _no_active_device_hint(e)
        return "error", 500
    return "ok"

@app.post("/pause")
def cmd_pause():
    print("CMD: TOGGLE PAUSE/PLAY (from ESP32)")
    try:
        pb = sp.current_playback()
        if pb and pb.get("is_playing"):
            sp.pause_playback()
        else:
            sp.start_playback()
    except Exception as e:
        print("PAUSE/PLAY failed:", e)
        _no_active_device_hint(e)
        return "error", 500
    return "ok"

@app.post("/seek")
def cmd_seek():
    # POST /seek?delta_ms=10000 or -10000
    try:
        delta_ms = int(request.args.get("delta_ms", "0"))
    except ValueError:
        return "bad delta_ms", 400

    print("CMD: SEEK delta_ms =", delta_ms)

    try:
        pb = sp.current_playback()
        if not pb or "progress_ms" not in pb:
            return "no playback", 400

        progress = int(pb["progress_ms"])
        item = pb.get("item") or {}
        duration = int(item.get("duration_ms") or 0)

        new_pos = progress + delta_ms
        if new_pos < 0:
            new_pos = 0
        if duration > 0 and new_pos > duration - 1000:
            new_pos = max(duration - 1000, 0)

        sp.seek_track(new_pos)
    except Exception as e:
        print("SEEK failed:", e)
        _no_active_device_hint(e)
        return "error", 500

    return "ok"

def run_server():
    print("Command server running on http://0.0.0.0:5000")
    # 0.0.0.0 allows ESP32 to connect from your Wi-Fi
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    t = threading.Thread(target=now_playing_loop, daemon=True)
    t.start()
    run_server()
