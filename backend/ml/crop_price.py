import os
import math
import joblib
import numpy as np
import pandas as pd
from datetime import datetime


class CropPriceModel:
    # Crops that have trained SARIMAX .pkl files
    ML_CROPS = ["brinjal", "cabbage", "lemon", "tomato"]

    # Extra Northeast India crops estimated from regional base prices + month-wise seasonal multipliers.
    # No random values — the daily variation uses a deterministic sine wave keyed to day-of-year.
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
                print(f"WARNING: Model not found for {crop} at {path}")

    def _estimate_seasonal(self, date: datetime) -> dict[str, float]:
        """Deterministic seasonal price estimation — no randomness."""
        month = date.month
        doy = date.timetuple().tm_yday
        result: dict[str, float] = {}
        for crop, data in self.SEASONAL_CROPS.items():
            seasonal = data["seasonal"][month - 1]
            # ±4% deterministic daily ripple using sine wave on day-of-year
            daily = 1.0 + 0.04 * math.sin(2 * math.pi * doy / 365.0)
            result[crop] = round(data["base"] * seasonal * daily, 2)
        return result

    def forecast(self, date_str: str | None = None) -> dict[str, float]:
        """
        Return prices for all 10 crops on date_str (DD-MM-YYYY).
        ML crops use SARIMAX; seasonal crops use the formula above.
        """
        if date_str is None:
            date_str = datetime.today().strftime('%d-%m-%Y')

        target = pd.to_datetime(date_str, format="%d-%m-%Y", errors='coerce')
        if target is pd.NaT:
            return {"error": "Invalid date format. Use DD-MM-YYYY."}

        predictions: dict[str, float] = {}

        # ML-modelled crops
        for crop, model_fit in self._models.items():
            last_date = model_fit.data.dates[-1]
            steps = (target - pd.to_datetime(last_date)).days
            if steps <= 0:
                steps = 1
            fc = model_fit.forecast(steps=steps)
            predictions[crop] = round(float(np.expm1(fc.iloc[-1])), 2)

        # Seasonal crops
        predictions.update(self._estimate_seasonal(target.to_pydatetime()))

        return predictions
