#include <LiquidCrystal.h>

// RS, E, D4, D5, D6, D7
LiquidCrystal lcd(12, 11, 7, 6, 5, 4);

const int BTN_PIN = 13;

bool running = false;
unsigned long lastDebounce = 0;
const unsigned long debounceMs = 120;

String line = "";

void setup() {
  pinMode(BTN_PIN, INPUT_PULLUP);

  Serial.begin(115200);

  lcd.begin(16, 2);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Ready");
  lcd.setCursor(0, 1);
  lcd.print("Press button");
}

void showStatus() {
  lcd.clear();
  lcd.setCursor(0, 0);
  if (running) {
    lcd.print("Session: RUN");
    lcd.setCursor(0, 1);
    lcd.print("Scoring...");
  } else {
    lcd.print("Session: STOP");
    lcd.setCursor(0, 1);
    lcd.print("Waiting score");
  }
}

void showScore(int score) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Activity Score");

  lcd.setCursor(0, 1);
  lcd.print(score);
  lcd.print("/100");
}

void loop() {
  // ---- Button toggle start/stop ----
  if (millis() - lastDebounce > debounceMs) {
    if (digitalRead(BTN_PIN) == LOW) {
      lastDebounce = millis();

      // toggle
      running = !running;

      if (running) Serial.println("START");
      else         Serial.println("STOP");

      showStatus();

      // wait for release so it doesn't double-trigger
      while (digitalRead(BTN_PIN) == LOW) delay(5);
    }
  }

  // ---- Read score from PC ----
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      line.trim();

      // Expect: SCORE:83
      if (line.startsWith("SCORE:")) {
        int score = line.substring(6).toInt();
        if (score < 0) score = 0;
        if (score > 100) score = 100;
        showScore(score);
      }

      line = "";
    } else {
      line += c;
      if (line.length() > 40) line = ""; // safety
    }
  }
}
