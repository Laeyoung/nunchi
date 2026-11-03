import collections, hashlib, json, logging, math, time
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config as cfg
from . import meta_client as mc
from .prompts import LANG_NAMES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("nunchi")

CACHE = cfg.ROOT / "cache"
CACHE.mkdir(exist_ok=True)
app = FastAPI(title=cfg.APP_NAME)
_regions: "collections.OrderedDict[str, dict]" = collections.OrderedDict()  # (image, tap) -> box; LRU
_REGIONS_MAX = 500
_calls: dict[str, collections.deque] = collections.defaultdict(collections.deque)


def _remember_region(key: str, box: dict):
    _regions[key] = box
    _regions.move_to_end(key)
    while len(_regions) > _REGIONS_MAX:
        _regions.popitem(last=False)


def _gate(request: Request) -> JSONResponse | None:
    """Before any live model call: live mode on and per-IP rate limit not exceeded."""
    if not cfg.LIVE:
        return JSONResponse({"error": "offline"}, status_code=503)
    ip = request.client.host if request.client else "?"
    now, q = time.time(), _calls[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= cfg.RATE_PER_MIN:
        return JSONResponse({"error": "rate_limited"}, status_code=429)
    q.append(now)
    return None


def _bad(msg: str) -> JSONResponse:
    return JSONResponse({"error": "bad_request", "detail": msg}, status_code=400)


def _key(*parts) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:24]


def _fail(e: Exception, where: str) -> JSONResponse:
    timeout = "timeout" in type(e).__name__.lower() or "timed out" in str(e).lower()
    log.warning("%s failed: %s: %s", where, type(e).__name__, str(e)[:200])
    return JSONResponse({"error": "timeout" if timeout else "upstream"}, status_code=504 if timeout else 502)


@app.get("/api/config")
def config():
    return {"name": cfg.APP_NAME, "tagline": cfg.APP_TAGLINE}


def _seg_path(digest: str):
    return CACHE / f"seg_{_key(digest, cfg.MAX_SIDE)}.json"


def _segment_box(digest: str, img, nx: float, ny: float) -> dict | None:
    """Smallest highlighted candidate box that contains the tap (if /api/segment already ran)."""
    p = _seg_path(digest)
    if not p.exists():
        return None
    x, y = nx * img.width, ny * img.height
    hits = [b for b in json.loads(p.read_text())["boxes"]
            if b["x1"] <= x <= b["x2"] and b["y1"] <= y <= b["y2"]]
    return min(hits, key=lambda b: (b["x2"] - b["x1"]) * (b["y2"] - b["y1"])) if hits else None


DEMO = json.loads((cfg.ROOT / "backend" / "demo.json").read_text())
DEMO_FILES = {p["file"] for p in DEMO["photos"]}


@app.get("/api/demo")
def demo():
    return DEMO


@app.get("/demo-images/{name}")
def demo_image(name: str):
    if name not in DEMO_FILES:  # only licensed demo photos are served
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(cfg.ROOT / "test-images" / name, media_type="image/jpeg")


@app.post("/api/segment")
async def segment(request: Request, image: UploadFile = File(...)):
    raw = await image.read(cfg.MAX_UPLOAD_BYTES + 1)
    cached = _seg_path(hashlib.sha256(raw).hexdigest())
    if cached.exists():
        return json.loads(cached.read_text())
    if (blocked := _gate(request)):
        return blocked
    try:
        img = mc.load_image(raw)
    except Exception:
        return _bad("unreadable or too large image")
    t = time.time()
    try:
        boxes = mc.sam_concept(img, "sign")
    except Exception as e:
        return _fail(e, "segment")
    out = {"width": img.width, "height": img.height, "boxes": boxes}
    log.info("segment boxes=%d sam_s=%.2f", len(boxes), time.time() - t)
    cached.write_text(json.dumps(out))
    return out


@app.post("/api/explain")
async def explain(request: Request, image: UploadFile = File(...), lang: str = Form("ja"),
                  nx: float | None = Form(None), ny: float | None = Form(None)):
    """nx, ny: tap position normalized 0-1 on the displayed photo.
    If the tap is inside a /api/segment candidate box, that box is used and the SAM point call is skipped."""
    raw = await image.read(cfg.MAX_UPLOAD_BYTES + 1)
    if lang not in LANG_NAMES:
        return _bad("unsupported lang")
    if (nx is None) != (ny is None) or (nx is not None and not all(
            math.isfinite(v) and 0 <= v <= 1 for v in (nx, ny))):
        return _bad("nx, ny must both be in [0, 1]")
    digest = hashlib.sha256(raw).hexdigest()
    if nx is not None and ny is not None:
        nx, ny = round(nx, 3), round(ny, 3)
    tap_id = (nx, ny)
    key = _key(digest, lang, tap_id, cfg.MAX_SIDE)
    cached = CACHE / f"{key}.json"
    if cached.exists():  # demo safety net: replay when the network fails
        return json.loads(cached.read_text()) | {"cached": True}

    if (blocked := _gate(request)):
        return blocked
    try:
        img = mc.load_image(raw)
    except Exception:
        return _bad("unreadable or too large image")
    t0 = time.time()
    region_box, sam_source = None, "none"
    rkey = _key(digest, tap_id, cfg.MAX_SIDE)
    try:
        given = _segment_box(digest, img, nx, ny) if nx is not None and ny is not None else None
        if given:
            region_box, sam_source = given, "segment"
        elif rkey in _regions:
            region_box, sam_source = _regions[rkey], "memo"
        elif nx is not None and ny is not None:
            px, py = int(nx * img.width), int(ny * img.height)
            try:
                found = mc.sam_point(img, px, py)
            except Exception as e:  # SAM down -> keep going with a fixed crop
                log.warning("sam_point failed, using fallback crop: %s", e)
                found = None
            if mc.box_usable(img, found) or (found and mc.box_area(img, found) > cfg.SAM_MAX_AREA):
                region_box, sam_source = found, "sam_point"
            else:
                region_box, sam_source = mc.fallback_box(img, px, py), "fallback"
                if found:
                    log.info("sam_point rejected box=%s", found)
            _remember_region(rkey, region_box)
        t1 = time.time()
        # A box covering most of the photo adds nothing over the photo itself: send the photo only.
        whole = region_box is not None and mc.box_area(img, region_box) > cfg.SAM_MAX_AREA
        region = mc.crop(img, region_box) if region_box and not whole else None
        full = img if (cfg.SEND_FULL or region is None) else None
        result = mc.explain_hedged(full, region, lang)
    except Exception as e:
        return _fail(e, "explain")
    timing = {"sam_s": round(t1 - t0, 2), "spark_s": round(time.time() - t1, 2),
              "total_s": round(time.time() - t0, 2)}
    log.info("explain lang=%s region=%s %s", lang, sam_source, timing)
    out = {"box": region_box, "region_source": sam_source, "image_size": [img.width, img.height],
           "result": result, "timing": timing}
    cached.write_text(json.dumps(out, ensure_ascii=False))
    return out


app.mount("/", StaticFiles(directory=cfg.ROOT / "frontend", html=True), name="frontend")
