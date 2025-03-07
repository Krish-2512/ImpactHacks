import pandas as pd
import numpy as np
import os
import joblib
from statsmodels.tsa.statespace.sarimax import SARIMAX
from datetime import datetime
import json

# Define the base directory to store models
BASE_DIR = os.path.join(os.getcwd(), "crop_models")
os.makedirs(BASE_DIR, exist_ok=True)  # Ensure the directory exists

def train_and_save_models(file_paths, model_dir=BASE_DIR):
    """
    Train SARIMAX models for multiple crops using predefined parameters and save them.

    Args:
    file_paths (dict): Dictionary mapping crop names to CSV file paths.
    model_dir (str): Directory to save trained models.
    """
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    crop_params = {
        "brinjal": ((2, 1, 2), (1, 1, 1, 7)),
        "cabbage": ((1, 1, 1), (1, 1, 0, 7)),
        "lemon": ((2, 1, 2), (0, 1, 1, 7)),
        "tomato": ((1, 1, 1), (1, 1, 1, 7))  # ✅ Fixed formatting error
    }

    for crop, file_path in file_paths.items():
        df = pd.read_csv(file_path)
        df['Date'] = pd.to_datetime(df['Date'], format="%d-%m-%Y", errors='coerce')  # Handle incorrect dates
        df.dropna(subset=['Date'], inplace=True)  # Drop invalid dates
        df.set_index('Date', inplace=True)

        if 'Median_Price' not in df.columns:
            print(f"⚠️ Skipping {crop}: 'Median_Price' column not found in {file_path}")
            continue  # Skip if no price data

        df = df[['Median_Price']].resample('D').mean().interpolate()  # Fill missing values
        df['Log_Price'] = np.log1p(df['Median_Price'])  # Log transform to stabilize variance

        order, seasonal_order = crop_params[crop]

        # Train SARIMAX Model
        model = SARIMAX(df['Log_Price'], order=order, seasonal_order=seasonal_order,
                        enforce_stationarity=False, enforce_invertibility=False)
        model_fit = model.fit(disp=False)

        # Save trained model
        model_path = os.path.join(model_dir, f"{crop}_sarimax.pkl")
        joblib.dump(model_fit, model_path)
        print(f"✅ Model saved: {model_path}")  # Log successful saves

def load_models_and_forecast(target_date, model_dir=BASE_DIR):
    """
    Load trained models and predict crop prices for a given future date.

    Args:
    target_date (str): Future date in 'DD-MM-YYYY' format.

    Returns:
    dict: Forecasted crop prices.
    """
    target_datetime = pd.to_datetime(target_date, format="%d-%m-%Y", errors='coerce')

    if target_datetime is pd.NaT:
        return {"error": "Invalid date format. Use 'DD-MM-YYYY'."}

    predictions = {}

    for model_file in os.listdir(model_dir):
        if model_file.endswith("_sarimax.pkl"):
            crop_name = model_file.replace("_sarimax.pkl", "")
            model_path = os.path.join(model_dir, model_file)

            model_fit = joblib.load(model_path)
            last_date = model_fit.data.dates[-1]
            forecast_days = (target_datetime - pd.to_datetime(last_date)).days

            if forecast_days < 0:
                predictions[crop_name] = "⚠️ Target date must be in the future."
            else:
                forecast = model_fit.forecast(steps=forecast_days)
                predicted_price = np.expm1(forecast.iloc[-1])  # Convert back from log scale
                predictions[crop_name] = round(float(predicted_price), 2)  # ✅ Round to 2 decimal places

    return predictions

# Define file paths for each crop
file_paths = {
    "brinjal": r"C:\Users\HP\Desktop\AgroApp\AgroApp\Models\CropPricePrediction\brinjal.csv",
    "cabbage": r"C:\Users\HP\Desktop\AgroApp\AgroApp\Models\CropPricePrediction\cabbage.csv",
    "lemon": r"C:\Users\HP\Desktop\AgroApp\AgroApp\Models\CropPricePrediction\lemon.csv",
    "tomato": r"C:\Users\HP\Desktop\AgroApp\AgroApp\Models\CropPricePrediction\tomato.csv"
}

# Train models for all crops
train_and_save_models(file_paths)

# Forecast prices for today
target_date = datetime.today().strftime('%d-%m-%Y')
predicted_prices = load_models_and_forecast(target_date)

# Save predictions to JSON
json_path = os.path.join(BASE_DIR, "predicted_prices.json")
with open(json_path, "w") as json_file:
    json.dump(predicted_prices, json_file, indent=4)

print(f"📄 Predictions saved to: {json_path}")
