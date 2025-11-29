#include <Servo.h>

Servo myServo;

// change these if servo is reversed
const int OPEN_ANGLE  = 20;   // angle for "open hand"
const int CLOSE_ANGLE = 160;  // angle for "closed hand"

void setup() {
  Serial.begin(9600);
  myServo.attach(9);       // servo signal pin
  myServo.write(OPEN_ANGLE); // start open
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();

    if (cmd == 'O') {           // open
      myServo.write(OPEN_ANGLE);
    } else if (cmd == 'C') {    // close
      myServo.write(CLOSE_ANGLE);
    }
    // you can ignore other characters or add more if you want
  }
}
