#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// =================== WIFI ==========================
const char* WIFI_SSID = "Raccoon";
const char* WIFI_PASS = "Lynn@89McGill";

WebServer server(80);

// =================== WORKING PIN MAP (A) ===========
// Freenove ESP32 WROVER CAM (your board) — Variant A
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     21
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       19
#define Y4_GPIO_NUM       18
#define Y3_GPIO_NUM        5
#define Y2_GPIO_NUM        4
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// =================== CAMERA INIT ====================
bool startCamera() {
  camera_config_t c;
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer   = LEDC_TIMER_0;

  c.pin_d0 = Y2_GPIO_NUM;
  c.pin_d1 = Y3_GPIO_NUM;
  c.pin_d2 = Y4_GPIO_NUM;
  c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM;
  c.pin_d5 = Y7_GPIO_NUM;
  c.pin_d6 = Y8_GPIO_NUM;
  c.pin_d7 = Y9_GPIO_NUM;

  c.pin_xclk = XCLK_GPIO_NUM;
  c.pin_pclk = PCLK_GPIO_NUM;
  c.pin_vsync = VSYNC_GPIO_NUM;
  c.pin_href = HREF_GPIO_NUM;

  c.pin_sccb_sda = SIOD_GPIO_NUM;
  c.pin_sccb_scl = SIOC_GPIO_NUM;

  c.pin_pwdn = PWDN_GPIO_NUM;
  c.pin_reset = RESET_GPIO_NUM;

  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;

  // Stable for streaming + browser motion detection
  c.frame_size = FRAMESIZE_QVGA;   // 320x240
  c.jpeg_quality = 12;
  c.fb_count = 2;

  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return false;
  }

  // Print detected sensor
  sensor_t* s = esp_camera_sensor_get();
  if (s) {
    Serial.printf("✅ Camera PID detected: 0x%04x\n", s->id.PID);
    // If image is upside down, keep vflip=1, otherwise set to 0
    s->set_vflip(s, 0);
  }

  return true;
}

// =================== WEB UI (Motion detection on laptop) ==========
void handleRoot() {
  const char* html = R"rawliteral(
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>ESP32-CAM Motion Alert</title>
<style>
  body{font-family:Arial;margin:16px}
  .row{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}
  .card{border:1px solid #ddd;border-radius:12px;padding:12px}
  #stream{width:480px;max-width:100%;border-radius:12px;border:1px solid #ddd}
  #alertBox{display:none;padding:12px;border-radius:12px;background:#ffe8e8;border:1px solid #ffb3b3;margin-top:12px}
  label{display:block;margin-top:10px}
  button{padding:10px 14px;border-radius:10px;border:1px solid #ccc;cursor:pointer}
  .small{color:#555;font-size:.92rem}
</style>
</head>
<body>
<h2>ESP32-CAM (Freenove WROVER) — Motion Alerts</h2>
<p class="small">Motion detection runs in your laptop browser: popup + beep when motion is detected.</p>

<div class="row">
  <div class="card">
    <img id="stream" src="/stream" />
    <div id="alertBox"><b>⚠ Motion detected!</b> <span id="t"></span></div>
  </div>

  <div class="card">
    <h3>Settings</h3>

    <label>Sensitivity (lower = more sensitive):
      <input id="thr" type="range" min="4" max="40" value="14"/>
      <span id="thrV">14</span>
    </label>

    <label>Check every (ms):
      <input id="int" type="range" min="100" max="1200" value="250"/>
      <span id="intV">250</span>
    </label>

    <label>Cooldown (seconds):
      <input id="cd" type="range" min="1" max="20" value="5"/>
      <span id="cdV">5</span>
    </label>

    <p class="small">
      If you get false alerts: increase Sensitivity or increase Cooldown.
      If it misses motion: lower Sensitivity (closer to 4).
    </p>
  </div>
</div>

<canvas id="c" width="160" height="120" style="display:none"></canvas>

<script>
const img=document.getElementById('stream');
const canvas=document.getElementById('c');
const ctx=canvas.getContext('2d',{willReadFrequently:true});
const box=document.getElementById('alertBox');
const t=document.getElementById('t');

const thr=document.getElementById('thr');
const it=document.getElementById('int');
const cd=document.getElementById('cd');
const thrV=document.getElementById('thrV');
const intV=document.getElementById('intV');
const cdV=document.getElementById('cdV');

function sync(){thrV.textContent=thr.value;intV.textContent=it.value;cdV.textContent=cd.value;}
thr.oninput=it.oninput=cd.oninput=sync; sync();

function beep(){
  try{
    const AC=window.AudioContext||window.webkitAudioContext;
    const a=new AC(), o=a.createOscillator(), g=a.createGain();
    o.frequency.value=880; g.gain.value=0.03;
    o.connect(g); g.connect(a.destination);
    o.start();
    setTimeout(()=>{o.stop();a.close();},180);
  }catch(e){}
}

function showAlert(){
  t.textContent=" ("+new Date().toLocaleTimeString()+")";
  box.style.display="block";
  setTimeout(()=>box.style.display="none",2500);
}

let prev=null, last=0;

function loop(){
  const threshold=parseInt(thr.value,10);
  const interval=parseInt(it.value,10);
  const cooldown=parseInt(cd.value,10)*1000;

  try{
    ctx.drawImage(img,0,0,canvas.width,canvas.height);
    const cur=ctx.getImageData(0,0,canvas.width,canvas.height).data;

    if(prev){
      const step=12;   // higher = faster, lower = more accurate
      let diff=0,count=0;
      for(let i=0;i<cur.length;i+=4*step){
        diff += Math.abs(cur[i+1]-prev[i+1]); // use green channel
        count++;
      }
      const avg=diff/count;
      const now=Date.now();

      if(avg>threshold && (now-last)>cooldown){
        last=now;
        showAlert();
        beep();
      }
    }
    prev=cur;
  }catch(e){}

  setTimeout(loop, interval);
}

img.onload=()=>setTimeout(loop,500);
</script>
</body>
</html>
)rawliteral";

  server.send(200, "text/html", html);
}

// =================== STREAM HANDLER =================
void handleStream() {
  WiFiClient client = server.client();

  String hdr =
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n"
    "Cache-Control: no-cache\r\n"
    "Connection: close\r\n\r\n";
  server.sendContent(hdr);

  while (client.connected()) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) continue;

    server.sendContent("--frame\r\n");
    server.sendContent("Content-Type: image/jpeg\r\n");
    server.sendContent("Content-Length: " + String(fb->len) + "\r\n\r\n");
    server.sendContent((const char*)fb->buf, fb->len);
    server.sendContent("\r\n");

    esp_camera_fb_return(fb);
    delay(30);
  }
}

// =================== SETUP / LOOP ===================
void setup() {
  Serial.begin(115200);
  delay(400);

  Serial.println("\nStarting camera (Pin Map A)...");
  if (!startCamera()) {
    Serial.println("❌ Camera failed to start.");
    while (true) delay(1000);
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }

  Serial.println("\n✅ WiFi connected!");
  Serial.print("Open this on your laptop: http://");
  Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.on("/stream", handleStream);
  server.begin();
}

void loop() {
  server.handleClient();
}
