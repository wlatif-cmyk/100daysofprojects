// ESP32 Joystick -> Serial stream for PC mouse control
// Sends: dx,dy,sw\n   (integers; sw = 1 when pressed)

#define VRX_PIN 32
#define VRY_PIN 35
#define SW_PIN  25

// Tuning
const int CAL_SAMPLES = 200;
const int DEADZONE    = 120;   // increase if cursor drifts
const int MAX_OUTPUT  = 1000;  // scale of dx/dy sent to PC

int cx = 2048, cy = 2048;

int clampInt(int v, int lo, int hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

void setup() {
  Serial.begin(115200);
  pinMode(SW_PIN, INPUT_PULLUP);

  // Calibrate center (don't touch joystick during this)
  long sx = 0, sy = 0;
  for (int i = 0; i < CAL_SAMPLES; i++) {
    sx += analogRead(VRX_PIN);
    sy += analogRead(VRY_PIN);
    delay(3);
  }
  cx = sx / CAL_SAMPLES;
  cy = sy / CAL_SAMPLES;

  Serial.print("Center cx="); Serial.print(cx);
  Serial.print(" cy="); Serial.println(cy);
}

void loop() {
  int x  = analogRead(VRX_PIN);
  int y  = analogRead(VRY_PIN);
  int sw = (digitalRead(SW_PIN) == LOW) ? 1 : 0;

  int dx = x - cx;
  int dy = y - cy;

  // Deadzone to stop drifting
  if (abs(dx) < DEADZONE) dx = 0;
  if (abs(dy) < DEADZONE) dy = 0;

  // Map roughly to -MAX_OUTPUT..MAX_OUTPUT (ESP32 ADC ~0..4095)
  // 2048-ish is center; range is about +/-2048
  dx = (dx * MAX_OUTPUT) / 2048;
  dy = (dy * MAX_OUTPUT) / 2048;

  dx = clampInt(dx, -MAX_OUTPUT, MAX_OUTPUT);
  dy = clampInt(dy, -MAX_OUTPUT, MAX_OUTPUT);

  // Send as CSV
  Serial.print(dx);
  Serial.print(",");
  Serial.print(dy);
  Serial.print(",");
  Serial.println(sw);

  delay(10); // ~100 updates/sec
}
