import cv2
import mediapipe as mp

# just tell it what pic to show when you do the eye/mouth thing
SECRET_IMAGE_PATH = "mymomiskindahomeless.jpg"

# adjust these if it triggers too easily or not enough
EYE_RATIO_CLOSED = 0.18
MOUTH_RATIO_SMALL = 0.25

# load the picture we wanna flash on screen
secret_img = cv2.imread(SECRET_IMAGE_PATH)
if secret_img is None:
    raise FileNotFoundError(f"Could not find image: {SECRET_IMAGE_PATH}")

# grab the webcam
cap = cv2.VideoCapture(0)

# setting up the fancy face landmark thing from mediapipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# pulling out the landmark groups for eyes + mouth
left_eye_idx = set()
right_eye_idx = set()
lips_idx = set()

for c in mp_face_mesh.FACEMESH_LEFT_EYE:
    left_eye_idx.update(c)
for c in mp_face_mesh.FACEMESH_RIGHT_EYE:
    right_eye_idx.update(c)
for c in mp_face_mesh.FACEMESH_LIPS:
    lips_idx.update(c)

# tiny helper to see how "open" or "closed" a region is
def region_ratio(landmarks, idx_set, img_w, img_h):
    xs, ys = [], []
    for i in idx_set:
        lm = landmarks[i]
        xs.append(lm.x * img_w)
        ys.append(lm.y * img_h)

    if not xs:
        return None

    # basic box around the points
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width = max_x - min_x
    height = max_y - min_y

    if width == 0:
        return None

    return height / width  # the vibe check for tall/wide

while True:
    ret, frame = cap.read()
    if not ret:
        break  # webcam said nope

    h, w, _ = frame.shape

    # mediapipe wants RGB, so we give it RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    show_secret = False
    status_text = "no face here"

    # if it found a face, cool, let's do stuff
    if results.multi_face_landmarks:
        face = results.multi_face_landmarks[0].landmark

        eye_ratio_left = region_ratio(face, left_eye_idx, w, h)
        eye_ratio_right = region_ratio(face, right_eye_idx, w, h)
        mouth_ratio = region_ratio(face, lips_idx, w, h)

        # just average both eyes so it's not weird
        if eye_ratio_left is not None and eye_ratio_right is not None and mouth_ratio is not None:
            eye_ratio = (eye_ratio_left + eye_ratio_right) / 2.0

            # these are the triggers
            eyes_closed = eye_ratio < EYE_RATIO_CLOSED
            mouth_small = mouth_ratio < MOUTH_RATIO_SMALL

            if eyes_closed and mouth_small:
                show_secret = True
                status_text = "yo it's happening"
            else:
                status_text = f"eyes: {eye_ratio:.2f}, mouth: {mouth_ratio:.2f}"

    # decide what to show — either webcam or your secret pic
    if show_secret:
        display = cv2.resize(secret_img, (w, h))
    else:
        display = frame.copy()

    # put a little text on screen so you know what's up
    cv2.putText(display, status_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("secret trigger", display)

    # press q to bounce
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# clean-up so the camera isn't stuck later
cap.release()
cv2.destroyAllWindows()
