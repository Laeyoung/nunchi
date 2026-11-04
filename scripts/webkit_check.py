"""iPhone stand-in check: runs the demo flow in Playwright WebKit (Safari's engine) with iPhone 13 emulation.
Uses cached demo results only, so it costs nothing. Needs a running server on :8000 and
`pip install playwright && python -m playwright install webkit` (not in requirements.txt).
Usage: python scripts/webkit_check.py [screenshot_dir]
Not covered by emulation: the real camera, iOS speech autoplay policy, and device voices."""
import sys, json
from playwright.sync_api import sync_playwright
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
with sync_playwright() as p:
    b = p.webkit.launch()
    for lang in ["ja", "en"]:
        ctx = b.new_context(**p.devices["iPhone 13"], locale="ja-JP" if lang=="ja" else "en-US")
        pg = ctx.new_page(); errs=[]
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: m.type=="error" and errs.append(m.text))
        pg.goto(f"http://localhost:8000/?demo=1&lang={lang}")
        pg.wait_for_selector("#grid img")
        info = pg.evaluate("""() => ({ua:navigator.userAgent.slice(0,80), speech: 'speechSynthesis' in window,
          voices: speechSynthesis.getVoices().length, title: document.title,
          capture: document.querySelector('#file')?.getAttribute('capture'), accept: document.querySelector('#file')?.accept,
          hscroll: document.documentElement.scrollWidth > innerWidth})""")
        pg.screenshot(path=f"{OUT}/wk_{lang}_home.png")
        imgs = pg.locator("#grid img"); n = imgs.count()
        target = [i for i in range(n) if imgs.nth(i).get_attribute("alt").startswith("15_")][0]
        imgs.nth(target).click()
        pg.wait_for_function("document.getElementById('photo').naturalWidth > 0")
        pg.wait_for_timeout(800); pg.locator("#photo").scroll_into_view_if_needed(); pg.wait_for_timeout(500)
        box = pg.locator("#photo").bounding_box()
        pg.mouse.click(box["x"]+box["width"]*0.5, box["y"]+box["height"]*0.55)
        pg.wait_for_selector("#card", state="visible", timeout=30000)
        pg.wait_for_timeout(400); meta = pg.inner_text("#meta") + " | play=" + pg.inner_text("#play"); meaning = pg.inner_text("#meaning")
        pg.locator("#card").screenshot(path=f"{OUT}/wk_{lang}_card.png")
        pg.click("#moreBtn"); pg.wait_for_selector("#more a", timeout=35000)
        links = pg.locator("#more a").count()
        pg.screenshot(path=f"{OUT}/wk_{lang}_more.png", full_page=True)
        print(json.dumps({"lang":lang, **info, "meta":meta, "meaning":meaning[:60], "links":links, "errors":errs}, ensure_ascii=False))
        ctx.close()
    b.close()
