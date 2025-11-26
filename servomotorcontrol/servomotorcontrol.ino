#include <Servo.h>
#include <IRremote.hpp>   // using the newer IRremote library

Servo myServo;

// Joystick pins
const int vrxPin   = A0;   // X movement
const int vryPin   = A1;   // Y movement
const int swPin    = 4;    // click button on joystick

// IR receiver pin
const uint8_t IR_RECEIVE_PIN = 5;

// Servo output pin
const int servoPin = 9;

// LED pins
const int greenLed = 13;
const int redLed   = 12;

// State tracking
bool autoMode = false;
bool lastButton = HIGH;
bool joystickEnabled = true;

// Servo position storage
int servoAngle = 90;

// How far the servo should jump when using the remote
int remoteStep = 30;

// Replace these with the codes from your remote
unsigned long TOGGLE_JOYSTICK_CODE = 0xBA45FF00; 
unsigned long IR_UP_CODE           = 0xF609FF00; 
unsigned long IR_DOWN_CODE         = 0xF807FF00; 

void setup() {
  myServo.attach(servoPin);
  myServo.write(servoAngle);

  pinMode(swPin, INPUT_PULLUP);
  pinMode(greenLed, OUTPUT);
  pinMode(redLed, OUTPUT);

  Serial.begin(9600);

  // Start the IR system
  IrReceiver.begin(IR_RECEIVE_PIN, ENABLE_LED_FEEDBACK);
  Serial.println("System ready.");
}

void loop() {

  // -----------------------
  // Handle IR remote input
  // -----------------------
  if (IrReceiver.decode()) {
    unsigned long code = IrReceiver.decodedIRData.decodedRawData;
    Serial.print("Remote code: 0x");
    Serial.println(code, HEX);

    // Toggle the joystick on or off
    if (code == TOGGLE_JOYSTICK_CODE) {
      joystickEnabled = !joystickEnabled;
      Serial.print("Joystick now: ");
      Serial.println(joystickEnabled ? "ON" : "OFF");
      delay(250);
    }

    // Move servo upward in bigger steps
    else if (code == IR_UP_CODE) {
      joystickEnabled = false;      // remote takes over
      servoAngle += remoteStep;
      if (servoAngle > 180) servoAngle = 180;
      myServo.write(servoAngle);
      Serial.println("Remote: moving up");
    }

    // Move servo downward in bigger steps
    else if (code == IR_DOWN_CODE) {
      joystickEnabled = false;
      servoAngle -= remoteStep;
      if (servoAngle < 0) servoAngle = 0;
      myServo.write(servoAngle);
      Serial.println("Remote: moving down");
    }

    IrReceiver.resume();
  }

  // -----------------------
  // Joystick button: toggle auto sweeping
  // -----------------------
  bool currentButton = digitalRead(swPin);

  if (currentButton == LOW && lastButton == HIGH) {
    autoMode = !autoMode;
    delay(200);
  }
  lastButton = currentButton;

  // -----------------------
  // Automatic back-and-forth motion
  // -----------------------
  if (autoMode) {
    for (int pos = 0; pos <= 180 && autoMode; pos++) {
      myServo.write(pos);
      servoAngle = pos;

      if (digitalRead(swPin) == LOW) {
        autoMode = false;
        delay(150);
        break;
      }
    }

    for (int pos = 180; pos >= 0 && autoMode; pos--) {
      myServo.write(pos);
      servoAngle = pos;

      if (digitalRead(swPin) == LOW) {
        autoMode = false;
        delay(150);
        break;
      }
    }
  }

  // -----------------------
  // Manual joystick mode
  // -----------------------
  else if (joystickEnabled) {
    int xValue = analogRead(vrxPin);
    int yValue = analogRead(vryPin);

    servoAngle = map(xValue, 0, 1023, 0, 180);
    myServo.write(servoAngle);

    int midpoint = 512;

    // Green LED comes on if you push the joystick upward
    if (yValue > midpoint + 50) {
      digitalWrite(greenLed, HIGH);
    } else {
      digitalWrite(greenLed, LOW);
    }
  }

  // When joystick is disabled, keep the green LED off
  else {
    digitalWrite(greenLed, LOW);
  }

  // -----------------------
  // Red LED: simply tells you when joystick mode is active
  // -----------------------
  if (joystickEnabled && !autoMode) {
    digitalWrite(redLed, HIGH);
  } else {
    digitalWrite(redLed, LOW);
  }
}
