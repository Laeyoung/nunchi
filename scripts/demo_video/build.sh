#!/bin/sh
# Rebuild the demo video from the live app's cached results (no model calls when the server runs with LIVE=0).
# Needs: macOS (`say` voices Daniel / Kyoko / Samantha), ffmpeg, and `pip install playwright httpx && playwright install chromium`.
# Run the app first:  LIVE=0 .venv/bin/uvicorn backend.app:app --port 8000
set -e
HERE=$(cd "$(dirname "$0")" && pwd); export OUT=${OUT:-$HERE/out}; mkdir -p "$OUT"
cp "$HERE/stage.html" "$HERE/lines.json" "$OUT/"
python "$HERE/prepare.py"
(cd "$OUT" && python -m http.server 8765 --bind 127.0.0.1 >/dev/null 2>&1 & echo $! > "$OUT/http.pid")
sleep 1; python "$HERE/record.py"; kill "$(cat "$OUT/http.pid")"
python "$HERE/mux.py" "$OUT"; echo "-> $OUT/nunchi-demo.mp4"
