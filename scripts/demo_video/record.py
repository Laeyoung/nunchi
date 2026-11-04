"""Drive the real app inside stage.html, capture frames via CDP screencast, log audio cue times."""
import asyncio, base64, json, os, subprocess, time
from playwright.async_api import async_playwright

V = os.environ.get("OUT") or os.path.dirname(os.path.abspath(__file__))
L = json.load(open(f"{V}/lines.json"))
DATA = {k: json.load(open(f"{V}/data/{k}.json"))["result"] for k in ["01_ja", "15_ja", "19_ja", "19_en"]}
CREDITS = open(f"{V}/credits.txt").read()
DUR = {}
for f in os.listdir(f"{V}/audio"):
    if f.endswith(".aiff"):
        DUR[f[:-5]] = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                     "-of", "csv=p=0", f"{V}/audio/{f}"]))
IF_X, IF_Y, SC = 208, 52, 1.169
APP = os.environ.get("APP", "http://localhost:8000")  # the own-photo scene needs a LIVE=1 server
PHONE_TAP = (0.5, 0.2)  # the "미끄럼 주의" headline
cues, frames = [], []


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await b.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto("http://localhost:8765/stage.html")
        await page.evaluate("document.getElementById('app').src='" + APP + "/?demo=1&lang=ja'")
        await page.wait_for_timeout(1500)
        fr = next(f for f in page.frames if f.url.startswith(APP))
        await fr.wait_for_function("document.querySelectorAll('#grid img').length > 15 && [...document.querySelectorAll('#grid img')].every(i => i.complete)")
        imgs = ",".join(f"'{n}'" for n in ["01_road_oneway","04_road_school_zone","06_road_stop","08_safety_slippery","09_safety_cctv",
            "11_subway_transfer","13_subway_door_emergency","15_food_menu","16_shop_holiday_notice","17_food_restaurant_24h",
            "18_daily_recycling","19_daily_toilet","20_shop_no_kids_zone","03_road_no_parking"])

        await fr.evaluate("() => { const s = document.createElement('style'); s.textContent = 'body{padding-bottom:700px}'; document.head.appendChild(s); }")
        cdp = await page.context.new_cdp_session(page)

        async def on_frame(prm):
            frames.append((prm["metadata"]["timestamp"], prm["data"]))
            try: await cdp.send("Page.screencastFrameAck", {"sessionId": prm["sessionId"]})
            except Exception: pass
        cdp.on("Page.screencastFrame", lambda prm: asyncio.ensure_future(on_frame(prm)))

        js = page.evaluate
        async def sleep(s): await asyncio.sleep(s)
        def cue(key, trim=None):
            cues.append({"t": time.time(), "key": key, "trim": trim})
            return time.time() + (trim or DUR[key])
        async def until(t):
            d = t - time.time()
            if d > 0: await asyncio.sleep(d)
        async def narrate(key):
            await js("([t]) => sub(t)", [L[key]])
            return cue(key)
        async def app_voice(key, trim, label, text):
            if trim:  # cut at a sentence end near the target length; estimate timing from character share
                import re
                parts = re.findall(r".+?(?:[。．.!?！？]|$)\s*", text)
                best, acc = parts[0], ""
                for ptxt in parts:
                    acc += ptxt
                    if len(acc) / len(text) * DUR[key] <= trim + 1.5: best = acc
                trim = min(DUR[key], len(best) / len(text) * DUR[key] + 0.6); text = best.strip()
            await js("([t, l]) => sub(t, l)", [text, label])
            await until(cue(key, trim))
            await js("sub('')")
            await sleep(0.6)
        async def tap_el(sel, idx=0):
            r = await fr.evaluate("([s, i]) => { const b = document.querySelectorAll(s)[i].getBoundingClientRect(); return [b.x + b.width/2, b.y + b.height/2]; }", [sel, idx])
            await tap_xy(*r)
        async def tap_xy(x, y):
            px, py = IF_X + x * SC, IF_Y + y * SC
            await js("([x, y]) => ripple(x, y)", [px, py]); await page.mouse.click(px, py)
        async def tap_photo(nx, ny):
            r = await fr.evaluate("() => { const b = document.getElementById('photo').getBoundingClientRect(); return [b.x, b.y, b.width, b.height]; }")
            await tap_xy(r[0] + r[2] * nx, r[1] + r[3] * ny)
        async def scroll_to(sel, offset=12):
            await fr.evaluate("([s, o]) => { const e = document.querySelector(s); window.scrollTo({top: e.getBoundingClientRect().top + scrollY - o, behavior: 'smooth'}); }", [sel, offset])
        async def scroll_top():
            await fr.evaluate("() => window.scrollTo({top: 0, behavior: 'smooth'})")
        async def open_photo(name):
            idx = await fr.evaluate("(n) => [...document.querySelectorAll('#grid img')].findIndex(i => i.alt.startsWith(n))", name)
            await fr.evaluate("(i) => document.querySelectorAll('#grid img')[i].scrollIntoView({block: 'center', behavior: 'smooth'})", idx)
            await sleep(0.9); await tap_el("#grid img", idx)
            await fr.wait_for_function("document.querySelectorAll('.cand').length > 0", timeout=10000)
            await sleep(0.8); await scroll_to("#stage", 150)

        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": 1920, "maxHeight": 1080})
        t_start = time.time()

        # 0. Problem
        await js(f"""() => slide(`<div class=collage>${{[{imgs},{imgs}].map(n => '<img src=http://localhost:8000/demo-images/'+n+'.jpg>').join('')}}</div>
          <div class=center><div class=big>A sea of letters<br>you can't read.</div>
          <div class=mid>Translation gives you the words.<br>Standing in front of a sign, you need the <b style="color:#ffcf7a">reason</b> and the <b style="color:#ffcf7a">next step</b>.</div></div>`)""")
        await sleep(0.6); await until(await narrate("n1")); await sleep(0.5)

        # 1. Title
        await js("""() => slide(`<div class=center><div class=logo>Nunchi <span>눈치</span></div>
          <div class=tag>Tap a Korean sign. Hear why it's there and what to do.</div>
          <div class=by>Built for the Meta Global AI Developer Hackathon · SAM 3.1 + Muse Spark 1.3 · mobile web app</div></div>`)""")
        await until(await narrate("n2")); await sleep(0.4)

        # 2. One-way sign, Japanese
        await js("() => { slide(''); scene({step: 'Live app · Japanese traveller', title: 'Tap the sign', note: 'On upload, <b>SAM 3.1</b> (concept prompt “sign”) outlines candidates. A tap inside one uses that box directly.', on: ['tap']}); }")
        end = await narrate("n3")
        await sleep(1.4); await open_photo("01_"); await sleep(2.6)
        await tap_photo(0.48, 0.36)
        await fr.wait_for_selector("#card", state="visible")
        await js("() => scene({step: 'Live app · Japanese traveller', title: '일방통행 → 一方通行', note: '<b>Muse Spark 1.3</b> gets the whole photo plus the tapped crop and returns strict JSON: reading, meaning, why it is here, what to do, a native-language bridge and a narration.', on: ['tap', 'explain']})")
        await until(end); await scroll_to("#card"); await sleep(0.9)
        await js("() => scene({step: 'Live app · Japanese traveller', title: 'Heard, not read', note: 'The narration is read aloud with the phone’s own voice (Web Speech API), so your hands and eyes stay free.', on: ['tap', 'explain', 'listen']})")
        await app_voice("a01", None, "Nunchi reads aloud · ja-JP voice", DATA["01_ja"]["narration"])
        await fr.evaluate("() => { const b = document.getElementById('bridgeRow'); b.style.outline = '4px solid #e5484d'; b.style.outlineOffset = '3px'; }")
        await scroll_to("#bridgeRow", 260)
        await js("() => scene({step: 'Native-language bridge', title: '일방통행 = 一方通行', note: 'Many Korean words share Chinese-character roots with Japanese. Nunchi points them out, and the prompt forbids inventing hanja for native Korean words.', on: ['tap', 'explain', 'listen']})")
        await until(await narrate("n4")); await sleep(0.4)
        await fr.evaluate("() => document.getElementById('bridgeRow').style.outline = ''")

        # 3. Menu
        await js("() => scene({step: 'Live app · Japanese traveller', title: 'A restaurant menu', note: 'Dishes, prices and how to order. The bridge links 포장 (takeout) to 包装.', on: ['tap', 'explain', 'listen']})")
        end = await narrate("n5")
        await scroll_top(); await sleep(0.6); await open_photo("15_"); await sleep(1.6)
        await tap_photo(0.5, 0.55); await fr.wait_for_selector("#card", state="visible")
        await until(end); await scroll_to("#card"); await sleep(0.7)
        await app_voice("a15", 10.5, "Nunchi reads aloud · ja-JP voice", DATA["15_ja"]["narration"])

        # 4. Restroom sign
        await js("() => scene({step: 'Live app · Japanese traveller', title: 'Where translation falls short', note: '“Please throw used tissue in the toilet” is the words. Nunchi adds <b>why</b> and <b>what to do</b>.', on: ['tap', 'explain', 'listen']})")
        end = await narrate("n6")
        await scroll_top(); await sleep(0.6); await open_photo("19_"); await sleep(1.6)
        await tap_photo(0.33, 0.45); await fr.wait_for_selector("#card", state="visible")
        await until(end); await scroll_to("#card"); await sleep(0.7)
        await app_voice("a19", 11.5, "Nunchi reads aloud · ja-JP voice", DATA["19_ja"]["narration"])

        # 5. Tell me more
        await js("() => scene({step: 'Tell me more', title: 'Grounded, with sources', note: 'Only on request: <b>Muse Spark</b> via the Responses API with the <b>web_search</b> tool. Two source links, so you can check it yourself.', on: ['tap', 'explain', 'listen', 'more']})")
        end = await narrate("n7")
        await scroll_to("#moreBtn", 420); await sleep(1.0); await tap_el("#moreBtn")
        await fr.wait_for_selector("#more a", timeout=15000); await sleep(0.4); await scroll_to("#more", 330)
        await until(end); await sleep(2.0)

        # 6. English
        await js("() => scene({step: 'Same tap, English', title: 'The bridge adapts', note: 'For English there is no shared vocabulary, so the bridge becomes one accurate Hangul reading tip — never a made-up etymology.', on: ['tap', 'explain', 'listen']})")
        end = await narrate("n8")
        await scroll_top(); await sleep(0.8)
        await tap_el("#lang"); await fr.select_option("#lang", "en")
        await fr.wait_for_selector("#card", state="visible"); await sleep(1.0); await scroll_to("#card")
        await until(end); await sleep(0.3)
        await app_voice("a19en", 12.0, "Nunchi reads aloud · en-US voice", DATA["19_en"]["narration"])

        # 6b. Own photo: library upload, resized in the browser, analysed live
        await js("() => scene({step: 'Your own photo', title: 'Camera or library, live', note: 'A 4032×3024 phone photo is resized in the browser (1600 px, EXIF upright). Then <b>SAM 3.1</b> and <b>Muse Spark 1.3</b> run live on it. Try it: <b>nunchi-three.vercel.app</b>', on: ['tap', 'explain', 'listen']})")
        end = await narrate("n8b")
        await fr.evaluate("() => { document.getElementById('pickRow').style.display = 'flex'; window.scrollTo({top: 0, behavior: 'smooth'}); }")
        await sleep(1.2)
        await fr.evaluate("() => document.getElementById('albumBtn').style.outline = '4px solid #e5484d'")
        r = await fr.evaluate("() => { const b = document.getElementById('albumBtn').getBoundingClientRect(); return [b.x + b.width/2, b.y + b.height/2]; }")
        await js("([x, y]) => ripple(x, y)", [IF_X + r[0] * SC, IF_Y + r[1] * SC]); await sleep(0.8)
        await fr.evaluate("() => document.getElementById('albumBtn').style.outline = ''")
        await fr.set_input_files("#file2", f"{V}/phone_photo.jpg")
        await fr.wait_for_function("document.querySelectorAll('.cand').length > 0", timeout=30000)
        await sleep(0.8); await scroll_to("#stage", 150); await sleep(1.0)
        await tap_photo(*PHONE_TAP); await fr.wait_for_selector("#card", state="visible", timeout=40000)
        await sleep(0.5); await scroll_to("#card"); await until(end); await sleep(2.5)

        # 7. Architecture
        await js("""() => slide(`<div style="position:absolute;left:120px;top:90px"><div style="font-size:30px;color:#e5484d;font-weight:700;letter-spacing:.06em">HOW IT WORKS</div>
          <div style="font-size:60px;font-weight:800;margin-top:12px">Phone → FastAPI → Meta Model API</div></div>
          <div class=arch>
            <div class=node style="left:0;top:180px;width:300px"><b>Phone browser</b><span>single-page web app · camera · tap · Web Speech TTS</span></div>
            <div class=node style="left:440px;top:40px;width:330px"><b>/api/segment</b><span>on upload: sign candidates</span></div>
            <div class=node style="left:440px;top:210px;width:330px"><b>/api/explain</b><span>tap → box → crop</span></div>
            <div class=node style="left:440px;top:380px;width:330px"><b>/api/more</b><span>only when asked</span></div>
            <div class="node meta" style="left:900px;top:40px;width:420px"><b>SAM 3.1</b><span>concept prompt “sign” · point prompt for the tap</span></div>
            <div class="node meta" style="left:900px;top:210px;width:420px"><b>Muse Spark 1.3</b><span>photo + crop → strict JSON (10 fields) · reasoning_effort minimal</span></div>
            <div class="node meta" style="left:900px;top:380px;width:420px"><b>Muse Spark + web_search</b><span>Responses API · 2 sources</span></div>
            <div class=node style="left:1420px;top:210px;width:260px"><b>Cache</b><span>demo replays offline</span></div>
            <svg class=edges><g stroke="#6f655c" stroke-width="3" fill="none">
              <path d="M300 250 L440 95"/><path d="M300 265 L440 265"/><path d="M300 280 L440 435"/>
              <path d="M770 95 L900 95"/><path d="M770 255 L900 120"/><path d="M770 265 L900 265"/><path d="M770 435 L900 435"/><path d="M1320 265 L1420 265"/></g></svg>
          </div>
          <div style="position:absolute;left:120px;bottom:110px;font-size:30px;color:#b9afa4">Measured: ~8–9 s for a new tap · regression set 39/40 keyword matches · no paid OCR or translation APIs</div>`)""")
        await until(await narrate("n9")); await sleep(0.6)

        # 8. Close
        await js(f"""() => slide(`<div class=center><div class=logo style="font-size:120px">Nunchi <span>눈치</span></div>
          <div class=tag>Read the room, in Korea.</div>
          <div class=mid style="font-size:32px">Built during the hackathon: the whole app — tap-to-region pipeline, prompts and schema, native-language bridge, Tell me more, demo cache, spend guard.<br>
          Next: voice questions with Muse Voice Transcribe · more languages.</div>
          <div class=by>Try it: nunchi-three.vercel.app · github.com/Laeyoung/nunchi</div></div>
          <div class=credits>Photos (Wikimedia Commons / Hugging Face, used under their licenses): {CREDITS}</div>`)""")
        await until(await narrate("n10")); await sleep(2.5)

        t_end = time.time()
        await cdp.send("Page.stopScreencast"); await sleep(0.5)
        await b.close()

    os.makedirs(f"{V}/frames", exist_ok=True)
    for f in os.listdir(f"{V}/frames"): os.remove(f"{V}/frames/{f}")
    frames.sort()
    lines = []
    for i, (ts, data) in enumerate(frames):
        fn = f"{V}/frames/f{i:05d}.jpg"; open(fn, "wb").write(base64.b64decode(data))
        nxt = frames[i + 1][0] if i + 1 < len(frames) else t_end
        lines += [f"file '{fn}'", f"duration {max(nxt - ts, 0.001):.4f}"]
    lines.append(f"file '{V}/frames/f{len(frames)-1:05d}.jpg'")
    open(f"{V}/frames.txt", "w").write("\n".join(lines))
    t0 = frames[0][0]
    json.dump({"t0": t0, "t_end": t_end, "cues": [{**c, "t": c["t"] - t0} for c in cues]}, open(f"{V}/cues.json", "w"), indent=1)
    print(f"frames={len(frames)} length={t_end - t0:.1f}s")

asyncio.run(main())
