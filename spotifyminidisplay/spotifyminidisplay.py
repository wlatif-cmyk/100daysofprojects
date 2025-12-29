import time
import threading
import requests
import spotipy
from flask import Flask
from spotipy.oauth2 import SpotifyOAuth

# ===== EDIT THESE =====
ESP32_IP = "192.168.5.253"  # ESP32 receiver endpoint: http://ESP32_IP/spotify

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
        # IMPORTANT FIX: longer timeout so occasional lag doesn't kill it
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
                payload = {"title": "Not playing", "artist": "", "progress_ms": 0, "duration_ms": 1, "is_playing": False}
                post_to_esp32(payload)
                time.sleep(2)
                continue

            item = data["item"]
            is_playing = bool(data.get("is_playing", False))

            title = item.get("name", "Unknown")
            artists = ", ".join(a["name"] for a in item.get("artists", [])) or "Unknown"

            progress_ms = int(data.get("progress_ms") or 0)
            duration_ms = int(item.get("duration_ms") or 1)

            if item.get("id") and item.get("id") != last_track_id:
                last_track_id = item.get("id")
                print(f"Now playing: {title} — {artists}")

            payload = {
                "title": title,
                "artist": artists,
                "progress_ms": progress_ms,
                "duration_ms": duration_ms,
                "is_playing": is_playing,
            }

            # IMPORTANT FIX: reduce spam; send once per second tick or change
            key = (title, artists, progress_ms // 1000, duration_ms, is_playing)
            if key != last_sent:
                post_to_esp32(payload)
                last_sent = key

            # IMPORTANT FIX: slightly slower keeps ESP32 happy
            time.sleep(1.5)

        except Exception as e:
            print("Now-playing error:", e)
            time.sleep(2)

@app.post("/next")
def cmd_next():
    print("CMD: NEXT (from ESP32)")
    try:
        sp.next_track()
    except Exception as e:
        print("NEXT failed:", e)
        return "error", 500
    return "ok"

@app.post("/prev")
def cmd_prev():
    print("CMD: PREV (from ESP32)")
    try:
        sp.previous_track()
    except Exception as e:
        print("PREV failed:", e)
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
        return "error", 500
    return "ok"

def run_server():
    print("Command server running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    t = threading.Thread(target=now_playing_loop, daemon=True)
    t.start()
    run_server()
