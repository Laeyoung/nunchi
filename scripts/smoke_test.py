"""Run first: confirms the API key works from Korea for Muse Spark (image + strict JSON) and SAM 3.1 (point prompt).
Usage: MODEL_API_KEY=... python -m scripts.smoke_test ../test-images/01_road_oneway.jpg"""
import json, sys, time, pathlib
from backend import meta_client as mc

path = pathlib.Path(sys.argv[1])
img = mc.load_image(path.read_bytes())
print("image", img.size)

t = time.time(); box = mc.sam_point(img, img.width // 2, img.height // 2)
print(f"[SAM point] {time.time()-t:.1f}s ->", box)

t = time.time(); res = mc.explain(img, mc.crop(img, box) if box else None, "ja")
print(f"[Muse Spark] {time.time()-t:.1f}s")
print(json.dumps(res, ensure_ascii=False, indent=2))
