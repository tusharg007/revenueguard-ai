# RevenueGuard AI

> Razorpay AI Buildathon 2026 · Track 03: AI Revenue Recovery

RevenueGuard AI turns failed-payment events into explainable, policy-safe recovery actions. It combines ML triage, gateway-health intelligence, a LangGraph decision agent, deterministic guardrails, human approval for high-value cases, and an A/B evaluation framework.

[![Live Dashboard](https://img.shields.io/badge/Live_Dashboard-Vercel-00897B?style=for-the-badge)](https://revenueguard-ai-five.vercel.app)
[![API Health](https://img.shields.io/badge/API-Healthy-2563EB?style=for-the-badge)](https://revenueguard-ai-2.onrender.com/api/health)
[![API Docs](https://img.shields.io/badge/OpenAPI-Docs-6B7280?style=for-the-badge)](https://revenueguard-ai-2.onrender.com/docs)
[![Repository](https://img.shields.io/badge/Source-GitHub-181717?style=for-the-badge&logo=github)](https://github.com/tusharg007/revenueguard-ai)

> **Demo video:** upload pending. The final unlisted YouTube link will be placed here before submission.

## Product in one sentence

A recovery operations layer that understands *why* a payment failed, predicts whether recovery is likely, chooses the safest next action, and records evidence for every decision.

## Why it matters

Payment failures are not interchangeable. A bank timeout should be deferred until the rail stabilizes; insufficient funds should trigger a respectful customer nudge; a business-rule failure may need human review. Blindly retrying every failure wastes gateway calls, increases customer fatigue, and gives operations teams no defensible audit trail.

RevenueGuard AI addresses that gap with:

- probability-based triage and SHAP reason codes;
- systemic, customer, and business failure classification;
- gateway circuit breakers that suppress harmful retries;
- deterministic policy checks before any action;
- human-in-the-loop approval above ₹50,000;
- stable control/treatment assignment and statistical reporting.

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

- [Open the live control room](https://revenueguard-ai-five.vercel.app)
- [Inspect API health](https://revenueguard-ai-2.onrender.com/api/health)
- [Explore interactive OpenAPI docs](https://revenueguard-ai-2.onrender.com/docs)
- [View the public source repository](https://github.com/tusharg007/revenueguard-ai)

Render's free service may cold-start; allow roughly 15–30 seconds on the first request, then refresh the dashboard once.

## System architecture

~~~mermaid
flowchart TD
    RZ[Razorpay webhook] -->|HMAC verification + idempotency| API[FastAPI]
    API --> DB[(PostgreSQL)]
    API --> Q[(Redis queue)]
    Q --> W[Recovery worker]
    W --> ML[LightGBM triage + SHAP]
    W --> GH[Gateway health + circuit breaker]
    ML --> EXP[A/B assignment]
    GH --> EXP
    EXP -->|Control| BL[Fixed retry baseline]
    EXP -->|Treatment| AG[LangGraph recovery agent]
    AG --> D[Diagnosis]
    D --> S[Strategy]
    S --> CH[Channel selection]
    CH --> PE[Policy engine]
    PE -->|amount > ₹50K| HITL[Human approval]
    PE --> EX[Execute or simulate]
    HITL --> EX
    API --> UI[Next.js operations dashboard]
~~~

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
    evals/                   Batch evaluator and committed results
    frontend/                Next.js operations dashboard
    models/                  Trained model and explainability artifacts
    tests/                   Regression tests for enqueueing, timestamps, strategy
    docs/                    Setup, deployment, recording guide, screenshots
    Dockerfile               Production API image
    docker-compose.yml       Local PostgreSQL and Redis
    render.yaml              Render deployment reference

## Demo recording

The recommended submission workflow is **OBS Studio + your own narration + YouTube Unlisted**. It avoids Loom's hard five-minute cutoff and keeps the final link accessible to judges. Use the exact checklist in [docs/DEMO_VIDEO_GUIDE.md](docs/DEMO_VIDEO_GUIDE.md).

## License

Released under the [MIT License](LICENSE).
