"""Spend tracking. Meta's API has no credit-balance endpoint, so every model call is appended to
usage/usage.jsonl with an estimated cost (prices from dev.meta.ai/docs/pricing-rate-limits, 2026-11-03).
Live calls are refused once estimated spend reaches BUDGET_USD."""
import json, os, threading, time

from . import config as cfg

PRICES = {  # USD
    "muse-spark-1.3": {"in": 1.25e-6, "cached_in": 0.15e-6, "out": 4.25e-6},
    "sam-3.1": {"image": 2.50e-3},
    "web_search": {"query": 2.50e-3},
}
PRIOR_SPEND_USD = float(os.environ.get("PRIOR_SPEND_USD", "3.0"))  # estimate of spend before the ledger existed
BUDGET_USD = float(os.environ.get("BUDGET_USD", "50"))

LEDGER = cfg.ROOT / "usage" / "usage.jsonl"
try:
    LEDGER.parent.mkdir(exist_ok=True)
except OSError:  # read-only filesystem (cache-only hosting); record() is never reached with LIVE=0
    pass
_lock = threading.Lock()
_total: float | None = None


# Charged when a call fails or reports no usage: the API may still bill a request we gave up on.
FAILED_CALL_USD = {"spark": 0.01, "more": 0.02, "sam": PRICES["sam-3.1"]["image"]}


class BudgetExceeded(RuntimeError):
    pass


def total() -> float:
    global _total
    if _total is None:
        _total = PRIOR_SPEND_USD
        if LEDGER.exists():
            for line in LEDGER.read_text().splitlines():
                if line.strip():
                    _total += json.loads(line)["usd"]
    return _total


def check():
    if total() >= BUDGET_USD:
        raise BudgetExceeded(f"estimated spend ${total():.2f} reached budget ${BUDGET_USD:.0f}")


def record(model: str, usd: float, **detail):
    global _total
    with _lock:
        total()
        _total += usd
        with LEDGER.open("a") as f:
            f.write(json.dumps({"ts": round(time.time()), "model": model, "usd": round(usd, 6), **detail}) + "\n")


def record_failed(kind: str, model: str, error: Exception):
    record(model, FAILED_CALL_USD[kind], failed=type(error).__name__, kind=kind)


def record_spark(model: str, usage) -> float:
    if usage is None:
        record(model, FAILED_CALL_USD["spark"], missing_usage=True)
        return FAILED_CALL_USD["spark"]
    p = PRICES.get(model, PRICES["muse-spark-1.3"])
    inp = getattr(usage, "prompt_tokens", 0) or 0
    out = getattr(usage, "completion_tokens", 0) or 0
    cached = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0
    usd = (inp - cached) * p["in"] + cached * p["cached_in"] + out * p["out"]
    record(model, usd, inp=inp, cached=cached, out=out)
    return usd


def record_sam():
    record("sam-3.1", PRICES["sam-3.1"]["image"], images=1)


def record_search(queries: int = 1):
    record("web_search", PRICES["web_search"]["query"] * queries, queries=queries)
