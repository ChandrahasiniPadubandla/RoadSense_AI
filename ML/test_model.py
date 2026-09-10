import pandas as pd
import joblib
import os


# ============================================================
# 1. LOAD MODEL
# ============================================================

MODEL_PATH = "model/traffic_congestion_random_forest.pkl"
TIME_FILE = "results/expected_congestion_time.csv"

if not os.path.exists(MODEL_PATH):
    print("Model file not found!")
    exit()

model = joblib.load(MODEL_PATH)


# ============================================================
# 2. TEST DATA
# ============================================================
# Temporary hard-coded data.
# Later we will replace these with user inputs.

start_location = "LB Nagar"
start_latitude = 17.3457
start_longitude = 78.5522

end_location = "Mehdipatnam"
end_latitude = 17.3963
end_longitude = 78.4283

road_id = "LB-03"
road_type = "Highway"

hour = 19
day_of_week = "Friday"
holiday = 0

vehicle_count = 580
average_speed = 20
traffic_density = 85
road_capacity = 600
previous_traffic = 560

weather = "Rainy"
rainfall = 20
temperature = 24
visibility = 4

road_condition = "Poor"
historical_accidents = 5

# ============================================================
# 3. CREATE INPUT DATA
# ============================================================

new_data = pd.DataFrame({
    "road_id": [road_id],
    "location": [start_location],
    "latitude": [start_latitude],
    "longitude": [start_longitude],
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


# ============================================================
# 4. PREDICT CONGESTION
# ============================================================

try:

    prediction = model.predict(new_data)[0]

except Exception as e:

    print("Prediction error:")
    print(e)
    exit()


# ============================================================
# 5. FORMAT TIME
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
# 6. FIND EXPECTED CONGESTION TIME
# ============================================================

expected_time = "Unable to determine"


if os.path.exists(TIME_FILE):

    time_data = pd.read_csv(TIME_FILE)

    # --------------------------------------------------------
    # Clean data
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


    # ========================================================
    # ONLY USE REALISTIC TRAFFIC HOURS
    #
    # 6 AM to 9 PM
    #
    # 12 AM - 5 AM are ignored.
    # ========================================================

    time_data["hour"] = pd.to_numeric(
        time_data["hour"],
        errors="coerce"
    )

    time_data = time_data.dropna(
        subset=["hour"]
    )

    time_data = time_data[
        (time_data["hour"] >= 6) &
        (time_data["hour"] <= 21)
    ].copy()


    # --------------------------------------------------------
    # User values
    # --------------------------------------------------------

    location_value = (
        start_location
        .strip()
        .lower()
    )

    day_value = (
        day_of_week
        .strip()
        .lower()
    )

    congestion_value = (
        str(prediction)
        .strip()
        .upper()
    )


    # ========================================================
    # METHOD 1
    # Location + Day + Predicted Congestion
    # ========================================================

    matching = time_data[
        (time_data["location"] == location_value)
        &
        (time_data["day_of_week"] == day_value)
        &
        (time_data["congestion_level"] == congestion_value)
    ].copy()


    # ========================================================
    # METHOD 2
    # Location + Predicted Congestion
    # ========================================================

    if matching.empty:

        matching = time_data[
            (time_data["location"] == location_value)
            &
            (time_data["congestion_level"] == congestion_value)
        ].copy()


    # ========================================================
    # METHOD 3
    # Predicted Congestion Only
    # ========================================================

    if matching.empty:

        matching = time_data[
            time_data["congestion_level"] == congestion_value
        ].copy()


    # ========================================================
    # FIND BEST HISTORICAL HOUR
    # ========================================================

    if not matching.empty:

        # ----------------------------------------------------
        # If percentage is available, choose highest percentage
        # ----------------------------------------------------

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

        elif not matching.empty:

            # If percentage is not available,
            # choose the most frequent hour.

            hour_counts = (
                matching["hour"]
                .value_counts()
            )

            best_hour = int(
                hour_counts.idxmax()
            )

            expected_time = (
                f"{format_time(best_hour)} - "
                f"{format_time(best_hour + 1)}"
            )

            best_row = None

        else:

            best_row = None


        # ----------------------------------------------------
        # Convert selected hour into time range
        # ----------------------------------------------------

        if best_row is not None:

            best_hour = int(
                best_row["hour"]
            )

            next_hour = (
                best_hour + 1
            ) % 24

            expected_time = (
                f"{format_time(best_hour)} - "
                f"{format_time(next_hour)}"
            )


    # ========================================================
    # FINAL FALLBACK
    # ========================================================

    else:

        # If no location/day/congestion combination exists,
        # find the most common realistic traffic hour in the
        # complete historical dataset.

        if not time_data.empty:

            hour_counts = (
                time_data["hour"]
                .value_counts()
            )

            best_hour = int(
                hour_counts.idxmax()
            )

            next_hour = (
                best_hour + 1
            ) % 24

            expected_time = (
                f"{format_time(best_hour)} - "
                f"{format_time(next_hour)}"
            )


# ============================================================
# 7. FINAL OUTPUT
# ============================================================
# ONLY 4 RESULTS ARE DISPLAYED.

print()
print("=" * 50)
print("       TRAFFIC CONGESTION RESULT")
print("=" * 50)

print()
print("Start Location:")
print(start_location)

print()
print("End Location:")
print(end_location)

print()
print("Predicted Congestion:")
print(prediction)

print()
print("Expected Traffic Congestion:")
print(expected_time)

print()
print("=" * 50)