# Nunchi · 찍으면 들리는 한국

Point your phone at any Korean sign, menu or notice, tap the text, and hear — in your own language —
what it says, **why it is there**, and **what you should do now**, plus a fun link to your native language
(e.g. 일방통행 = 一方通行 for Japanese travellers).

Translation apps change the letters. Nunchi explains the place.

## How it works
1. **SAM 3.1** (point prompt) segments the exact sign you tapped.
2. **Muse Spark 1.3** reads the full photo + the cropped sign and returns a strict-JSON explanation
   (reading, meaning, why here, what to do, native-language bridge, 30-second narration).
3. The browser speaks the narration (Web Speech API) and the original Korean.

## Run
```bash
uv venv --python 3.12 .venv && uv pip install -r requirements.txt   # or: python -m venv .venv && pip install -r requirements.txt
cp .env.example .env                 # put your dev.meta.ai key in MODEL_API_KEY
.venv/bin/python -m scripts.smoke_test test-images/01_road_oneway.jpg   # 1) verify API access
.venv/bin/python -m scripts.warm_cache ja en                             # 2) pre-fill demo results + regression check
.venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8000             # 3) open http://localhost:8000
```
- `http://localhost:8000/?demo=1` — demo mode: a grid of test photos; taps snap to preset points so cached results replay instantly, even offline.
- `?lang=ja|en|zh` picks the language from the URL.

### On a phone (HTTPS is required for the camera)
```bash
cloudflared tunnel --url http://localhost:8000     # prints https://<random>.trycloudflare.com
```
Open the printed URL in iPhone Safari. Narration uses the device voices (best on iOS/macOS: Kyoko / O-ren for Japanese, Samantha for English, Yuna for Korean).

### Tuning (env vars)
| var | default | meaning |
|---|---|---|
| `SPARK_EFFORT` | `minimal` | Muse Spark `reasoning_effort` |
| `MAX_SIDE` | `1280` | longest image side sent to the models |
| `SEND_FULL` | `1` | send full photo + tapped crop (`0` = crop only) |
| `HEDGE_S` / `REQUEST_TIMEOUT_S` | `9` / `20` | duplicate a slow Spark request after 9 s; give up after 20 s |
| `APP_NAME` | `Nunchi` | app name shown in the UI |

### Scripts
- `scripts/latency_test.py` — compares effort / image size / crop-only settings.
- `scripts/batch_test.py test-images ja en` — whole-photo explanation for every image → `report.html` for human review + keyword check against `scripts/expectations.json`.
- `scripts/warm_cache.py` — fills `cache/` for every demo photo × preset tap × language through the real endpoints and checks `korean_text` against `scripts/expectations.json`.

## How a tap is resolved
1. On upload, `/api/segment` asks SAM 3.1 for the concept `sign`; candidates are drawn faintly.
2. A tap inside a candidate uses that box directly (no extra SAM call).
3. Otherwise SAM 3.1 gets a point prompt. If it returns nothing, a box under 2% of the image, or confidence < 0.4,
   a fixed square around the tap (35% of the short side) is used instead.
4. A box covering more than 80% of the photo is not cropped: Muse Spark just gets the photo.

## Notes
- Muse Wonder is not available in South Korea, so everything runs on Muse Spark 1.3.
- Meta Model API has no text-to-speech; speech uses the browser.
- `reasoning_effort=minimal` cut Muse Spark latency from ~14 s to ~8 s with no visible quality loss on the test set; `low` regularly hit 15 s.
- SAM 3.1 point prompts on small signs often return a tiny fragment with low confidence (e.g. conf 0.23), hence the fallback rules above.
- SAM 3.1 concept prompts take one noun phrase per request: `sign` works, `sign, text` returns nothing.
- Results are cached in `cache/` so the demo replays even if the network drops. Uploaded photos are never stored; logs keep only timing.
- Test photos: openly licensed, see `test-images/sources.csv` for authors and licenses. Photo 12 is excluded (license unconfirmed).
