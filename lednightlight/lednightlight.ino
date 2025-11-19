#define LED_PIN1 3
#define LED_PIN2 5 


//overall pin setup 
void setup() {
  pinMode(LED_PIN1, OUTPUT);
  pinMode(LED_PIN2, OUTPUT);
  Serial.begin(9600);

}

//led's connected to analog pins 
void loop() {
  int value = analogRead(A0);

  delay(50);

  Serial.println(value);


//brightness for pins when dark
  int brightness = map(value, 1023, 0, 0, 255);
  brightness = constrain(brightness, 0, 255);

    if(value > 400) {
      digitalWrite(LED_PIN1, HIGH);
      digitalWrite(LED_PIN2, HIGH);
    } else {
    analogWrite(LED_PIN1, brightness);
    analogWrite(LED_PIN2, brightness);
    }

    delay(200);
}