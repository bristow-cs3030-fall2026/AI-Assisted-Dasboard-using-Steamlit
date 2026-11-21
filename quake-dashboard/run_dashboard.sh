#!/usr/bin/env bash
# Download USGS data, build the Docker image, and run the dashboard.
set -euo pipefail   # stop on errors, unset variables, and failed pipes
 
URL="https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
IMAGE="quake-dashboard"
DATA_DIR="$(cd "$(dirname "$0")" && pwd)/data"
OUT="$DATA_DIR/all_day.geojson"
TMP="$OUT.tmp"
 
mkdir -p "$DATA_DIR"
 
echo "Downloading earthquake data..."
# -f fail on HTTP errors, -s quiet, -S still show errors, -L follow redirects
# --max-time / --max-filesize keep a bad download from hanging or filling the disk
curl -fsSL --max-time 30 --max-filesize 10485760 "$URL" -o "$TMP"
 
# Security practice: check data before you use it.
# Only replace the old file if the new one looks like real GeoJSON.
if [ ! -s "$TMP" ] || ! grep -q '"FeatureCollection"' "$TMP"; then
    echo "Error: downloaded file is empty or not GeoJSON. Keeping old data." >&2
    rm -f "$TMP"
    exit 1
fi
mv "$TMP" "$OUT"
# Make sure the non-root user inside the container can read the data
chmod 755 "$DATA_DIR"
chmod 644 "$OUT"
echo "Saved $OUT"
 
echo "Building Docker image..."
docker build -t "$IMAGE" "$(dirname "$0")"
 
echo "Starting dashboard at http://localhost:8501 (Ctrl+C to stop)"
# --rm   delete the container when it stops
# -v ... bind-mount data/ into the container; :ro makes it read-only
docker run --rm -p 127.0.0.1:8501:8501 -v "$DATA_DIR:/app/data:ro" "$IMAGE"
 
