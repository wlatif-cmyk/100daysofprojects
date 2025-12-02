// Ultrasonic distance -> Serial (cm)
// Used as a "features on/off" kill switch

const int TRIG_PIN = 9;
const int ECHO_PIN = 10;

long durationMicroseconds = 0;

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
}

float measureDistanceCm() {
  // trigger pulse
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // echo pulse
  durationMicroseconds = pulseIn(ECHO_PIN, HIGH, 30000); // timeout 30ms
  if (durationMicroseconds == 0) return -1.0;

  // time -> distance (cm)
  return durationMicroseconds * 0.0343f / 2.0f;
}

void loop() {
  float distanceCm = measureDistanceCm();
  if (distanceCm > 0) {
    Serial.println(distanceCm);
  } else {
    Serial.println("NaN");
  }
  delay(100); // ~10 Hz
}
