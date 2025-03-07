# Agrow: Revolutionizing Agriculture in Northeast India

## Overview
Agrow is an online application specifically created to help farmers in Northeast India by providing them with easy-to-use platforms to effectively control their agricultural crop, monitor stocks, and drive data-based insights for maximizing yield. The web application incorporates AI models to project weather patterns and decide on proper crop prices in order to aid farmers in driving informed decisions and increasing their crop productivity.

## Key Features
- **Product & Stock Management**: Farmers are able to monitor the products they sell and maintain their stock levels in an efficient manner.
- **AI-based Weather Forecasting**: The app offers weather forecasts that enable farmers to plan agricultural activities effectively.
- **Optimal Crop Pricing Model**: With AI-based analysis, Agrow recommends the optimal price for crops to ensure maximum profit for farmers.
- **Easy-to-use Interface**: Built with simplicity, Agrow makes it easy for farmers with low technical competency to use it.

## Tech Stack
### Web Application Development
- **Backend**: Django (A Python-based web framework for managing database interactions and logic)
- **Frontend**: HTML, CSS, JavaScript (For an interactive and user-friendly interface)

### Machine Learning & AI Implementation
#### Programming Language
- Python (Core programming language for data analysis and machine learning models)

#### Libraries & Frameworks
##### Data Manipulation & Analysis
- `pandas` (Data processing and structuring)
- `numpy` (Numerical computations)

##### Time Series Forecasting
- `statsmodels` (SARIMAX model for weather and crop price forecasting)

##### Machine Learning & Classification
- `XGBoost` (XGBClassifier for weather condition prediction)
- `scikit-learn` (Data preprocessing, model evaluation, and dataset splitting)

##### Model Persistence & Storage
- `joblib` (Saving and loading trained models efficiently)

##### File Handling & JSON Processing	
- `os` (File and directory operations)
- `json` (Data storage and formatting for seamless integration)

## How to Run Agrow Web Application Locally
To run Agrow on your local machine, follow these steps:

### Prerequisites
1. Install **Python (3.8 or later)**
2. Install **Git**
3. Install **virtualenv** for managing the Python environment

### Setup Process
1. **Clone the Repository**
```bash
  git clone <your-github-repo-link>
  cd agrow
```

2. **Create a Virtual Environment**
```bash
  python -m venv venv
```

3. **Activate the Virtual Environment**
   - On Windows:
   ```bash
   venv\Scripts\activate
   ```
   - On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

4. **Install Dependencies**
```bash
  pip install -r requirements.txt
```

5. **Run the Development Server**
```bash
  python manage.py runserver
```
This will start the server at `http://127.0.0.1:8000/site`.

### Running Machine Learning Model
Ensure that the model files (saved using `joblib`) are in the appropriate directory as expected by the Django application. If necessary, retrain the model by running:
```bash
  python train_model.py
```
Once trained, ensure the model is loaded correctly in the Django views before making predictions.

## Target Audience & Impact
Agrow is tailor-made for Northeast Indian farmers, with the objective to:
- **Boost Productivity**: Farmers can schedule crops according to weather forecasts and maximize output.
- **Improve Profitability**: AI-based crop price recommendations allow farmers to sell at the optimal price.
- **Minimize Losses**: Stock management features track better and minimize wastage.
- **Accessibility**: Simple platform that makes farm management easy without needing sophisticated technical expertise.

## Possible Improvements
- **Integration with Microfinance & Insurance**: Automated credit scoring for farmers and insurance products tomitigate crop loss risks..
- **Offline Accessibility**: Mail-based interactions for farmers with limited internet access.
- **Community & Advisory Features**: A platform where farmers can exchange experiences and get expert advice.
- **Continuous Improvements to the Time Series Model**: We plan to continuously keep scraping current day’s weather using the Weather API. We will then add this data to our dataset on a weekly basis and re-train the model. This increase in data can help the model capture seasonal and yearly trends, improving prediction performance.

## Conclusion
Agrow's mission is to transform farming in Northeast India through the use of AI and technology to enhance efficiency, profitability, and sustainability for farmers. By offering crucial tools and predictive information, Agrow aids farmers in making knowledge-informed decisions, ultimately leading to the development of the agricultural sector in the region.

