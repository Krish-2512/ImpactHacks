import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime


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
                print(f"WARNING: Weather model not found for {col} at {path}")

    def forecast(self, date_str: str | None = None) -> dict[str, float]:
        """
        Forecast weather parameters for a given date.
        date_str: 'YYYY-MM-DD' format. Defaults to today.
        """
        if date_str is None:
            date_str = datetime.today().strftime('%Y-%m-%d')

        target = pd.to_datetime(date_str)
        result: dict[str, float] = {}

        for col, model_fit in self._models.items():
            last_date = model_fit.data.dates[-1]
            steps = (target - pd.to_datetime(last_date)).days
            if steps <= 0:
                steps = 1
            forecast = model_fit.forecast(steps=steps)
            result[col] = float(max(0.0, forecast.iloc[-1]))

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
            print(f"WARNING: Classifier models not found in {self.model_dir}")

    def predict(self, weather_dict: dict) -> str:
        """
        Predict weather condition string from a forecast dict
        with keys Temperature, Humidity, Wind_Speed, Precipitation.
        """
        if self._model is None or self._encoder is None:
            return "Unknown"

        input_df = pd.DataFrame([{
            'Temperature': weather_dict.get('Temperature', 25.0),
            'Humidity': weather_dict.get('Humidity', 60.0),
            'Wind_Speed': weather_dict.get('Wind_Speed', 10.0),
            'Precipitation': weather_dict.get('Precipitation', 0.0),
        }])
        label = self._model.predict(input_df)[0]
        return str(self._encoder.inverse_transform([label])[0])
