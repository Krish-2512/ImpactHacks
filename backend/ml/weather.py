import os
import math
import joblib
import numpy as np
import pandas as pd
from datetime import datetime


# Seasonal baselines for Northeast India (Guwahati region)
_WEATHER_SEASONAL = {
    "Temperature":   {"base": 25.0, "amp": 10.0,  "peak_month": 6},
    "Humidity":      {"base": 78.0, "amp": 15.0,  "peak_month": 7},
    "Wind_Speed":    {"base": 12.0, "amp": 5.0,   "peak_month": 5},
    "Precipitation": {"base": 5.0,  "amp": 12.0,  "peak_month": 7},
}


def _seasonal_weather(date: datetime) -> dict[str, float]:
    """Deterministic seasonal weather estimate — no randomness."""
    doy = date.timetuple().tm_yday
    result = {}
    for col, p in _WEATHER_SEASONAL.items():
        peak_doy = (p["peak_month"] - 1) * 30 + 15
        value = p["base"] + p["amp"] * math.cos(2 * math.pi * (doy - peak_doy) / 365.0)
        result[col] = round(max(0.0, value), 2)
    return result


def _rule_based_condition(w: dict) -> str:
    precip = w.get("Precipitation", 0)
    wind   = w.get("Wind_Speed", 0)
    humid  = w.get("Humidity", 60)
    if precip > 20 or wind > 22:
        return "Stormy"
    if precip > 5:
        return "Rainy"
    if humid > 70:
        return "Cloudy"
    return "Sunny"


class WeatherModel:
    COLUMNS = ['Temperature', 'Humidity', 'Wind_Speed', 'Precipitation']

    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self._models: dict = {}
        self._load()

    def _load(self):
        for col in self.COLUMNS:
            path = os.path.join(self.model_dir, f"{col}_sarimax.pkl")
            if os.path.exists(path):
                self._models[col] = joblib.load(path)
            else:
                print(f"WARNING: Weather model not found for {col} at {path} — using seasonal fallback")

    def forecast(self, date_str: str | None = None) -> dict[str, float]:
        if date_str is None:
            date_str = datetime.today().strftime('%Y-%m-%d')

        target = pd.to_datetime(date_str)
        result: dict[str, float] = {}

        for col in self.COLUMNS:
            if col in self._models:
                model_fit = self._models[col]
                last_date = model_fit.data.dates[-1]
                steps = max(1, (target - pd.to_datetime(last_date)).days)
                fc = model_fit.forecast(steps=steps)
                result[col] = float(max(0.0, fc.iloc[-1]))
            else:
                result[col] = _seasonal_weather(target.to_pydatetime())[col]

        return result


class WeatherClassifier:
    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self._model = None
        self._encoder = None
        self._load()

    def _load(self):
        model_path = os.path.join(self.model_dir, "weather_condition_model.pkl")
        encoder_path = os.path.join(self.model_dir, "label_encoder.pkl")
        if os.path.exists(model_path) and os.path.exists(encoder_path):
            self._model = joblib.load(model_path)
            self._encoder = joblib.load(encoder_path)
        else:
            print(f"WARNING: Classifier models not found in {self.model_dir} — using rule-based fallback")

    def predict(self, weather_dict: dict) -> str:
        if self._model is None or self._encoder is None:
            return _rule_based_condition(weather_dict)

        input_df = pd.DataFrame([{
            'Temperature':   weather_dict.get('Temperature', 25.0),
            'Humidity':      weather_dict.get('Humidity', 60.0),
            'Wind_Speed':    weather_dict.get('Wind_Speed', 10.0),
            'Precipitation': weather_dict.get('Precipitation', 0.0),
        }])
        label = self._model.predict(input_df)[0]
        return str(self._encoder.inverse_transform([label])[0])
