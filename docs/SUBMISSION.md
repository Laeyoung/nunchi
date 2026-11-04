# Submission draft (CV platform)

Submit at https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit
before **Nov 4, 9:00 PM ET (= Nov 5, 11:00 KST)**. One submission per team; list everyone who worked on it.

## Links
- Repository (public): https://github.com/Laeyoung/nunchi
- Demo video (2:58): https://youtu.be/0poEphOVf5Y
- Live product: https://nunchi-three.vercel.app

## Project name
Nunchi (눈치)

## Tagline (one line)
Tap a Korean sign. Hear why it's there and what to do, in your own language.

## Short description
Nunchi is a mobile web app for travellers in Korea. Point your phone at a sign, menu or notice and tap the
text. SAM 3.1 finds the sign region, and Muse Spark 1.3 reads it together with the whole scene. It returns
what the sign says, why it is there, what you should do now, and a link to your own language
(e.g. 일방통행 = 一方通行 for Japanese). The answer is read aloud. Translation apps change the letters;
Nunchi explains the place.

## How it uses Meta models
- **SAM 3.1:** On upload, a concept prompt (`sign`) outlines the sign candidates. A tap inside a candidate uses
  that box directly. A tap anywhere else uses a point prompt to segment the tapped region.
- **Muse Spark 1.3:** It gets the full photo plus the tapped crop. It returns a strict 10-field JSON
  (reading, meaning, why, what to do, native-language bridge, narration, confidence…) using
  `reasoning_effort=minimal`, in about 8–9 s per new tap.
- **Muse Spark 1.3 + `web_search`** (Responses API): powers "Tell me more". It returns 2–3 grounded sentences
  with source links, and runs only when the user asks.
- No paid OCR or translation APIs. Speech uses the browser's Web Speech API.

## What was built during the hackathon
Everything. The repository has no earlier codebase; see the git history (Oct 27 – Nov 4, 2026). This covers:
- the tap-to-region pipeline,
- the prompts and JSON schema, including the native-language bridge rules (no invented hanja),
- "Tell me more" with sources,
- the mobile web app (camera and library upload with in-browser resize, candidate boxes, narration, demo mode),
- the cache, rate limit and spend guard,
- the regression and UI test scripts.

## Languages
Japanese, English, Chinese (UI and narration).

## Tech stack
FastAPI (Python) · single-page HTML/JS (PWA) · Meta Model API (SAM 3.1, Muse Spark 1.3) · deployed on Vercel.

## Team
Laeyoung Chang (solo)

---

# Form answers

Sentences are never wrapped mid-line, so each answer pastes cleanly into the form; blank lines and dashes are intentional.

- **Team Name:** Nunchi
- **Track:** the track matching *Build for Your World* (not Most Viral unless posting on X)
- **Problem statement:** Build for Your World
- **X post link:** leave empty
- **Public GitHub Repository:** https://github.com/Laeyoung/nunchi
- **3-Minute Demo Video:** https://youtu.be/0poEphOVf5Y

## Project Description
Travellers in Korea are surrounded by signs, menus and notices they cannot read. A translation app turns the letters into words, but standing in front of a sign you need more: why is it here, and what should I do now?

Nunchi is a mobile web app that answers that. Take a photo or pick one from your library, and tap the Korean text. SAM 3.1 finds the sign region, and Muse Spark 1.3 reads it together with the whole scene. It returns:
- what the sign says and how to read it
- why it is there
- what you should do now
- a bridge to your own language (e.g. 일방통행 = 一方通行 for Japanese speakers)

The answer is read aloud in Japanese, English or Chinese, and "Tell me more" adds web-grounded detail with sources. It runs in the phone browser with no install.

Try it: https://nunchi-three.vercel.app

## Describe your use of Meta products to build the submitted project
All model calls go through the Meta Model API.

- SAM 3.1: On upload, a concept prompt ("sign") outlines every sign candidate so the user sees what is tappable. A tap inside a candidate reuses that box; a tap elsewhere sends a point prompt to segment exactly the tapped region.
- Muse Spark 1.3 (Chat Completions): It receives the full photo plus the tapped crop and returns a strict 10-field JSON (reading, meaning, why it is here, what to do, native-language bridge, narration, confidence and more). We use reasoning_effort=minimal, which cut latency from about 14 s to about 8 s with no visible quality loss. The prompt has rules against inventing hanja for native Korean words and against stating numbers or laws that are not on the sign.
- Muse Spark 1.3 (Responses API + web_search): It powers "Tell me more", giving 2-3 grounded sentences with source links, called only when the user asks.

We use no other vision, OCR or translation models.

## Why are Meta's models important to your solution?
The product is "understand this sign in its context", which takes two things at once: locating text in a cluttered street photo, and reasoning about the scene, not just the letters.

- SAM 3.1's concept and point prompts turn a rough finger tap into a precise region without a separate OCR or detection model.
- Muse Spark reads Korean directly from the image and explains the cultural reason behind the sign (e.g. why a restroom has no trash can), in the traveller's language, in one strict-JSON call fast enough for someone standing on the street.
- The Responses API web search lets the same model back up longer answers with sources.

One API key covers segmentation, multimodal reasoning and grounded search, which kept the app to a single small FastAPI server.

## Provide feedback from your experience using partner technologies
Not used. Everything ran on the Meta Model API.

## What was the biggest obstacle your team hit while building this project?
Latency and reliability on a phone. With default reasoning a card took about 14 s, and a few responses took 15-18 s. We switched to reasoning_effort=minimal, sent a second request after 9 s and used whichever answered first, and pre-computed SAM sign candidates on upload so most taps skip a second segmentation. That brought a new tap to about 8-9 s.

The other obstacle was the accuracy of the native-language bridge. Early outputs invented hanja for native Korean words (e.g. 국밥 as 國飯), which we fixed with explicit rules and a 40-case regression set.

Smaller issues:
- SAM point prompts sometimes returned tiny low-confidence fragments, so we added fallback rules.
- Responses API web search returned empty url_citation annotations, so sources come from web_search_call.results.
- There is no API to check the credit balance, so we built our own spend ledger.
