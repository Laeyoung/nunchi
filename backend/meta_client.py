import base64, io, json, logging, re, time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from openai import OpenAI
from PIL import Image, ImageOps

from . import config as cfg, usage
from .schema import EXPLAIN_SCHEMA
from .prompts import SYSTEM, user_prompt

log = logging.getLogger("nunchi.api")
_client: OpenAI | None = None


def client() -> OpenAI:
    """Created lazily so the server can start (and serve cached demo results) without a key."""
    global _client
    if _client is None:
        import os
        key = os.environ.get("MODEL_API_KEY")
        if not key:
            raise RuntimeError("MODEL_API_KEY is not set (put it in app/.env)")
        _client = OpenAI(base_url=cfg.BASE_URL, api_key=key, timeout=cfg.REQUEST_TIMEOUT_S, max_retries=0)
    return _client


def load_image(raw: bytes, max_side: int | None = None) -> Image.Image:
    """Apply EXIF rotation (SAM coordinates must match the displayed image) and downscale."""
    if len(raw) > cfg.MAX_UPLOAD_BYTES:
        raise ValueError("image too large")
    img = Image.open(io.BytesIO(raw))
    if img.width * img.height > cfg.MAX_PIXELS:
        raise ValueError("image has too many pixels")
    side = max_side or cfg.MAX_SIDE
    img.draft("RGB", (side, side))  # JPEG: decode at reduced scale (no-op for other formats)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((side, side))
    return img


def to_data_url(img: Image.Image, quality: int = 85) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


BOX_RE = re.compile(r"(\d+)<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)(?:;c=([\d.]+))?\|>")


def parse_boxes(text: str) -> list[dict]:
    boxes = []
    for m in BOX_RE.finditer(text or ""):
        oid, x1, y1, x2, y2, w, h, c = m.groups()
        boxes.append({"id": int(oid), "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2),
                      "w": int(w), "h": int(h), "conf": float(c) if c else None})
    return boxes


def _sam(img: Image.Image, prompt_text: str) -> list[dict]:
    usage.check()
    t = time.time()
    resp = client().with_options(timeout=cfg.SAM_TIMEOUT_S).responses.create(
        model=cfg.SAM_MODEL,
        input=[{"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": prompt_text},
            {"type": "input_image", "image_url": to_data_url(img)},
        ]}],
        metadata={"include_confidence": "true", "mask_encoding": "one_bit"},
    )
    usage.record_sam()
    log.info("model=%s latency=%.2fs", cfg.SAM_MODEL, time.time() - t)
    return parse_boxes(resp.output_text)


def sam_concept(img: Image.Image, concept: str = "sign") -> list[dict]:
    """Highlight candidates. One noun phrase per request (SAM 3.1 rule)."""
    return _sam(img, concept)


def sam_point(img: Image.Image, x: int, y: int) -> dict | None:
    """Segment the object the user tapped. x, y in pixels of `img`."""
    w, h = img.size
    x, y = max(0, min(w - 1, x)), max(0, min(h - 1, y))
    boxes = _sam(img, f"<0f>1<|point;x={x};y={y};w={w};h={h}|>")
    return boxes[0] if boxes else None


def box_area(img: Image.Image, box: dict) -> float:
    return (box["x2"] - box["x1"]) * (box["y2"] - box["y1"]) / (img.width * img.height)


def box_usable(img: Image.Image, box: dict | None) -> bool:
    if not box:
        return False
    area = box_area(img, box)
    if area < cfg.SAM_MIN_AREA or area > cfg.SAM_MAX_AREA:
        return False
    return box.get("conf") is None or box["conf"] >= cfg.SAM_MIN_CONF


def fallback_box(img: Image.Image, x: int, y: int) -> dict:
    """Fixed-size square around the tap, shifted to stay inside the image."""
    s = int(min(img.size) * cfg.FALLBACK_CROP)
    x1 = max(0, min(img.width - s, x - s // 2))
    y1 = max(0, min(img.height - s, y - s // 2))
    return {"id": 0, "x1": x1, "y1": y1, "x2": x1 + s, "y2": y1 + s,
            "w": img.width, "h": img.height, "conf": None, "fallback": True}


def crop(img: Image.Image, box: dict, pad: float = 0.08) -> Image.Image:
    bw, bh = box["x2"] - box["x1"], box["y2"] - box["y1"]
    return img.crop((max(0, box["x1"] - int(bw * pad)), max(0, box["y1"] - int(bh * pad)),
                     min(img.width, box["x2"] + int(bw * pad)), min(img.height, box["y2"] + int(bh * pad))))


def explain(img: Image.Image | None, region: Image.Image | None, lang: str,
            effort: str | None = None) -> dict:
    """img: full photo for context (None = crop only). region: tapped crop (None = whole photo)."""
    content = [{"type": "text", "text": user_prompt(lang, has_full=img is not None, has_crop=region is not None)}]
    for im in (img, region):
        if im is not None:
            content.append({"type": "image_url", "image_url": {"url": to_data_url(im)}})
    usage.check()
    t = time.time()
    resp = client().chat.completions.create(
        model=cfg.SPARK_MODEL,
        reasoning_effort=effort or cfg.SPARK_EFFORT,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "SignExplanation", "strict": True, "schema": EXPLAIN_SCHEMA}},
    )
    usd = usage.record_spark(cfg.SPARK_MODEL, resp.usage)
    log.info("model=%s effort=%s latency=%.2fs out_tokens=%s usd=%.4f total_usd=%.2f", cfg.SPARK_MODEL,
             effort or cfg.SPARK_EFFORT, time.time() - t, getattr(resp.usage, "completion_tokens", None), usd,
             usage.total())
    return json.loads(resp.choices[0].message.content)


_pool = ThreadPoolExecutor(8)


def explain_hedged(img, region, lang: str, effort: str | None = None) -> dict:
    """Muse Spark latency has a long tail. If the first call is slower than HEDGE_S, fire an identical
    second call and return whichever finishes first (successful) within REQUEST_TIMEOUT_S."""
    deadline = time.time() + cfg.REQUEST_TIMEOUT_S
    futs = [_pool.submit(explain, img, region, lang, effort)]
    done, _ = wait(futs, timeout=cfg.HEDGE_S)
    if not done:
        log.info("spark slower than %.0fs, sending hedge request", cfg.HEDGE_S)
        futs.append(_pool.submit(explain, img, region, lang, effort))
    errors = []
    pending = set(futs)
    while pending and time.time() < deadline:
        done, pending = wait(pending, timeout=max(0, deadline - time.time()), return_when=FIRST_COMPLETED)
        for f in done:
            if f.exception() is None:
                return f.result()
            errors.append(f.exception())
    if errors and not pending:
        raise errors[0]
    raise TimeoutError("Muse Spark request timed out")
