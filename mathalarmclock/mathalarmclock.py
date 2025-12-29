import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import random
import time
import threading
import os

#config
SOUND_FILENAME = "mixkit-facility-alarm-sound-999.wav"
SOUND_PATH = SOUND_FILENAME

# In this environment, the uploaded file is mounted here:
FALLBACK_SOUND_PATH = "/mnt/data/mixkit-facility-alarm-sound-999.wav"

# Volume ramp settings (0.0 to 1.0)
START_VOLUME = 0.10
VOLUME_STEP = 0.06
VOLUME_STEP_SECONDS = 1.5


# ----------------- Sleep prevention (Windows only) -----------------
def prevent_sleep_windows(enable: bool):
    if os.name != "nt":
        return
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if enable else 0)
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
    except Exception:
        pass


# ----------------- Alarm sound via pygame (WAV) -----------------
def start_alarm_sound(stop_flag, sound_path: str):
    """
    Plays a WAV file in a loop and gradually increases volume while stop_flag() is False.
    """
    try:
        import pygame
    except Exception:
        # If pygame isn't installed, we can't play the WAV.
        # Fallback: terminal bell (still annoying)
        while not stop_flag():
            print("\a", end="", flush=True)
            time.sleep(0.2)
        return

    # Resolve file path
    chosen = sound_path
    if not os.path.exists(chosen):
        if os.path.exists(FALLBACK_SOUND_PATH):
            chosen = FALLBACK_SOUND_PATH

    try:
        pygame.mixer.init()
        pygame.mixer.music.load(chosen)
    except Exception:
        # Fallback if audio init/load fails
        while not stop_flag():
            print("\a", end="", flush=True)
            time.sleep(0.2)
        return

    volume = max(0.0, min(1.0, START_VOLUME))
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play(-1)  # loop forever

    while not stop_flag():
        time.sleep(VOLUME_STEP_SECONDS)
        volume = min(1.0, volume + VOLUME_STEP)
        pygame.mixer.music.set_volume(volume)

    try:
        pygame.mixer.music.stop()
    except Exception:
        pass


# ----------------- Problem generation with difficulty -----------------
def make_problem(difficulty: str, level: int):
    """
    difficulty: Easy / Medium / Hard / Mixed
    level: ramps within difficulty as streak grows
    Returns: (problem_str, answer_int)
    """

    def easy():
        a, b = random.randint(1, 20), random.randint(1, 20)
        op = random.choice(["+", "-"])
        ans = a + b if op == "+" else a - b
        return f"{a} {op} {b}", ans

    def medium():
        # multiplication or clean division
        if random.random() < 0.65:
            a, b = random.randint(2, 12), random.randint(2, 12)
            return f"{a} * {b}", a * b
        b = random.randint(2, 12)
        k = random.randint(2, 12)
        a = b * k
        return f"{a} / {b}", k

    def hard():
        # two-step; sometimes clean division in expression
        if random.random() < 0.7:
            a, b = random.randint(2, 14), random.randint(2, 14)
            c = random.randint(1, 35)
            op = random.choice(["+", "-"])
            ans = (a * b) + c if op == "+" else (a * b) - c
            return f"({a} * {b}) {op} {c}", ans

        b = random.randint(2, 12)
        k = random.randint(2, 12)
        a = b * k
        c = random.randint(1, 20)
        op = random.choice(["+", "-"])
        ans = (a // b) + c if op == "+" else (a // b) - c
        return f"({a} / {b}) {op} {c}", ans

    if difficulty == "Mixed":
        if level <= 1:
            return easy()
        if level == 2:
            return random.choice([easy, medium])()
        return random.choice([medium, hard])()

    if difficulty == "Easy":
        if level <= 2:
            return easy()
        a, b = random.randint(10, 60), random.randint(1, 40)
        op = random.choice(["+", "-"])
        ans = a + b if op == "+" else a - b
        return f"{a} {op} {b}", ans

    if difficulty == "Medium":
        if level <= 2:
            return medium()
        if random.random() < 0.6:
            a, b = random.randint(8, 18), random.randint(3, 14)
            return f"{a} * {b}", a * b
        b = random.randint(3, 15)
        k = random.randint(3, 15)
        a = b * k
        return f"{a} / {b}", k

    return hard()


# ----------------- Main app -----------------
class MathAlarmPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Math Alarm")
        self.root.geometry("700x460")
        self.root.minsize(700, 460)

        # state
        self.alarm_dt = None
        self.ringing = False
        self.solved = False

        self.streak = 0
        self.streak_needed = tk.IntVar(value=3)
        self.level = 1

        self.difficulty = tk.StringVar(value="Medium")
        self.problem = ""
        self.answer = 0

        self._sound_thread = None
        self._flash_on = False

        # close lock
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # style
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        self.style.configure("Clock.TLabel", font=("Consolas", 32, "bold"))
        self.style.configure("Big.TLabel", font=("Segoe UI", 12))
        self.style.configure("StatusGood.TLabel", foreground="#1a7f37", font=("Segoe UI", 11, "bold"))
        self.style.configure("StatusWarn.TLabel", foreground="#b54708", font=("Segoe UI", 11, "bold"))
        self.style.configure("StatusBad.TLabel", foreground="#b42318", font=("Segoe UI", 11, "bold"))
        self.style.configure("Card.TFrame", padding=14)
        self.style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"))
        self.style.configure("TButton", padding=8)

        self.build_ui()

        # keybind: Enter submits (only when ringing)
        self.root.bind("<Return>", self.on_enter)

        prevent_sleep_windows(True)
        self.update_clock()

    def build_ui(self):
        top = ttk.Frame(self.root, padding=14)
        top.pack(fill="x")

        ttk.Label(top, text="Math Alarm", style="Title.TLabel").pack(side="left")
        self.status_badge = ttk.Label(top, text="NOT SET", style="StatusWarn.TLabel")
        self.status_badge.pack(side="right")

        main = ttk.Frame(self.root, padding=(14, 0, 14, 14))
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        right = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right.pack(side="right", fill="both", expand=True)

        # Left card: time and alarm controls
        card1 = ttk.Frame(left, style="Card.TFrame")
        card1.pack(fill="both", expand=True)

        ttk.Label(card1, text="Current Time", style="Big.TLabel").grid(row=0, column=0, sticky="w")
        self.clock_lbl = ttk.Label(card1, text="--:--:--", style="Clock.TLabel")
        self.clock_lbl.grid(row=1, column=0, sticky="w", pady=(4, 14))

        ttk.Label(card1, text="Set Alarm (24h)", style="Big.TLabel").grid(row=2, column=0, sticky="w")

        alarm_row = ttk.Frame(card1)
        alarm_row.grid(row=3, column=0, sticky="w", pady=(6, 10))

        ttk.Label(alarm_row, text="Hour").pack(side="left", padx=(0, 6))
        self.hour_spin = tk.Spinbox(alarm_row, from_=0, to=23, width=3, font=("Segoe UI", 11))
        self.hour_spin.pack(side="left", padx=(0, 12))

        ttk.Label(alarm_row, text="Min").pack(side="left", padx=(0, 6))
        self.min_spin = tk.Spinbox(alarm_row, from_=0, to=59, width=3, font=("Segoe UI", 11))
        self.min_spin.pack(side="left", padx=(0, 12))

        btn_row = ttk.Frame(card1)
        btn_row.grid(row=4, column=0, sticky="w", pady=(0, 10))

        self.set_btn = ttk.Button(btn_row, text="Set Alarm", style="Accent.TButton", command=self.set_alarm)
        self.set_btn.pack(side="left", padx=(0, 8))

        self.clear_btn = ttk.Button(btn_row, text="Clear", command=self.clear_alarm)
        self.clear_btn.pack(side="left", padx=(0, 8))

        self.test_btn = ttk.Button(btn_row, text="Test Now", command=self.test_alarm)
        self.test_btn.pack(side="left")

        self.info_lbl = ttk.Label(card1, text="No alarm set.", style="Big.TLabel")
        self.info_lbl.grid(row=5, column=0, sticky="w", pady=(6, 0))

        # Right card: settings + solve
        card2 = ttk.Frame(right, style="Card.TFrame")
        card2.pack(fill="both", expand=True)

        ttk.Label(card2, text="Settings", style="Big.TLabel").grid(row=0, column=0, sticky="w")

        settings_grid = ttk.Frame(card2)
        settings_grid.grid(row=1, column=0, sticky="we", pady=(8, 10))
        settings_grid.columnconfigure(1, weight=1)

        ttk.Label(settings_grid, text="Difficulty").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        self.diff_combo = ttk.Combobox(
            settings_grid,
            textvariable=self.difficulty,
            values=["Easy", "Medium", "Hard", "Mixed"],
            state="readonly",
        )
        self.diff_combo.grid(row=0, column=1, sticky="we", pady=4)

        ttk.Label(settings_grid, text="Correct in a row").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        self.streak_spin = tk.Spinbox(
            settings_grid, from_=1, to=10, width=5, font=("Segoe UI", 11), textvariable=self.streak_needed
        )
        self.streak_spin.grid(row=1, column=1, sticky="w", pady=4)

        ttk.Separator(card2).grid(row=2, column=0, sticky="we", pady=10)

        ttk.Label(card2, text="Alarm Challenge", style="Big.TLabel").grid(row=3, column=0, sticky="w")

        self.challenge_lbl = ttk.Label(card2, text="Not ringing.", style="Big.TLabel")
        self.challenge_lbl.grid(row=4, column=0, sticky="w", pady=(6, 6))

        self.progress = ttk.Progressbar(card2, mode="determinate", maximum=10)
        self.progress.grid(row=5, column=0, sticky="we", pady=(0, 10))

        solve_row = ttk.Frame(card2)
        solve_row.grid(row=6, column=0, sticky="we")
        solve_row.columnconfigure(0, weight=1)

        self.answer_entry = ttk.Entry(solve_row, font=("Segoe UI", 16))
        self.answer_entry.grid(row=0, column=0, sticky="we", padx=(0, 10))

        self.submit_btn = ttk.Button(solve_row, text="Submit", style="Accent.TButton", command=self.submit_answer)
        self.submit_btn.grid(row=0, column=1)

        self.hint_lbl = ttk.Label(card2, text="Tip: Press Enter to submit.", style="Big.TLabel")
        self.hint_lbl.grid(row=7, column=0, sticky="w", pady=(10, 0))

        # Fix for the textbox selection glitch:
        # - Ensure clicking the entry reliably focuses it
        # - Avoid constantly stealing focus during flashing
        self.answer_entry.bind("<Button-1>", lambda e: self.answer_entry.focus_set())

        self.set_solve_enabled(False)
        self.set_default_alarm_inputs()

    def set_default_alarm_inputs(self):
        now = datetime.now() + timedelta(minutes=1)
        self.hour_spin.delete(0, "end")
        self.hour_spin.insert(0, str(now.hour))
        self.min_spin.delete(0, "end")
        self.min_spin.insert(0, f"{now.minute:02d}")

    def set_solve_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.answer_entry.config(state=state)
        self.submit_btn.config(state=state)
        if enabled:
            self._focus_answer_entry()
        else:
            self.answer_entry.delete(0, "end")

    def _focus_answer_entry(self):
        # Schedule focus to happen after UI updates (prevents focus issues)
        self.root.after(60, lambda: (self.answer_entry.focus_set(), self.answer_entry.icursor("end")))

    def on_enter(self, event=None):
        if self.ringing and not self.solved:
            self.submit_answer()

    def update_clock(self):
        now = datetime.now()
        self.clock_lbl.config(text=now.strftime("%H:%M:%S"))

        if self.alarm_dt and not self.ringing:
            if now >= self.alarm_dt:
                self.trigger_alarm()
            else:
                remaining = self.alarm_dt - now
                mins, secs = divmod(int(remaining.total_seconds()), 60)
                self.info_lbl.config(text=f"Alarm set for {self.alarm_dt.strftime('%H:%M')} (in {mins:02d}:{secs:02d})")
                self.status_badge.config(text="SET", style="StatusGood.TLabel")

        self.root.after(1000, self.update_clock)

    def set_alarm(self):
        if self.ringing and not self.solved:
            self.info_lbl.config(text="Solve the alarm first.")
            return

        try:
            h = int(str(self.hour_spin.get()).strip())
            m = int(str(self.min_spin.get()).strip())
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except Exception:
            self.info_lbl.config(text="Enter a valid time (Hour 0-23, Min 0-59).")
            self.status_badge.config(text="NOT SET", style="StatusWarn.TLabel")
            return

        now = datetime.now()
        alarm = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if alarm <= now:
            alarm += timedelta(days=1)

        self.alarm_dt = alarm
        self.ringing = False
        self.solved = False
        self.level = 1
        self.streak = 0
        self._stop_flashing()

        self.info_lbl.config(text=f"Alarm set for {alarm.strftime('%H:%M')}.")
        self.status_badge.config(text="SET", style="StatusGood.TLabel")

    def clear_alarm(self):
        if self.ringing and not self.solved:
            self.info_lbl.config(text="You can't clear it while it's ringing. Solve it.")
            return

        self.alarm_dt = None
        self.ringing = False
        self.solved = False
        self.level = 1
        self.streak = 0
        self._stop_flashing()

        self.info_lbl.config(text="No alarm set.")
        self.status_badge.config(text="NOT SET", style="StatusWarn.TLabel")
        self.challenge_lbl.config(text="Not ringing.")
        self.progress["value"] = 0
        self.set_solve_enabled(False)

    def test_alarm(self):
        if self.ringing and not self.solved:
            self.info_lbl.config(text="Already ringing. Solve it.")
            return
        self.alarm_dt = datetime.now()
        self.trigger_alarm()

    def trigger_alarm(self):
        self.ringing = True
        self.solved = False
        self.streak = 0
        self.level = 1

        # Make it harder to ignore, but DO NOT spam focus_force (that causes textbox selection glitches)
        self.root.attributes("-topmost", True)
        self.root.lift()

        self.status_badge.config(text="RINGING", style="StatusBad.TLabel")
        self.info_lbl.config(text="Alarm ringing. Solve to stop it.")
        self.set_solve_enabled(True)

        self.new_problem()
        self._start_flashing()
        self._focus_keepalive()

        # Start WAV alarm sound thread with gradual volume increase
        if self._sound_thread is None or not self._sound_thread.is_alive():
            stop = lambda: (not self.ringing) or self.solved
            self._sound_thread = threading.Thread(
                target=start_alarm_sound,
                daemon=True,
                args=(stop, SOUND_PATH),
            )
            self._sound_thread.start()

    def _focus_keepalive(self):
        """
        Gentle focus keepalive:
        - lifts window occasionally (without stealing selection constantly)
        - refocuses entry if focus is lost
        """
        if not self.ringing or self.solved:
            return

        try:
            self.root.lift()
        except Exception:
            pass

        try:
            # If focus drifted, bring it back to the entry
            if self.root.focus_get() is None or self.root.focus_get() != self.answer_entry:
                self._focus_answer_entry()
        except Exception:
            self._focus_answer_entry()

        self.root.after(1200, self._focus_keepalive)

    def new_problem(self):
        needed = max(1, int(self.streak_needed.get()))
        self.progress.configure(maximum=needed)
        self.progress["value"] = self.streak

        # Ramp difficulty within chosen mode using streak
        self.level = 1 + min(4, self.streak)

        diff = self.difficulty.get().strip()
        self.problem, self.answer = make_problem(diff, self.level)

        self.challenge_lbl.config(
            text=f"Solve: {self.problem}   |   Streak: {self.streak}/{needed}   |   Difficulty: {diff}"
        )

        self.answer_entry.delete(0, "end")
        self._focus_answer_entry()

    def submit_answer(self):
        if not self.ringing or self.solved:
            return

        raw = self.answer_entry.get().strip()
        try:
            val = int(raw)
        except Exception:
            self.hint_lbl.config(text="Enter a whole number.")
            return

        needed = max(1, int(self.streak_needed.get()))

        if val == self.answer:
            self.streak += 1
            self.hint_lbl.config(text="Correct. Keep going.")
            self.progress["value"] = self.streak

            if self.streak >= needed:
                self.stop_alarm_success()
            else:
                self.new_problem()
        else:
            self.streak = 0
            self.progress["value"] = 0
            self.hint_lbl.config(text="Wrong. Streak reset.")
            self.new_problem()

    def stop_alarm_success(self):
        self.solved = True
        self.ringing = False
        self.alarm_dt = None

        self._stop_flashing()
        self.root.attributes("-topmost", False)

        self.status_badge.config(text="CLEARED", style="StatusGood.TLabel")
        self.info_lbl.config(text="Alarm cleared. You can close the window now.")
        self.challenge_lbl.config(text="Not ringing.")
        self.hint_lbl.config(text="Set a new alarm anytime.")

        self.set_solve_enabled(False)

    def _start_flashing(self):
        self._flash_on = False
        self._flash_step()

    def _flash_step(self):
        # Visual urgency WITHOUT stealing focus constantly
        if not self.ringing or self.solved:
            return
        self._flash_on = not self._flash_on
        bg = "#2b1b1b" if self._flash_on else "#1b1f2b"
        try:
            self.root.configure(bg=bg)
        except Exception:
            pass
        self.root.after(500, self._flash_step)

    def _stop_flashing(self):
        try:
            self.root.configure(bg="")
        except Exception:
            pass

    def on_close(self):
        if self.ringing and not self.solved:
            self.info_lbl.config(text="You can't close this until you solve the alarm.")
            return
        prevent_sleep_windows(False)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MathAlarmPro(root)
    root.mainloop()
