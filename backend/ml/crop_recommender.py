"""
Crop Recommendation Model — Random Forest Classifier

Trained at startup from synthetic data generated using established agronomic
parameters for Northeast India crops (ICAR crop guides). 300 samples per crop,
7 soil + climate features, 10 crop classes.

Features: N, P, K (kg/ha), temperature (°C), humidity (%), pH, rainfall (mm/year)
"""
import os
import numpy as np
import joblib
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent.parent / "ml_data" / "crop_recommender.pkl"

# Agronomic ideal ranges for each crop in Northeast India (source: ICAR guidelines)
CROP_RANGES = {
    "tomato":   {"N": (60,80),   "P": (40,60),  "K": (60,80),   "temp": (20,27), "humidity": (60,75), "pH": (6.0,7.0), "rainfall": (600,1200)},
    "brinjal":  {"N": (80,100),  "P": (40,60),  "K": (80,100),  "temp": (22,35), "humidity": (65,80), "pH": (5.5,6.6), "rainfall": (600,1200)},
    "cabbage":  {"N": (100,120), "P": (40,60),  "K": (60,80),   "temp": (15,20), "humidity": (70,85), "pH": (6.0,7.5), "rainfall": (300,500)},
    "lemon":    {"N": (60,80),   "P": (20,40),  "K": (60,80),   "temp": (20,30), "humidity": (55,70), "pH": (5.5,7.0), "rainfall": (750,1250)},
    "potato":   {"N": (80,100),  "P": (60,80),  "K": (100,120), "temp": (15,20), "humidity": (75,85), "pH": (5.0,6.5), "rainfall": (500,700)},
    "onion":    {"N": (60,80),   "P": (40,60),  "K": (40,60),   "temp": (13,24), "humidity": (60,75), "pH": (6.0,7.0), "rainfall": (350,550)},
    "ginger":   {"N": (60,80),   "P": (40,60),  "K": (80,100),  "temp": (20,30), "humidity": (75,90), "pH": (5.5,6.5), "rainfall": (1500,3000)},
    "turmeric": {"N": (60,80),   "P": (40,60),  "K": (80,100),  "temp": (20,35), "humidity": (75,90), "pH": (4.5,7.5), "rainfall": (1500,2500)},
    "chili":    {"N": (80,100),  "P": (40,60),  "K": (40,60),   "temp": (20,30), "humidity": (60,75), "pH": (6.0,7.0), "rainfall": (600,1200)},
    "garlic":   {"N": (60,80),   "P": (40,60),  "K": (40,60),   "temp": (12,24), "humidity": (55,70), "pH": (6.0,7.0), "rainfall": (250,500)},
}

FEATURES = ["N", "P", "K", "temperature", "humidity", "pH", "rainfall"]


def _generate_training_data(samples_per_crop: int = 350, seed: int = 42):
    rng = np.random.default_rng(seed)
    X, y = [], []
    for crop, ranges in CROP_RANGES.items():
        vals = list(ranges.values())
        lo  = np.array([v[0] for v in vals], dtype=float)
        hi  = np.array([v[1] for v in vals], dtype=float)
        mid = (lo + hi) / 2
        spread = (hi - lo) / 2

        # Core samples: uniform within ideal range
        core = rng.uniform(lo, hi, size=(int(samples_per_crop * 0.7), len(lo)))
        # Fringe samples: gaussian around midpoint (allows slight overlap between crops)
        fringe = rng.normal(mid, spread * 0.4, size=(samples_per_crop - len(core), len(lo)))
        samples = np.vstack([core, fringe])

        X.append(samples)
        y.extend([crop] * len(samples))

    return np.vstack(X), np.array(y)


class CropRecommender:
    def __init__(self):
        self._model = None
        self._classes = None

    def load_or_train(self) -> None:
        if MODEL_PATH.exists():
            data = joblib.load(MODEL_PATH)
            self._model   = data["model"]
            self._classes = data["classes"]
            print(f"CropRecommender: loaded from {MODEL_PATH}")
        else:
            self._train_and_save()

    def _train_and_save(self) -> None:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import LabelEncoder

        print("CropRecommender: training Random Forest on synthetic agronomic data...")
        X, y_raw = _generate_training_data()

        le = LabelEncoder()
        y  = le.fit_transform(y_raw)

        clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=None,
            min_samples_split=4,
            random_state=42,
            n_jobs=-1,
        )
        clf.fit(X, y)

        self._model   = clf
        self._classes = le.classes_

        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": clf, "classes": le.classes_}, MODEL_PATH)
        print(f"CropRecommender: trained ({len(le.classes_)} crops) → saved to {MODEL_PATH}")

    def predict(
        self,
        N: float, P: float, K: float,
        temperature: float, humidity: float,
        pH: float, rainfall: float,
        top_k: int = 3,
    ) -> list[dict]:
        x = np.array([[N, P, K, temperature, humidity, pH, rainfall]])
        proba = self._model.predict_proba(x)[0]
        top_idx = np.argsort(proba)[::-1][:top_k]
        return [
            {
                "crop":       self._classes[i],
                "confidence": round(float(proba[i]) * 100, 1),
                "suitability": "Excellent" if proba[i] > 0.5 else "Good" if proba[i] > 0.2 else "Moderate",
            }
            for i in top_idx
        ]

    def feature_importance(self) -> dict:
        """Returns how much each soil/climate factor matters for crop selection."""
        importances = self._model.feature_importances_
        return {f: round(float(v) * 100, 1) for f, v in zip(FEATURES, importances)}
