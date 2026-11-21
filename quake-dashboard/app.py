"""Streamlit dashboard: today's earthquakes worldwide (USGS)."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_FILE = Path(__file__).parent / "data" / "all_day.geojson"
MAX_FILE_BYTES = 10 * 1024 * 1024  # refuse files bigger than 10 MB


def is_number(value):
    """True for real numbers only (bool is excluded on purpose)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def load_quakes(path):
    """Read and VALIDATE the GeoJSON file. Returns (DataFrame, skipped_count).

    Security practice: never trust data just because it came from a
    well-known website. Check it before using it.
    """
    # 1. Check the file itself
    if not path.is_file():
        raise ValueError("Data file not found. Run ./run_dashboard.sh first.")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Data file is unexpectedly large; refusing to load it.")

    # 2. Check it is valid JSON
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ValueError(f"Data file is not valid JSON: {err}")

    # 3. Check the overall structure
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise ValueError("Data file is not a GeoJSON FeatureCollection.")
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError("Data file has no 'features' list.")

    # 4. Check every record; skip the bad ones instead of crashing
    rows, skipped = [], 0
    for feature in features:
        try:
            props = feature["properties"]
            lon, lat, *rest = feature["geometry"]["coordinates"]
            depth = rest[0] if rest else None
            mag, time_ms = props["mag"], props["time"]

            if not (is_number(lon) and is_number(lat)):
                raise ValueError("coordinates are not numbers")
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError("coordinates out of range")
            if not (is_number(mag) and -2 <= mag <= 10):
                raise ValueError("magnitude missing or out of range")
            if not is_number(time_ms):
                raise ValueError("bad time")

            place = props.get("place")
            rows.append({
                "time (UTC)": datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc),
                "place": place if isinstance(place, str) else "Unknown",
                "magnitude": float(mag),
                "depth (km)": float(depth) if is_number(depth) else None,
                "lat": float(lat),
                "lon": float(lon),
            })
        except (KeyError, TypeError, ValueError, OSError, OverflowError):
            skipped += 1

    return pd.DataFrame(rows), skipped


st.set_page_config(page_title="Earthquakes Today", layout="wide")
st.title("🌍 Earthquakes in the Last 24 Hours")
st.caption("Source: USGS Earthquake Hazards Program")

try:
    df, skipped = load_quakes(DATA_FILE)
except ValueError as err:
    st.error(str(err))
    st.stop()

if skipped:
    st.warning(f"Skipped {skipped} record(s) that failed validation.")
if df.empty:
    st.info("No valid earthquakes found in the file.")
    st.stop()

min_mag = st.slider("Minimum magnitude", 0.0, 8.0, 0.0, 0.1)
shown = df[df["magnitude"] >= min_mag].sort_values("time (UTC)", ascending=False)

col1, col2, col3 = st.columns(3)
col1.metric("Earthquakes shown", len(shown))
col2.metric("Strongest", f"M {shown['magnitude'].max():.1f}" if len(shown) else "-")
col3.metric("Total in file", len(df))

if len(shown):
    # Bigger magnitude -> bigger dot (size is in meters on the map)
    map_df = shown.assign(size=(shown["magnitude"].clip(lower=0) + 1) ** 2 * 8000)
    st.map(map_df, latitude="lat", longitude="lon", size="size")
    st.dataframe(
        shown[["time (UTC)", "place", "magnitude", "depth (km)"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No earthquakes at or above that magnitude.")
