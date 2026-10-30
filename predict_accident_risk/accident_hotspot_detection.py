import os
import sys
import argparse
from typing import Optional, Dict, Any
import pandas as pd

# Ensure standard output can handle utf-8 characters without cp1252 crashes
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_risk_level(risk: float) -> str:
    """Convert average risk into categorical risk level."""
    risk_val = float(risk or 0.0)
    if risk_val < 30.0:
        return "LOW"
    elif risk_val < 55.0:
        return "MEDIUM"
    elif risk_val < 75.0:
        return "HIGH"
    else:
        return "SEVERE"


def get_dataset_path() -> str:
    """Finds the dataset file across potential local locations."""
    candidates = [
        os.path.join(BASE_DIR, "dataset", "hyderabad_traffic_accident_15000.csv"),
        os.path.join("dataset", "hyderabad_traffic_accident_15000.csv"),
        os.path.join("predict_accident_risk", "dataset", "hyderabad_traffic_accident_15000.csv"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        "Could not locate dataset 'hyderabad_traffic_accident_15000.csv' in expected directories."
    )


def load_accidents_dataset(dataset_path: Optional[str] = None) -> pd.DataFrame:
    """Loads and filters only records where an accident occurred."""
    path = dataset_path or get_dataset_path()
    df = pd.read_csv(path)
    # Keep only actual accident records
    accidents = df[df["accident_occurred"] == 1].copy()
    return accidents


def detect_all_hotspots(
    dataset_path: Optional[str] = None,
    save_csv: bool = True,
    output_csv_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Groups accidents across Hyderabad by route corridor:
    (start_location, end_location, start_latitude, start_longitude, end_latitude, end_longitude).
    Calculates total accidents, average risk score, and risk classification.
    """
    accidents = load_accidents_dataset(dataset_path)

    # Group accidents by route corridor
    hotspots = (
        accidents.groupby([
            "start_location",
            "end_location",
            "start_latitude",
            "start_longitude",
            "end_latitude",
            "end_longitude",
        ])
        .agg(
            accidents=("accident_occurred", "sum"),
            average_risk=("accident_risk", "mean"),
        )
        .reset_index()
    )

    hotspots["risk"] = hotspots["average_risk"].apply(get_risk_level)

    # Sort by number of accidents descending
    hotspots = hotspots.sort_values(
        by="accidents",
        ascending=False
    ).reset_index(drop=True)

    # Add hotspot ranking / ID
    hotspots.insert(0, "hotspot_id", range(1, len(hotspots) + 1))

    if save_csv:
        csv_dest = output_csv_path or os.path.join(BASE_DIR, "accident_hotspots.csv")
        hotspots.to_csv(csv_dest, index=False)
        print(f"\nHotspot results saved to {csv_dest}")

    return hotspots


def detect_hotspot(
    start_location: str,
    end_location: str,
    hotspots_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Evaluates whether the route between start_location and end_location is an accident hotspot.
    Checks direct route, reverse route, and fuzzy location names.
    """
    if hotspots_df is None:
        csv_path = os.path.join(BASE_DIR, "accident_hotspots.csv")
        if os.path.exists(csv_path):
            hotspots_df = pd.read_csv(csv_path)
        else:
            hotspots_df = detect_all_hotspots(save_csv=True)

    clean_start = str(start_location).strip().lower()
    clean_end = str(end_location).strip().lower()

    # Exact or substring match in forward direction
    direct_match = hotspots_df[
        hotspots_df["start_location"].str.lower().str.contains(clean_start, na=False, regex=False)
        & hotspots_df["end_location"].str.lower().str.contains(clean_end, na=False, regex=False)
    ]

    # Check reverse corridor if not found
    reverse_match = pd.DataFrame()
    if direct_match.empty:
        reverse_match = hotspots_df[
            hotspots_df["start_location"].str.lower().str.contains(clean_end, na=False, regex=False)
            & hotspots_df["end_location"].str.lower().str.contains(clean_start, na=False, regex=False)
        ]

    matched_row = None
    is_reverse = False
    if not direct_match.empty:
        matched_row = direct_match.iloc[0]
    elif not reverse_match.empty:
        matched_row = reverse_match.iloc[0]
        is_reverse = True

    if matched_row is not None:
        acc_count = int(matched_row["accidents"])
        avg_risk = float(matched_row["average_risk"])
        risk_level = str(matched_row["risk"])
        hotspot_id = int(matched_row["hotspot_id"])
        is_hotspot = acc_count >= 15 or risk_level in ["HIGH", "SEVERE"]

        return {
            "found": True,
            "is_hotspot": is_hotspot,
            "hotspot_id": hotspot_id,
            "start_location": str(matched_row["start_location"]),
            "end_location": str(matched_row["end_location"]),
            "is_reverse": is_reverse,
            "start_latitude": float(matched_row["start_latitude"]),
            "start_longitude": float(matched_row["start_longitude"]),
            "end_latitude": float(matched_row["end_latitude"]),
            "end_longitude": float(matched_row["end_longitude"]),
            "accidents": acc_count,
            "average_risk": round(avg_risk, 2),
            "risk": risk_level,
            "message": (
                f"Accident Hotspot #{hotspot_id}: {matched_row['start_location']} -> {matched_row['end_location']} "
                f"with {acc_count} recorded accidents and {avg_risk:.2f}% average risk ({risk_level})."
            )
        }

    return {
        "found": False,
        "is_hotspot": False,
        "hotspot_id": None,
        "start_location": start_location,
        "end_location": end_location,
        "is_reverse": False,
        "start_latitude": None,
        "start_longitude": None,
        "end_latitude": None,
        "end_longitude": None,
        "accidents": 0,
        "average_risk": 0.0,
        "risk": "LOW",
        "message": f"No hotspot records found for route corridor: {start_location} -> {end_location}."
    }


def main():
    parser = argparse.ArgumentParser(
        description="Hyderabad Accident Hotspot Detection Pipeline (RoadSense AI)"
    )
    parser.add_argument(
        "--start",
        "-s",
        type=str,
        default=None,
        help="Start location name to check hotspot status (e.g. 'Jubilee Hills')",
    )
    parser.add_argument(
        "--end",
        "-e",
        type=str,
        default=None,
        help="End location name to check hotspot status (e.g. 'Bachupally')",
    )
    parser.add_argument(
        "--top",
        "-t",
        type=int,
        default=20,
        help="Number of top accident hotspots to display (default: 20)",
    )
    args = parser.parse_args()

    # If start and end locations are passed, evaluate that specific corridor
    if args.start and args.end:
        print(f"\nEvaluating Hotspot Status for Route: {args.start} -> {args.end}\n")
        result = detect_hotspot(args.start, args.end)
        if result["found"]:
            print(f"Status: Identified Accident Hotspot (Rank #{result['hotspot_id']})")
            print(f"Matched Route: {result['start_location']} -> {result['end_location']}")
            print(f"Total Recorded Accidents: {result['accidents']}")
            print(f"Risk Level: {result['risk']}")
            print(f"Average Risk: {result['average_risk']}%")
            print(f"Coordinates: [{result['start_latitude']}, {result['start_longitude']}] -> [{result['end_latitude']}, {result['end_longitude']}]")
        else:
            print(result["message"])
        return

    # Otherwise run batch detection across all routes
    print("\nRunning Accident Hotspot Detection across Hyderabad Routes...\n")
    hotspots = detect_all_hotspots(save_csv=True)

    print(f"\nTop {args.top} Accident Hotspots\n")
    for _, row in hotspots.head(args.top).iterrows():
        print(f"Accident Hotspot #{row['hotspot_id']}")
        print(f"Route: {row['start_location']} -> {row['end_location']}")
        print(f"Accidents: {row['accidents']}")
        print(f"Risk: {row['risk']}")
        print(f"Average Risk: {row['average_risk']:.2f}%")
        print("-" * 40)


if __name__ == "__main__":
    main()
