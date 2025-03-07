import requests
import numpy as np
import pandas as pd

# Replace 'YOUR_API_KEY' with your actual API key
API_KEY = '898daaee6b0e494a83c181621250503'
BASE_URL = 'http://api.weatherapi.com/v1'

def get_current_weather():
    ENDPOINT = '/current.json'
    # Get the city name from the user
    city = input("Enter city name: ")
    # Construct the API URL
    url = f"{BASE_URL}{ENDPOINT}?key={API_KEY}&q={city}"

    try:
        # Make a GET request to the API
        response = requests.get(url)
        data = response.json()

        # Check if the response was successful
        if response.status_code == 200:
            # Extract and print weather information
            location = data['location']['name']
            region = data['location']['region']
            country = data['location']['country']
            temperature = data['current']['temp_c']
            condition = data['current']['condition']['text']
            humidity = data['current']['humidity']
            wind_speed = data['current']['wind_kph']

            print(f"Weather in {location}, {region}, {country}:")
            print(f"Temperature: {temperature}°C")
            print(f"Condition: {condition}")
            print(f"Humidity: {humidity}%")
            print(f"Wind Speed: {wind_speed} km/h")
        else:
            print("Error:", data.get('error', {}).get('message', 'Failed to retrieve data.'))

    except requests.RequestException as e:
        print("Error: Unable to connect to the API.", e)

def get_historical_weather(start_date,end_date):
    cities=['Guwahati']
    # Create a date range using numpy's datetime64
    start = np.datetime64(start_date,'D')
    end = np.datetime64(end_date,'D')

    # Generate an array of dates and convert to string format
    dates = np.arange(start, end + np.timedelta64(1, 'D'), dtype='datetime64[D]')
    date_strings = dates.astype(str)
    ENDPOINT = '/history.json'

    if not API_KEY:
        print("Error: API key not found. Make sure it's in the .env file.")
        exit()

    # Get city and date inputs

    for city in cities:
        condition,temperature,wind_speed,precipitation,humidity=[],[],[],[],[]
        for date in date_strings:

            # Build the request URL
            url = f"{BASE_URL}{ENDPOINT}?key={API_KEY}&q={city}&dt={date}"

            try:
                response = requests.get(url)
                data = response.json()

                if response.status_code == 200:
                    # Extract hourly data
                    for hour_data in data['forecast']['forecastday'][0]['hour']:
                        condition.append(hour_data['condition']['text'])
                        temperature.append(hour_data['temp_c'])
                        wind_speed.append(hour_data['wind_kph'])
                        precipitation.append(hour_data['precip_mm'])
                        humidity.append(hour_data['humidity'])

                else:
                    print("Error:", data.get('error', {}).get('message', 'Failed to retrieve data.'))

            except requests.RequestException as e:
                print("Error: Unable to connect to the API.", e)

        start_date=start_date+" 00:00"
        end_date=end_date+" 23:00"
        date_range=pd.date_range(start=start_date,end=end_date,freq='h')
        df=pd.DataFrame({
            'Temperature':np.array(temperature),
            'Humidity':np.array(humidity),
            'Wind_Speed':np.array(wind_speed),
            'Precipitation':np.array(precipitation),
            'Condition':np.array(condition)
        },index=date_range)
        df.index.name='Date_Hour'
        df.to_csv(f'{city}_Weather1.csv')
        print(f'{city} Weather data saved!')

get_historical_weather('2024-01-01','2024-01-31')

df1=pd.read_csv('Guwahati_Weather1.csv')
df2=pd.read_csv('Weather.csv')
df=pd.concat([df1,df2],axis=0)
df.to_csv('f1Weather.csv')
