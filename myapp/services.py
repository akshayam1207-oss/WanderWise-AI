import logging
import requests

logger = logging.getLogger("wanderwise.services")

# Known coordinates for popular destinations
DESTINATION_COORDINATES = {
    "ooty": {"lat": 11.4102, "lon": 76.6950, "default_temp": 18, "condition": "Cool & Misty", "advisory": "Pack a light sweater or fleece jacket."},
    "manali": {"lat": 32.2432, "lon": 77.1892, "default_temp": 14, "condition": "Crisp Mountain Air", "advisory": "Carry warm thermals and sturdy footwear."},
    "goa": {"lat": 15.2993, "lon": 74.1240, "default_temp": 30, "condition": "Sunny & Coastal Breeze", "advisory": "Ideal beach weather! Carry sunscreen and hats."},
    "bali": {"lat": -8.4095, "lon": 115.1889, "default_temp": 28, "condition": "Tropical Warmth", "advisory": "Great time for exploring temples and coastlines."},
    "munnar": {"lat": 10.0889, "lon": 77.0595, "default_temp": 19, "condition": "Fresh Tea Valley Mist", "advisory": "Bring rain jackets and comfortable walking shoes."},
    "kerala": {"lat": 9.9312, "lon": 76.2673, "default_temp": 29, "condition": "Warm Backwaters", "advisory": "Light cotton clothing and mosquito repellent recommended."},
    "jaipur": {"lat": 26.9124, "lon": 75.7873, "default_temp": 31, "condition": "Bright Royal Skies", "advisory": "Stay hydrated during afternoon heritage fort visits."},
    "rishikesh": {"lat": 30.0869, "lon": 78.2676, "default_temp": 24, "condition": "Refreshing River Breezes", "advisory": "Perfect weather for river rafting and yoga."},
    "pondicherry": {"lat": 11.9416, "lon": 79.8083, "default_temp": 29, "condition": "Pleasant Coastal Sun", "advisory": "Great for cycling tours in the French Quarter."},
    "kodaikanal": {"lat": 10.2381, "lon": 77.4892, "default_temp": 17, "condition": "Chilly Pine Mist", "advisory": "Carry jackets for lakeside walks and Coaker's Walk."},
}

# Weather code mapping to friendly text and emoji
WMO_WEATHER_CODES = {
    0: ("☀️ Clear sky", "Sunny and bright"),
    1: ("🌤️ Mainly clear", "Pleasant with scattered sunshine"),
    2: ("⛅ Partly cloudy", "Comfortable with gentle cloud cover"),
    3: ("☁️ Overcast", "Cloudy skies"),
    45: ("🌫️ Foggy", "Misty mountain atmosphere"),
    48: ("🌫️ Depositing rime fog", "Dense fog conditions"),
    51: ("🌦️ Light drizzle", "Light passing showers"),
    61: ("🌧️ Slight rain", "Intermittent rain showers"),
    63: ("🌧️ Moderate rain", "Steady rainfall - carry umbrellas"),
    71: ("❄️ Slight snow fall", "Light snowfall in higher passes"),
    80: ("🌦️ Rain showers", "Brief passing showers"),
    95: ("⛈️ Thunderstorm", "Occasional thunder and lightning"),
}


def get_destination_weather(destination_name, timeout_seconds=3.0, force_timeout=False):
    """
    Third-party API call to Open-Meteo with strict timeout and fallback response.
    
    Parameters:
      - destination_name: Name of destination (e.g. 'Ooty', 'Goa', 'Jaipur')
      - timeout_seconds: Maximum time in seconds to wait before falling back (default 3.0s)
      - force_timeout: Testing flag to simulate timeout behavior
      
    Returns a dictionary with:
      - destination: Name
      - temperature: In Celsius
      - condition: Friendly description
      - advisory: Travel advice
      - is_fallback: True if fallback response was returned due to timeout or error
      - fallback_reason: Explanation if fallback was triggered
      - source: API or Fallback description
      - response_time_ms: Request duration in milliseconds
    """
    key = destination_name.lower().strip()
    matched_key = next((k for k in DESTINATION_COORDINATES if k in key), None)
    default_info = DESTINATION_COORDINATES.get(matched_key, {
        "lat": 12.9716, "lon": 77.5946, "default_temp": 24,
        "condition": "Pleasant Travel Weather", "advisory": "Check local weather before daily excursions."
    })

    if force_timeout:
        logger.warning("Simulated timeout requested for weather API.")
        return {
            "destination": destination_name,
            "temperature": default_info["default_temp"],
            "condition": default_info["condition"],
            "advisory": default_info["advisory"],
            "is_fallback": True,
            "fallback_reason": f"Simulated external API timeout ({timeout_seconds}s limit)",
            "source": "WanderWise Fallback Travel Engine (Local Cache)",
            "response_time_ms": int(timeout_seconds * 1000),
        }

    lat = default_info["lat"]
    lon = default_info["lon"]
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"

    try:
        resp = requests.get(url, timeout=timeout_seconds)
        if resp.status_code == 200:
            data = resp.json().get("current", {})
            temp = round(data.get("temperature_2m", default_info["default_temp"]))
            wcode = data.get("weather_code", 0)
            condition_tuple = WMO_WEATHER_CODES.get(wcode, ("⛅ Pleasant", "Good travel conditions"))
            humidity = data.get("relative_humidity_2m", 60)
            wind = data.get("wind_speed_10m", 10)

            return {
                "destination": destination_name,
                "temperature": temp,
                "condition": condition_tuple[0],
                "description": condition_tuple[1],
                "humidity": f"{humidity}%",
                "wind_speed": f"{wind} km/h",
                "advisory": default_info["advisory"],
                "is_fallback": False,
                "fallback_reason": None,
                "source": "Open-Meteo Meteorological API (Live)",
                "response_time_ms": round(resp.elapsed.total_seconds() * 1000, 1),
            }
        else:
            raise requests.RequestException(f"External API returned HTTP status {resp.status_code}")

    except requests.exceptions.Timeout as e:
        logger.warning("Third-party weather API timed out after %ss: %s", timeout_seconds, e)
        return {
            "destination": destination_name,
            "temperature": default_info["default_temp"],
            "condition": default_info["condition"],
            "advisory": default_info["advisory"],
            "is_fallback": True,
            "fallback_reason": f"External API timed out after {timeout_seconds}s (Strict SLA limit triggered)",
            "source": "WanderWise Fallback Travel Engine (Local Cache)",
            "response_time_ms": int(timeout_seconds * 1000),
        }
    except Exception as e:
        logger.warning("Third-party weather API connection issue: %s", e)
        return {
            "destination": destination_name,
            "temperature": default_info["default_temp"],
            "condition": default_info["condition"],
            "advisory": default_info["advisory"],
            "is_fallback": True,
            "fallback_reason": f"External service unavailable ({type(e).__name__}) - fallback activated safely",
            "source": "WanderWise Fallback Travel Engine (Local Cache)",
            "response_time_ms": 15,
        }
