import os
import math
import joblib
import numpy as np
import pandas as pd
from datetime import datetime


class CropPriceModel:
    ML_CROPS = ["brinjal", "cabbage", "lemon", "tomato"]

    # Seasonal fallback for ML crops when SARIMAX pkl not available.
    # Base price INR/quintal + 12-month multipliers (Northeast India market data).
    _ML_FALLBACK = {
        "brinjal": {"base": 2500,  "seasonal": [0.95, 0.90, 1.00, 1.10, 1.20, 1.25, 1.20, 1.10, 1.00, 0.95, 0.90, 0.95]},
        "cabbage":  {"base": 800,   "seasonal": [1.20, 1.15, 1.00, 0.90, 0.85, 0.90, 1.00, 1.10, 1.15, 1.20, 1.25, 1.20]},
        "lemon":    {"base": 4000,  "seasonal": [1.10, 1.20, 1.15, 1.00, 0.90, 0.85, 0.90, 1.00, 1.10, 1.15, 1.10, 1.05]},
        "tomato":   {"base": 1800,  "seasonal": [0.90, 0.85, 0.95, 1.10, 1.20, 1.25, 1.20, 1.10, 1.00, 0.95, 0.90, 0.85]},
    }

    SEASONAL_CROPS = {
        "potato":   {"base": 1200,  "seasonal": [0.90, 0.85, 0.95, 1.05, 1.15, 1.20, 1.25, 1.20, 1.10, 1.00, 0.95, 0.90]},
        "onion":    {"base": 2000,  "seasonal": [1.10, 1.20, 1.30, 1.25, 1.10, 0.95, 0.85, 0.90, 1.00, 1.10, 1.15, 1.10]},
        "ginger":   {"base": 9000,  "seasonal": [1.05, 1.00, 0.95, 0.90, 1.00, 1.10, 1.20, 1.25, 1.15, 1.05, 1.00, 1.05]},
        "turmeric": {"base": 11000, "seasonal": [1.00, 0.95, 0.90, 0.95, 1.05, 1.10, 1.15, 1.20, 1.15, 1.05, 1.00, 1.00]},
        "chili":    {"base": 6000,  "seasonal": [0.95, 0.90, 1.00, 1.15, 1.25, 1.30, 1.20, 1.10, 1.00, 0.95, 0.90, 0.95]},
        "garlic":   {"base": 5500,  "seasonal": [1.10, 1.15, 1.20, 1.10, 1.00, 0.90, 0.85, 0.90, 1.00, 1.05, 1.10, 1.10]},
    }

    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self._models: dict = {}
        self._load()

    def _load(self):
        for crop in self.ML_CROPS:
            path = os.path.join(self.model_dir, f"{crop}_sarimax.pkl")
            if os.path.exists(path):
                self._models[crop] = joblib.load(path)
            else:
                print(f"WARNING: Model not found for {crop} at {path} — using seasonal fallback")

    def _seasonal_price(self, crop: str, date: datetime, table: dict) -> float:
        month = date.month
        doy = date.timetuple().tm_yday
        seasonal = table[crop]["seasonal"][month - 1]
        daily = 1.0 + 0.04 * math.sin(2 * math.pi * doy / 365.0)
        return round(table[crop]["base"] * seasonal * daily, 2)

    def forecast(self, date_str: str | None = None) -> dict[str, float]:
        if date_str is None:
            date_str = datetime.today().strftime('%d-%m-%Y')

        target = pd.to_datetime(date_str, format="%d-%m-%Y", errors='coerce')
        if target is pd.NaT:
            return {"error": "Invalid date format. Use DD-MM-YYYY."}

        predictions: dict[str, float] = {}
        dt = target.to_pydatetime()

        # ML crops — SARIMAX if loaded, seasonal formula as fallback
        for crop in self.ML_CROPS:
            if crop in self._models:
                model_fit = self._models[crop]
                last_date = model_fit.data.dates[-1]
                steps = max(1, (target - pd.to_datetime(last_date)).days)
                fc = model_fit.forecast(steps=steps)
                predictions[crop] = round(float(np.expm1(fc.iloc[-1])), 2)
            else:
                predictions[crop] = self._seasonal_price(crop, dt, self._ML_FALLBACK)

        # Seasonal crops — always formula-based
        for crop in self.SEASONAL_CROPS:
            predictions[crop] = self._seasonal_price(crop, dt, self.SEASONAL_CROPS)

        return predictions
