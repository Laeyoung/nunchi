"""Fill cache/ for demo mode: every demo photo x preset tap x language, through the real API endpoints
(same code path and cache keys as the app). Re-running only calls the API for missing entries.
Also pre-fetches the "Tell me more" (web search) result for each, unless --no-more.
Usage: python -m scripts.warm_cache [ja en] [--no-more]"""
import json, pathlib, sys, time
from fastapi.testclient import TestClient
from backend.app import app, DEMO, CACHE

args = [a for a in sys.argv[1:] if not a.startswith("--")]
langs = args or DEMO["langs"]
expect = json.loads((pathlib.Path(__file__).parent / "expectations.json").read_text())
api = TestClient(app)
fails = 0
for photo in DEMO["photos"]:
    path = pathlib.Path("test-images") / photo["file"]
    raw = path.read_bytes()
    seg = api.post("/api/segment", files={"image": (path.name, raw, "image/jpeg")})
    nseg = len(seg.json().get("boxes", [])) if seg.is_success else f"ERR {seg.status_code}"
    for nx, ny in photo["taps"]:
        for lang in langs:
            t = time.time()
            r = api.post("/api/explain", files={"image": (path.name, raw, "image/jpeg")},
                         data={"lang": lang, "nx": nx, "ny": ny})
            if not r.is_success:
                fails += 1
                print(f"FAIL {path.stem:32s} {lang} HTTP {r.status_code} {r.text[:120]}")
                continue
            d = r.json(); res = d["result"]
            kws = expect.get(path.stem, [])
            ok = not kws or any(k.replace(" ", "") in res["korean_text"].replace(" ", "") for k in kws)
            fails += not ok
            if "--no-more" not in sys.argv and res["korean_text"]:
                m = api.post("/api/more", data={"korean_text": res["korean_text"], "meaning": res["meaning"], "lang": lang})
                mj = m.json() if m.is_success else {}
                if not mj.get("text"):
                    fails += 1
                    print(f"FAIL {path.stem:32s} {lang} more HTTP {m.status_code}")
                elif not mj.get("cached"):
                    print(f"     {path.stem:32s} {lang} more sources={len(mj.get('sources', []))}")
            print(f"{'ok  ' if ok else 'MISS'} {path.stem:32s} {lang} seg={nseg} region={d.get('region_source'):9s} "
                  f"{'cached' if d.get('cached') else f'{time.time()-t:4.1f}s'} conf={res['confidence']:6s} "
                  f"{res['korean_text'][:30]!r}")
print(f"\n{fails} problem(s)")
sys.exit(1 if fails else 0)
