import pandas as pd
import joblib
import os


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "model",
    "traffic_congestion_random_forest.pkl"
)

TIME_FILE = os.path.join(
    BASE_DIR,
    "results",
    "expected_congestion_time.csv"
)


# ============================================================
# LOAD MODEL
# ============================================================

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model file not found: {MODEL_PATH}"
    )

# Compatibility shim for scikit-learn models pickled across versions
import sklearn.compose._column_transformer as ct
if not hasattr(ct, '_RemainderColsList'):
    class _RemainderColsList(list):
        pass
    ct._RemainderColsList = _RemainderColsList

model = joblib.load(MODEL_PATH)


# ============================================================
# FORMAT TIME
# ============================================================

def format_time(hour_value):

    hour_value = int(hour_value)

    if hour_value == 0:
        return "12:00 AM"

    elif hour_value < 12:
        return f"{hour_value}:00 AM"

    elif hour_value == 12:
        return "12:00 PM"

    else:
        return f"{hour_value - 12}:00 PM"


# ============================================================
# FIND EXPECTED CONGESTION TIME
# ============================================================

def get_expected_congestion_time(
    location,
    day_of_week,
    congestion_level
):

    expected_time = "Unable to determine"

    if not os.path.exists(TIME_FILE):
        return expected_time

    time_data = pd.read_csv(TIME_FILE)

    # --------------------------------------------------------
    # Clean text columns
    # --------------------------------------------------------

    time_data["location"] = (
        time_data["location"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    time_data["day_of_week"] = (
        time_data["day_of_week"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    time_data["congestion_level"] = (
        time_data["congestion_level"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # Clean hour
    # --------------------------------------------------------

    time_data["hour"] = pd.to_numeric(
        time_data["hour"],
        errors="coerce"
    )

    time_data = time_data.dropna(
        subset=["hour"]
    )

    # --------------------------------------------------------
    # Only realistic traffic hours
    # 6 AM to 9 PM
    # --------------------------------------------------------

    time_data = time_data[
        (time_data["hour"] >= 6) &
        (time_data["hour"] <= 21)
    ].copy()

    location_value = (
        str(location)
        .strip()
        .lower()
    )

    day_value = (
        str(day_of_week)
        .strip()
        .lower()
    )

    congestion_value = (
        str(congestion_level)
        .strip()
        .upper()
    )

    # ========================================================
    # METHOD 1
    # Location + Day + Congestion
    # ========================================================

    matching = time_data[
        (time_data["location"] == location_value) &
        (time_data["day_of_week"] == day_value) &
        (time_data["congestion_level"] == congestion_value)
    ].copy()

    # ========================================================
    # METHOD 2
    # Location + Congestion
    # ========================================================

    if matching.empty:

        matching = time_data[
            (time_data["location"] == location_value) &
            (time_data["congestion_level"] == congestion_value)
        ].copy()

    # ========================================================
    # METHOD 3
    # Congestion only
    # ========================================================

    if matching.empty:

        matching = time_data[
            time_data["congestion_level"] == congestion_value
        ].copy()

    # ========================================================
    # FIND BEST HISTORICAL HOUR
    # ========================================================

    if not matching.empty:

        if "percentage" in matching.columns:

            matching["percentage"] = pd.to_numeric(
                matching["percentage"],
                errors="coerce"
            )

            matching = matching.dropna(
                subset=["percentage"]
            )

        if (
            not matching.empty
            and "percentage" in matching.columns
        ):

            best_row = matching.loc[
                matching["percentage"].idxmax()
            ]

            best_hour = int(best_row["hour"])

        else:

            hour_counts = (
                matching["hour"]
                .value_counts()
            )

            best_hour = int(
                hour_counts.idxmax()
            )

    else:

        # ----------------------------------------------------
        # Final fallback
        # ----------------------------------------------------

        if time_data.empty:
            return expected_time

        hour_counts = (
            time_data["hour"]
            .value_counts()
        )

        best_hour = int(
            hour_counts.idxmax()
        )

    next_hour = (best_hour + 1) % 24

    expected_time = (
        f"{format_time(best_hour)} - "
        f"{format_time(next_hour)}"
    )

    return expected_time


# ============================================================
# MAIN PREDICTION FUNCTION
# ============================================================

def predict_congestion(
    road_id,
    location,
    latitude,
    longitude,
    road_type,
    hour,
    day_of_week,
    holiday,
    vehicle_count,
    average_speed,
    traffic_density,
    road_capacity,
    previous_traffic,
    weather,
    rainfall,
    temperature,
    visibility,
    road_condition,
    historical_accidents
):

    # --------------------------------------------------------
    # Create input DataFrame
    # --------------------------------------------------------

    new_data = pd.DataFrame({

        "road_id": [road_id],

        "location": [location],

        "latitude": [latitude],

        "longitude": [longitude],

        "road_type": [road_type],

        "hour": [hour],

        "day_of_week": [day_of_week],

        "holiday": [holiday],

        "vehicle_count": [vehicle_count],

        "average_speed": [average_speed],

        "traffic_density": [traffic_density],

        "road_capacity": [road_capacity],

        "previous_traffic": [previous_traffic],

        "weather": [weather],

        "rainfall": [rainfall],

        "temperature": [temperature],

        "visibility": [visibility],

        "road_condition": [road_condition],

        "historical_accidents": [historical_accidents]
    })

    # --------------------------------------------------------
    # Predict congestion
    # --------------------------------------------------------

    try:

        prediction = model.predict(new_data)[0]

    except Exception as e:

        raise RuntimeError(
            f"Prediction error: {e}"
        )

    # --------------------------------------------------------
    # Find expected congestion time
    # --------------------------------------------------------

    expected_time = get_expected_congestion_time(
        location,
        day_of_week,
        prediction
    )

    # --------------------------------------------------------
    # Return result to backend
    # --------------------------------------------------------

    return {
        "predicted_congestion": str(prediction),
        "expected_congestion_time": expected_time
    }