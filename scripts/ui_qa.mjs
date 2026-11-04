// UI layout check with ego-browser: 5 viewports x 3 languages x 7 states (home, samples, photo, card, more,
// cache-only notice, error). Prints one JSON line per state with layout issues (horizontal overflow, content wider
// than its box, header/body misalignment, wrapped buttons, small tap targets); saves screenshots for QA.shots.
// Needs a live server (LIVE=1) on :8002 and a cache-only one (LIVE=0) on :8000. Run:
//   ego-browser nodejs <<'EOF'
//   globalThis.QA = { shots: ["320_ja", "1280_en"], out: "/tmp/nunchi-ui-qa" };
//   await import("file:///<repo>/scripts/ui_qa.mjs");
//   EOF
const CFG0 = globalThis.QA || {};
const OUT = CFG0.out || "/tmp/nunchi-ui-qa";
const LIVE = CFG0.live || "http://localhost:8002", OFF = CFG0.off || "http://localhost:8000";
const ALLV = [[320, 640, 2, true], [360, 780, 3, true], [390, 844, 3, true], [768, 1024, 2, true], [1280, 800, 1, false]];
const CFG = globalThis.QA || {};
const VPS = CFG.vps ? ALLV.filter(v => CFG.vps.includes(v[0])) : ALLV;
const LANGS = CFG.langs || ["ja", "en", "zh"];
const SHOTS = new Set(CFG.shots || []);
const step = s => CFG.trace && console.log("step " + s);

const task = await taskSpace(CFG0.space ?? "nunchi ui qa");
const page = (await task.pages())[0] || await task.newPage();
console.log(JSON.stringify({ space: task.spaceId, page: page.label }));

function measure(state) {
  const vw = innerWidth, out = [];
  const name = el => el.id ? "#" + el.id : el.className && typeof el.className === "string" ? el.tagName.toLowerCase() + "." + el.className.split(" ")[0] : el.tagName.toLowerCase();
  const shown = el => { const r = el.getBoundingClientRect(), s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none"; };
  const R = el => { if (!el || !shown(el)) return null; const r = el.getBoundingClientRect(); return { l: Math.round(r.left), r: Math.round(r.right), t: Math.round(r.top + scrollY), b: Math.round(r.bottom + scrollY), w: Math.round(r.width), h: Math.round(r.height) }; };
  if (document.documentElement.scrollWidth > vw + 1) out.push("page h-scroll: " + document.documentElement.scrollWidth + " > " + vw);
  for (const el of document.querySelectorAll("body *")) {
    if (!shown(el) || ["SCRIPT", "STYLE", "OPTION"].includes(el.tagName)) continue;
    const r = el.getBoundingClientRect();
    if (r.right > vw + 1 || r.left < -1) out.push("outside viewport: " + name(el) + " [" + Math.round(r.left) + "," + Math.round(r.right) + "]");
    const s = getComputedStyle(el);
    if (el.scrollWidth > el.clientWidth + 2 && el.clientWidth > 0 && !["IMG", "SELECT", "HTML", "BODY"].includes(el.tagName) && s.overflowX !== "auto")
      out.push("content wider than box: " + name(el) + " " + el.scrollWidth + ">" + el.clientWidth);
  }
  const h1 = document.querySelector("h1"), sel = document.getElementById("lang");
  const a = R(h1), b = R(sel);
  if (a && b && a.r > b.l && a.b > b.t && b.b > a.t) out.push("header overlap: h1 " + a.l + "-" + a.r + " vs select " + b.l + "-" + b.r);
  const lefts = {};
  for (const id of ["appName", "pickRow", "samples", "stage", "card", "err", "notice"]) { const r = R(document.getElementById(id)); if (r) lefts[id] = r.l; }
  const rights = {};
  for (const id of ["lang", "pickRow", "stage", "card"]) { const r = R(document.getElementById(id)); if (r) rights[id] = r.r; }
  const btnLines = {};
  for (const id of ["takeBtn", "albumBtn", "play", "playKo", "moreBtn", "retry"]) {
    const el = document.getElementById(id); if (!el || !shown(el)) continue;
    const lh = parseFloat(getComputedStyle(el).lineHeight) || parseFloat(getComputedStyle(el).fontSize) * 1.25;
    const pad = parseFloat(getComputedStyle(el).paddingTop) + parseFloat(getComputedStyle(el).paddingBottom);
    btnLines[id] = Math.round((el.getBoundingClientRect().height - pad) / lh);
  }
  const small = [];
  for (const el of document.querySelectorAll("button, label.btn, select, summary, #grid img, #more a")) {
    if (!shown(el)) continue; const r = el.getBoundingClientRect();
    if (r.height < 40 && el.tagName !== "A") small.push(name(el) + " h=" + Math.round(r.height));
  }
  return { state, issues: [...new Set(out)].slice(0, 12), lefts, rights, btnLines, smallTargets: [...new Set(small)].slice(0, 6),
           header: { h1: a, select: b } };
}

async function vp(w, h, dpr, mobile) {
  await page.cdp("Network.enable", {}); await page.cdp("Network.setCacheDisabled", { cacheDisabled: true });
  await page.cdp("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: dpr, mobile });
  await page.cdp("Emulation.setTouchEmulationEnabled", { enabled: mobile });
}
async function shot(tag) {
  if (SHOTS.has("all") || SHOTS.has(tag.split("_").slice(0, 2).join("_"))) await page.screenshot({ path: `${OUT}/${tag}.png` });
}
async function report(tag, w, lang) {
  const m = await page.evaluate(measure, tag.split("_").pop());
  console.log(JSON.stringify({ w, lang, ...m }));
  await shot(tag);
}

for (const [w, h, dpr, mobile] of VPS) {
  await vp(w, h, dpr, mobile);
  for (const lang of LANGS) {
    const T = `${w}_${lang}`;
    await page.goto(`${LIVE}/?lang=${lang}`); await page.waitForFunction(() => document.querySelectorAll("#grid img").length > 15); await page.waitForTimeout(400);
    step("home"); await report(`${T}_home`, w, lang);
    await page.click("#samplesLabel"); await page.waitForTimeout(300);
    step("samples"); await report(`${T}_samples`, w, lang);
    await page.evaluate(() => document.querySelector('#grid img[alt^="15_"]').click());
    await page.waitForFunction(() => document.querySelectorAll(".cand").length > 0, undefined, { timeout: 15000 });
    await page.waitForTimeout(700);
    step("photo"); await report(`${T}_photo`, w, lang);
    await page.evaluate(() => explain(0.5, 0.55));
    await page.waitForFunction(() => getComputedStyle(document.getElementById("card")).display !== "none", undefined, { timeout: 40000 });
    await page.evaluate(() => document.getElementById("card").scrollIntoView({ block: "start" }));
    await page.waitForTimeout(300);
    step("card"); await report(`${T}_card`, w, lang);
    await page.evaluate(() => document.getElementById("moreBtn").click());
    await page.waitForFunction(() => document.querySelector("#more a") || /\S/.test(document.getElementById("moreBtn").textContent) && document.getElementById("moreBtn").disabled === false && getComputedStyle(document.getElementById("more")).display !== "none", undefined, { timeout: 40000 }).catch(() => {});
    await page.evaluate(() => (document.getElementById("more").style.display === "block" ? document.getElementById("more") : document.getElementById("moreBtn")).scrollIntoView({ block: "center" }));
    await page.waitForTimeout(300);
    step("more"); await report(`${T}_more`, w, lang);
    // cache-only server: offline notice + error box
    await page.goto(`${OFF}/?lang=${lang}`); await page.waitForFunction(() => document.querySelectorAll("#grid img").length > 15); await page.waitForTimeout(400);
    step("offline"); await report(`${T}_offline`, w, lang);
    await page.evaluate(() => document.querySelector('#grid img[alt^="07_"]').click());
    await page.waitForFunction(() => document.getElementById("photo").naturalWidth > 0); await page.waitForTimeout(500);
    await page.evaluate(() => explain(0.1, 0.1));
    await page.waitForFunction(() => getComputedStyle(document.getElementById("err")).display !== "none", undefined, { timeout: 15000 });
    await page.evaluate(() => document.getElementById("err").scrollIntoView({ block: "center" }));
    step("error"); await report(`${T}_error`, w, lang);
  }
}
await page.cdp("Emulation.clearDeviceMetricsOverride", {});
console.log(JSON.stringify({ done: true }));
