#include <LiquidCrystal.h>
LiquidCrystal lcd(13, 12, 11, 10, 9, 8);

int buzzerPin = 2;
char incoming;

void setup() {
  pinMode(buzzerPin, OUTPUT);
  digitalWrite(buzzerPin, LOW);

  lcd.begin(16, 2);
  lcd.clear();

  Serial.begin(9600);  // must match Python baud rate
}

void loop() {
  if (Serial.available() > 0) {
    incoming = Serial.read();

    if (incoming == 'B') {
      // turn ACTIVE buzzer ON
      digitalWrite(buzzerPin, HIGH);

      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Pay attention!");
    }
    else if (incoming == 'S') {
      // turn ACTIVE buzzer OFF
      digitalWrite(buzzerPin, LOW);

      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("You're good :)");
    }
  }
}
