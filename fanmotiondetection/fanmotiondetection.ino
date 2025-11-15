// button pi9in
const int buttonPin = 10;   // Button: one side to D10, other to GND

// ultrasonic sensor pins
const int trigPin = 2;
const int echoPin = 3;

// L293D motor control pins
const int enablePin = 7;    // L293D pin 1
const int motorIn1  = 5;    // L293D pin 2
const int motorIn2  = 6;    // L293D pin 7

long duration;
int distance;

// 1 = motion detection enabled, 0 = disabled (fan always ON)
int detectionEnabled = 1;

void setup() {
  // Ultrasonic
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  // Motor driver
  pinMode(enablePin, OUTPUT);
  pinMode(motorIn1, OUTPUT);
  pinMode(motorIn2, OUTPUT);
  digitalWrite(enablePin, HIGH);  // enable driver

  // Button with internal pull-up
  pinMode(buttonPin, INPUT_PULLUP);

  Serial.begin(9600);
  Serial.println("System starting...");
}

void loop() {
  // button toggle
  if (digitalRead(buttonPin) == LOW) {   // button pressed
    detectionEnabled = !detectionEnabled;
    Serial.print("Motion detection: ");
    Serial.println(detectionEnabled ? "ENABLED" : "DISABLED");
    delay(250);  // simple debounce so one press = one toggle
  }

  // detection disabled - fan always on
  if (!detectionEnabled) {
    // keep ultrasonic idle
    digitalWrite(trigPin, LOW);

    // fan ON (forward)
    digitalWrite(motorIn1, HIGH);
    digitalWrite(motorIn2, LOW);

    delay(50);
    return;  // skip ultrasonic logic
  }

  // detection enabled - tell arduino to use ultrasonic

  // Trigger ultrasonic pulse
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Read echo pulse
  duration = pulseIn(echoPin, HIGH);
  distance = duration * 0.034 / 2;  // cm

  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.print(" cm | detectionEnabled = ");
  Serial.println(detectionEnabled);

  // < 20 cm → fan ON, else OFF
  if (distance > 0 && distance < 20) {
    digitalWrite(motorIn1, HIGH);
    digitalWrite(motorIn2, LOW);
  } else {
    digitalWrite(motorIn1, LOW);
    digitalWrite(motorIn2, LOW);
  }

  delay(50);
}
