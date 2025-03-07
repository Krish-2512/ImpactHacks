import subprocess
import json
from django.shortcuts import render

def weather_view(request):
    try:
        # Run weather.py and capture JSON output
        result = subprocess.run(
            ["python", "weather.py"], capture_output=True, text=True, check=True
        )
        weather_data = json.loads(result.stdout)  # Convert output to dict

    except Exception as e:
        weather_data = {"error": f"Failed to get weather data: {str(e)}"}

    return render(request, "weather.html", {"weather": weather_data})