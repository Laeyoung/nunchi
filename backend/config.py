"""Single place for names and tunables. Change APP_NAME to rename the app everywhere."""
import os, pathlib

from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")  # also accept the key one level up (outside the repo)

APP_NAME = os.environ.get("APP_NAME", "Nunchi")
APP_NAME_KO = os.environ.get("APP_NAME_KO", "눈치")
APP_TAGLINE = "찍으면 들리는 한국"

BASE_URL = "https://api.meta.ai/v1"
SPARK_MODEL = os.environ.get("SPARK_MODEL", "muse-spark-1.3")
SAM_MODEL = "sam-3.1"
SPARK_EFFORT = os.environ.get("SPARK_EFFORT", "minimal")       # minimal | low | ...
MAX_SIDE = int(os.environ.get("MAX_SIDE", "1280"))         # longest image side sent to the models
SEND_FULL = os.environ.get("SEND_FULL", "1") == "1"        # send full photo + crop (1) or crop only (0)
REQUEST_TIMEOUT_S = float(os.environ.get("REQUEST_TIMEOUT_S", "20"))  # Muse Spark, total incl. hedge
HEDGE_S = float(os.environ.get("HEDGE_S", "9"))  # send a duplicate Spark request if the first is slower
MORE_TIMEOUT_S = float(os.environ.get("MORE_TIMEOUT_S", "25"))  # "Tell me more" (web search)
SAM_TIMEOUT_S = float(os.environ.get("SAM_TIMEOUT_S", "8"))  # SAM point failure falls back to a fixed crop

# SAM point result is rejected (-> fixed-size crop around the tap) when:
SAM_MIN_AREA = 0.02    # box smaller than 2% of the image
SAM_MAX_AREA = 0.80    # box larger than 80% of the image
SAM_MIN_CONF = 0.40    # confidence below this
FALLBACK_CROP = 0.35   # fallback crop side = 35% of the image's short side

# Abuse limits (the app has no login; keep public deployments cheap)
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 40_000_000            # reject decompression bombs before decoding
RATE_PER_MIN = int(os.environ.get("RATE_PER_MIN", "20"))   # live model calls per client IP per minute
LIVE = os.environ.get("LIVE", "1") == "1"  # 0 = serve cached results only (public demo link)
