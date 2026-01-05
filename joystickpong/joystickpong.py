import math, random, time, threading
from dataclasses import dataclass

import pygame
import serial
import serial.tools.list_ports

# ----------------- setup -----------------
PORT = "COM3"      
BAUD = 115200

W, H = 900, 600
FPS = 60

PADDLE_W, PADDLE_H = 140, 14
TOP_Y = 40
BOT_Y = H - 50

BALL_R = 7

MIN_PWR_MS = 60
MAX_PWR_MS = 1500
MIN_SPEED = 5.0
MAX_SPEED = 13.0

SWING_WINDOW_MS = 160
RELEASE_COOLDOWN_MS = 120

SPEEDUP = 1.045
MAX_RALLY_SPEED = 19.0

# bot smooth + a bit unpredictable
AI_REACT_MIN = 0.04
AI_REACT_MAX = 0.13
AI_AIM_ERR_MIN = -26
AI_AIM_ERR_MAX = 26
AI_WOBBLE = 9
AI_MAX_V = 10.0
AI_ACCEL = 1.25
AI_TARGET_BLEND = 0.08
AI_FAKEOUT_CHANCE = 0.06
AI_FAKEOUT_RANGE = 60

# meter
METER_X, METER_Y = 18, 18
METER_W, METER_H = 220, 16


# ----------------- serial -----------------
@dataclass
class Ctrl:
    x: int = 512
    btn: int = 0
    sw: int = 0
    chg_ms: int = 0
    pwr_ms: int = 0

class SerialController:
    def __init__(self, port: str, baud: int):
        self.port = port
        self.baud = baud
        self.state = Ctrl()
        self._lock = threading.Lock()
        self._stop = False
        self._t = None
        self._ser = None

    def start(self):
        self._ser = serial.Serial(self.port, self.baud, timeout=0.05)
        time.sleep(1.2)
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def stop(self):
        self._stop = True
        if self._t:
            self._t.join(timeout=0.5)
        if self._ser and self._ser.is_open:
            self._ser.close()

    def _parse(self, line: str):
        parts = [p.strip() for p in line.split(",") if p.strip() != ""]
        if len(parts) < 2:
            return
        d = {}
        for i in range(0, len(parts) - 1, 2):
            d[parts[i].upper()] = parts[i + 1]

        with self._lock:
            if "X" in d: self.state.x = int(float(d["X"]))
            if "BTN" in d: self.state.btn = int(float(d["BTN"]))
            if "SW" in d: self.state.sw = int(float(d["SW"]))
            if "CHGMS" in d: self.state.chg_ms = int(float(d["CHGMS"]))
            if "PWRMS" in d: self.state.pwr_ms = int(float(d["PWRMS"]))

    def _run(self):
        buf = b""
        while not self._stop:
            try:
                chunk = self._ser.read(256)
                if chunk:
                    buf += chunk
                    while b"\n" in buf:
                        raw, buf = buf.split(b"\n", 1)
                        s = raw.decode("utf-8", errors="ignore").strip()
                        if s:
                            self._parse(s)
                else:
                    time.sleep(0.004)
            except Exception:
                time.sleep(0.05)

    def snapshot(self) -> Ctrl:
        with self._lock:
            return Ctrl(**self.state.__dict__)


# ----------------- helpers -----------------
def clamp(v, a, b): 
    return max(a, min(b, v))

def mapv(v, a, b, c, d):
    if b == a:
        return c
    t = (v - a) / (b - a)
    return c + t * (d - c)

def speed_from_power(ms: int) -> float:
    ms = int(clamp(ms, MIN_PWR_MS, MAX_PWR_MS))
    return mapv(ms, MIN_PWR_MS, MAX_PWR_MS, MIN_SPEED, MAX_SPEED)

def scale_vel(vx, vy, factor):
    vx *= factor
    vy *= factor
    s = math.hypot(vx, vy)
    if s > MAX_RALLY_SPEED:
        k = MAX_RALLY_SPEED / s
        vx *= k
        vy *= k
    return vx, vy


# ----------------- objects -----------------
class Paddle:
    def __init__(self, y):
        self.y = y
        self.cx = W // 2

    def set_x(self, x):
        self.cx = int(clamp(x, 0, W))

    def rect(self):
        return pygame.Rect(int(self.cx - PADDLE_W/2), int(self.y - PADDLE_H/2), PADDLE_W, PADDLE_H)

class Ball:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = W / 2
        self.y = H / 2
        self.vx = 0.0
        self.vy = 0.0
        self.live = False

    def r(self):
        return pygame.Rect(int(self.x - BALL_R), int(self.y - BALL_R), BALL_R*2, BALL_R*2)

    def update(self):
        if not self.live:
            return
        self.x += self.vx
        self.y += self.vy

        if self.x - BALL_R <= 0:
            self.x = BALL_R
            self.vx *= -1
        elif self.x + BALL_R >= W:
            self.x = W - BALL_R
            self.vx *= -1

    def serve_from_bottom(self, paddle_x, power_ms):
        speed = speed_from_power(power_ms)
        self.x = paddle_x
        self.y = BOT_Y - 10

        self.vx = random.uniform(-0.35, 0.35) * speed
        self.vy = -math.sqrt(max(0.0, speed*speed - self.vx*self.vx))
        self.live = True

    def smash_up(self, paddle: Paddle, power_ms: int):
        speed = speed_from_power(power_ms)
        hit = (self.x - paddle.cx) / (PADDLE_W / 2)
        hit = clamp(hit, -1.0, 1.0)
        ang = mapv(hit, -1, 1, -0.75, 0.75)
        self.vx = math.sin(ang) * speed
        self.vy = -math.cos(ang) * speed


# ----------------- draw -----------------
def draw_meter(screen, font, chg_ms):
    pygame.draw.rect(screen, (255,255,255), (METER_X, METER_Y, METER_W, METER_H), 2)
    pct = clamp(chg_ms / MAX_PWR_MS, 0.0, 1.0)
    fill = int((METER_W - 4) * pct)
    if fill > 0:
        pygame.draw.rect(screen, (255,255,255), (METER_X+2, METER_Y+2, fill, METER_H-4))
    txt = font.render(f"{int(pct*100)}%", True, (200,200,200))
    screen.blit(txt, (METER_X + METER_W + 10, METER_Y - 2))


# ----------------- main -----------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("pong")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)

    ctrl = SerialController(PORT, BAUD)
    try:
        ctrl.start()
    except Exception as e:
        print("serial failed:", e)
        print([p.device for p in serial.tools.list_ports.comports()])
        return

    top = Paddle(TOP_Y)
    bot = Paddle(BOT_Y)
    ball = Ball()

    score_top = 0
    score_bot = 0

    # input smoothing
    bot_x_s = W/2

    # fool-proof release detection (python side)
    prev_btn = 0
    prev_chg = 0
    last_release_time = 0.0
    last_charge_ms = 0

    # swing window
    swing_until = 0.0
    swing_power = 0

    # bot smooth motion
    ai_target = W/2
    ai_target_s = float(ai_target)
    ai_v = 0.0
    next_react = time.time() + random.uniform(AI_REACT_MIN, AI_REACT_MAX)

    running = True
    while running:
        clock.tick(FPS)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

        s = ctrl.snapshot()

        if s.chg_ms > 0:
            last_charge_ms = s.chg_ms

        # bottom paddle x only (smooth)
        tx = mapv(s.x, 0, 1023, 0, W)
        bot_x_s = bot_x_s * 0.75 + tx * 0.25
        bot.set_x(bot_x_s)

        # reset point
        if s.sw == 1:
            ball.reset()

        # release detection that won't miss
        btn_fell = (prev_btn == 1 and s.btn == 0)
        chg_reset = (prev_chg > 0 and s.chg_ms == 0)

        now = time.time()
        cooldown_ok = (now - last_release_time) * 1000.0 >= RELEASE_COOLDOWN_MS
        released = cooldown_ok and (btn_fell or chg_reset)

        if released:
            last_release_time = now
            pwr = s.pwr_ms if s.pwr_ms > 0 else last_charge_ms
            pwr = int(clamp(pwr, MIN_PWR_MS, MAX_PWR_MS))

            if not ball.live:
                ball.serve_from_bottom(bot.cx, pwr)
            else:
                swing_power = pwr
                swing_until = now + SWING_WINDOW_MS / 1000.0

        prev_btn = s.btn
        prev_chg = s.chg_ms

        # bot: smoother + unpredictable but not dumb
        now = time.time()
        if ball.live and now >= next_react:
            next_react = now + random.uniform(AI_REACT_MIN, AI_REACT_MAX)

            aim_err = random.uniform(AI_AIM_ERR_MIN, AI_AIM_ERR_MAX)
            if random.random() < AI_FAKEOUT_CHANCE:
                aim_err += random.uniform(-AI_FAKEOUT_RANGE, AI_FAKEOUT_RANGE)

            wob = random.uniform(-AI_WOBBLE, AI_WOBBLE)
            ai_target = clamp(ball.x + aim_err + wob, 0, W)

        ai_target_s = (1 - AI_TARGET_BLEND) * ai_target_s + AI_TARGET_BLEND * ai_target

        dx = ai_target_s - top.cx
        desired_v = clamp(dx * 0.18, -AI_MAX_V, AI_MAX_V)

        if ai_v < desired_v:
            ai_v = min(ai_v + AI_ACCEL, desired_v)
        else:
            ai_v = max(ai_v - AI_ACCEL, desired_v)

        top.set_x(top.cx + ai_v)

        # ball + collisions
        ball.update()

        if ball.live:
            br = ball.r()

            # bottom hit
            if ball.vy > 0 and br.colliderect(bot.rect()):
                ball.y = bot.y - PADDLE_H/2 - BALL_R - 1

                if time.time() <= swing_until:
                    ball.smash_up(bot, swing_power)
                else:
                    ball.vy *= -1
                    hit = (ball.x - bot.cx) / (PADDLE_W/2)
                    ball.vx += clamp(hit, -1, 1) * 1.05

                ball.vx, ball.vy = scale_vel(ball.vx, ball.vy, SPEEDUP)

            # top hit
            if ball.vy < 0 and br.colliderect(top.rect()):
                ball.y = top.y + PADDLE_H/2 + BALL_R + 1
                ball.vy *= -1
                hit = (ball.x - top.cx) / (PADDLE_W/2)
                ball.vx += clamp(hit, -1, 1) * 0.85

                ball.vx, ball.vy = scale_vel(ball.vx, ball.vy, SPEEDUP)

            # score
            if ball.y < -20:
                score_bot += 1
                ball.reset()
                ai_v *= 0.4
            elif ball.y > H + 20:
                score_top += 1
                ball.reset()
                ai_v *= 0.4

        # draw
        screen.fill((0,0,0))
        pygame.draw.rect(screen, (255,255,255), top.rect())
        pygame.draw.rect(screen, (255,255,255), bot.rect())

        if ball.live:
            pygame.draw.circle(screen, (255,255,255), (int(ball.x), int(ball.y)), BALL_R)
        else:
            pygame.draw.circle(screen, (255,255,255), (int(bot.cx), int(bot.y - 10)), BALL_R)

        score = font.render(f"{score_top} : {score_bot}", True, (255,255,255))
        screen.blit(score, (W - score.get_width() - 18, 14))

        draw_meter(screen, font, s.chg_ms)

        pygame.display.flip()

    ctrl.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
