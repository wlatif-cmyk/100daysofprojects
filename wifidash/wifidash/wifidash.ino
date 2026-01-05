#include <WiFi.h>
#include <WebServer.h>

const char* STA_SSID = "";
const char* STA_PASS = "";

WebServer server(80);

String encTypeToStr(wifi_auth_mode_t e) {
  switch (e) {
    case WIFI_AUTH_OPEN: return "OPEN";
    case WIFI_AUTH_WEP: return "WEP";
    case WIFI_AUTH_WPA_PSK: return "WPA";
    case WIFI_AUTH_WPA2_PSK: return "WPA2";
    case WIFI_AUTH_WPA_WPA2_PSK: return "WPA/WPA2";
    case WIFI_AUTH_WPA2_ENTERPRISE: return "WPA2-ENT";
    case WIFI_AUTH_WPA3_PSK: return "WPA3";
    case WIFI_AUTH_WPA2_WPA3_PSK: return "WPA2/WPA3";
    default: return "UNKNOWN";
  }
}

// Basic JSON escaping for SSIDs
String jsonEscape(const String& s) {
  String out;
  out.reserve(s.length() + 8);
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == '\\' || c == '\"') out += '\\';
    if (c == '\n') { out += "\\n"; continue; }
    if (c == '\r') { out += "\\r"; continue; }
    if (c == '\t') { out += "\\t"; continue; }
    out += c;
  }
  return out;
}

void handleRoot() {
  String msg = "ESP32 WiFi Ranker\n\nEndpoints:\n/scan -> JSON scan results\n";
  server.send(200, "text/plain", msg);
}

void handleScan() {
  // Force a fresh scan each request
  int n = WiFi.scanNetworks(/*async=*/false, /*hidden=*/true);

  // Build JSON
  String json = "{\"count\":";
  json += String(n);
  json += ",\"networks\":[";

  for (int i = 0; i < n; i++) {
    if (i) json += ",";
    String ssid = WiFi.SSID(i);
    int32_t rssi = WiFi.RSSI(i);
    int32_t ch = WiFi.channel(i);
    wifi_auth_mode_t enc = WiFi.encryptionType(i);

    json += "{";
    json += "\"ssid\":\"" + jsonEscape(ssid) + "\",";
    json += "\"rssi\":" + String(rssi) + ",";
    json += "\"channel\":" + String(ch) + ",";
    json += "\"security\":\"" + encTypeToStr(enc) + "\"";
    json += "}";
  }

  json += "]}";

  WiFi.scanDelete(); // free memory

  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
}

void setup() {
  Serial.begin(115200);
  delay(300);

  WiFi.mode(WIFI_STA);
  WiFi.begin(STA_SSID, STA_PASS);

  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.on("/scan", handleScan);
  server.begin();

  Serial.println("HTTP server started. Hit /scan for JSON.");
}

void loop() {
  server.handleClient();
}
