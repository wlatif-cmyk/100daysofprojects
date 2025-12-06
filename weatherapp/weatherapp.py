import requests

API_KEY = "8d9596cd5d904491b4a92943250612"  # api key plz no steal
BASE_URL = "http://api.weatherapi.com/v1/current.json"

def get_weather(city_name):
    params = {
        "key": API_KEY,
        "q": city_name,
        "aqi": "no"
    }

    response = requests.get(BASE_URL, params=params)
    data = response.json()

    if response.status_code == 200:
        location = data["location"]
        current = data["current"]

        print(f"\nWeather in {location['name']}, {location['region']}:")
        print(f" Temperature: {current['temp_c']}°C")
        print(f" Feels like:  {current['feelslike_c']}°C")
        print(f" Condition:   {current['condition']['text']}")
    else:
        print("\nCould not get weather data.")
        print("Error:", data.get("error", data))

def main():
    print("=== WeatherAPI App ===")
    city = input("Enter a city name: ").strip()
    get_weather(city)

if __name__ == "__main__":
    main()
