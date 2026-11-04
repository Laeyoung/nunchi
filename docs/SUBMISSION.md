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
