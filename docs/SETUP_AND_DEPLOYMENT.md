# Setup and Deployment

This guide reproduces RevenueGuard AI locally and documents the public hackathon deployment.

## Local development

### Required software

- Python 3.11
- Node.js 20 with npm
- Docker Desktop

### Configure the repository

    git clone https://github.com/tusharg007/revenueguard-ai.git
    cd revenueguard-ai

Create the local environment file:

    Copy-Item .env.example .env

For macOS/Linux use **cp .env.example .env**.

Start PostgreSQL and Redis:

    docker compose up -d

Set the following local values in **.env**:

    APP_ENV=development
    DATABASE_URL=postgresql+asyncpg://revenueguard:revenueguard@localhost:5432/revenueguard
    REDIS_URL=redis://localhost:6379
    NEXT_PUBLIC_API_URL=http://localhost:8000

The simulation pipeline does not require Razorpay credentials. Add **GROQ_API_KEY** for full LLM reasoning. Add Razorpay test credentials only when exercising checkout or signed webhooks.

### Python services

    python -m venv .venv

Activate the environment:

- Windows: **.\.venv\Scripts\Activate.ps1**
- macOS/Linux: **source .venv/bin/activate**

Install dependencies and start the API:

    python -m pip install --upgrade pip
    pip install -r requirements.txt
    uvicorn backend.api.main:app --reload --port 8000

In a second activated terminal:

    python -m backend.worker

### Frontend

In a third terminal:

    cd frontend
    npm ci
    npm run dev

Open [http://localhost:3000](http://localhost:3000).

### Smoke test

    curl http://localhost:8000/api/health
    curl http://localhost:8000/api/metrics

Inject a deterministic demo workload:

    curl -X POST http://localhost:8000/api/simulate/batch -H "Content-Type: application/json" -d "{\"count\": 25}"

Expected behavior:

1. The API returns 25 created case IDs.
2. Redis receives case IDs.
3. The worker moves cases through triage and policy evaluation.
4. The dashboard refreshes metrics and recent events.
5. Treatment cases contain an agent decision trace; control cases use the fixed baseline.

## Run tests and builds

Backend:

    python -m pytest -q

Frontend:

    cd frontend
    npm run lint
    npm run build

Evaluation:

    python -m evals.batch_runner

The evaluation command updates files under **evals/results**. Review those diffs before committing.

## Production environment

### Backend on Render

Create a Docker web service from the repository.

- Dockerfile: **./Dockerfile**
- Health check: **/api/health**
- API command: provided by Dockerfile
- Public service used by this submission: [revenueguard-ai-2.onrender.com](https://revenueguard-ai-2.onrender.com)

Configure:

    APP_ENV=production
    DATABASE_URL=<Neon pooled PostgreSQL URL>
    REDIS_URL=<Upstash rediss:// URL>
    LLM_PROVIDER=groq
    LLM_MODEL=openai/gpt-oss-120b
    GROQ_API_KEY=<secret>
    RAZORPAY_KEY_ID=<test key>
    RAZORPAY_KEY_SECRET=<secret>
    RAZORPAY_WEBHOOK_SECRET=<secret>

Keep all secrets in the hosting dashboards. Do not place them in Vercel public variables or repository files.

### Worker

Run the same source with:

    python -m backend.worker

A continuously running worker normally needs a paid worker service or another always-on runtime. For the hackathon demo it can run locally against the production Neon and Upstash URLs. Keep those secrets only in the local **.env** file.

### Frontend on Vercel

Import the GitHub repository and set:

- Root directory: **frontend**
- Framework preset: Next.js
- Install command: **npm ci**
- Build command: **npm run build**
- Environment variable: **NEXT_PUBLIC_API_URL=https://revenueguard-ai-2.onrender.com**

The code has the same public API as a production fallback; the environment variable remains the recommended configuration.

### Razorpay webhook

Register:

    https://revenueguard-ai-2.onrender.com/webhooks/razorpay

Enable **payment.failed** and set the same secret in Razorpay and Render. Use test-mode keys for the hackathon demonstration.

## Post-deployment checks

Open or call each link:

1. [API health](https://revenueguard-ai-2.onrender.com/api/health) returns status **ok** and environment **production**.
2. [OpenAPI docs](https://revenueguard-ai-2.onrender.com/docs) renders.
3. [Dashboard](https://revenueguard-ai-five.vercel.app) loads without localhost requests.
4. **/api/metrics** and **/api/cases** return the expected demo dataset.
5. The sandbox page reports whether Razorpay test credentials are connected.
6. The GitHub README screenshots match the deployed UI.

Render may take 15–30 seconds to wake on the first request.
