#include <LiquidCrystal.h>
#define TRIG_PIN 3
#define ECHO_PIN 2
#define BUZZ_PIN 11
#define BUTTON_PIN 8

LiquidCrystal lcd(13, 12, 7, 6, 5, 4);

float distance = 0.0;
float timing = 0.0;
long timer = 5460;
int lastButtonState = LOW;


void setup() { 
  lcd.begin(16, 2);
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZ_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
}

void loop() {

  int buttonPressed = digitalRead(BUTTON_PIN);

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  timing = pulseIn(ECHO_PIN, HIGH);
  distance = (timing * 0.034) / 2;

  Serial.println(distance);

  if(distance > 0 && distance < 30) {
    timer--;
    delay(1000);
    int hours = timer / 3600;
    int minutes = (timer % 3600) / 60;
    lcd.setCursor(0,0);
    lcd.print("Timer:");
    lcd.setCursor(7,0);
    lcd.print("   ");
    lcd.setCursor(7,0);
    lcd.print(hours);
    lcd.print(":");
    lcd.print(minutes);
    digitalWrite(BUZZ_PIN, LOW);
  }
  else if(distance > 30) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Study!");
    digitalWrite(BUZZ_PIN, HIGH);
    timer = 5400;
  } else {
    digitalWrite(BUZZ_PIN, LOW);
  }

  if(timer <= 0){
    lcd.setCursor(0, 0);
    lcd.print("Timer done!");
    digitalWrite(BUZZ_PIN, HIGH);
    digitalWrite(BUZZ_PIN, LOW);
  }
  
  if(buttonPressed == HIGH && lastButtonState == LOW) {
    timer = 5460;
  }

  lastButtonState = buttonPressed;

  Serial.println(timer);
}


