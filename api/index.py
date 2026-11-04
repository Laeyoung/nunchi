"""Vercel entry point.
Live analysis runs only when the Vercel project sets LIVE=1 and MODEL_API_KEY; otherwise the demo is cache-only.
The filesystem is read-only except /tmp, so new results and the spend ledger go to /tmp/nunchi (per instance,
temporary). Vercel sets x-real-ip, so the per-IP rate limit uses it."""
import os, sys

if not os.environ.get("MODEL_API_KEY"):
    os.environ["LIVE"] = "0"
os.environ.setdefault("LIVE", "0")
os.environ.setdefault("WRITE_DIR", "/tmp/nunchi")
os.environ.setdefault("TRUST_PROXY", "1")
# The spend ledger lives in /tmp, so the budget guard is per instance: keep each instance's cap small.
# Account-wide protection is the spend limit / card on the Meta billing page.
os.environ.setdefault("BUDGET_USD", "5")
os.environ.setdefault("PRIOR_SPEND_USD", "0")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app  # noqa: E402,F401
