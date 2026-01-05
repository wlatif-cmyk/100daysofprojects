import time
import requests
import tkinter as tk
from tkinter import ttk

ESP32_IP = ""
SCAN_URL = f"http://{ESP32_IP}/scan"
REFRESH_MS = 2500

def rssi_to_quality(rssi):
    if rssi >= -50: return 100
    if rssi <= -90: return 0
    return int((rssi + 90) * (100 / 40))

def channel_penalty(channel, crowd):
    return min(25, int(crowd.get(channel, 0) * 2.5))

def security_bonus(sec):
    if sec == "OPEN": return -5
    if "WPA3" in sec: return 6
    if "WPA2" in sec: return 4
    if "WPA" in sec: return 2
    return 0

def compute_scores(networks):
    crowd = {}
    for n in networks:
        ch = int(n.get("channel", 0))
        crowd[ch] = crowd.get(ch, 0) + 1

    scored = []
    for n in networks:
        rssi = int(n.get("rssi", -100))
        ch = int(n.get("channel", 0))
        sec = n.get("security", "UNKNOWN")

        score = max(
            0,
            min(
                100,
                rssi_to_quality(rssi)
                - channel_penalty(ch, crowd)
                + security_bonus(sec),
            ),
        )

        scored.append({
            "ssid": n.get("ssid") or "(hidden)",
            "rssi": rssi,
            "quality": rssi_to_quality(rssi),
            "channel": ch,
            "security": sec,
            "crowd": crowd.get(ch, 0),
            "score": score
        })

    return sorted(scored, key=lambda x: x["score"], reverse=True)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ESP32 Wi-Fi Ranker")
        self.geometry("860x480")

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        self.status = tk.StringVar(value="Ready")
        ttk.Label(top, text="ESP32 URL:").pack(side="left")

        self.url_var = tk.StringVar(value=SCAN_URL)
        ttk.Entry(top, textvariable=self.url_var, width=45).pack(side="left", padx=8)

        ttk.Button(top, text="Scan", command=self.refresh).pack(side="left")
        ttk.Label(top, textvariable=self.status).pack(side="right")

        cols = ("Rank", "SSID", "Score", "RSSI", "Quality", "Channel", "Ch Crowd", "Security")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=90 if c != "SSID" else 260, anchor="center")

        self.after(300, self.refresh)

    def refresh(self):
        try:
            self.status.set("Scanning...")
            data = requests.get(self.url_var.get(), timeout=6).json()
            scored = compute_scores(data.get("networks", []))

            self.tree.delete(*self.tree.get_children())
            for i, n in enumerate(scored, 1):
                self.tree.insert("", "end", values=(
                    i, n["ssid"], n["score"], n["rssi"],
                    n["quality"], n["channel"], n["crowd"], n["security"]
                ))

            self.status.set(f"Found {len(scored)} networks — {time.strftime('%H:%M:%S')}")
        except Exception as e:
            self.status.set(f"Error: {e}")

        self.after(REFRESH_MS, self.refresh)

if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    App().mainloop()
