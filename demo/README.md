# RevenueGuard AI — automated product film

Caption-led, 4:04, 1920×1080 at 30 fps. Main export includes original, quietly mixed instrumental synthesis and UI sound effects. Silent export has a silent AAC track for broad player compatibility. No human narration or operation is required.

## Deliverables

- `final/revenueguard-buildathon-demo.mp4` — submission export
- `final/revenueguard-buildathon-demo-silent.mp4` — same edit, no audible sound
- `final/revenueguard-buildathon-demo.srt` — accessible caption transcript
- `final/revenueguard-thumbnail.jpg` — suggested thumbnail from the proof climax at 03:52
- `timeline.json` — timestamped source/route/action/caption/expected-state manifest; shared defaults cover omitted optional event fields
- `shot-list.md` — editorial ranking, shooting plan and claim boundaries
- `logs/` — sanitized proof JSON, contact sheets, render diagnostics and validation

## Reproduce

Prerequisites: the project dependencies and model artifacts from the root README; Python with Pillow, NumPy, httpx and python-dotenv; Node; Chrome; Playwright; FFmpeg/ffprobe on PATH; Docker running. Windows Segoe UI fonts are used by the compositor. This workstation can use its bundled Playwright; for other machines install Playwright in `demo/` and its recording dependency:

```powershell
cd demo
npm install
npx playwright install chrome ffmpeg
cd ..
.venv\Scripts\python.exe demo/run.py
```

The root `.env` must contain a working Groq or OpenRouter key and **Razorpay test** key ID/secret. The runner rejects live Razorpay key IDs. Never commit `.env`. LLM requests and test-mode order creation use the configured external providers; this can consume provider quota. No checkout, charge, refund, live payment, or publishing action is performed.

Ports 8010, 3010 and 6389 must be free. The script creates a unique SQLite database under `demo/work/`, a uniquely named Redis container bound to loopback, the real API, the real worker and the Next frontend. It seeds explicitly synthetic telemetry and fixture inputs—not fabricated scores, approval outcomes or UI responses. All production application modules remain unchanged.

The runner stops its own processes and Redis container on exit. The stopped container and isolated database are retained for diagnostics, not deleted. Raw footage/database/server logs are local and excluded by `demo/.gitignore`; do not publish these without checking their contents. Final MP4s are also ignored to avoid bloating Git history—upload the finished main export to your video host instead.

```powershell
# Capture only, then edit/render without calling providers again:
.venv\Scripts\python.exe demo/run.py --capture-only
.venv\Scripts\python.exe demo/render.py --draft draft1
.venv\Scripts\python.exe demo/run.py --render-only
.venv\Scripts\python.exe demo/validate.py
node demo/player-check.cjs
```

Capture uses semantic Playwright selectors, eased cursor movement, hover-before-click, real HTTP responses and explicit proof gates. Each shot excludes startup/loading pre-roll. A missing state produces a diagnostic screenshot and aborts rather than forging a successful scene. External checkout is intentionally not automated; a real test order and a separately labelled, locally signed synthetic webhook replay demonstrate the integration reliably.

## Evidence and limitations

- Batch: actual simulation endpoint → Redis queue → recovery worker → persisted cases.
- Gateway: synthetic SBI/UPI telemetry → actual circuit breaker → OPEN/DEFER.
- Selected case: actual ML/SHAP and LLM graph execution. The high-value fixture is deliberately assigned to treatment using the implementation's real **per-case** hash assignment.
- Approval: actual pending approval, dashboard click, persisted approval, worker resumption and deferred action. This is prototype policy enforcement—not a certification or guarantee of production financial safety.
- Razorpay: actual test-mode order. **No completed checkout or Razorpay-origin webhook is claimed.** The subsequent intake proof is a locally signed synthetic Razorpay-format event sent to the actual webhook endpoint; invalid signature rejection, valid acceptance and duplicate suppression are independently asserted.
- Evaluation: committed `evals/results/summary.json`: 523 held-out synthetic events; ML F1 80.3%; control 151/401 (37.7%), treatment 58/122 (47.5%); +9.9 percentage points / +26.3%; one-sided p=0.025; SRM p≈0.057 passes the configured 0.01 threshold. Recovery outcomes come from the offline **policy simulation**, not production transactions or an end-to-end live LLM experiment. The two-sided 95% interval crosses zero; the film does not claim two-sided significance.
- A configured LLM is called; generated diagnosis wording can vary across re-recordings. The same validated raw footage can be rendered deterministically without new provider calls.

## Audio and licensing

`render.py` synthesizes an original four-chord instrumental bed and click/typing transients mathematically. No downloaded music, commercial sound samples, copied reference assets, or narration are used. The mix targets approximately −30 LUFS. All editorial graphics are drawn specifically for this film; application visuals come from this project. Existing product names identify integrations, not an endorsement.

## YouTube

Title: **RevenueGuard AI — Intelligent Payment Recovery | Razorpay AI Buildathon 2026**

Description:

RevenueGuard AI turns failed payments into explainable, policy-checked recovery decisions for Razorpay. This automated demonstration follows synthetic payment failures through ML triage, SHAP explanations, gateway circuit breaking, agent reasoning, high-value human approval, test-mode integration and measurable evaluation.

This is an isolated local prototype demonstration. No real charges are made. Razorpay order creation uses test mode; webhook verification is demonstrated separately with a locally signed synthetic replay. The +9.9 percentage-point lift is from a held-out synthetic policy simulation with simulated outcomes—not production recovery results or measured live LLM uplift.

- Source and setup: https://github.com/tusharg007/revenueguard-ai
- Live frontend: https://revenueguard-ai-five.vercel.app
- API: https://revenueguard-ai-2.onrender.com

Chapters:

```text
00:00 Why blind retries fail
00:20 Recovery operations
00:52 A systemic SBI outage
01:25 Explainable ML and agent decisions
02:19 Deterministic policy
02:31 Human approval
03:04 Razorpay test-mode integration
03:30 Measure against the baseline
03:59 RevenueGuard AI
```

Upload the main MP4 as an **Unlisted** YouTube video if the submission asks for a public-access link without broad publication. Wait for HD processing, attach the SRT if desired, and verify the link in a signed-out window. This pipeline does not upload or publish anything automatically.
