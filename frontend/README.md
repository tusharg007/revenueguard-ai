# RevenueGuard AI Dashboard

Next.js 14 operations console for the RevenueGuard AI payment-recovery system.

## Pages

- **Control Room:** live metrics, gateway summary, experiment snapshot, and simulation controls
- **Sandbox:** Razorpay test-mode checkout and webhook trace
- **Cases:** searchable recovery queue
- **Case detail:** ML score, reason codes, policy decisions, actions, approvals, and audit timeline
- **Experiments:** control/treatment recovery analysis
- **Gateway Health:** per-bank and per-rail health with circuit-breaker state

## Development

Create **frontend/.env.local**:

    NEXT_PUBLIC_API_URL=http://localhost:8000

Then run:

    npm ci
    npm run dev

Open [http://localhost:3000](http://localhost:3000).

## Quality checks

    npm run lint
    npm run build

## Production

Deploy the **frontend** directory as the Vercel project root and set:

    NEXT_PUBLIC_API_URL=https://revenueguard-ai-2.onrender.com

Live deployment: [revenueguard-ai-five.vercel.app](https://revenueguard-ai-five.vercel.app)

See the [root README](../README.md) and [deployment guide](../docs/SETUP_AND_DEPLOYMENT.md) for the full system.
