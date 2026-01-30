#include <LiquidCrystal.h>

LiquidCrystal lcd(26, 27, 14, 13, 23, 22);

#define BTN_PIN 18

static const int LCD_COLS = 16;
static const int LCD_ROWS = 2;

static const int MAX_GAMES = 20;
String g1[MAX_GAMES];
String g2[MAX_GAMES];
int gameCount = 0;
int gameIndex = 0;

String fit16(String s) {
  s.replace("\n", " ");
  s.replace("\r", " ");
  if ((int)s.length() > LCD_COLS) s = s.substring(0, LCD_COLS);
  while ((int)s.length() < LCD_COLS) s += " ";
  return s;
}

void showLCD(const String &l1, const String &l2) {
  lcd.setCursor(0, 0);
  lcd.print(fit16(l1));
  lcd.setCursor(0, 1);
  lcd.print(fit16(l2));
}

void showCurrentGame() {
  Serial.print("Show game index: ");
  Serial.print(gameIndex);
  Serial.print(" / ");
  Serial.println(gameCount);

  if (gameCount <= 0) {
    showLCD("No games", "Run Python");
    return;
  }
  showLCD(g1[gameIndex], g2[gameIndex]);
}

void parsePacket(const String &pkt) {
  Serial.println("=== PACKET RECEIVED ===");
  Serial.println(pkt);

  if (!pkt.startsWith("NBA;")) {
    Serial.println("Packet does not start with NBA;");
    return;
  }

  int first = pkt.indexOf(';');
  int second = pkt.indexOf(';', first + 1);
  if (second < 0) {
    Serial.println("Malformed packet");
    return;
  }

  String countStr = pkt.substring(first + 1, second);
  int n = countStr.toInt();

  Serial.print("Game count in packet: ");
  Serial.println(n);

  int newCount = 0;
  int pos = second + 1;

  while (newCount < MAX_GAMES && newCount < n) {
    int nextSemi = pkt.indexOf(';', pos);
    if (nextSemi < 0) break;

    String item = pkt.substring(pos, nextSemi);
    int bar = item.indexOf('|');

    if (bar > 0) {
      g1[newCount] = item.substring(0, bar);
      g2[newCount] = item.substring(bar + 1);
      Serial.print("Stored game ");
      Serial.print(newCount);
      Serial.print(": ");
      Serial.print(g1[newCount]);
      Serial.print(" | ");
      Serial.println(g2[newCount]);
      newCount++;
    }
    pos = nextSemi + 1;
  }

  gameCount = newCount;
  gameIndex = 0;

  Serial.print("Total games stored: ");
  Serial.println(gameCount);

  showCurrentGame();
}

void setup() {
  Serial.begin(115200);
  pinMode(BTN_PIN, INPUT_PULLUP);

  lcd.begin(LCD_COLS, LCD_ROWS);
  showLCD("Waiting NBA...", "Run Python...");
}

void loop() {
  // Button scroll (edge detect)
  static int lastBtn = HIGH;
  int nowBtn = digitalRead(BTN_PIN);

  if (lastBtn == HIGH && nowBtn == LOW) {
    Serial.println("BUTTON PRESS DETECTED");
    if (gameCount > 0) {
      gameIndex = (gameIndex + 1) % gameCount;
      showCurrentGame();
    }
    delay(200);
  }
  lastBtn = nowBtn;

  // Serial receive
  if (Serial.available()) {
    String pkt = Serial.readStringUntil('\n');
    pkt.trim();
    parsePacket(pkt);
  }
}
