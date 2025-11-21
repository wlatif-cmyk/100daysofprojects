#define BUZZER_PIN   9
#define BUTTON1_PIN  3
#define BUTTON2_PIN  2

void setup() {
  pinMode(BUZZER_PIN, OUTPUT);

  pinMode(BUTTON1_PIN, INPUT);
  pinMode(BUTTON2_PIN, INPUT);

  Serial.begin(9600);
}

void loop() {
  int b1 = digitalRead(BUTTON1_PIN);
  int b2 = digitalRead(BUTTON2_PIN);

  Serial.print("B1 = ");
  Serial.print(b1);
  Serial.print("  B2 = ");
  Serial.println(b2);


  bool button1Pressed = (b1 == LOW);  
  bool button2Pressed = (b2 == LOW);  

  if (button1Pressed && !button2Pressed) {
    tone(BUZZER_PIN, 440);   // A4
  }
  else if (button2Pressed && !button1Pressed) {
    tone(BUZZER_PIN, 523);   // C5
  }
  else if (button1Pressed && button2Pressed) {
    tone(BUZZER_PIN, 660);   // both pressed
  }
  else {
    noTone(BUZZER_PIN);       }
}
