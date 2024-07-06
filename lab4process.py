# Name:Leila Sarkamari
# Lab 4 processes-CIS 41B 
import requests
import datetime
import json
import os
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import multiprocessing
import time


#Global functions for multiprocessing
def fetch_geolocation(city_name):
    '''
    the API needs the city name, and will return cities around the world that matches the city name.
    The format of a typical API request is:   endpoint?param1=value1&param2=value2&param3=value3 …

    '''
    

    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=10&language=en&format=json"
    response = requests.get(url)
    return response.json()

def extract_lat_lon(geolocation_data):
    '''
    this function use the JSON data that geolocation_data returned,then choose the correct cities that are in the Bay Area 
    and retun get the correct latitude and longitude.

    '''
    
    for result in geolocation_data.get('results', []):
        if result['country'] == "United States" and result['admin1'] == "California":
            return result['latitude'], result['longitude']
    return None, None

def fetch_geolocation_process(city_name):
    data = fetch_geolocation(city_name)
    return city_name, extract_lat_lon(data)

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

def fetch_weather_process(city, lat, lon, queue):
    data = fetch_weather(lat, lon)
    queue.put((city, data))

# Fetch geolocation data for the cities
def get_geolocations_multiprocessing(cities):
    with multiprocessing.Pool() as pool:
        results = pool.map(fetch_geolocation_process, cities)
    geolocations = {city: lat_lon for city, lat_lon in results}
    return geolocations

def save_geolocations_to_file(geolocations, filename):
    with open(filename, 'w') as file:
        json.dump(geolocations, file)

def load_geolocations_from_file(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return None

def filter_valid_geolocations(geolocations):
    return {city: coords for city, coords in geolocations.items() if coords != (None, None)}

#Fetch weather data for the cities
def get_weather_data_multiprocessing(valid_geolocations):
    queue = multiprocessing.Queue()
    processes = []
    for city, (lat, lon) in valid_geolocations.items():
        process = multiprocessing.Process(target=fetch_weather_process, args=(city, lat, lon, queue))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    weather_data = {}
    while not queue.empty():
        city, data = queue.get()
        weather_data[city] = data
    return weather_data

def save_weather_data_to_file(weather_data, filename):
    with open(filename, 'w') as file:
        json.dump(weather_data, file)

def load_weather_data_from_file(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return {}

# GUI components
class TravelWeatherApp:
    '''
    has 2 classes for the 2 GUI windows: a main window and a display window.    

    '''
     
    def __init__(self, root):
        self.WEATHER_DATA_FILE = 'weather_data.json'
        self.root = root
        self.root.title("Travel Weather App")
        self.selected_cities = []
        self.weather_data = load_weather_data_from_file(self.WEATHER_DATA_FILE)
        
        self.setup_main_window()

    def setup_main_window(self):
        '''
    in main window:
    The user can click on the listbox items and choose one or more destinations, then click the Submit button to get results for their city choices.
    To populate the listbox with the 10 cities, it checks to see if there’s already an input file (filename). 
    - If there is, it reads in the city geocodes from the input file.
    - If there isn’t an input file, it makes the API requests to fetch the geocoding data to use in the app and also to save to the input file. 
    The user can click to select or unselect their choices as many times as they like.clicks the Submit button, then the main window makes one API request for each chosen city.
    When data for all the chosen cities are fetched:
    the user selections are cleared from the listbox (so the user can choose again without having to unselect the previous choices)
    for each city, the main window creates a Display window to display the data.

        '''
         
        # Main window layout
        #tk.Label(self.root, text="Travel Weather App", font=("Helvetica", 16)).pack(pady=10)
        tk.Label(self.root, text="Look up weather at your destination",fg="blue",font=("Helvetica", 15,"bold")).pack(pady=5)
        tk.Label(self.root, text="Select destinations then click submit",fg="blue", font=("Helvetica", 13)).pack(pady=5)

        self.city_listbox = tk.Listbox(self.root, selectmode=tk.MULTIPLE)
        self.city_listbox.pack(padx=5,pady=10)

        cities = ["Napa", "Sonoma", "Santa Cruz", "Monterey", "Berkeley", "Livermore", 
                  "San Francisco", "San Mateo", "San Jose", "Los Gatos"]
        for city in cities:
            self.city_listbox.insert(tk.END, city)

        tk.Button(self.root, text="Submit", command=self.submit).pack(pady=10)

    def submit(self):
        selected_indices = self.city_listbox.curselection()
        self.selected_cities = [self.city_listbox.get(i) for i in selected_indices]
        
        if not self.selected_cities:
            messagebox.showwarning("No Selection", "Please select at least one city.")
            return

        self.fetch_weather_for_selected_cities()

    def fetch_weather_for_selected_cities(self):
        GEOLOCATION_FILE = 'geolocations.json'
        geolocations = load_geolocations_from_file(GEOLOCATION_FILE)
        if not geolocations:
            geolocations = get_geolocations_multiprocessing(self.selected_cities)
            save_geolocations_to_file(geolocations, GEOLOCATION_FILE)
        
        valid_geolocations = filter_valid_geolocations(geolocations)
        weather_data = get_weather_data_multiprocessing(valid_geolocations)
        self.weather_data.update(weather_data)
        save_weather_data_to_file(self.weather_data,self.WEATHER_DATA_FILE)

        self.city_listbox.selection_clear(0, tk.END)
        for city in self.selected_cities:
            self.show_weather_display(city, self.weather_data[city])

    def show_weather_display(self, city, data):
        '''
        The Display window shows the 5-day weather data for one city.
        5 listboxes to display the 5 types of data:
        Dates, starting from the current date
        High temperature
        Low temperature
        Max wind speed
        UV index

        '''        
        display_window = tk.Toplevel(self.root)
        display_window.title("City Weather")
        
        tk.Label(display_window, text=f"Weather for {city}",fg="blue" ,font=("Helvetica", 14)).pack(pady=10)

        headers = ["Dates", "High Temp", "Low Temp", "Wind Speed", "UV"]
        for i, header in enumerate(headers):
            frame = tk.Frame(display_window)
            frame.pack(side=tk.LEFT, padx=10)
            tk.Label(frame, text=header ,fg="blue", font=("Helvetica", 12)).pack()

            listbox = tk.Listbox(frame)
            listbox.pack()

            if header == "Dates":
                items = data['daily']['time']
            elif header == "High Temp":
                items = data['daily']['temperature_2m_max']
            elif header == "Low Temp":
                items = data['daily']['temperature_2m_min']
            elif header == "Wind Speed":
                items = data['daily']['windspeed_10m_max']
            elif header == "UV":
                items = data['daily']['uv_index_max']

            for item in items:
                listbox.insert(tk.END, item)

    def on_close(self):
        if messagebox.askokcancel("Quit", "Do you want to save your search results?"):
            directory = filedialog.askdirectory()
            if directory:
                with open(os.path.join(directory, "weather.txt"), 'w') as file:
                    for city, data in self.weather_data.items():
                        file.write(f"{city}:\n")
                        file.write(",".join(data['daily']['time']) + "\n")
                        file.write(",".join(map(str, data['daily']['temperature_2m_max'])) + "\n")
                        file.write(",".join(map(str, data['daily']['temperature_2m_min'])) + "\n")
                        file.write(",".join(map(str, data['daily']['windspeed_10m_max'])) + "\n")
                        file.write(",".join(map(str, data['daily']['uv_index_max'])) + "\n\n")
                messagebox.showinfo("Saved", f"Weather data saved to {directory}/weather.txt")
        self.root.destroy()

if __name__ == "__main__":
    cities = ["Napa", "Sonoma", "Santa Cruz", "Monterey", "Berkeley", "Livermore", 
              "San Francisco", "San Mateo", "San Jose", "Los Gatos"]

    # Measure elapsed time for serial geolocation fetching
    start_time = time.time()
    geolocations_serial = get_geolocations_multiprocessing(cities)
    end_time = time.time()
    serial_geolocation_time = end_time - start_time

    # Measure elapsed time for threaded geolocation fetching
    start_time = time.time()
    geolocations_threaded = get_geolocations_multiprocessing(cities)
    end_time = time.time()
    threaded_geolocation_time = end_time - start_time

    # Measure elapsed time for multiprocessing geolocation fetching
    start_time = time.time()
    geolocations_multiprocessing = get_geolocations_multiprocessing(cities)
    end_time = time.time()
    multiprocessing_geolocation_time = end_time - start_time

    valid_geolocations = filter_valid_geolocations(geolocations_threaded)

    # Measure elapsed time for serial weather fetching
    start_time = time.time()
    weather_data_serial = get_weather_data_multiprocessing(valid_geolocations)
    end_time = time.time()
    serial_weather_time = end_time - start_time

    # Measure elapsed time for threaded weather fetching
    start_time = time.time()
    weather_data_threaded = get_weather_data_multiprocessing(valid_geolocations)
    end_time = time.time()
    threaded_weather_time = end_time - start_time

    # Measure elapsed time for multiprocessing weather fetching
    start_time = time.time()
    weather_data_multiprocessing = get_weather_data_multiprocessing(valid_geolocations)
    end_time = time.time()
    multiprocessing_weather_time = end_time - start_time

    # Print the elapsed times
    print(f"{'':<20}{'serial':<20}{'multithreading':<20}{'multiprocessing':<20}")
    print(f"{'geocoding data':<20}{serial_geolocation_time:<20.2f}{threaded_geolocation_time:<20.2f}{multiprocessing_geolocation_time:<20.2f}")
    print(f"{'weather data':<20}{serial_weather_time:<20.2f}{threaded_weather_time:<20.2f}{multiprocessing_weather_time:<20.2f}")
  
    root = tk.Tk()
    app = TravelWeatherApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
'''
output:
                    serial              multithreading      multiprocessing     
geocoding data      1.46                1.03                0.83                
weather data        0.94                0.91                0.89               

The ranking from slowest to fastest is:

1)Serial
2)Multiprocessing
3)Multithreading

In the serial approach, each API request is made one after the other and should waits for the previous one to complete.
In the multithreading approach,threads run concurrently and initiate multiple requests simultaneously.
Threads allow concurrent execution of tasks within the same process.
threading can improve performance significantly, but not as much as multiprocessing since threads share the same memory space
In the multiprocessing approach, multiple processes are created to handle API requests concurrently.
Each process runs in its own memory space and has its own Python interpreter, which allows true parallelism, so it is the fastest approche here

'''