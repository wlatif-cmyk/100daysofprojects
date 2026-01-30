import cv2
import time
import math
import random
import numpy as np
import pygame
import mediapipe as mp

# -----------------------------
# Hand Saber (CV + Pygame)
# -----------------------------

W, H = 1280, 720
FPS = 60

# Gameplay tuning
ORB_RADIUS = 28
HIT_RADIUS = 55          # how close hand must be to "slice"
TRAIL_LEN = 14           # hand trail length for slicing feel
SPAWN_BASE = 0.65        # seconds between spawns at start
SPEED_BASE = 280         # pixels/sec at start
DIFF_RAMP = 0.012        # difficulty increases per second
MISS_PENALTY = 7         # score penalty on miss

# Orbs: color id 0=left hand, 1=right hand, 2=either
ORB_TYPES = [
    (0, (70, 170, 255), "LEFT"),   # blue-ish
    (1, (255, 110, 110), "RIGHT"), # red-ish
    (2, (180, 255, 120), "ANY"),   # green-ish
]

def clamp(x, a, b): return max(a, min(b, x))

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def to_pygame_surf(bgr_frame):
    # Convert OpenCV BGR to RGB, then to pygame Surface
    rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
    rgb = np.rot90(rgb)  # rotate for pygame (width/height swap)
    return pygame.surfarray.make_surface(rgb)

class Orb:
    def __init__(self, x, y, kind, speed, wobble=0.0):
        self.x = x
        self.y = y
        self.kind = kind
        self.color = ORB_TYPES[kind][1]
        self.label = ORB_TYPES[kind][2]
        self.speed = speed
        self.wobble = wobble
        self.spawn_t = time.time()
        self.hit = False
        self.missed = False

    def update(self, dt):
        # subtle lateral wobble
        t = time.time() - self.spawn_t
        self.x += math.sin(t * 4.5) * self.wobble * dt
        self.y += self.speed * dt

    def draw(self, screen):
        # Outer glow ring
        pygame.draw.circle(screen, (*self.color, 60), (int(self.x), int(self.y)), ORB_RADIUS + 10, width=6)
        pygame.draw.circle(screen, (*self.color, 170), (int(self.x), int(self.y)), ORB_RADIUS + 3, width=4)
        # Core
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), ORB_RADIUS)
        # Center highlight
        pygame.draw.circle(screen, (255, 255, 255), (int(self.x-8), int(self.y-8)), 7)

class SlashFx:
    def __init__(self, pos, color):
        self.pos = pos
        self.color = color
        self.life = 0.35
        self.t = 0.0
        self.particles = []
        for _ in range(24):
            ang = random.random() * math.tau
            spd = random.uniform(140, 520)
            self.particles.append([pos[0], pos[1],
                                   math.cos(ang)*spd, math.sin(ang)*spd,
                                   random.uniform(0.12, 0.32)])

    def update(self, dt):
        self.t += dt
        for p in self.particles:
            p[0] += p[2]*dt
            p[1] += p[3]*dt
            p[3] += 780*dt  # gravity-ish
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]

    def draw(self, screen):
        alpha = int(255 * (1 - self.t / self.life)) if self.life > 0 else 0
        alpha = clamp(alpha, 0, 255)
        for p in self.particles:
            a = int(alpha * (p[4] / 0.32))
            col = (self.color[0], self.color[1], self.color[2], a)
            pygame.draw.circle(screen, col, (int(p[0]), int(p[1])), 4)

    def dead(self):
        return self.t >= self.life or len(self.particles) == 0

def main():
    pygame.init()
    pygame.display.set_caption("Hand Saber (CV Spell Slicer)")
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()

    # Fonts
    font_big = pygame.font.SysFont("Consolas", 44, bold=True)
    font = pygame.font.SysFont("Consolas", 26, bold=True)
    font_small = pygame.font.SysFont("Consolas", 20)

    # Webcam
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)

    # MediaPipe Hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=2,
        model_complexity=0,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )

    # Trails for slicing feel
    left_trail = []
    right_trail = []

    # Game state
    orbs = []
    fx = []
    score = 0
    combo = 0
    max_combo = 0
    misses = 0
    start_time = time.time()
    last_spawn = 0.0
    paused = False

    def spawn_orb(difficulty):
        # Spawn near top with some randomness
        x = random.uniform(0.15*W, 0.85*W)
        y = random.uniform(-120, -40)
        kind = random.choices([0,1,2], weights=[0.38, 0.38, 0.24])[0]
        speed = SPEED_BASE + difficulty * 520 + random.uniform(-40, 90)
        wobble = random.uniform(0, 90) * (0.15 + difficulty*0.2)
        orbs.append(Orb(x, y, kind, speed, wobble=wobble))

    def draw_trail(trail, color):
        # Draw thick polyline based on trail points
        if len(trail) < 2:
            return
        for i in range(len(trail)-1):
            p1 = trail[i]
            p2 = trail[i+1]
            thickness = int(18 * (i+1)/len(trail) + 4)
            alpha = int(220 * (i+1)/len(trail))
            col = (color[0], color[1], color[2], alpha)
            pygame.draw.line(screen, col, p1, p2, thickness)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    paused = not paused
                if event.key == pygame.K_r:
                    # reset
                    orbs.clear()
                    fx.clear()
                    score = 0
                    combo = 0
                    max_combo = 0
                    misses = 0
                    start_time = time.time()

        # Read frame
        ret, frame = cap.read()
        if not ret:
            break

        # Mirror for natural control
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Hand tracking
        result = hands.process(frame_rgb)

        left_hand = None
        right_hand = None

        if result.multi_hand_landmarks and result.multi_handedness:
            for lm, handed in zip(result.multi_hand_landmarks, result.multi_handedness):
                label = handed.classification[0].label  # 'Left' or 'Right' (from camera POV)
                # Use index finger tip for slicing point
                ix = lm.landmark[8].x
                iy = lm.landmark[8].y
                px = int(ix * W)
                py = int(iy * H)

                # Because frame is mirrored, MediaPipe labels may appear swapped in "your POV".
                # We'll still treat them as left/right gameplay hands by screen position for robustness:
                if px < W // 2:
                    left_hand = (px, py)
                else:
                    right_hand = (px, py)

        # Update trails
        if left_hand:
            left_trail.append(left_hand)
            left_trail = left_trail[-TRAIL_LEN:]
        else:
            left_trail = left_trail[-max(0, TRAIL_LEN//3):]  # fade out quickly

        if right_hand:
            right_trail.append(right_hand)
            right_trail = right_trail[-TRAIL_LEN:]
        else:
            right_trail = right_trail[-max(0, TRAIL_LEN//3):]

        # Difficulty
        t = time.time() - start_time
        difficulty = t * DIFF_RAMP

        if not paused:
            # Spawn control (gets faster over time)
            spawn_interval = max(0.18, SPAWN_BASE - difficulty * 0.22)
            last_spawn += dt
            if last_spawn >= spawn_interval:
                last_spawn = 0.0
                # sometimes double spawn at higher difficulty
                spawn_orb(difficulty)
                if difficulty > 0.9 and random.random() < 0.22:
                    spawn_orb(difficulty)

            # Update orbs
            for o in orbs:
                o.update(dt)

            # Check hits (using trail segments for slicing feel)
            # We'll treat the last trail point as the slice "tip", but also allow near recent segment
            def trail_hit(trail, orb_pos):
                if len(trail) == 0:
                    return False
                # check last few points
                for p in trail[-6:]:
                    if dist(p, orb_pos) <= HIT_RADIUS:
                        return True
                return False

            for o in orbs:
                if o.hit or o.missed:
                    continue

                pos = (o.x, o.y)

                can_left = (o.kind == 0 or o.kind == 2)
                can_right = (o.kind == 1 or o.kind == 2)

                hit_now = False
                hit_color = o.color

                if can_left and trail_hit(left_trail, pos):
                    hit_now = True
                if can_right and trail_hit(right_trail, pos):
                    hit_now = True

                if hit_now:
                    o.hit = True
                    combo += 1
                    max_combo = max(max_combo, combo)

                    # Score: base + combo bonus + small timing bonus (higher is better)
                    timing_bonus = int(clamp(120 - abs((o.y - H*0.55)) * 0.15, 0, 120))
                    score += 40 + combo * 3 + timing_bonus

                    fx.append(SlashFx((int(o.x), int(o.y)), hit_color))

            # Misses (orb goes off bottom)
            for o in orbs:
                if not o.hit and not o.missed and o.y > H + 80:
                    o.missed = True
                    combo = 0
                    misses += 1
                    score = max(0, score - MISS_PENALTY)

            # Clean up old orbs
            orbs = [o for o in orbs if not (o.hit or o.missed)]

            # Update FX
            for f in fx:
                f.update(dt)
            fx = [f for f in fx if not f.dead()]

        # Draw background camera into pygame
        cam_surf = to_pygame_surf(frame)
        cam_surf = pygame.transform.scale(cam_surf, (W, H))
        screen.blit(cam_surf, (0, 0))

        # Overlay a soft vignette / darken
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 65))
        screen.blit(overlay, (0, 0))

        # Draw a center divider (optional)
        pygame.draw.line(screen, (255, 255, 255, 55), (W//2, 0), (W//2, H), 2)

        # Trails
        draw_trail(left_trail, (70, 170, 255))
        draw_trail(right_trail, (255, 110, 110))

        # Orbs
        for o in orbs:
            o.draw(screen)

        # FX
        for f in fx:
            f.draw(screen)

        # HUD
        title = font_big.render("HAND SABER", True, (240, 240, 240))
        screen.blit(title, (26, 18))

        hud1 = font.render(f"Score: {score}", True, (255, 255, 255))
        hud2 = font.render(f"Combo: x{combo}   Max: x{max_combo}", True, (255, 255, 255))
        hud3 = font.render(f"Misses: {misses}", True, (255, 255, 255))
        screen.blit(hud1, (28, 74))
        screen.blit(hud2, (28, 106))
        screen.blit(hud3, (28, 138))

        # Simple instruction line
        hint = font_small.render("SPACE: pause  |  R: reset  |  ESC: quit", True, (220, 220, 220))
        screen.blit(hint, (28, H - 34))

        # Pause banner
        if paused:
            banner = pygame.Surface((W, 110), pygame.SRCALPHA)
            banner.fill((0, 0, 0, 160))
            screen.blit(banner, (0, H//2 - 55))
            txt = font_big.render("PAUSED", True, (255, 255, 255))
            screen.blit(txt, (W//2 - txt.get_width()//2, H//2 - txt.get_height()//2))

        pygame.display.flip()

    hands.close()
    cap.release()
    pygame.quit()

if __name__ == "__main__":
    main()
