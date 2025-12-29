#include <WiFi.h>
#include <esp_now.h>

#define BUTTON_PIN 18

uint8_t receiverMAC[] = {0xEC, 0xE3, 0x34, 0x19, 0x80, 0xF8}; // <-- ESP2 MAC

bool lastPressed = false;

void onSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
  Serial.print("Send status: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "OK" : "FAIL");
}

void setup() {
  Serial.begin(115200);
  delay(500);

  // Button wiring: GPIO18 -> button -> GND
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }

  esp_now_register_send_cb(onSent);

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, receiverMAC, 6);
  peer.channel = 0;
  peer.encrypt = false;

  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.println("Failed to add peer");
    return;
  }

  Serial.println("ESP1 ready. Press button to scroll LEDs.");
}

void loop() {
  bool pressed = (digitalRead(BUTTON_PIN) == LOW); // LOW = pressed

  // detect a NEW button press (edge)
  if (pressed && !lastPressed) {
    uint8_t msg = 1;

    esp_err_t result = esp_now_send(receiverMAC, &msg, sizeof(msg));
    Serial.println(result == ESP_OK ? "Button press -> sent" : "Send error");

    delay(200); // debounce / prevents double-sends
  }

  lastPressed = pressed;
}
