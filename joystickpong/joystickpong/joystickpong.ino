#define PIN_BTN 2
#define PIN_SW  3
#define PIN_VRX A0

const unsigned long DEBOUNCE_MS = 25;

bool rawLast = false;
bool btnStable = false;
unsigned long lastRawChange = 0;

unsigned long pressStart = 0;

void setup() {
  pinMode(PIN_BTN, INPUT_PULLUP);
  pinMode(PIN_SW, INPUT_PULLUP);
  Serial.begin(115200);
}

void loop() {
  int x = analogRead(PIN_VRX);
  bool sw = (digitalRead(PIN_SW) == LOW);

  bool raw = (digitalRead(PIN_BTN) == LOW);
  unsigned long now = millis();

  if (raw != rawLast) {
    rawLast = raw;
    lastRawChange = now;
  }

  bool fire = false;
  unsigned long chg = 0;
  unsigned long pwr = 0;

  if ((now - lastRawChange) >= DEBOUNCE_MS) {
    if (btnStable != raw) {
      btnStable = raw;
      if (btnStable) {
        pressStart = now;
      } else {
        fire = true;
        pwr = now - pressStart;
      }
    }
  }

  if (btnStable) chg = now - pressStart;

  Serial.print("X,");     Serial.print(x);
  Serial.print(",BTN,");  Serial.print(btnStable ? 1 : 0);
  Serial.print(",SW,");   Serial.print(sw ? 1 : 0);
  Serial.print(",CHGMS,");Serial.print(chg);
  Serial.print(",PWRMS,");Serial.println(fire ? pwr : 0);

  delay(6);
}
