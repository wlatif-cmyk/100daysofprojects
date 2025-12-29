#include <ESP32Servo.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// -----------------  pins -----------------
#define VRX_PIN 32
#define VRY_PIN 35
#define SW_PIN  25
#define SERVO_PIN 27

// ---- Joystick detection tuning (unchanged) ----
const int TRIGGER  = 900;
const int RELEASE  = 500;
const unsigned long COOLDOWN_MS = 200;

// ---- Servo angles (unchanged) ----
const int LOCK_ANGLE = 0;
const int UNLOCK_ANGLE = 90;
const unsigned long UNLOCK_MS = 3000;

// ---- Cheat code (unchanged) ----
const char cheatCode[] = {'U','U','D','L','R','P'};
const int codeLength = sizeof(cheatCode);

char inputCode[codeLength];
int inputIndex = 0;

int cx = 2048, cy = 2048;
bool armed = true;
unsigned long lastEvent = 0;

Servo lockServo;

// ----------------- BLE settings (added) -----------------
const char* BLE_NAME = "ESP32_DOORLOCK";
const String BLE_PIN = "1234"; // CHANGE THIS!

// UUIDs
#define SERVICE_UUID        "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define CMD_CHAR_UUID       "6e400002-b5a3-f393-e0a9-e50e24dcca9e" // write commands
#define RESP_CHAR_UUID      "6e400003-b5a3-f393-e0a9-e50e24dcca9e" // notify responses

BLECharacteristic* respChar = nullptr;
bool deviceConnected = false;

void sendResp(const String& msg) {
  Serial.println("BLE RESP: " + msg);
  if (deviceConnected && respChar) {
    respChar->setValue(msg.c_str());
    respChar->notify();
  }
}

class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) override {
    deviceConnected = true;
    Serial.println("BLE connected");
  }
  void onDisconnect(BLEServer* pServer) override {
    deviceConnected = false;
    Serial.println("BLE disconnected");
    BLEDevice::startAdvertising();
  }
};

class CmdCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* pCharacteristic) override {
    String cmd = pCharacteristic->getValue();
    cmd.trim();
    if (cmd.length() == 0) return;

    Serial.print("BLE cmd: ");
    Serial.println(cmd);

    if (cmd == "STATUS") {
      sendResp("OK: online");
      return;
    }

    if (cmd == "LOCK") {
      lockServo.write(LOCK_ANGLE);
      sendResp("OK: locked");
      return;
    }

    if (cmd.startsWith("UNLOCK ")) {
      String pin = cmd.substring(7);
      pin.trim();

      if (pin == BLE_PIN) {
        sendResp("OK: unlocked");
        Serial.println("UNLOCKED (BLE)");
        unlockDoor();
      } else {
        sendResp("ERR: bad pin");
      }
      return;
    }

    sendResp("Commands: UNLOCK <pin>, LOCK, STATUS");
  }
};

void setupBLE() {
  BLEDevice::init(BLE_NAME);

  BLEServer* server = BLEDevice::createServer();
  server->setCallbacks(new MyServerCallbacks());

  BLEService* service = server->createService(SERVICE_UUID);

  BLECharacteristic* cmdChar = service->createCharacteristic(
    CMD_CHAR_UUID,
    BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR
  );
  cmdChar->setCallbacks(new CmdCallbacks());

  respChar = service->createCharacteristic(
    RESP_CHAR_UUID,
    BLECharacteristic::PROPERTY_NOTIFY
  );
  respChar->addDescriptor(new BLE2902()); // FIX: needs #include <BLE2902.h>

  service->start();

  BLEAdvertising* advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  advertising->setScanResponse(true);
  advertising->start();

  Serial.println("BLE advertising as: " + String(BLE_NAME));
  Serial.println("Use nRF Connect: write 'UNLOCK 1234' to CMD char");
}

void setup() {
  Serial.begin(115200);
  pinMode(SW_PIN, INPUT_PULLUP);

  // Calibrate joystick center (don't touch stick during this)
  long sx = 0, sy = 0;
  for (int i = 0; i < 100; i++) {
    sx += analogRead(VRX_PIN);
    sy += analogRead(VRY_PIN);
    delay(5);
  }
  cx = sx / 100;
  cy = sy / 100;

  Serial.print("Center X="); Serial.print(cx);
  Serial.print("  Center Y="); Serial.println(cy);

  // Servo init (ESP32)
  lockServo.setPeriodHertz(50);
  lockServo.attach(SERVO_PIN, 500, 2400);
  lockServo.write(LOCK_ANGLE);

  // BLE init
  setupBLE();

  Serial.println("Enter cheat code: U U D L R P (P = press)");
  Serial.println("BLE commands: UNLOCK <pin>, LOCK, STATUS");
}

void loop() {
  // ---- Joystick code (UNCHANGED) ----
  int x = analogRead(VRX_PIN);
  int y = analogRead(VRY_PIN);
  int sw = digitalRead(SW_PIN);

  int dx = x - cx;
  int dy = y - cy;

  // Button press = 'P'
  if (sw == LOW && millis() - lastEvent > COOLDOWN_MS) {
    registerMove('P');
    fired();
    return;
  }

  // Direction move when armed
  if (armed && millis() - lastEvent > COOLDOWN_MS) {
    if (abs(dy) > abs(dx)) {
      if (dy > TRIGGER) { registerMove('D'); fired(); }
      else if (dy < -TRIGGER) { registerMove('U'); fired(); }
    } else {
      if (dx > TRIGGER) { registerMove('R'); fired(); }
      else if (dx < -TRIGGER) { registerMove('L'); fired(); }
    }
  }

  // Re-arm when back near center
  if (!armed) {
    if (abs(dx) < RELEASE && abs(dy) < RELEASE) {
      armed = true;
    }
  }
}


void fired() {
  lastEvent = millis();
  armed = false;
}

void registerMove(char m) {
  Serial.print("Input: ");
  Serial.println(m);

  inputCode[inputIndex++] = m;

  if (inputIndex >= codeLength) {
    checkCode();
    inputIndex = 0;
  }
}

void checkCode() {
  for (int i = 0; i < codeLength; i++) {
    if (inputCode[i] != cheatCode[i]) {
      Serial.println("Wrong code");
      return;
    }
  }
  Serial.println("UNLOCKED");
  unlockDoor();
}

void unlockDoor() {
  lockServo.write(UNLOCK_ANGLE);
  delay(UNLOCK_MS);
  lockServo.write(LOCK_ANGLE);
}
