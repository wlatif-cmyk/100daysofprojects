#include <Servo.h>

Servo myServo;
String input = "";

void setup() {
  Serial.begin(9600);
  myServo.attach(9);
  myServo.write(90);  // center
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      if (input == "L") {
        myServo.write(0);    // move left
      } 
      else if (input == "R") {
        myServo.write(180);  // move right
      }
      else if (input == "N") {
        myServo.write(90);   // center
      }

      input = "";  // clear
    } 
    else {
      input += c;
    }
  }
}
