
import json
import time
from uuid import uuid4

import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Mission Planner", layout="wide")

# ---------------- Session state ----------------
if "waypoints" not in st.session_state:
    st.session_state.waypoints = []  # list of dicts: {"lat":..., "lon":...}
if "center" not in st.session_state:
    # Default center (Barcelona). Change if you like.
    st.session_state.center = (41.387, 2.170)
if "zoom" not in st.session_state:
    st.session_state.zoom = 14

# ---------------- Sidebar controls ----------------
st.sidebar.title("Mission Controls")

# Mission parameters (affect JSON only)
mission_id = st.sidebar.text_input("Mission ID", value=str(uuid4())[:8])
default_speed = st.sidebar.number_input("Default speed (m/s)", min_value=0.0, value=1.0, step=0.1)
loop_flag = st.sidebar.checkbox("Loop mission", value=False)

# Import/export
uploaded = st.sidebar.file_uploader("Import waypoints (GeoJSON or JSON)", type=["json", "geojson"])
if uploaded is not None:
    try:
        data = json.load(uploaded)
        # Accept either our mission format or plain FeatureCollection/coordinates
        new_wps = []
        if isinstance(data, dict) and "waypoints" in data:
            for wp in data["waypoints"]:
                new_wps.append({"lat": float(wp["lat"]), "lon": float(wp["lon"])})  # noqa: E501
        elif isinstance(data, dict) and data.get("type") == "FeatureCollection":
            # Pull any Point coordinates
            for feat in data.get("features", []):
                if feat.get("geometry", {}).get("type") == "Point":
                    lon, lat = feat["geometry"]["coordinates"][:2]
                    new_wps.append({"lat": float(lat), "lon": float(lon)})
        elif isinstance(data, dict) and data.get("type") == "LineString":
            for lon, lat in data.get("coordinates", []):
                new_wps.append({"lat": float(lat), "lon": float(lon)})
        else:
            st.sidebar.warning("Unrecognized format. Expect mission JSON or GeoJSON.")
            new_wps = []
        if new_wps:
            st.session_state.waypoints = new_wps
            st.success(f"Imported {len(new_wps)} waypoints.")
    except Exception as e:
        st.sidebar.error(f"Import failed: {e}")

col_a, col_b, col_c, col_d = st.sidebar.columns(4)
if col_a.button("Undo"):
    if st.session_state.waypoints:
        st.session_state.waypoints.pop()

if col_b.button("Clear"):
    st.session_state.waypoints = []

# ---------------- Map & interaction ----------------
st.title("🗺️ Mission Planner (Click to add waypoints)")

# Build Folium map
m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom, control_scale=True)
folium.TileLayer("OpenStreetMap").add_to(m)

# Add existing waypoint markers and polyline BEFORE rendering
if st.session_state.waypoints:
    latlngs = [(wp["lat"], wp["lon"]) for wp in st.session_state.waypoints]
    for i, (lat, lon) in enumerate(latlngs, start=1):
        folium.Marker(
            location=(lat, lon),
            tooltip=f"WP {i}",
            icon=folium.Icon(color="blue", icon="flag")
        ).add_to(m)
    # Solid line for planned route
    folium.PolyLine(latlngs, weight=4, opacity=0.9).add_to(m)
    # Dashed duplicate line to compare visually
    folium.PolyLine(latlngs, weight=3, opacity=0.9, dash_array="6,6").add_to(m)

# Optional: popup on click for debugging
folium.LatLngPopup().add_to(m)

# Render map and capture clicks (IMPORTANT: request last_clicked)
out = st_folium(
    m,
    width=None,
    height=650,
    returned_objects=["last_clicked"],  # <-- this enables click capture
    key="mission_map",
)

# Handle click → add waypoint
if out and out.get("last_clicked"):
    lat = out["last_clicked"]["lat"]
    lon = out["last_clicked"]["lng"]
    # Avoid duplicate if user double-clicks quickly
    if not st.session_state.waypoints or (
        st.session_state.waypoints[-1]["lat"] != lat or st.session_state.waypoints[-1]["lon"] != lon
    ):
        st.session_state.waypoints.append({"lat": lat, "lon": lon})
        st.rerun()  # immediately re-render to show the new marker/line

# ---------------- Mission generation ----------------
st.subheader("Waypoints")
st.caption("Click on the map to add points. Use **Undo** or **Clear** in the sidebar to edit.")
if st.session_state.waypoints:
    st.dataframe(st.session_state.waypoints, use_container_width=True)
else:
    st.write("No waypoints yet.")

def build_mission_json():
    return {
        "mission_id": mission_id,
        "created_at": int(time.time()),
        "frame": "WGS84",
        "waypoints": [
            {"lat": wp["lat"], "lon": wp["lon"], "speed_mps": default_speed}
            for wp in st.session_state.waypoints
        ],
        "loop": loop_flag,
    }

st.divider()
left, right = st.columns([1,1], vertical_alignment="center")

with left:
    if st.button("Generate Mission JSON", type="primary", use_container_width=True, disabled=not st.session_state.waypoints):
        st.session_state.generated = json.dumps(build_mission_json(), indent=2)

with right:
    if st.session_state.waypoints:
        mission_bytes = json.dumps(build_mission_json(), indent=2).encode("utf-8")
        st.download_button(
            "Download Mission JSON",
            data=mission_bytes,
            file_name=f"mission_{mission_id}.json",
            mime="application/json",
            use_container_width=True
        )

# Show generated JSON preview
if "generated" in st.session_state:
    st.subheader("Preview")
    st.code(st.session_state.generated, language="json")
