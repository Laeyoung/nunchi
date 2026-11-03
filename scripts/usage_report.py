"""Estimated Meta API spend from usage/usage.jsonl (+ PRIOR_SPEND_USD). Usage: python -m scripts.usage_report"""
import collections, json
from backend import usage

by = collections.defaultdict(lambda: [0, 0.0])
if usage.LEDGER.exists():
    for line in usage.LEDGER.read_text().splitlines():
        if line.strip():
            r = json.loads(line); by[r["model"]][0] += 1; by[r["model"]][1] += r["usd"]
for m, (n, usd) in sorted(by.items()):
    print(f"{m:18s} {n:5d} calls  ${usd:7.3f}")
print(f"{'prior (estimate)':18s}             ${usage.PRIOR_SPEND_USD:7.3f}")
print(f"{'TOTAL':18s}             ${usage.total():7.3f}  / budget ${usage.BUDGET_USD:.0f}")
