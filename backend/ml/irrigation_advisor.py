"""
Irrigation Advisor — Decision Tree Classifier

Trained at startup from crop water requirement agronomic rules.
Recommends whether to irrigate and how much water to apply (mm).

Features: crop_encoded, growth_stage_encoded, days_since_rain, rain_this_week,
          temperature, humidity, soil_moisture_estimate
Output:   should_irrigate (bool), recommended_mm, urgency (low/medium/high)
"""
import numpy as np
import joblib
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent.parent / "ml_data" / "irrigation_advisor.pkl"

# Crop weekly water needs (mm/week) by growth stage
# Source: FAO Crop Evapotranspiration guidelines adapted for NE India
CROP_WATER_NEED = {
    "tomato":   {"seedling": 18, "vegetative": 28, "flowering": 38, "fruiting": 32},
    "brinjal":  {"seedling": 16, "vegetative": 26, "flowering": 35, "fruiting": 30},
    "cabbage":  {"seedling": 20, "vegetative": 30, "flowering": 25, "fruiting": 22},
    "lemon":    {"seedling": 12, "vegetative": 20, "flowering": 30, "fruiting": 25},
    "potato":   {"seedling": 22, "vegetative": 32, "flowering": 40, "fruiting": 28},
    "onion":    {"seedling": 15, "vegetative": 22, "flowering": 28, "fruiting": 18},
    "ginger":   {"seedling": 25, "vegetative": 35, "flowering": 40, "fruiting": 30},
    "turmeric": {"seedling": 25, "vegetative": 35, "flowering": 40, "fruiting": 30},
    "chili":    {"seedling": 15, "vegetative": 25, "flowering": 32, "fruiting": 28},
    "garlic":   {"seedling": 12, "vegetative": 20, "flowering": 22, "fruiting": 15},
}

CROPS         = sorted(CROP_WATER_NEED.keys())
STAGES        = ["seedling", "vegetative", "flowering", "fruiting"]
CROP_IDX      = {c: i for i, c in enumerate(CROPS)}
STAGE_IDX     = {s: i for i, s in enumerate(STAGES)}


def _generate_training_data(samples: int = 8000, seed: int = 7):
    rng = np.random.default_rng(seed)
    X, y_irrigate, y_amount = [], [], []

    for _ in range(samples):
        crop  = rng.choice(CROPS)
        stage = rng.choice(STAGES)
        need  = CROP_WATER_NEED[crop][stage]  # mm/week needed

        days_since_rain  = float(rng.integers(0, 15))
        rain_this_week   = float(rng.uniform(0, 80))   # mm
        temp             = float(rng.uniform(12, 38))  # °C
        humidity         = float(rng.uniform(30, 95))  # %

        # Estimate soil moisture (heuristic for label generation)
        soil_moisture = min(100.0, rain_this_week * 0.8 + max(0, 40 - days_since_rain * 4))
        soil_moisture = max(0.0, soil_moisture - temp * 0.3)

        # Deficit = what the crop needs minus what it got from rain
        deficit = max(0.0, need - rain_this_week)
        # High temp or low humidity increases effective need
        heat_stress = max(0.0, (temp - 28) * 0.5)
        effective_deficit = deficit + heat_stress

        should_irrigate = int(effective_deficit > 8 or (days_since_rain > 5 and rain_this_week < 10))
        recommended_mm  = round(float(effective_deficit * 0.9), 1) if should_irrigate else 0.0

        X.append([
            float(CROP_IDX[crop]),
            float(STAGE_IDX[stage]),
            days_since_rain,
            rain_this_week,
            temp,
            humidity,
            soil_moisture,
        ])
        y_irrigate.append(should_irrigate)
        y_amount.append(recommended_mm)

    return np.array(X, dtype=float), np.array(y_irrigate), np.array(y_amount)


class IrrigationAdvisor:
    def __init__(self):
        self._clf    = None  # Decision Tree for should_irrigate
        self._reg    = None  # Decision Tree regressor for amount

    def load_or_train(self) -> None:
        if MODEL_PATH.exists():
            data = joblib.load(MODEL_PATH)
            self._clf = data["clf"]
            self._reg = data["reg"]
            print(f"IrrigationAdvisor: loaded from {MODEL_PATH}")
        else:
            self._train_and_save()

    def _train_and_save(self) -> None:
        from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

        print("IrrigationAdvisor: training Decision Tree on water-need agronomic data...")
        X, y_clf, y_reg = _generate_training_data()

        clf = DecisionTreeClassifier(max_depth=10, min_samples_split=20, random_state=42)
        clf.fit(X, y_clf)

        irrigate_mask = y_clf == 1
        reg = DecisionTreeRegressor(max_depth=8, min_samples_split=15, random_state=42)
        reg.fit(X[irrigate_mask], y_reg[irrigate_mask])

        self._clf = clf
        self._reg = reg

        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"clf": clf, "reg": reg}, MODEL_PATH)
        print(f"IrrigationAdvisor: trained → saved to {MODEL_PATH}")

    def predict(
        self,
        crop: str,
        growth_stage: str,
        days_since_rain: float,
        rain_this_week: float,
        temperature: float,
        humidity: float,
    ) -> dict:
        crop_clean  = crop.lower()
        stage_clean = growth_stage.lower()

        if crop_clean not in CROP_IDX:
            crop_clean = "tomato"
        if stage_clean not in STAGE_IDX:
            stage_clean = "vegetative"

        soil_moisture = min(100.0, rain_this_week * 0.8 + max(0, 40 - days_since_rain * 4))
        soil_moisture = max(0.0, soil_moisture - temperature * 0.3)

        x = np.array([[
            float(CROP_IDX[crop_clean]),
            float(STAGE_IDX[stage_clean]),
            float(days_since_rain),
            float(rain_this_week),
            float(temperature),
            float(humidity),
            float(soil_moisture),
        ]])

        should_irrigate = bool(self._clf.predict(x)[0])
        recommended_mm  = 0.0
        if should_irrigate:
            recommended_mm = max(0.0, float(self._reg.predict(x)[0]))
            recommended_mm = round(recommended_mm, 1)

        # Urgency based on days since rain + deficit
        need = CROP_WATER_NEED.get(crop_clean, {}).get(stage_clean, 25)
        deficit = max(0.0, need - rain_this_week)
        if not should_irrigate:
            urgency = "none"
        elif deficit > 20 or days_since_rain > 8:
            urgency = "high"
        elif deficit > 10 or days_since_rain > 4:
            urgency = "medium"
        else:
            urgency = "low"

        return {
            "should_irrigate":  should_irrigate,
            "recommended_mm":   recommended_mm,
            "urgency":          urgency,
            "crop_water_need":  need,
            "rain_deficit_mm":  round(max(0.0, float(need - rain_this_week)), 1),
            "advice":           _advice_text(should_irrigate, recommended_mm, urgency, crop_clean, stage_clean),
        }


def _advice_text(irrigate: bool, mm: float, urgency: str, crop: str, stage: str) -> str:
    if not irrigate:
        return f"No irrigation needed. Soil moisture is adequate for {crop} in {stage} stage."
    icon = {"high": "🚨", "medium": "⚠️", "low": "💧"}.get(urgency, "💧")
    return (
        f"{icon} Apply ~{mm} mm of water to {crop} ({stage} stage). "
        f"Use drip or furrow irrigation in the early morning to minimize evaporation."
    )
