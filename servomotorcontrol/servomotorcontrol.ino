#include <Servo.h>

Servo myServo;

const int vrxPin   = A0;   // joystick X-axis
const int swPin    = 4;    // joystick button (SW)
const int servoPin = 9;    // servo signal pin

bool autoMode = false;     // false = joystick mode, true = auto sweep
bool lastButton = HIGH;

void setup() {
  myServo.attach(servoPin);
  pinMode(swPin, INPUT_PULLUP);  // SW is active LOW
  Serial.begin(9600);
}

void loop() {
  bool currentButton = digitalRead(swPin);

  // toggle mode on button press
  if (currentButton == LOW && lastButton == HIGH) {
    autoMode = !autoMode;
    delay(200); // debounce
  }
  lastButton = currentButton;

  // for auto mode to sweep back and forth
  if (autoMode) {
    for (int pos = 0; pos <= 180 && autoMode; pos++) {
      myServo.write(pos);
      if (digitalRead(swPin) == LOW) {  // allow immediate exit
        autoMode = false;
        delay(200);
        break;
      }
    }

    for (int pos = 180; pos >= 0 && autoMode; pos--) {
      myServo.write(pos);
      if (digitalRead(swPin) == LOW) {
        autoMode = false;
        delay(200);
        break;
      }
    }
  }

  // direct control , when autobounce turned off only
  else {
    int xValue = analogRead(vrxPin);       // 0–1023
    int angle  = map(xValue, 0, 1023, 0, 180);
    myServo.write(angle);
    delay(10);
  }
}
