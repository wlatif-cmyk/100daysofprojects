#include <LiquidCrystal.h>
#include "DHT.h"

// LCD: RS, EN, D4, D5, D6, D7
LiquidCrystal lcd(13, 12, 11, 10, 9, 8);

#define DHTPIN 7     
#define DHTTYPE DHT11  

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(9600);

  lcd.begin(16, 2);     // 16x2 LCD
  lcd.clear();
  lcd.print("Starting...");

  dht.begin();
  delay(2000);         
}
void loop() {
  float h = dht.readHumidity();
  float t = dht.readTemperature(); // in °C

  lcd.clear();
  lcd.setCursor(0, 0);

  if (isnan(h) || isnan(t)) {
    Serial.println(F("Failed to read from DHT sensor!"));

    lcd.print("DHT ERROR");
  } else {
    Serial.print("Humidity: ");
    Serial.print(h);
    Serial.print(" %  Temp: ");
    Serial.print(t);
    Serial.println(" *C");


    // temp
    if(t > 23) {
      lcd.clear();
      delay(200);
      lcd.print("T-shirt and shorts!");
    } else {
      lcd.clear();
      delay(200);
      lcd.print("hoodie!");

    }
  }

  delay(2000); 
}
