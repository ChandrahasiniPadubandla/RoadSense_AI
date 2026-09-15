import pandas as pd
from pathlib import Path

DATASET_PATH = (
    Path(__file__).resolve().parent.parent
    / "dataset"
    / "traffic_accident_cleaned_10000.csv"
)

df = pd.read_csv(DATASET_PATH)

def get_accident_hotspots(top_n=15):
    """
    Identify the top accident hotspots.

    Parameters:
        top_n (int): Number of hotspots to return.

    Returns:
        list: Accident hotspot information as dictionaries.
    """

    # Select only records where an accident occurred
    accident_data = df[df["accident_occurred"] == 1].copy()

    # Group accidents by location and coordinates
    hotspots = (
        accident_data
        .groupby(["location", "latitude", "longitude"])
        .size()
        .reset_index(name="accident_count")
        .sort_values("accident_count", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    # Assign risk level based on accident count
    def get_risk_level(count):
        if count >= 700:
            return "HIGH"
        elif count >= 600:
            return "MEDIUM"
        else:
            return "LOW"

    hotspots["risk_level"] = hotspots["accident_count"].apply(
        get_risk_level
    )

    # Convert DataFrame into a list of dictionaries
    return hotspots.to_dict(orient="records")



if __name__ == "__main__":

    hotspots = get_accident_hotspots()

    print("\n===== ACCIDENT HOTSPOTS =====\n")

    for index, hotspot in enumerate(hotspots, start=1):

        print(f"Accident Hotspot #{index}")
        print(f"Location: {hotspot['location']}")
        print(f"Latitude: {hotspot['latitude']}")
        print(f"Longitude: {hotspot['longitude']}")
        print(f"Accidents: {hotspot['accident_count']}")
        print(f"Risk: {hotspot['risk_level']}")
        print("-" * 40)
