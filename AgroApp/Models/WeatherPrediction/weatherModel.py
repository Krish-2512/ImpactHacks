import pandas as pd
import numpy as np
import joblib
import os
import json
import warnings
from pathlib import Path
from datetime import datetime
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_squared_error, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

_MODULE_DIR = Path(__file__).parent
SARIMAX_DIR = str(_MODULE_DIR / "sarimax_models")
CLASSIFIER_DIR = str(_MODULE_DIR / "classification_models")
WEATHER_CSV = str(_MODULE_DIR / "Weather.csv")

os.makedirs(SARIMAX_DIR, exist_ok=True)
os.makedirs(CLASSIFIER_DIR, exist_ok=True)


def train_and_save_sarimax_models(df, best_params, model_dir=SARIMAX_DIR):
    """
    Train SARIMAX models for weather parameters, evaluate performance, and save models.

    Args:
    df (pd.DataFrame): Complete dataset.
    best_params (dict): Tuned SARIMA hyperparameters.
    model_dir (str): Directory to save models.

    Returns:
    dict: RMSE performance of the models for each weather parameter.
    """
    numeric_columns = ['Temperature', 'Humidity', 'Wind_Speed', 'Precipitation']

    df['Date_Hour'] = pd.to_datetime(df['Date_Hour'], format='%d-%m-%Y %H:%M', errors='coerce')
    df.set_index('Date_Hour', inplace=True)

    weather_data = df[numeric_columns].resample('D').mean().interpolate()

    split_idx = int(len(weather_data) * 0.8)
    train, test = weather_data.iloc[:split_idx], weather_data.iloc[split_idx:]

    performance = {}
    os.makedirs(model_dir, exist_ok=True)

    for col in numeric_columns:
        order = best_params[col]['order']
        seasonal_order = best_params[col]['seasonal_order']

        model = SARIMAX(train[col], order=order, seasonal_order=seasonal_order,
                        enforce_stationarity=False, enforce_invertibility=False)
        model_fit = model.fit(disp=False)

        test_forecast = model_fit.forecast(steps=len(test))
        rmse = np.sqrt(mean_squared_error(test[col], test_forecast))
        performance[col] = float(rmse)

        final_model = SARIMAX(weather_data[col], order=order, seasonal_order=seasonal_order,
                              enforce_stationarity=False, enforce_invertibility=False)
        final_model_fit = final_model.fit(disp=False)
        joblib.dump(final_model_fit, os.path.join(model_dir, f"{col}_sarimax.pkl"))

    return performance


def load_models_and_forecast(target_date, model_dir=SARIMAX_DIR):
    """
    Load saved SARIMAX models and predict weather conditions for a given date.

    Args:
    target_date (str): Future date in 'YYYY-MM-DD' format.
    model_dir (str): Directory where models are saved.

    Returns:
    dict: Forecasted weather conditions for the target date.
    """
    target_datetime = pd.to_datetime(target_date)
    numeric_columns = ['Temperature', 'Humidity', 'Wind_Speed', 'Precipitation']

    forecasts = {}

    for col in numeric_columns:
        model_path = os.path.join(model_dir, f"{col}_sarimax.pkl")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file {model_path} not found. Train the model first.")

        model_fit = joblib.load(model_path)
        last_date = model_fit.data.dates[-1]
        forecast_days = (target_datetime - pd.to_datetime(last_date)).days

        if forecast_days < 0:
            raise ValueError("Target date must be in the future.")

        forecast = model_fit.forecast(steps=forecast_days)
        forecasts[col] = float(max(0, forecast.iloc[-1]))

    return forecasts


def train_and_save_weather_model(df, model_dir=CLASSIFIER_DIR):
    """
    Train an XGBoost Classifier to predict weather conditions and save the trained model.

    Args:
    df (pd.DataFrame): Weather dataset containing features and the 'Condition' column.

    Returns:
    dict: Performance metrics (accuracy).
    """
    os.makedirs(model_dir, exist_ok=True)
    numeric_columns = ['Temperature', 'Humidity', 'Wind_Speed', 'Precipitation']

    label_encoder = LabelEncoder()
    df = df.copy()
    df['Condition'] = label_encoder.fit_transform(df['Condition'])
    joblib.dump(label_encoder, os.path.join(model_dir, 'label_encoder.pkl'))

    X = df[numeric_columns]
    y = df['Condition']
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    best_model = XGBClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="mlogloss"
    )
    best_model.fit(X_train, y_train)
    joblib.dump(best_model, os.path.join(model_dir, 'weather_condition_model.pkl'))

    y_pred = best_model.predict(X_test)
    return {"Accuracy": accuracy_score(y_test, y_pred)}


def predict_weather_condition(temp, humidity, wind_speed, precipitation,
                               model_dir=CLASSIFIER_DIR):
    """
    Predict the weather condition based on given input values.

    Returns:
    str: Predicted weather condition label.
    """
    model = joblib.load(os.path.join(model_dir, "weather_condition_model.pkl"))
    label_encoder = joblib.load(os.path.join(model_dir, "label_encoder.pkl"))

    input_df = pd.DataFrame([{
        'Temperature': temp,
        'Humidity': humidity,
        'Wind_Speed': wind_speed,
        'Precipitation': precipitation
    }])

    predicted_label = model.predict(input_df)[0]
    return label_encoder.inverse_transform([predicted_label])[0]


if __name__ == "__main__":
    df = pd.read_csv(WEATHER_CSV)

    best_sarima_params = {
        'Temperature':   {'order': (0, 1, 2), 'seasonal_order': (1, 1, 1, 7)},
        'Humidity':      {'order': (0, 1, 2), 'seasonal_order': (0, 1, 1, 7)},
        'Wind_Speed':    {'order': (0, 0, 2), 'seasonal_order': (0, 1, 1, 7)},
        'Precipitation': {'order': (0, 0, 0), 'seasonal_order': (0, 1, 0, 7)},
    }

    # Uncomment to retrain SARIMAX models:
    # performance_metrics = train_and_save_sarimax_models(df, best_sarima_params)

    target_date = datetime.today().strftime('%Y-%m-%d')
    forecast = load_models_and_forecast(target_date=target_date)
    train_and_save_weather_model(df)
    condition = predict_weather_condition(
        forecast['Temperature'], forecast['Humidity'],
        forecast['Wind_Speed'], forecast['Precipitation']
    )

    weather_output = {**forecast, "Condition": condition}
    out_path = str(_MODULE_DIR.parent.parent / "MainSite" / "weather.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(weather_output, f, indent=4, ensure_ascii=False)
    print(f"Saved weather forecast to {out_path}")
