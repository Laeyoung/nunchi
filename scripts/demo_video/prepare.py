"""Fetch cached demo results, write photo credits, and synthesize voice clips (macOS `say`) into $OUT."""
import csv, json, os, subprocess, httpx
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.environ["OUT"]; os.makedirs(f"{OUT}/data", exist_ok=True); os.makedirs(f"{OUT}/audio", exist_ok=True)
for f, lang, x, y in [("01_road_oneway.jpg", "ja", .48, .36), ("15_food_menu.jpg", "ja", .5, .55),
                      ("19_daily_toilet.jpg", "ja", .33, .45), ("19_daily_toilet.jpg", "en", .33, .45)]:
    r = httpx.post("http://localhost:8000/api/explain", files={"image": open(f"{ROOT}/test-images/{f}", "rb")},
                   data={"lang": lang, "nx": x, "ny": y}, timeout=40)
    r.raise_for_status(); json.dump(r.json(), open(f"{OUT}/data/{f[:2]}_{lang}.json", "w"), ensure_ascii=False)
# A phone-sized library photo for the own-photo scene: 4032x3024, stored sideways with EXIF orientation 6,
# so the in-browser resize (EXIF upright, 1600 px) does real work and the request misses the sample cache.
from PIL import Image
im = Image.open(f"{ROOT}/test-images/08_safety_slippery.jpg").convert("RGB").resize((4032, 3024), Image.LANCZOS)
exif = Image.Exif(); exif[0x0112] = 6
im.rotate(90, expand=True).save(f"{OUT}/phone_photo.jpg", quality=92, exif=exif.tobytes())
rows = [r for r in csv.DictReader(open(f"{ROOT}/test-images/sources.csv")) if not r["filename"].startswith("12")]
open(f"{OUT}/credits.txt", "w").write(" · ".join(f'{r["filename"][:2]} {r["author"].splitlines()[0]} ({r["license"] or "see sources.csv"})' for r in rows))
for k, t in json.load(open(f"{HERE}/lines.json")).items():
    subprocess.run(["say", "-v", "Daniel", "-r", "182", "-o", f"{OUT}/audio/{k}.aiff", t], check=True)
for k, (v, f) in {"a01": ("Kyoko", "01_ja"), "a15": ("Kyoko", "15_ja"), "a19": ("Kyoko", "19_ja"), "a19en": ("Samantha", "19_en")}.items():
    subprocess.run(["say", "-v", v, "-o", f"{OUT}/audio/{k}.aiff", json.load(open(f"{OUT}/data/{f}.json"))["result"]["narration"]], check=True)
