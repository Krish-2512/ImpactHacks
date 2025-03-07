import pandas as pd
import numpy as np
import joblib
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_squared_error
import os
import json
import warnings
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier
warnings.filterwarnings("ignore")


BASE_DIR = os.path.join(os.getcwd(), "sarimax_models")
os.makedirs(BASE_DIR, exist_ok=True)
# Your model training code here...

def train_and_save_sarimax_models(df, best_params, model_dir=BASE_DIR):
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

    # Ensure the date column is in datetime format and set as index
    df['Date_Hour'] = pd.to_datetime(df['Date_Hour'], format='%d-%m-%Y %H:%M', errors='coerce')
    df.set_index('Date_Hour', inplace=True)

    # Resample to daily level and fill missing values with interpolation
    weather_data = df[numeric_columns].resample('D').mean().interpolate()

    # Train-test split (80% train, 20% test)
    split_idx = int(len(weather_data) * 0.8)
    train, test = weather_data.iloc[:split_idx], weather_data.iloc[split_idx:]

    performance = {}

    # Create directory if it doesn't exist
    os.makedirs(model_dir, exist_ok=True)

    for col in numeric_columns:
        order = best_params[col]['order']
        seasonal_order = best_params[col]['seasonal_order']

        # Train SARIMAX model on training set
        model = SARIMAX(train[col], order=order, seasonal_order=seasonal_order,
                        enforce_stationarity=False, enforce_invertibility=False)
        model_fit = model.fit(disp=False)

        # Predict on test set
        test_forecast = model_fit.forecast(steps=len(test))

        # Calculate RMSE
        rmse = np.sqrt(mean_squared_error(test[col], test_forecast))
        performance[col] = float(rmse)  # Convert to Python float

        # Train SARIMAX on full dataset and save the model
        final_model = SARIMAX(weather_data[col], order=order, seasonal_order=seasonal_order,
                              enforce_stationarity=False, enforce_invertibility=False)
        final_model_fit = final_model.fit(disp=False)

        joblib.dump(final_model_fit, f"{model_dir}/{col}_sarimax.pkl")

    return performance

def load_models_and_forecast(target_date, model_dir=BASE_DIR):
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
        model_path = f"{model_dir}/{col}_sarimax.pkl"

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file {model_path} not found. Please train the model first.")

        # Load trained SARIMAX model
        model_fit = joblib.load(model_path)

        # Determine forecast steps
        last_date = model_fit.data.dates[-1]
        forecast_days = (target_datetime - pd.to_datetime(last_date)).days

        if forecast_days < 0:
            raise ValueError("Target date must be in the future.")

        # Forecast for the given date
        forecast = model_fit.forecast(steps=forecast_days)
        forecasts[col] = float(max(0, forecast.iloc[-1]))  # Ensure precipitation is non-negative

    return forecasts

BASE_DIR = os.path.join(os.getcwd(), "classification_models")
os.makedirs(BASE_DIR, exist_ok=True)

def train_and_save_weather_model(df, model_dir=BASE_DIR):
    """
    Train an XGBoost Classifier to predict weather conditions and save the trained model.

    Args:
    df (pd.DataFrame): Weather dataset containing features and the 'Condition' column.

    Returns:
    dict: Performance metrics (accuracy and classification report).
    """
    os.makedirs(model_dir, exist_ok=True)
    numeric_columns = ['Temperature', 'Humidity', 'Wind_Speed', 'Precipitation']

    # Encode 'Condition' column
    label_encoder = LabelEncoder()
    df['Condition'] = label_encoder.fit_transform(df['Condition'])

    # Save label encoder for future decoding
    joblib.dump(label_encoder, f'{model_dir}/label_encoder.pkl')

    # Train-test split
    X = df[numeric_columns]
    y = df['Condition']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Define the XGBoost Classifier with optimized parameters
    best_model = XGBClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        use_label_encoder=False,
        eval_metric="mlogloss"
    )

    # Train the model
    best_model.fit(X_train, y_train)

    # Save the trained model
    joblib.dump(best_model, f'{model_dir}/weather_condition_model.pkl')

    # Evaluate the model
    y_pred = best_model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    return {"Accuracy": accuracy}


def predict_weather_condition(temp, humidity, wind_speed, precipitation):
    """
    Predict the weather condition based on given input values.

    Args:
    temp (float): Temperature value.
    humidity (float): Humidity percentage.
    wind_speed (float): Wind speed value.
    precipitation (float): Precipitation value.

    Returns:
    str: Predicted weather condition.
    """
    # Load trained model and label encoder

    MODEL_PATH = os.path.join(BASE_DIR, "weather_condition_model.pkl")
    ENCODER_PATH = os.path.join(BASE_DIR, "label_encoder.pkl")
    model = joblib.load(MODEL_PATH)
    label_encoder = joblib.load(ENCODER_PATH)

    # Prepare input data
    input_df = pd.DataFrame([{
        'Temperature': temp,
        'Humidity': humidity,
        'Wind_Speed': wind_speed,
        'Precipitation': precipitation
    }])

    # Predict condition
    predicted_label = model.predict(input_df)[0]

    # Convert numeric prediction back to original label
    predicted_condition = label_encoder.inverse_transform([predicted_label])[0]

    return predicted_condition

# Example usage: Train and save model
df = pd.read_csv('C:\\Users\\HP\\Desktop\\AgroApp\\AgroApp\\Models\\WeatherPrediction\\Weather.csv')

best_sarima_params = {
    'Temperature': {'order': (0, 1, 2), 'seasonal_order': (1, 1, 1, 7)},
    'Humidity': {'order': (0, 1, 2), 'seasonal_order': (0, 1, 1, 7)},
    'Wind_Speed': {'order': (0, 0, 2), 'seasonal_order': (0, 1, 1, 7)},
    'Precipitation': {'order': (0, 0, 0), 'seasonal_order': (0, 1, 0, 7)}
}

# Train and save the models
#performance_metrics = train_and_save_sarimax_models(df, best_sarima_params)
from datetime import datetime
target_date = datetime.today().strftime('%Y-%m-%d')
forecast = load_models_and_forecast(target_date=target_date)
train_and_save_weather_model(df)
condition=predict_weather_condition(forecast['Temperature'], forecast['Humidity'], forecast['Wind_Speed'], forecast['Precipitation'])

# Data
weather_data = {
    "Temperature":forecast['Temperature'],
    "Humidity": forecast['Humidity'],
    "Wind_Speed": forecast['Wind_Speed'],
    "Precipitation": forecast['Precipitation'],
    "Condition":condition
}

file_path = r"C:\Users\HP\Desktop\AgroApp\AgroApp\MainSite\weather.json"

# Ensure the directory exists
os.makedirs(os.path.dirname(file_path), exist_ok=True)
# Write JSON data to the file
with open(file_path, 'w', encoding='utf-8') as json_file:
    json.dump(weather_data, json_file, indent=4, ensure_ascii=False)
