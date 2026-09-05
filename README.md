# RevenueGuard AI

> Razorpay AI Buildathon 2026 · Track 03: AI Revenue Recovery

RevenueGuard AI turns failed-payment events into explainable, policy-safe recovery actions. It combines ML triage, gateway-health intelligence, a LangGraph decision agent, deterministic guardrails, human approval for high-value cases, and an A/B evaluation framework.

[![Live Dashboard](https://img.shields.io/badge/Live_Dashboard-Vercel-00897B?style=for-the-badge)](https://revenueguard-ai-five.vercel.app)
[![API Health](https://img.shields.io/badge/API-Healthy-2563EB?style=for-the-badge)](https://revenueguard-ai-2.onrender.com/api/health)
[![API Docs](https://img.shields.io/badge/OpenAPI-Docs-6B7280?style=for-the-badge)](https://revenueguard-ai-2.onrender.com/docs)
[![Repository](https://img.shields.io/badge/Source-GitHub-181717?style=for-the-badge&logo=github)](https://github.com/tusharg007/revenueguard-ai)
[![Watch Demo](https://img.shields.io/badge/Watch_Demo-YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/watch?v=LvwdreXkLb4)

## Watch the 4-minute product demo

[![Watch RevenueGuard AI — Intelligent Payment Recovery](https://i.ytimg.com/vi/LvwdreXkLb4/hqdefault.jpg)](https://www.youtube.com/watch?v=LvwdreXkLb4)

**[RevenueGuard AI — Intelligent Payment Recovery | Razorpay AI Buildathon 2026](https://www.youtube.com/watch?v=LvwdreXkLb4)**

The film is a fully automated, caption-led demonstration of the real product flow. It uses an isolated local environment, synthetic payment failures, a real Razorpay **test-mode** order, and a separately labelled locally signed webhook replay. No real payment is charged and no production recovery result is claimed.

## Product in one sentence

A recovery operations layer that understands *why* a payment failed, predicts whether recovery is likely, chooses the safest next action, and records evidence for every decision.

## Why it matters

Payment failures are not interchangeable. A bank timeout should be deferred until the rail stabilizes; insufficient funds should trigger a respectful customer nudge at a useful time; a business-rule failure may need human review. A conventional retry scheduler often treats all three as the same event and simply tries again after a fixed delay.

That creates a real merchant problem: unnecessary gateway calls during outages, repeated customer friction, poor recovery economics, and no defensible explanation of why an action was taken. At scale, even a small improvement in recovery rate can protect meaningful revenue—but aggressive automation can also damage customer trust or take unsafe actions. RevenueGuard is designed around both sides of that trade-off: **recover more when evidence supports it, and stop when it does not.**

RevenueGuard AI addresses that gap with:

- probability-based triage and SHAP reason codes;
- systemic, customer, and business failure classification;
- gateway circuit breakers that suppress harmful retries;
- deterministic policy checks before any action;
- human-in-the-loop approval above ₹50,000;
- stable control/treatment assignment and statistical reporting.

## Real-world use case

Imagine an online merchant processing subscriptions, loan repayments, insurance renewals, or high-value purchases through Razorpay:

1. A customer's ₹75,000 UPI payment fails while SBI is experiencing elevated technical failures and timeouts.
2. Razorpay sends a `payment.failed` webhook. RevenueGuard verifies its HMAC signature, deduplicates the event, normalizes it, persists a recovery case, and queues it for processing.
3. The ML triage model estimates recovery probability and exposes the most influential features as SHAP reason codes. The score is decision support—not permission to act.
4. Gateway-health intelligence recognizes that this is likely a rail-level problem rather than an isolated customer problem. The SBI/UPI circuit opens and changes the recommended strategy to **DEFER** instead of retrying into an outage.
5. The treatment agent diagnoses the failure, selects a strategy and channel, and records each step in an inspectable decision trace.
6. Deterministic policies enforce consent, quiet hours, retry limits, cooldowns, circuit state, and the high-value threshold. Because the amount exceeds ₹50,000, any non-STOP recovery action requires human approval.
7. After approval, the worker resumes from persisted state. Approval does not override the gateway circuit breaker; the action can still remain safely deferred.
8. The outcome is attributed to a stable experiment arm so the merchant can compare RevenueGuard with a fixed-retry baseline instead of trusting an impressive-looking dashboard.

The same control loop applies beyond outages. Customer-correctable failures can receive a respectful nudge, transient technical failures can be retried when conditions recover, and business or high-risk cases can be stopped or escalated.

### What each layer contributes

| Layer | Question answered | Output |
|---|---|---|
| Razorpay intake | Is this an authentic, new failure event? | Verified and deduplicated recovery case |
| ML triage | Is recovery likely to be worthwhile? | Probability plus SHAP reason codes |
| Gateway health | Is the bank/rail currently safe to retry? | Health snapshot, circuit state, retry/defer signal |
| Recovery agent | What strategy, channel, and timing fit this case? | Structured decision with an audit trace |
| Policy engine | Is the proposed action allowed? | Deterministic allow, stop, defer, or approval gate |
| Human approval | Should a high-value action proceed? | Persisted approve/reject decision |
| Experimentation | Does the system outperform the baseline? | Recovery lift, significance, and SRM checks |

## Live proof

These screenshots are captured from the deployed Vercel application backed by the public Render API. They are not design mockups.

![Recovery operations dashboard](docs/screenshots/dashboard.png)

<table>
<tr>
<td width="50%"><img src="docs/screenshots/cases.png" alt="Payment failure case queue"></td>
<td width="50%"><img src="docs/screenshots/sandbox.png" alt="Razorpay test-mode sandbox"></td>
</tr>
</table>

![Explainable recovery-case decision trace](docs/screenshots/case-detail.png)

![Control-versus-treatment experiment results](docs/screenshots/experiments.png)

- [Open the live control room](https://revenueguard-ai-five.vercel.app)
- [Watch the complete automated demo](https://www.youtube.com/watch?v=LvwdreXkLb4)
- [Inspect API health](https://revenueguard-ai-2.onrender.com/api/health)
- [Explore interactive OpenAPI docs](https://revenueguard-ai-2.onrender.com/docs)
- [View the public source repository](https://github.com/tusharg007/revenueguard-ai)

Render's free service may cold-start; allow roughly 15–30 seconds on the first request, then refresh the dashboard once.

## System architecture

### High-level recovery flow

<p align="center">
  <a href="docs/architecture-flow.svg">
    <img src="docs/architecture-flow.svg" width="100%" alt="RevenueGuard AI high-level architecture from Razorpay webhook intake through ML triage, gateway health, experiment routing, LangGraph recovery agent, deterministic policy, human approval, execution and dashboard">
  </a>
</p>

### Decision and safety architecture

<p align="center">
  <a href="docs/architecture.svg">
    <img src="docs/architecture.svg" width="100%" alt="RevenueGuard AI architecture: Razorpay intake, ML and gateway intelligence, LangGraph decisioning, deterministic policy, human approval, audit trail, dashboard and experimentation">
  </a>
</p>

### Decision path

1. Verify and deduplicate the failure event.
2. Persist the recovery case before queueing it.
3. Score recovery probability and produce human-readable reason codes.
4. Fuse internal failure windows with Razorpay gateway signals.
5. Assign the case to a stable control or treatment arm.
6. Select a recovery strategy, channel, and timing.
7. Apply deterministic guardrails and high-value approval.
8. Execute, audit, and publish live status updates.

## Evaluation evidence

Offline evaluation uses 523 held-out synthetic events committed with the repository. These results are separate from the small live demo sample shown in the dashboard.

| Metric | Result |
|---|---:|
| Precision | **80.2%** |
| Recall | **80.5%** |
| F1 score | **80.3%** |
| Treatment recovery rate | **47.5%** (122 cases) |
| Control recovery rate | 37.7% (401 cases) |
| Absolute lift | **+9.9 percentage points** |
| Relative lift | **+26.3%** |
| One-sided p-value | **0.025** |
| Sample-ratio-mismatch check | **Pass** (χ² 3.62, p 0.057) |

Reproducible artifacts:

- [Evaluation summary](evals/results/summary.json)
- [Per-case results](evals/results/rows.json)
- [Held-out event batch](data/test_batch.json)
- [Trained model artifacts](models)

## Technology

| Layer | Implementation |
|---|---|
| Agent | LangGraph StateGraph |
| Language model | Groq GPT-OSS 120B; OpenRouter fallback |
| ML and explainability | LightGBM, XGBoost, scikit-learn, SHAP |
| Channel optimization | Thompson Sampling with MABWiser |
| API | FastAPI, Pydantic v2, async SQLAlchemy |
| Data | PostgreSQL/Neon in production; SQLite for lightweight local development |
| Queue and health windows | Redis/Upstash |
| Frontend | Next.js 14, React Query, Recharts, Tailwind CSS |
| Payments | Official Razorpay Python SDK and signed webhooks |
| Hosting | Vercel frontend, Render API, Neon Postgres, Upstash Redis |

## Run locally

### Prerequisites

- Python 3.11
- Node.js 20 and npm
- Docker Desktop, for PostgreSQL and Redis
- Optional: Groq and Razorpay test credentials for the full agent and checkout paths

### 1. Clone and configure

    git clone https://github.com/tusharg007/revenueguard-ai.git
    cd revenueguard-ai

macOS/Linux:

    cp .env.example .env

Windows PowerShell:

    Copy-Item .env.example .env

For Docker-backed local infrastructure, set these values in **.env**:

    DATABASE_URL=postgresql+asyncpg://revenueguard:revenueguard@localhost:5432/revenueguard
    REDIS_URL=redis://localhost:6379

Simulation and read-only dashboard paths work without Razorpay credentials. Add **GROQ_API_KEY** for LLM reasoning and Razorpay test keys for checkout/webhook demonstrations.

### 2. Install and start infrastructure

    python -m venv .venv

macOS/Linux:

    source .venv/bin/activate

Windows PowerShell:

    .\.venv\Scripts\Activate.ps1

Then:

    python -m pip install --upgrade pip
    pip install -r requirements.txt
    docker compose up -d

### 3. Start the services

Terminal 1 — API:

    uvicorn backend.api.main:app --reload --port 8000

Terminal 2 — worker:

    python -m backend.worker

Terminal 3 — frontend:

    cd frontend
    npm ci
    npm run dev

Open [http://localhost:3000](http://localhost:3000). API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 4. Verify the stack

    curl http://localhost:8000/api/health
    curl -X POST http://localhost:8000/api/simulate/batch -H "Content-Type: application/json" -d "{\"count\": 25}"

The worker should consume queued cases while the control room updates.

Full setup and deployment notes: [docs/SETUP_AND_DEPLOYMENT.md](docs/SETUP_AND_DEPLOYMENT.md)

## Public API surface

| Method | Endpoint | Purpose |
|---|---|---|
| GET | **/api/health** | Liveness and environment |
| GET | **/api/metrics** | Recovery operations summary |
| GET | **/api/cases** | Paginated, filterable recovery cases |
| GET | **/api/cases/{case_id}** | Decision trace, actions, approvals, audit trail |
| GET | **/api/gateway-health** | Gateway and circuit-breaker snapshots |
| GET | **/api/experiments/{id}/results** | Control/treatment statistics |
| POST | **/api/simulate/batch** | Inject synthetic payment failures |
| POST | **/api/simulate/outage** | Generate a controlled gateway outage |
| POST | **/webhooks/razorpay** | Signed Razorpay webhook intake |
| WS | **/ws/events** | Live dashboard event stream |

## Deployment

The checked-in Dockerfile packages the Python API and worker code. The current public demo uses:

- **Vercel:** frontend, root directory **frontend**
- **Render:** Docker web service running the FastAPI command
- **Neon:** pooled PostgreSQL connection
- **Upstash:** TLS Redis connection
- **Local/managed worker:** **python -m backend.worker**

Required production environment variables are documented in [.env.example](.env.example). Never commit real keys.

For Vercel, set:

    NEXT_PUBLIC_API_URL=https://revenueguard-ai-2.onrender.com

The frontend also contains the public Render URL as a production fallback so a missing Vercel variable cannot silently point judges to localhost.

Register the Razorpay test webhook at:

    https://revenueguard-ai-2.onrender.com/webhooks/razorpay

Enable the **payment.failed** event and use the same signing secret as **RAZORPAY_WEBHOOK_SECRET**.

## Safety and trust

- Raw webhook bodies are HMAC-SHA256 verified before parsing.
- Razorpay event IDs provide idempotency.
- Cases are committed before queueing, preventing worker read races.
- High-value actions require approval.
- Quiet hours, retry caps, cooldowns, and gateway state are enforced deterministically.
- Public customer responses exclude internal recovery context.
- Credentials are environment variables and ignored by Git.

## Honest limitations

- The hosted free API can cold-start.
- A continuously running worker is not included in the free Render web service; the demo worker is run separately.
- Thompson Sampling needs sustained outcome history to converge; the hackathon build is warm-started.
- Customer delivery integrations remain sandbox/simulated where provider approval is required.
- Database migrations should replace **create_all** before production use.

## Repository map

    backend/                 FastAPI, agent graph, policies, worker, integrations
    data/                    Synthetic generator and held-out event batch
    demo/                    Automated capture, composition, validation and film manifest
    evals/                   Batch evaluator and committed results
    frontend/                Next.js operations dashboard
    models/                  Trained model and explainability artifacts
    tests/                   Regression tests for enqueueing, timestamps, strategy
    docs/                    Setup, deployment, recording guide, screenshots
    Dockerfile               Production API image
    docker-compose.yml       Local PostgreSQL and Redis
    render.yaml              Render deployment reference

## What the demo shows

The published [4:04 product film](https://www.youtube.com/watch?v=LvwdreXkLb4) is structured as one recovery story rather than a page-by-page tour:

| Time | Scene | What happens | What it proves |
|---:|---|---|---|
| 00:00 | The problem | Failed payments are framed as different failure classes, not one retry queue. | Blind retries can waste calls, increase friction, and retry into outages. |
| 00:20 | Recovery Operations | The control room shows active failures, revenue at risk, recovered revenue, and recovery rate. | RevenueGuard gives operators one operational view of exposure and outcomes. |
| 00:28 | Recovery batch | The demo submits 50 synthetic failures through the actual API, Redis queue, worker, and decision pipeline. | The dashboard is backed by a running system, not static mock data. |
| 00:52 | SBI outage | Controlled SBI/UPI technical failures are injected and Gateway Health opens the circuit. | Systemic rail degradation changes the recovery strategy to DEFER. |
| 01:25 | Explainable case | A treatment case shows ML probability, SHAP reason codes, decision timeline, and agent trace. | AI contributes triage and structured reasoning while remaining inspectable. |
| 02:19 | Deterministic policy | The proposed action passes through explicit policy checks. | Model output alone cannot authorize execution. |
| 02:31 | Human approval | A ₹75,000 case enters PENDING, is approved in the UI, persists its history, and resumes in the worker. | High-value actions retain human control; approval still cannot bypass an open circuit. |
| 03:04 | Razorpay integration | The app creates a real Razorpay test-mode order, then separately demonstrates invalid-signature rejection, valid signed intake, and duplicate suppression using a labelled local replay. | The integration uses real test APIs and the actual webhook verification/idempotency path without making a charge. |
| 03:30 | Experiments | The live experiment view transitions to the committed held-out evaluation. | RevenueGuard is judged against a baseline with lift, significance, and experiment-integrity checks. |
| 03:59 | Close | Explainable AI, deterministic safety, and measurable recovery are restated. | The product's value and trust model resolve into one message. |

### How the film was produced

The demo is fully automated and requires no manual narration or browser operation. A deterministic runner starts an isolated local stack, prepares safe synthetic scenarios, drives the real UI with semantic Playwright selectors, records validated browser footage, and composes the final 1920×1080 video with captions, eased cursor movement, original synthesized background audio, and subtle UI sounds.

Expected UI states are defined in a machine-readable timeline. If an important state is missing, capture stops and writes a diagnostic instead of fabricating a successful screen. Startup latency and loading waits are excluded from the finished edit.

- [Demo pipeline and reproduction guide](demo/README.md)
- [Machine-readable timeline](demo/timeline.json)
- [Editorial shot list and claim boundaries](demo/shot-list.md)
- [Accessible subtitle file](demo/final/revenueguard-buildathon-demo.srt)

The final MP4 is hosted on YouTube rather than committed to Git history. Local exports remain under `demo/final/` and are ignored by Git because video binaries unnecessarily enlarge repository clones.

## License

Released under the [MIT License](LICENSE).
