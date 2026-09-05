# RevenueGuard — product film

Target: 4:04, 1920×1080, 30 fps. Caption-led, original synthesized audio, no narration.
All browser scenes run against an isolated local database and dedicated Redis instance.

## Capability selection (editorial ranking, 1–10)

| Capability | Judge impact | Uniqueness | Business value | Visual clarity | Technical depth | Trust |
|---|---:|---:|---:|---:|---:|---:|
| Rail-level circuit breaker changes strategy | 10 | 9 | 10 | 9 | 9 | 10 |
| Enforced high-value approval and persisted resumption | 10 | 8 | 10 | 9 | 9 | 10 |
| Real ML probability, SHAP and graph audit | 9 | 9 | 9 | 8 | 10 | 9 |
| Reproducible offline policy evaluation | 10 | 8 | 10 | 10 | 9 | 10 |
| Signed intake with duplicate rejection | 8 | 7 | 9 | 7 | 9 | 10 |
| Test-mode Razorpay order | 8 | 6 | 8 | 9 | 7 | 8 |

## Story and shooting plan

| Time | Shot | Purpose |
|---|---|---|
| 00:00–00:12 | Original title treatments | Different failures need different responses |
| 00:12–00:28 | Control Room | Revenue exposure, not dashboard tourism |
| 00:28–00:52 | Actual batch + updated metrics | Establish the failed-payment workload |
| 00:52–01:25 | Actual outage + gateway health | Show circuit OPEN and recommended DEFER |
| 01:25–02:31 | Selected real treatment case | Probability → SHAP → diagnosis → policy |
| 02:31–03:04 | ₹75,000 approval | Pending, approve, persisted history and worker resumption |
| 03:04–03:30 | Razorpay sandbox + signed replay evidence | Real test order; separately labelled synthetic signed replay |
| 03:30–03:59 | Experiments + editorial evaluation cards | Distinguish live operational sample from offline simulated evidence |
| 03:59–04:04 | Original close | Explainability, safety, measurement |

## Claim boundaries

- Offline recovery outcomes are simulated by `evals/batch_runner.py`; this is not a production or live LLM uplift measurement.
- 523 held-out synthetic events, F1 80.3%; control 151/401, treatment 58/122; +9.9 pp, +26.3%, one-sided p=0.025. SRM passes its configured 0.01 threshold.
- Do not describe the one-sided result as a two-sided 95% confidence result.
- Assignment is per case, not per customer. No real charges or messages are needed for selected DEFER cases.
- The sandbox's apparent webhook indicators are not sufficient correlation proof. Instead independently exercise the HMAC/idempotency endpoint with a locally signed synthetic event, labelled as such.
- Approval demonstrates implemented prototype controls, not a guarantee of production financial safety.

## Failures and revisions

Missing states must fail capture with a diagnostic image. Never substitute fabricated UI. External checkout is excluded; a test order plus deterministic signed replay is the reliable integration story. Capture waits are trimmed before composition. Review contact sheets, source frames, caption clearance, audio and decode before final delivery.
