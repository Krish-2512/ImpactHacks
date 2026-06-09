"""
Price Anomaly Detector — Isolation Forest

Detects when today's crop prices deviate significantly from their seasonal baseline.
Trained at startup using 730 days of synthetic seasonal price history.
Returns an anomaly score and human-readable interpretation for each crop.
"""
import math
import numpy as np
import joblib
from pathlib import Path
from datetime import date, timedelta

MODEL_PATH = Path(__file__).parent.parent.parent / "ml_data" / "price_anomaly.pkl"

# Crop base prices (₹/quintal) + monthly seasonal multipliers (Jan–Dec)
_CROP_BASELINES = {
    "brinjal":  {"base": 1500,  "seasonal": [0.95,0.90,1.00,1.10,1.20,1.25,1.20,1.10,1.05,1.00,0.95,0.95]},
    "cabbage":  {"base": 900,   "seasonal": [1.10,1.15,1.10,0.95,0.85,0.80,0.85,0.90,1.00,1.10,1.15,1.10]},
    "lemon":    {"base": 2500,  "seasonal": [1.00,0.95,1.10,1.20,1.30,1.20,1.10,1.00,0.95,0.90,0.95,1.00]},
    "tomato":   {"base": 1800,  "seasonal": [0.90,0.85,0.95,1.10,1.25,1.30,1.20,1.10,1.00,0.95,0.90,0.90]},
    "potato":   {"base": 1200,  "seasonal": [0.90,0.85,0.95,1.05,1.15,1.20,1.25,1.20,1.10,1.00,0.95,0.90]},
    "onion":    {"base": 2000,  "seasonal": [1.10,1.20,1.30,1.25,1.10,0.95,0.85,0.90,1.00,1.10,1.15,1.10]},
    "ginger":   {"base": 9000,  "seasonal": [1.05,1.00,0.95,0.90,1.00,1.10,1.20,1.25,1.15,1.05,1.00,1.05]},
    "turmeric": {"base": 11000, "seasonal": [1.00,0.95,0.90,0.95,1.05,1.10,1.15,1.20,1.15,1.05,1.00,1.00]},
    "chili":    {"base": 6000,  "seasonal": [0.95,0.90,1.00,1.15,1.25,1.30,1.20,1.10,1.00,0.95,0.90,0.95]},
    "garlic":   {"base": 5500,  "seasonal": [1.10,1.15,1.20,1.10,1.00,0.90,0.85,0.90,1.00,1.05,1.10,1.10]},
}
CROPS = sorted(_CROP_BASELINES.keys())


def _seasonal_price(crop: str, d: date) -> float:
    cfg      = _CROP_BASELINES[crop]
    seasonal = cfg["seasonal"][d.month - 1]
    doy      = d.timetuple().tm_yday
    daily    = 1.0 + 0.04 * math.sin(2 * math.pi * doy / 365.0)
    return cfg["base"] * seasonal * daily


def _generate_training_data(n_days: int = 730, seed: int = 99) -> np.ndarray:
    rng   = np.random.default_rng(seed)
    start = date(2024, 1, 1)
    rows  = []
    for i in range(n_days):
        d    = start + timedelta(days=i)
        row  = [_seasonal_price(c, d) * (1 + rng.normal(0, 0.04)) for c in CROPS]
        rows.append(row)
    return np.array(rows, dtype=float)


class PriceAnomalyDetector:
    def __init__(self):
        self._model  = None
        self._scaler = None

    def load_or_train(self) -> None:
        if MODEL_PATH.exists():
            data = joblib.load(MODEL_PATH)
            self._model  = data["model"]
            self._scaler = data["scaler"]
            print(f"PriceAnomalyDetector: loaded from {MODEL_PATH}")
        else:
            self._train_and_save()

    def _train_and_save(self) -> None:
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler

        print("PriceAnomalyDetector: training Isolation Forest on 2-year price history...")
        X = _generate_training_data()

        scaler   = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        iso = IsolationForest(
            n_estimators=150,
            contamination=0.05,
            max_samples="auto",
            random_state=42,
        )
        iso.fit(X_scaled)

        self._model  = iso
        self._scaler = scaler

        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": iso, "scaler": scaler}, MODEL_PATH)
        print(f"PriceAnomalyDetector: trained ({len(CROPS)} crops) → saved to {MODEL_PATH}")

    def detect(self, prices: dict) -> dict:
        """prices: {crop: price_inr}. Returns anomaly flag + per-crop deviation."""
        x        = np.array([[prices.get(c, 0.0) for c in CROPS]])
        x_scaled = self._scaler.transform(x)

        raw_score  = float(self._model.score_samples(x_scaled)[0])
        is_anomaly = self._model.predict(x_scaled)[0] == -1

        mean = self._scaler.mean_
        std  = np.sqrt(self._scaler.var_)
        z    = (x[0] - mean) / (std + 1e-8)

        per_crop = []
        for i, crop in enumerate(CROPS):
            per_crop.append({
                "crop":      crop,
                "price":     round(prices.get(crop, 0.0), 2),
                "deviation": round(float(z[i]), 2),
                "status":    _deviation_label(float(z[i])),
            })

        return {
            "is_anomaly":  bool(is_anomaly),
            "anomaly_score": round(raw_score, 4),
            "alert_level": "high"   if is_anomaly and raw_score < -0.25 else
                           "medium" if is_anomaly else "normal",
            "summary":     _summary(is_anomaly, per_crop),
            "per_crop":    sorted(per_crop, key=lambda r: abs(r["deviation"]), reverse=True),
        }


def _deviation_label(z: float) -> str:
    if z > 2.0:   return "much_higher_than_usual"
    if z > 1.0:   return "higher_than_usual"
    if z < -2.0:  return "much_lower_than_usual"
    if z < -1.0:  return "lower_than_usual"
    return "normal"


def _summary(is_anomaly: bool, per_crop: list) -> str:
    if not is_anomaly:
        return "All crop prices are within normal seasonal ranges."
    unusual = [r for r in per_crop if r["status"] != "normal"]
    names   = ", ".join(r["crop"].capitalize() for r in unusual[:3])
    return f"Unusual price movement detected for: {names}. Consider reviewing market conditions."
