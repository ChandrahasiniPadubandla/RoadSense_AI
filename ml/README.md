# RoadSense AI — Machine Learning Pipeline

This module implements the **Traffic Congestion Prediction**, **Accident Risk Prediction**, and **Traffic Anomaly Detection** pipelines using an **API-first architecture**.

> [!IMPORTANT]
> To preserve system modularity and microservice isolation, **the ML pipeline does NOT connect directly to the database tables**. 
> Instead, it:
> 1. Fetches training and live operational data exclusively using backend `GET` APIs (`/api/roads`, `/api/zones`, `/api/traffic`, `/api/weather`, `/api/accidents`).
> 2. Trains and serializes Random Forest ML models to `.joblib` artifacts.
> 3. Periodically scores roads and posts predictions back to the backend using `POST /api/predictions/traffic`, `POST /api/predictions/accidents`, and `POST /api/anomalies/detect`.

---

## 1. Directory Structure

```text
RoadSense_AI/ml/
├── artifacts/                           # Serialized trained model pipelines
│   ├── traffic_congestion_model.joblib  # Trained Random Forest Congestion Classifier
│   └── accident_risk_model.joblib       # Trained Random Forest Accident Risk Classifier
├── api_client.py                        # REST API Client handling token auth, GETs & POSTs
├── train_traffic_model.py               # Ingests API data, trains & exports congestion model
├── train_accident_model.py              # Ingests API data, trains & exports accident risk model
├── run_predictions.py                   # Loads models, fetches live conditions & posts predictions
├── requirements.txt                     # ML python dependencies
└── README.md
```

---

## 2. Model Specifications

### Model 1: Traffic Congestion & Anomaly Model (`train_traffic_model.py`)
- **Data Ingestion**: `GET /api/traffic`, `GET /api/roads`, `GET /api/zones`, `GET /api/weather`.
- **Engineered Features**:
  - `hour`, `day_of_week`, `is_weekend` (temporal)
  - `vehicle_count`, `average_speed`, `traffic_density`
  - `road_capacity`, `speed_limit`, `number_of_lanes`, `road_type`
  - `rainfall`, `temperature`, `visibility`, `weather_condition`
- **Output Classes**: `LOW`, `MEDIUM`, `HIGH`, `SEVERE`.
- **Artifact**: `artifacts/traffic_congestion_model.joblib`.

### Model 2: Accident Risk & Safety Model (`train_accident_model.py`)
- **Data Ingestion**: `GET /api/accidents`, `GET /api/roads`, `GET /api/traffic`, `GET /api/weather`.
- **Engineered Features**:
  - Historical accident frequency by road ID
  - Speed differential (`average_speed` vs `speed_limit`)
  - Road condition (`wet`, `damaged`, `construction`, `normal`)
  - Adverse weather (`rainfall`, `visibility`, `weather_condition`)
- **Output Predictions**:
  - `risk_percentage` (0.0% to 100.0%)
  - `risk_level` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Artifact**: `artifacts/accident_risk_model.joblib`.

---

## 3. How to Run the Pipeline

Ensure the FastAPI server is running on `http://127.0.0.1:8000`.

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Train Models (Option A: Using Custom CSV Files or Option B: Using Database via REST APIs)

#### Option A: Train from Custom CSV Files (Recommended for large external datasets)
Drop your training dataset into `ml/data/` and specify the file path:
```bash
# Train Traffic Congestion model from CSV:
python train_traffic_model.py --csv data/my_traffic_dataset.csv

# Train Accident Risk model from CSV:
python train_accident_model.py --csv data/my_accidents_dataset.csv
```

#### Option B: Train directly from Database via REST APIs (No CSV required)
```bash
# Fetches historical records from /api/traffic, /api/roads, /api/weather, /api/zones:
python train_traffic_model.py

# Fetches incident records from /api/accidents, /api/roads, /api/traffic, /api/weather:
python train_accident_model.py
```
*Both methods generate calibrated and serialized `.joblib` model artifacts inside `ml/artifacts/`.*

---

### Step 3: Run Live Operational Predictions (From Database via APIs)
Once models are trained and saved, you **do not need the CSVs anymore**. 
In production, run:
```bash
python run_predictions.py
```
**What happens during prediction:**
1. Queries the **live operational state** from the database via backend `GET` APIs (`/api/roads`, `/api/traffic`, `/api/weather`).
2. Passes live road conditions through the trained Random Forest models.
3. Posts predictions back to the database prediction tables via `POST /api/predictions/traffic` and `POST /api/predictions/accidents`.
4. Automatically triggers alerts in the `alerts` table if high accident risk or severe congestion is detected!
