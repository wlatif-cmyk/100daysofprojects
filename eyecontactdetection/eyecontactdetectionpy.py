import cv2
import time
import threading
import platform

# --------------------------
# OPTIONAL ARDUINO SUPPORT
# --------------------------
USE_ARDUINO = False          # set True if you want Arduino too
ARDUINO_PORT = "COM3"
ARDUINO_BAUD = 9600

arduino = None
if USE_ARDUINO:
    try:
        import serial
        arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
        time.sleep(2)  # wait for Arduino reset
        print("[OK] Arduino connected.")
    except Exception as e:
        print(f"[WARN] Arduino not available, falling back to laptop beep. ({e})")
        arduino = None
        USE_ARDUINO = False

# --------------------------
# LAPTOP BEEP (NO DEPENDENCIES)
# --------------------------
IS_WINDOWS = platform.system().lower().startswith("win")

def _bell_beep():
    # Terminal bell (works on many systems, not all)
    print("\a", end="", flush=True)

def _windows_beep(freq=1000, dur_ms=200):
    import winsound
    winsound.Beep(freq, dur_ms)

def do_beep():
    if IS_WINDOWS:
        try:
            _windows_beep()
        except Exception:
            _bell_beep()
    else:
        _bell_beep()

# Background beeper thread control
beep_stop = threading.Event()
beep_thread = None

def start_beeping():
    global beep_thread
    if beep_thread and beep_thread.is_alive():
        return
    beep_stop.clear()

    def loop():
        # beeps repeatedly until stopped
        while not beep_stop.is_set():
            do_beep()
            time.sleep(0.35)

    beep_thread = threading.Thread(target=loop, daemon=True)
    beep_thread.start()

def stop_beeping():
    beep_stop.set()

# --------------------------
# OPENCV SETUP
# --------------------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
eye_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye.xml"
)

cap = cv2.VideoCapture(0)

NO_EYE_TIMEOUT = 2.0  # seconds of no eye contact before alert

last_eye_time = time.time()
alerting = False

# scoring
start_time = time.time()
eye_contact_total = 0.0
eye_contact_active = False
eye_contact_start = None

def set_alert(on: bool):
    """Turn alert on/off (beep + optional Arduino)."""
    global alerting
    if on and not alerting:
        if USE_ARDUINO and arduino:
            try:
                arduino.write(b'B')
            except Exception:
                pass
        else:
            start_beeping()
        alerting = True

    if (not on) and alerting:
        if USE_ARDUINO and arduino:
            try:
                arduino.write(b'S')
            except Exception:
                pass
        else:
            stop_beeping()
        alerting = False

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
        )

        eye_contact = False

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            roi_gray = gray[y:y + h, x:x + w]
            roi_color = frame[y:y + h, x:x + w]

            eyes = eye_cascade.detectMultiScale(
                roi_gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(20, 20),
            )

            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

            if len(eyes) >= 2:
                eye_contact = True
                break

        now = time.time()

        # ---- score tracking (accumulate eye-contact time) ----
        if eye_contact and not eye_contact_active:
            eye_contact_active = True
            eye_contact_start = now

        if (not eye_contact) and eye_contact_active:
            eye_contact_active = False
            if eye_contact_start is not None:
                eye_contact_total += (now - eye_contact_start)
                eye_contact_start = None

        # ---- alert logic ----
        if eye_contact:
            last_eye_time = now
            set_alert(False)
            status_text = "eye contact :)"
        else:
            status_text = "not looking"
            if (now - last_eye_time) > NO_EYE_TIMEOUT:
                set_alert(True)
            else:
                set_alert(False)

        # UI text
        color = (0, 255, 0) if eye_contact else (0, 0, 255)
        cv2.putText(
            frame,
            status_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            color,
            2
        )

        cv2.imshow("eye contact detector", frame)

        # Quit on 'q'
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        # Quit if window is closed
        if cv2.getWindowProperty("eye contact detector", cv2.WND_PROP_VISIBLE) < 1:
            break

finally:
    # finalize eye-contact segment if still active
    end_time = time.time()
    if eye_contact_active and eye_contact_start is not None:
        eye_contact_total += (end_time - eye_contact_start)

    # stop alerts + clean up
    set_alert(False)
    cap.release()
    cv2.destroyAllWindows()
    if arduino:
        try:
            arduino.close()
        except Exception:
            pass

    session_total = max(0.001, end_time - start_time)
    pct = (eye_contact_total / session_total) * 100.0

    print("\n--- Eye Contact Score ---")
    print(f"Session length:      {session_total:.1f}s")
    print(f"Eye contact time:    {eye_contact_total:.1f}s")
    print(f"Eye contact percent: {pct:.1f}%")
