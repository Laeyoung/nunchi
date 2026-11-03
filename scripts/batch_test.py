"""Regression test: explain every test image (whole photo, no tap) in each language and write report.html.
Usage: MODEL_API_KEY=... python -m scripts.batch_test ../test-images ja en"""
import html, json, pathlib, sys, time
from concurrent.futures import ThreadPoolExecutor
from backend import meta_client as mc

folder = pathlib.Path(sys.argv[1]); langs = sys.argv[2:] or ["ja"]
out = pathlib.Path("cache/batch"); out.mkdir(parents=True, exist_ok=True)
images = sorted(p for p in folder.glob("[0-9][0-9]_*.jpg"))


def run(job):
    p, lang = job
    t = time.time()
    try:
        r = mc.explain_hedged(mc.load_image(p.read_bytes()), None, lang)
    except Exception as e:  # keep going; the report shows the error
        r = {"error": str(e)}
    r["_s"] = round(time.time() - t, 1)
    (out / f"{p.stem}.{lang}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2))
    return p, lang, r


jobs = [(p, l) for p in images for l in langs]
with ThreadPoolExecutor(4) as ex:
    results = list(ex.map(run, jobs))

rows = []
for p, lang, r in results:
    cells = [f'<img src="{html.escape(str(p.resolve()))}" width="160">', p.stem, lang, f'{r.get("_s")}s']
    cells += [html.escape(str(r.get(k, ""))) for k in ("error", "korean_text", "meaning", "why_here", "what_to_do", "native_bridge", "confidence")]
    rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "<td>☐ OK ☐ 틀림</td></tr>")
head = "<tr>" + "".join(f"<th>{h}</th>" for h in ["photo", "file", "lang", "time", "error", "korean", "meaning", "why", "todo", "bridge", "conf", "검수"]) + "</tr>"
pathlib.Path("report.html").write_text(
    f"<meta charset=utf-8><style>td{{vertical-align:top;font:13px sans-serif;border-bottom:1px solid #ddd;padding:6px}}</style><table>{head}{''.join(rows)}</table>")
expect = json.loads((pathlib.Path(__file__).parent / "expectations.json").read_text())
misses = [(p.stem, lang, r.get("korean_text", r.get("error"))) for p, lang, r in results
          if expect.get(p.stem) and not any(k.replace(" ", "") in str(r.get("korean_text", "")).replace(" ", "")
                                            for k in expect[p.stem])]
for m in misses:
    print("MISS", *m)
print(f"expectations: {len(results) - len(misses)}/{len(results)} pass")
print("wrote report.html,", len(results), "results; avg",
      round(sum(r["_s"] for _, _, r in results) / max(1, len(results)), 1), "s")
