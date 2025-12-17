const int LED_PIN = 9;

String inputString = "";
bool stringComplete = false;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(9600);   // Must match Python baudrate
}

void loop() {
  // Read incoming serial characters
  while (Serial.available()) {
    char inChar = (char)Serial.read();

    if (inChar == '\n') {      // End of one value
      stringComplete = true;
      break;
    } else if (isDigit(inChar)) {
      inputString += inChar;   // Build up the number as text
    }
  }

  // When a full number has been received
  if (stringComplete) {
    int brightness = inputString.toInt();      // Convert to integer
    brightness = constrain(brightness, 0, 255);

    analogWrite(LED_PIN, brightness);          // Set LED brightness

    // Reset for next value
    inputString = "";
    stringComplete = false;
  }
}
