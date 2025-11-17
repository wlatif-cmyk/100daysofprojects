#include <LiquidCrystal.h>
#define TRIG_PIN 3
#define ECHO_PIN 2
#define BUZZ_PIN 11


//lcd setup
LiquidCrystal lcd(13, 12, 7, 6, 5, 4);

float distance = 0.0;
float timing = 0.0;

//overall code setup
void setup() { 
  lcd.begin(16, 2);
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZ_PIN, OUTPUT);

}

void loop() {


  digitalWrite(TRIG_PIN, LOW);
  delay(50);

  digitalWrite(TRIG_PIN, HIGH);
  delay(50);

  digitalWrite(TRIG_PIN, LOW);


  //ultrasonic sensor echo timing - distance calculations
  timing = pulseIn(ECHO_PIN, HIGH);
  distance = (timing * 0.034) / 2;

  Serial.println(distance);

  if(distance > 0 && distance > 30) {
    lcd.println("study");
    delay(100);
    lcd.clear();
    digitalWrite(BUZZ_PIN, HIGH);
  } else {
    digitalWrite(BUZZ_PIN, LOW);
  }

  //overall delay to prevent fluctuations 
  delay(200);

}