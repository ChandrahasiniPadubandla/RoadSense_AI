# Training Datasets Directory (`ml/data/`)

Place your offline or historical CSV dataset files in this folder for training machine learning models.

### Example File Names:
- `traffic_training_data.csv` (for `train_traffic_model.py`)
- `accident_training_data.csv` (for `train_accident_model.py`)

### Usage:
You can train the models directly using your custom CSV file:

```bash
# 1. Train traffic model from CSV
python train_traffic_model.py --csv data/traffic_training_data.csv

# 2. Train accident risk model from CSV
python train_accident_model.py --csv data/accident_training_data.csv
```

### Production Prediction Workflow:
Once the models are trained and saved to `ml/artifacts/`:
1. Run `python run_predictions.py`.
2. It fetches **live road telemetry** from the database via `GET` APIs (`/api/roads`, `/api/traffic`, `/api/weather`).
3. It generates predictions using your pre-trained models.
4. It writes predictions back to the database via `POST` APIs (`/api/predictions/traffic`, `/api/predictions/accidents`).
