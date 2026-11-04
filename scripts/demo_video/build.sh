#!/bin/sh
# Rebuild the demo video from the live app's cached results (no model calls when the server runs with LIVE=0).
# Needs: macOS (`say` voices Daniel / Kyoko / Samantha), ffmpeg, and `pip install playwright httpx pillow && playwright install chromium`.
# Run the app first:  LIVE=0 .venv/bin/uvicorn backend.app:app --port 8000, plus a LIVE=1 server for the own-photo scene (APP=http://localhost:8002); it makes ~2 model calls (about $0.02).
set -e
HERE=$(cd "$(dirname "$0")" && pwd); export OUT=${OUT:-$HERE/out}; mkdir -p "$OUT"
cp "$HERE/stage.html" "$HERE/lines.json" "$OUT/"
python "$HERE/prepare.py"
python -m http.server 8765 --bind 127.0.0.1 --directory "$OUT" >/dev/null 2>&1 & SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
sleep 1; python "$HERE/record.py"
python "$HERE/mux.py" "$OUT"; echo "-> $OUT/nunchi-demo.mp4"
