import requests
import datetime
import json
import os

GEOLOCATION_FILE = 'geolocations.json'

# Step 1: Fetch geolocation data for the cities
def fetch_geolocation(city_name):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=10&language=en&format=json"
    response = requests.get(url)
    return response.json()

def extract_lat_lon(geolocation_data):
    for result in geolocation_data.get('results', []):
        if result['country'] == "United States" and result['admin1'] == "California":
            return result['latitude'], result['longitude']
    return None, None

def get_geolocations(cities):
    geolocations = {}
    for city in cities:
        data = fetch_geolocation(city)
        lat_lon = extract_lat_lon(data)
        geolocations[city] = lat_lon
    return geolocations

def save_geolocations_to_file(geolocations, filename):
    with open(filename, 'w') as file:
        json.dump(geolocations, file)

def load_geolocations_from_file(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return None

# Step 2: Filter out cities without valid geolocation data
def filter_valid_geolocations(geolocations):
    return {city: coords for city, coords in geolocations.items() if coords != (None, None)}

# Step 3: Fetch weather data for the cities
def fetch_weather(latitude, longitude):
    start_date = datetime.datetime.now().date()
    end_date = start_date + datetime.timedelta(days=4)
    url = (f"https://api.open-meteo.com/v1/forecast?"
           f"latitude={latitude}&longitude={longitude}&"
           f"daily=temperature_2m_max,temperature_2m_min,windspeed_10m_max,uv_index_max&"
           f"temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&"
           f"start_date={start_date}&end_date={end_date}")
    response = requests.get(url)
    return response.json()

def get_weather_data(valid_geolocations):
    return {city: fetch_weather(lat, lon) for city, (lat, lon) in valid_geolocations.items()}

# Main function to orchestrate the steps
def main():
    cities = ["Napa", "Sonoma", "Santa Cruz", "Monterey", "Berkeley", "Livermore", 
              "San Francisco", "San Mateo", "San Jose", "Los Gatos"]
    
    # Load geolocations from file if it exists
    geolocations = load_geolocations_from_file(GEOLOCATION_FILE)
    
    # Step 1: If no geolocations file, get geolocations for cities and save to file
    if not geolocations:
        geolocations = get_geolocations(cities)
        save_geolocations_to_file(geolocations, GEOLOCATION_FILE)
    
    # Step 2: Filter out invalid geolocations
    valid_geolocations = filter_valid_geolocations(geolocations)
    
    # Step 3: Get weather data for valid geolocations
    weather_data = get_weather_data(valid_geolocations)
    
    # Print results
    print("Geolocations:")
    for city, coords in valid_geolocations.items():
        print(f"{city}: {coords}")
    
    print("\nWeather Data:")
    for city, data in weather_data.items():
        print(f"Weather data for {city}:")
        print(data)
        print()

if __name__ == "__main__":
    main()
