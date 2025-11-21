#include <LiquidCrystal.h>

#define LED_PIN1 3
#define LED_PIN2 5

// LCD in 4-bit mode: RS, E, D4, D5, D6, D7
LiquidCrystal lcd(13, 12, 11, 10, 9, 8);

// Simple clock variables (software clock using millis)
int hours   = 23;   // <-- set your start time here
int minutes = 59;
int seconds = 45;

// Alarm time – when reached, LEDs will flash
const int alarmHour   = 0;   // 00:00
const int alarmMinute = 0;

bool alarmTriggeredToday = false;

unsigned long previousMillis = 0;
const unsigned long oneSecond = 1000;

// ---------------- overall pin setup ----------------
void setup() {
  pinMode(LED_PIN1, OUTPUT);
  pinMode(LED_PIN2, OUTPUT);
  Serial.begin(9600);

  // LCD setup (assuming 16x2)
  lcd.begin(16, 2);
  lcd.print("Night Light");
  lcd.setCursor(0, 1);
  lcd.print("Clock starting");
  delay(2000);
  lcd.clear();
}

// ---------------- helper: night light flash --------
void flashNightLight() {
  // Flash the LEDs a few times instead of a buzzer alarm
  for (int i = 0; i < 10; i++) {
    digitalWrite(LED_PIN1, HIGH);
    digitalWrite(LED_PIN2, HIGH);

    lcd.setCursor(10, 0);
    lcd.print("ALRM");

    delay(250);

    digitalWrite(LED_PIN1, LOW);
    digitalWrite(LED_PIN2, LOW);

    lcd.setCursor(10, 0);
    lcd.print("    ");

    delay(250);
  }
}

// ---------------- main loop ----------------
void loop() {
  // --- update software clock using millis() ---
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= oneSecond) {
    previousMillis += oneSecond;
    seconds++;

    if (seconds >= 60) {
      seconds = 0;
      minutes++;
    }
    if (minutes >= 60) {
      minutes = 0;
      hours++;
    }
    if (hours >= 24) {
      hours = 0;
      // new day: allow alarm to trigger again
      alarmTriggeredToday = false;
    }
  }

  // --- light sensor + night light control (your original logic) ---
  int value = analogRead(A0);

  delay(50);

  Serial.println(value);

  // brightness for pins when dark
  int brightness = map(value, 1023, 0, 0, 255);
  brightness = constrain(brightness, 0, 255);

  if (value > 400) {
    digitalWrite(LED_PIN1, HIGH);
    digitalWrite(LED_PIN2, HIGH);
  } else {
    analogWrite(LED_PIN1, brightness);
    analogWrite(LED_PIN2, brightness);
  }

  // --- update LCD display ---
  // Line 0: Time
  lcd.setCursor(0, 0);
  lcd.print("Time ");

  if (hours < 10) lcd.print('0');
  lcd.print(hours);
  lcd.print(':');
  if (minutes < 10) lcd.print('0');
  lcd.print(minutes);

  // Line 1: Light sensor value
  lcd.setCursor(0, 1);
  lcd.print("L:");
  lcd.print(value);
  lcd.print("    ");  // clear leftover chars

  // --- check alarm time and flash night light instead of buzzer ---
  if (hours == alarmHour && minutes == alarmMinute && !alarmTriggeredToday) {
    flashNightLight();
    alarmTriggeredToday = true;
  }

  delay(200);
}
