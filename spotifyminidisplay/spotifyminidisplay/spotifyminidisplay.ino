/*******************************************************
  ESP32 + 16x2 LCD Spotify “Now Playing” Receiver + Buttons
  - Laptop POSTs JSON to:  http://ESP32_IP/spotify
  - ESP32 calls Laptop Flask commands on port 5000:
      POST /prev
      POST /next
      POST /pause
      POST /seek?delta_ms=10000   (or -10000)

  Buttons:
    BACK  = GPIO13 (INPUT_PULLUP)  short: prev track, hold: seek -10s repeating
    NEXT  = GPIO35 (INPUT)         short: next track, hold: seek +10s repeating
      NOTE: GPIO35 has NO internal pullup.
            You MUST add external pull-up: 10k from GPIO35 -> 3.3V,
            and button from GPIO35 -> GND.

  LCD:
    RS=14, E=27, D4=26, D5=25, D6=33, D7=32
    RW must be tied to GND

  Display:
    Splash on song change (title/artist for a bit),
    then: title + "mm:ss/mm:ss" (progress/duration)
*******************************************************/

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <LiquidCrystal.h>
#include <HTTPClient.h>

// ---------- Wi-Fi ----------
const char* WIFI_SSID = "Smart Family";
const char* WIFI_PASS = "klwa1413";

// ---------- Laptop (Flask server) ----------
const char* LAPTOP_IP = "192.168.5.250";  // <-- your laptop IPv4
const int   LAPTOP_PORT = 5000;

// ---------- LCD pins (16x2, 4-bit) ----------
const int LCD_RS = 14;
const int LCD_E  = 27;
const int LCD_D4 = 26;
const int LCD_D5 = 25;
const int LCD_D6 = 33;
const int LCD_D7 = 32;

LiquidCrystal lcd(LCD_RS, LCD_E, LCD_D4, LCD_D5, LCD_D6, LCD_D7);
WebServer server(80);

// ---------- Buttons ----------
const int BTN_BACK = 13;  // prev track (short), seek -10s (hold)
const int BTN_NEXT = 35;  // next track (short), seek +10s (hold) [external pullup required]

// ---------- Button timing ----------
const unsigned long DEBOUNCE_MS = 30;
const unsigned long HOLD_MS = 2000;              // hold 2s to start seeking
const unsigned long SEEK_REPEAT_MS = 500;        // repeat every 0.5s while holding after HOLD_MS

unsigned long lastBtnSampleMs = 0;

bool backDown = false, nextDown = false;
unsigned long backDownAt = 0, nextDownAt = 0;
bool backHoldActive = false, nextHoldActive = false;
unsigned long backLastSeekMs = 0, nextLastSeekMs = 0;

// both-pressed pause toggle edge
bool bothWasDown = false;

// ---------- Spotify state ----------
String spTitle = "Not playing";
String spArtist = "";
uint32_t spProgressMs = 0;
uint32_t spDurationMs = 1;
bool spPlaying = false;

// Timing
unsigned long lastTickMs = 0;
unsigned long lastLcdRefreshMs = 0;

// Splash on track change
String lastTrackKey = "";
unsigned long splashUntilMs = 0;
const unsigned long SPLASH_MS = 2500;

// LCD anti-freeze maintenance
unsigned long lastHardClearMs = 0;
unsigned long lastReinitMs = 0;
const unsigned long HARD_CLEAR_EVERY_MS = 30000;
const unsigned long REINIT_EVERY_MS     = 60000;

// ---------- Helpers ----------
String fit16(const String& s) {
  String out = s;
  if (out.length() > 16) out = out.substring(0, 16);
  while (out.length() < 16) out += " ";
  return out;
}

// 2:05 format (no leading zero minutes)
String mmssFromMs(uint32_t ms) {
  uint32_t t = ms / 1000;
  char buf[8];
  snprintf(buf, sizeof(buf), "%lu:%02lu", (unsigned long)(t / 60), (unsigned long)(t % 60));
  return String(buf);
}

void reinitLCD() {
  lcd.begin(16, 2);
  lcd.clear();
}

void write2Lines(const String& l1, const String& l2) {
  lcd.setCursor(0, 0); lcd.print("                ");
  lcd.setCursor(0, 1); lcd.print("                ");
  lcd.setCursor(0, 0); lcd.print(fit16(l1));
  lcd.setCursor(0, 1); lcd.print(fit16(l2));
}

String progressLine() {
  // Show: 2:20/2:50
  return mmssFromMs(spProgressMs) + "/" + mmssFromMs(spDurationMs);
}

void renderLCD() {
  const unsigned long now = millis();

  if (now - lastHardClearMs > HARD_CLEAR_EVERY_MS) {
    lcd.clear();
    lastHardClearMs = now;
  }
  if (now - lastReinitMs > REINIT_EVERY_MS) {
    reinitLCD();
    lastReinitMs = now;
  }

  if (spTitle == "Not playing") {
    write2Lines("Not playing", "0:00/0:00");
    return;
  }

  if (now < splashUntilMs) {
    write2Lines(spTitle, spArtist);
    return;
  }

  write2Lines(spTitle, progressLine());
}

// ---------- Laptop HTTP helpers ----------
bool httpPost(const String& url) {
  HTTPClient http;
  http.begin(url);
  int code = http.POST("");
  http.end();

  Serial.print("HTTP POST ");
  Serial.print(url);
  Serial.print(" -> ");
  Serial.println(code);

  return (code >= 200 && code < 300);
}

bool sendLaptopCmd(const char* path) {
  String url = String("http://") + LAPTOP_IP + ":" + String(LAPTOP_PORT) + path;
  Serial.print("CMD ");
  Serial.println(path);
  return httpPost(url);
}

bool sendSeekDeltaMs(int deltaMs) {
  String url = String("http://") + LAPTOP_IP + ":" + String(LAPTOP_PORT) +
               "/seek?delta_ms=" + String(deltaMs);
  Serial.print("CMD SEEK delta_ms=");
  Serial.println(deltaMs);
  return httpPost(url);
}

// ---------- Button logic ----------
void pollButtons() {
  unsigned long now = millis();
  if (now - lastBtnSampleMs < DEBOUNCE_MS) return;
  lastBtnSampleMs = now;

  bool backPressed = (digitalRead(BTN_BACK) == LOW);
  bool nextPressed = (digitalRead(BTN_NEXT) == LOW);

  // Both pressed => pause toggle (edge)
  bool bothDown = backPressed && nextPressed;
  if (bothDown && !bothWasDown) {
    sendLaptopCmd("/pause");
  }
  bothWasDown = bothDown;

  // BACK press/release
  if (backPressed && !backDown) {
    backDown = true;
    backDownAt = now;
    backHoldActive = false;
    backLastSeekMs = 0;
  }
  if (!backPressed && backDown) {
    unsigned long held = now - backDownAt;
    backDown = false;

    // If hold never activated => short press does prev track
    if (held < HOLD_MS) {
      // Avoid firing short-press if bothDown caused pause
      if (!bothDown) sendLaptopCmd("/prev");
    }
  }

  // NEXT press/release
  if (nextPressed && !nextDown) {
    nextDown = true;
    nextDownAt = now;
    nextHoldActive = false;
    nextLastSeekMs = 0;
  }
  if (!nextPressed && nextDown) {
    unsigned long held = now - nextDownAt;
    nextDown = false;

    if (held < HOLD_MS) {
      if (!bothDown) sendLaptopCmd("/next");
    }
  }

  // Hold behavior: after 2s, seek and repeat every 0.5s while held
  if (backDown && backPressed && !bothDown) {
    unsigned long held = now - backDownAt;
    if (held >= HOLD_MS) {
      if (!backHoldActive) {
        backHoldActive = true;
        backLastSeekMs = 0;
      }
      if (backLastSeekMs == 0 || (now - backLastSeekMs >= SEEK_REPEAT_MS)) {
        sendSeekDeltaMs(-10000);
        backLastSeekMs = now;
      }
    }
  }

  if (nextDown && nextPressed && !bothDown) {
    unsigned long held = now - nextDownAt;
    if (held >= HOLD_MS) {
      if (!nextHoldActive) {
        nextHoldActive = true;
        nextLastSeekMs = 0;
      }
      if (nextLastSeekMs == 0 || (now - nextLastSeekMs >= SEEK_REPEAT_MS)) {
        sendSeekDeltaMs(10000);
        nextLastSeekMs = now;
      }
    }
  }
}

// ---------- HTTP endpoints ----------
void handlePing() {
  server.send(200, "text/plain", "pong");
}

void handleSpotifyPost() {
  if (!server.hasArg("plain")) {
    server.send(400, "text/plain", "Missing body");
    return;
  }

  StaticJsonDocument<384> doc;
  if (deserializeJson(doc, server.arg("plain"))) {
    server.send(400, "text/plain", "Bad JSON");
    return;
  }

  Serial.println("HTTP POST /spotify:");
  serializeJson(doc, Serial);
  Serial.println();

  String newTitle  = doc["title"]  | spTitle;
  String newArtist = doc["artist"] | spArtist;

  spProgressMs = doc["progress_ms"] | spProgressMs;
  spDurationMs = doc["duration_ms"] | spDurationMs;
  spPlaying    = doc["is_playing"]  | spPlaying;

  if (spDurationMs == 0) spDurationMs = 1;
  if (spProgressMs > spDurationMs) spProgressMs = spDurationMs;

  spTitle = newTitle;
  spArtist = newArtist;

  String key = spTitle + "||" + spArtist;
  if (key != lastTrackKey && spTitle != "Not playing") {
    lastTrackKey = key;
    splashUntilMs = millis() + SPLASH_MS;
    lcd.clear();
  }

  // respond immediately (prevents HTTP timeouts)
  server.send(200, "application/json", "{\"ok\":true}");
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(BTN_BACK, INPUT_PULLUP);

  // GPIO35 has NO internal pullup. External 10k pull-up to 3.3V required.
  pinMode(BTN_NEXT, INPUT);

  lcd.begin(16, 2);
  lcd.clear();
  write2Lines("Connecting WiFi", "...");

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  lcd.clear();
  write2Lines("Spotify Ready", "POST /spotify");

  server.on("/ping", HTTP_GET, handlePing);
  server.on("/spotify", HTTP_POST, handleSpotifyPost);
  server.begin();

  lastTickMs = millis();
  lastLcdRefreshMs = millis();
  lastHardClearMs = millis();
  lastReinitMs = millis();
}

void loop() {
  server.handleClient();
  pollButtons();

  // local progress ticking for the display
  unsigned long now = millis();
  unsigned long dt = now - lastTickMs;
  lastTickMs = now;

  if (spPlaying && spTitle != "Not playing") {
    uint64_t newProg = (uint64_t)spProgressMs + (uint64_t)dt;
    if (newProg > spDurationMs) newProg = spDurationMs;
    spProgressMs = (uint32_t)newProg;
  }

  // refresh LCD
  if (now - lastLcdRefreshMs >= 500) {
    lastLcdRefreshMs = now;
    renderLCD();
  }
}
