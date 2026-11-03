"""Compare Muse Spark latency/quality across settings (P0-2).
Usage: python -m scripts.latency_test test-images/01_road_oneway.jpg [more.jpg ...]
Each image uses its centre as the tap (fallback crop), so only Spark settings vary."""
import json, statistics, sys, time, pathlib
from backend import meta_client as mc

CONFIGS = [  # (label, max_side, effort, send_full)
    ("1600 low full+crop", 1600, "low", True),
    ("1280 low full+crop", 1280, "low", True),
    ("1280 minimal full+crop", 1280, "minimal", True),
    ("1280 low crop-only", 1280, "low", False),
    ("1280 minimal crop-only", 1280, "minimal", False),
]
paths = [pathlib.Path(p) for p in sys.argv[1:]]
results = {c[0]: [] for c in CONFIGS}
for p in paths:
    raw = p.read_bytes()
    for label, side, effort, full in CONFIGS:
        img = mc.load_image(raw, side)
        region = mc.crop(img, mc.fallback_box(img, img.width // 2, img.height // 2))
        t = time.time()
        try:
            r = mc.explain(img if full else None, region, "ja", effort)
            dt = time.time() - t
            results[label].append(dt)
            print(f"{p.stem:28s} {label:24s} {dt:5.1f}s  {r['korean_text'][:20]!r:24s} "
                  f"conf={r['confidence']} narr={len(r['narration'])}ch bridge={r['native_bridge'][:30]!r}")
        except Exception as e:
            print(f"{p.stem:28s} {label:24s} ERROR {e}")
print()
for label, ts in results.items():
    if ts:
        print(f"{label:24s} median {statistics.median(ts):5.1f}s  max {max(ts):5.1f}s  n={len(ts)}")
