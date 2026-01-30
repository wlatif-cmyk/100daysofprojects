import sys, time, requests
from datetime import datetime, timedelta

import serial

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

def safe16(s: str) -> str:
    s = s.replace("\n", " ").replace("\r", " ")
    return (s[:16]).ljust(16)

def yyyymmdd(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")

def fetch_scoreboard(dt: datetime) -> dict:
    # Try by date first
    r = requests.get(BASE, params={"dates": yyyymmdd(dt)}, timeout=15)
    if r.status_code >= 400:
        r = requests.get(BASE, timeout=15)
    r.raise_for_status()
    return r.json()

def format_game(event: dict):
    comp = (event.get("competitions") or [{}])[0]
    competitors = comp.get("competitors") or []

    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)

    def abbr(team_obj):
        team = (team_obj or {}).get("team") or {}
        return team.get("abbreviation", "???")

    def score(team_obj):
        sc = (team_obj or {}).get("score", "")
        return str(sc) if sc != "" else ""

    ha, aa = abbr(home), abbr(away)
    hs, as_ = score(home), score(away)

    status = event.get("status") or {}
    st = status.get("type") or {}
    state = st.get("state", "")  # pre / in / post

    period = status.get("period") or ""
    clock = status.get("displayClock") or ""

    # Line 1: "AWY 102 HME 98"
    line1 = f"{aa} {as_} {ha} {hs}".strip()
    line1 = safe16(line1)

    # Line 2: live = Qx time, final = FINAL, pre = start time local-ish
    if state == "in":
        q = f"Q{period}" if period else "LIVE"
        line2 = f"{q} {clock}".strip()
    elif state == "post":
        line2 = "FINAL"
    else:
        # Use ESPN's shortDetail if available (often like "7:30 PM")
        detail = st.get("shortDetail") or st.get("detail") or "SCHED"
        # keep it short
        line2 = detail
    line2 = safe16(line2)

    return line1, line2

def get_games():
    now = datetime.now()
    # Check today then yesterday (in case late-night games / timezone weirdness)
    for d in [0, 1]:
        data = fetch_scoreboard(now - timedelta(days=d))
        events = data.get("events") or []
        if events:
            games = []
            for ev in events:
                try:
                    games.append(format_game(ev))
                except Exception:
                    continue
            if games:
                return games
    return []

def build_packet(games, max_games=20):
    games = games[:max_games]
    # Packet format: NBA;COUNT;L1|L2;L1|L2;...;
    parts = [f"NBA;{len(games)};"]
    for l1, l2 in games:
        parts.append(f"{l1}|{l2};")
    return "".join(parts) + "\n"

def main():
    if len(sys.argv) < 2:
        print("Usage: python nbalive_scroll.py COM4")
        sys.exit(1)

    port = sys.argv[1]
    ser = serial.Serial(port, 115200, timeout=1)
    time.sleep(2)  # ESP32 resets when serial opens

    while True:
        try:
            games = get_games()
            pkt = build_packet(games, max_games=20)
            ser.write(pkt.encode("utf-8"))
            print(f"Sent {len(games)} games")
        except Exception as e:
            print("ERROR:", e)
        time.sleep(30)

if __name__ == "__main__":
    main()
