#include <WiFi.h>
#include <esp_now.h>

#define RED_LED   14
#define BLUE_LED  25
#define GREEN_LED 32  // NOT 35

int currentLED = 0;

void showLED(int i) {
  digitalWrite(RED_LED, i == 0);
  digitalWrite(BLUE_LED, i == 1);
  digitalWrite(GREEN_LED, i == 2);
}

void onReceive(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  Serial.println("RECEIVED!");
  currentLED = (currentLED + 1) % 3;
  showLED(currentLED);
}

void setup() {
  Serial.begin(115200);

  pinMode(RED_LED, OUTPUT);
  pinMode(BLUE_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  showLED(0);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  esp_now_init();
  esp_now_register_recv_cb(onReceive);
}

void loop() {}
