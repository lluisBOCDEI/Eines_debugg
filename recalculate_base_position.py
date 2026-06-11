import math
import re
import pandas as pd

# ── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_CSV  = "coordenades_29-05_17-56.csv"   # path to your original CSV
OUTPUT_CSV = "coordenades_recalculated.csv"  # path for the new CSV

DISTANCE = 1.0   # <-- SET YOUR FIXED DISTANCE HERE (metres)
# ─────────────────────────────────────────────────────────────────────────────


def extract_yaw(vector3_str: str) -> float:
    """Extract the x value from a geometry_msgs Vector3 string.
    The yaw is stored in the x field: Vector3(x=<yaw>, y=0.0, z=0.0)
    """
    match = re.search(r"x=([-\d.eE+]+)", str(vector3_str))
    return float(match.group(1)) if match else float("nan")

def calculate_new_coordinates(lon, lat, angle, distance):
    """Compute a new (lon, lat) given a starting point, bearing and distance."""
    lat      = math.radians(lat)
    lon      = math.radians(lon)
    angle    = math.radians(angle)
    earth_radius = 6371000  # metres

    new_lat = math.asin(
        math.sin(lat) * math.cos(distance / earth_radius)
        + math.cos(lat) * math.sin(distance / earth_radius) * math.cos(angle)
    )
    new_lon = lon + math.atan2(
        math.sin(angle) * math.sin(distance / earth_radius) * math.cos(lat),
        math.cos(distance / earth_radius) - math.sin(lat) * math.sin(new_lat),
    )

    return math.degrees(new_lon), math.degrees(new_lat)

def main():
    df = pd.read_csv(INPUT_CSV)

    # Extract yaw (stored in the x field of the yaw_error Vector3 string)
    df["yaw"] = df["yaw_error"].apply(extract_yaw)

    # Recalculate base position row by row
    new_lons, new_lats = [], []
    for _, row in df.iterrows():
        new_lon, new_lat = calculate_new_coordinates(
            lon      = row["Lon_gps"],
            lat      = row["Lat gps"],
            angle    = row["yaw"],
            distance = DISTANCE,
        )
        new_lons.append(new_lon)
        new_lats.append(new_lat)

    df["Lat_base_new"] = new_lats
    df["Lon_base_new"] = new_lons

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Done! Saved {len(df)} rows to '{OUTPUT_CSV}'")
    print(df[["Lat gps", "Lon_gps", "yaw", "Lat_base_new", "Lon_base_new"]].head(10).to_string())


if __name__ == "__main__":
    main()
