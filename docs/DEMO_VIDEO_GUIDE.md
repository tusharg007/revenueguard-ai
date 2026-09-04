# Demo Video Recording and Upload Guide

## Final recommendation

Use **OBS Studio to record the screen and your microphone**, then upload the MP4 to **YouTube as Unlisted**.

This is the strongest submission route because:

- your voice establishes ownership and makes the reasoning easier to follow;
- OBS has no Loom-style five-minute recording cutoff;
- YouTube gives judges a stable link without requiring an account;
- you can trim the beginning and end before uploading;
- an unlisted video does not appear in normal public search.

Use Loom only as an emergency backup. Do not make a silent automated recording the primary submission: it proves the interface works, but loses the founder narrative and can feel less credible.

If recording the screen and narration together is difficult, record the demo silently first and then record one clean voice track. The two files can be synchronized afterward. A silent automated capture is also useful as backup B-roll.

## Target duration

Aim for **4:15–4:35**, leaving at least 25 seconds of safety below a five-minute submission limit.

## Before recording

1. Open the live API health URL once and wait for Render to wake.
2. Refresh the dashboard and confirm cases and metrics load.
3. Start the recovery worker if the demo requires new cases to execute.
4. Close private tabs, notifications, password managers, email, and chat apps.
5. Set browser zoom to 100% and use a 1920×1080 display if available.
6. Prepare these tabs in order:
   - control room;
   - one strong case-detail page;
   - experiments;
   - gateway health;
   - Razorpay sandbox;
   - GitHub README.
7. Put the pitch script beside the monitor, not over the demo window.
8. Record a 15-second audio test and listen back with headphones.

## OBS settings

### Video

- Canvas: 1920×1080
- Output: 1920×1080
- Frame rate: 30 FPS
- Capture source: browser window or display capture
- Keep the mouse pointer visible
- Avoid tiny terminal text

### Audio

- Add the microphone as **Mic/Aux**
- Speak 15–20 cm from the microphone
- Keep voice peaks around -12 dB to -6 dB
- Disable loud fans and phone notifications
- Use headphones if any demo audio is playing

### Recording format

Record to **MKV** for crash safety, then choose **File → Remux Recordings** in OBS to create an MP4. If you want the simplest path and the machine is stable, recording directly to MP4 is acceptable.

## Recommended five-minute run of show

### 0:00–0:25 — Hook

State the payment-recovery problem and the product in one sentence. Keep your face on camera only if it feels natural; otherwise use a clean title card and voice.

### 0:25–0:55 — Architecture

Show the README architecture. Explain that webhook intake is signed and idempotent, cases are persisted before queueing, and decisions pass through ML, gateway health, policy, and audit stages.

### 0:55–2:35 — Live recovery

Show the control room, inject a small batch, and open one case. Point to:

- recovery probability;
- SHAP reason codes;
- failure category;
- experiment arm;
- selected strategy/channel;
- policy checks;
- audit timeline.

Do not wait silently for processing. Narrate what should happen, then refresh.

### 2:35–3:20 — Safety differentiator

Simulate the SBI UPI outage and show the circuit breaker. Explain that RevenueGuard suppresses blind retries during systemic failures. Show the ₹50,000 human-approval threshold.

### 3:20–4:00 — Evidence

Show the experiment page and the committed offline evaluation:

- 523 held-out cases;
- 80.3% F1;
- +9.9 percentage-point absolute lift;
- p-value 0.025;
- sample-ratio-mismatch check passed.

Say explicitly that these are offline held-out results, while the dashboard shows the smaller live demo sample.

### 4:00–4:30 — Close

Summarize the business value: fewer wasted retries, safer recovery, explainable decisions, and measurable lift. End on the dashboard plus GitHub/live links.

## YouTube upload: first-time checklist

1. Sign in to [YouTube](https://www.youtube.com).
2. Click the camera-with-plus **Create** icon in the top-right.
3. Select **Upload video**.
4. Drop the final MP4 into the upload panel.
5. Use a clear title such as **RevenueGuard AI — Razorpay AI Buildathon 2026 Demo**.
6. Add the live dashboard and GitHub repository to the first lines of the description.
7. Choose **No, it is not made for kids**.
8. Continue through Video elements and Checks; neither needs special configuration for this demo.
9. Under Visibility, select **Unlisted**.
10. Click **Save**, copy the link, and open it in an incognito/private window.
11. Confirm playback reaches 1080p and captions/audio are understandable.
12. Replace the README's upload-pending note with this link and add the same link to the buildathon form.

Unlisted is preferable to Private: judges with the link can watch without being individually invited. Do not select Public unless you want the video searchable.

## Description template

    RevenueGuard AI — Razorpay AI Buildathon 2026, Track 03

    Live dashboard: https://revenueguard-ai-five.vercel.app
    API health: https://revenueguard-ai-2.onrender.com/api/health
    Source code: https://github.com/tusharg007/revenueguard-ai

    RevenueGuard AI detects failed payments, predicts recoverability, reasons about failure context, applies deterministic safety policies, and measures lift against a control baseline.

## Final validation

- Video duration is below five minutes.
- There is no visible secret, email, phone number, or local filesystem path.
- Narration is audible on a phone speaker.
- The dashboard and GitHub URLs are clickable in the description.
- The unlisted link works in an incognito/private window.
- The README video link has been replaced before final submission.
