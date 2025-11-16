#define BUTTON_PIN 2
#define LED_ORANGE 5
#define LED_BLUE 6 
int lastButtonState = LOW;
int buttonCounter = 0;

  int orangeState[] = {HIGH, LOW, LOW};
  int blueState[] = {LOW, HIGH, LOW};

void setup() {
  pinMode(BUTTON_PIN, INPUT);
  pinMode(LED_ORANGE, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  Serial.begin(9600);


}

void loop() {
  int buttonState = digitalRead(BUTTON_PIN);
  if (lastButtonState == LOW && buttonState == HIGH) {
    buttonCounter ++;
  }
  
  lastButtonState = buttonState;

  if(buttonCounter > 2) {
    buttonCounter = 0;
  }

  Serial.println(buttonCounter);

  int led[] = {LED_ORANGE, LED_BLUE};
  int states[] = {orangeState[buttonCounter], blueState[buttonCounter]};

  for(int i = 0; i < 2; i++) {
    digitalWrite(led[i], states[i]);
  }
}

