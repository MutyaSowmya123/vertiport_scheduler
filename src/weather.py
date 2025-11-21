import requests
from .models import WeatherData, Time


def fetch_weather_data(lat: float = 40.7128, lon: float = -74.0060) -> WeatherData:
    """
    Fetch real-time weather data from Open-Meteo API.
    Defaults to NYC coordinates; pass lat/lon for specific vertiport.
    Falls back to mock data if API fails.
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m,visibility,precipitation,temperature_2m"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data['current']
        return WeatherData(
            wind_speed=current['wind_speed_10m'] / 3.6,  # Convert km/h to m/s
            visibility=current['visibility'] / 1000,  # Convert meters to km
            precipitation=current['precipitation'],
            temperature=current['temperature_2m'],
            timestamp=int(current['time'].replace('-', '').replace('T', '').replace(':', '')[:12])  # Convert to int timestamp
        )
    except Exception as e:
        print(f"Weather API error: {e}. Using safe mock data.")
        return WeatherData(
            wind_speed=5.0,  # m/s
            visibility=10.0,  # km
            precipitation=0.0,  # mm/h
            temperature=20.0,  # Celsius
            timestamp=0  # current time
        )


def is_weather_safe(weather: WeatherData) -> bool:
    """
    Check if weather conditions are safe for vertiport operations.
    Based on FAA/ICAO standards for eVTOL operations.
    """
    # Example thresholds (adjust based on vertiport regulations)
    max_wind = 10.0  # m/s
    min_visibility = 5.0  # km
    max_precipitation = 2.5  # mm/h (light rain)
    min_temp = -10.0  # Celsius
    max_temp = 40.0  # Celsius

    return (
        weather.wind_speed <= max_wind and
        weather.visibility >= min_visibility and
        weather.precipitation <= max_precipitation and
        min_temp <= weather.temperature <= max_temp
    )


def get_weather_penalty(weather: WeatherData) -> float:
    """
    Calculate a penalty factor for scheduling based on weather severity.
    Higher penalty reduces priority or increases delays.
    """
    if is_weather_safe(weather):
        return 1.0  # No penalty

    # Simple penalty based on wind and visibility
    wind_penalty = max(0, weather.wind_speed - 5) / 5  # 0-1 scale
    vis_penalty = max(0, 5 - weather.visibility) / 5  # 0-1 scale
    return 1.0 + (wind_penalty + vis_penalty) / 2  # 1.0 to 2.0
