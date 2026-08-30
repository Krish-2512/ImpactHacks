from pathlib import Path
from backend.ml.crop_price import CropPriceModel
from backend.ml.weather import WeatherModel, WeatherClassifier
from backend.ml.crop_recommender import CropRecommender
from backend.ml.irrigation_advisor import IrrigationAdvisor
from backend.ml.price_anomaly import PriceAnomalyDetector

_ML_DATA = Path(__file__).parent.parent.parent / "ml_data"


class ModelCache:
    _instance: "ModelCache | None" = None

    def __init__(self):
        self.crop_price = CropPriceModel(
            model_dir=str(_ML_DATA / "crop_price" / "models")
        )
        self.weather = WeatherModel(
            model_dir=str(_ML_DATA / "weather" / "sarimax_models")
        )
        self.weather_classifier = WeatherClassifier(
            model_dir=str(_ML_DATA / "weather" / "classification_models")
        )

        self.crop_recommender = CropRecommender()
        self.crop_recommender.load_or_train()

        self.irrigation_advisor = IrrigationAdvisor()
        self.irrigation_advisor.load_or_train()

        self.price_anomaly = PriceAnomalyDetector()
        self.price_anomaly.load_or_train()

        print("ModelCache: all models loaded")

    @classmethod
    def load_all(cls) -> None:
        cls._instance = ModelCache()

    @classmethod
    def get(cls) -> "ModelCache":
        if cls._instance is None:
            cls.load_all()
        return cls._instance
