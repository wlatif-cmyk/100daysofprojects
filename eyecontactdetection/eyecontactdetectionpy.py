import cv2
import time
import serial

arduino = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)  # wait for Arduino to reset

# OPENCV SETUP
# use OpenCV's built-in haarcascade path instead of local files
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)
eye_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_eye.xml'
)

cap = cv2.VideoCapture(0)

# timing so it doesn't buzz immediately if blinking
NO_EYE_TIMEOUT = 2.0  # seconds of no eye contact before buzzing
last_eye_time = time.time()
buzzing = False

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )

    eye_contact = False

    for (x, y, w, h) in faces:
        # draw face box
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        roi_gray  = gray[y:y + h, x:x + w]
        roi_color = frame[y:y + h, x:x + w]

        eyes = eye_cascade.detectMultiScale(
            roi_gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(20, 20)
        )

        # draw eyes
        for (ex, ey, ew, eh) in eyes:
            cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

        # If we detect at least 2 eyes, assume eye contact-ish
        if len(eyes) >= 2:
            eye_contact = True
            break  # we don't need to check more faces

    if eye_contact:
        last_eye_time = time.time()
        status_text = "eye contact :)"
        # if buzzing, tell Arduino to stop
        if buzzing:
            arduino.write(b'S')  # send 'S' for stop
            buzzing = False
    else:
        status_text = "not looking"
        # check how long since last saw eyes
        if (time.time() - last_eye_time) > NO_EYE_TIMEOUT:
            if not buzzing:
                arduino.write(b'B')  # send 'B' for buzz
                buzzing = True

    # show status on screen
    cv2.putText(frame, status_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255) if not eye_contact else (0, 255, 0), 2)

    cv2.imshow('eye contact detector', frame)

    # press q to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# cleanup
cap.release()
cv2.destroyAllWindows()
arduino.close()
