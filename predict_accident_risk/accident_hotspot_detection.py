import pandas as pd

df = pd.read_csv("dataset/hyderabad_traffic_accident_balanced_15000.csv")

# Keep only actual accident records
accidents = df[df["accident_occurred"] == 1].copy()

# Group accidents by route
hotspots = (
    accidents
    .groupby([
        "start_location",
        "end_location",
        "start_latitude",
        "start_longitude",
        "end_latitude",
        "end_longitude"
    ])
    .agg(
        accidents=("accident_occurred", "sum"),
        average_risk=("accident_risk", "mean")
    )
    .reset_index()
)

# Convert average risk into risk level
def get_risk_level(risk):
    if risk < 30:
        return "LOW"
    elif risk < 55:
        return "MEDIUM"
    elif risk < 75:
        return "HIGH"
    else:
        return "SEVERE"

hotspots["risk"] = hotspots["average_risk"].apply(get_risk_level)

# Sort by number of accidents
hotspots = hotspots.sort_values(
    by="accidents",
    ascending=False
).reset_index(drop=True)

# Add hotspot number
hotspots.insert(
    0,
    "hotspot_id",
    range(1, len(hotspots) + 1)
)

# Display top 10 hotspots
print("\nTop Accident Hotspots\n")

for _, row in hotspots.head(20).iterrows():
    print(f"Accident Hotspot #{row['hotspot_id']}")
    print(
        f"Route: {row['start_location']} → "
        f"{row['end_location']}"
    )
    print(f"Accidents: {row['accidents']}")
    print(f"Risk: {row['risk']}")
    print(f"Average Risk: {row['average_risk']:.2f}%")
    print("-" * 40)

# Save hotspot data
hotspots.to_csv(
    "accident_hotspots.csv",
    index=False
)

print("\nHotspot results saved to accident_hotspots.csv")