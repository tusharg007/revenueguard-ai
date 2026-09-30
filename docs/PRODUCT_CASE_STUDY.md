# RevenueGuard AI — Product Case Study

> Razorpay AI Buildathon 2026 · Track 03: AI Revenue Recovery
>
> [Live product](https://revenueguard-ai-five.vercel.app) · [Product demo](https://www.youtube.com/watch?v=LvwdreXkLb4) · [Source](https://github.com/tusharg007/revenueguard-ai)

## 1. User & Problem

**Primary user:** a merchant's payments or revenue operations team. Approvers control consequential actions; engineers investigate failures and audit decisions.

A failed payment is a symptom, not a diagnosis. A bank outage, insufficient funds, an abandoned attempt, and a business-rule rejection call for different responses. A fixed retry schedule can send traffic into an unhealthy rail, contact customers at the wrong time, and spend money on cases unlikely to recover.

The operator needs to answer: **What happened? What should we do next? Why is that action safe?** Without a case-level record and control group, the team cannot tell whether a smarter workflow improves outcomes.

User pain includes unnecessary retries and gateway calls, customer friction, retries during outages, automation that is hard to explain, and no measurable control-versus-treatment view.

## 2. Product Goal

For each failed payment, help an operator decide whether to **retry, defer, contact the customer, stop, or request human review**. The recommendation should account for the failure cause, predicted recoverability, current gateway conditions, customer context, and policy constraints. Every decision should leave an inspectable trace.

The goal is to recover eligible revenue while suppressing harmful actions and measuring improvement against a baseline.

## 3. Non-Goals

- Autonomous movement of real money or a real charge in the demo.
- Replacing Razorpay or another payment gateway. RevenueGuard is an operations and decision layer around payment events.
- Fully autonomous high-value actions. Under the configured policy, a non-STOP action **above ₹50,000** requires approval.
- Claiming production recovery impact or live LLM uplift from synthetic evaluation.
- Equating a scheduled retry, queued message, or approval with a recovered payment. Some prototype actions are scheduled or logged rather than delivered.

## 4. MVP Scope

These priorities describe the order in which the product becomes useful and trustworthy. They are not claims that P2 features are missing from the repository.

| Priority | Capability | Why this priority? |
|---|---|---|
| P0 | Failed-payment ingestion | An authentic, deduplicated event is the foundation of every case. |
| P0 | Failure classification | Different causes require different actions; this prevents one-size-fits-all retries. |
| P0 | Recovery recommendation | Operators need a concrete next step and timing, not only an error code. |
| P0 | Deterministic policy checks | Consent, retry limits, cooldowns, quiet hours, and cost constraints must be enforced independently of model output. |
| P0 | Dashboard | Operations needs a visible queue, exposure, status, and decision history. |
| P0 | Persistent case state | Cases, actions, and audit entries must survive queue processing and remain reviewable. |
| P1 | Human-in-the-loop approval | High-value actions need explicit control once the core workflow exists. |
| P1 | SHAP explanations | Reason codes make the ML score useful for investigation and challenge. |
| P1 | Gateway circuit state | Bank and rail health can suppress retries into an outage once telemetry is available. |
| P1 | Control/treatment experimentation | A stable comparison distinguishes measured value from a persuasive demo. |
| P2 | Channel optimization | Learning the best contact channel requires enough outcome history. |
| P2 | Richer gateway/provider integration | Wider live signals and delivery channels need provider access and operational validation. |

## 5. User Stories & Acceptance Criteria

### Diagnose before acting

**As a revenue-operations user,** I want to understand why a payment failed so that I do not blindly retry it.

Acceptance criteria:

- Failure class and source are visible on the case.
- Recovery probability and ML reason codes are visible when scoring succeeds.
- The relevant bank/rail health state is visible.
- An unsafe proposed action is blocked or changed to a safe outcome by the decision path and deterministic policy.
- The case retains a decision and audit timeline.

### Control a consequential action

**As an approver,** I want high-value recovery actions to require confirmation so that consequential automation remains controlled.

Acceptance criteria:

- A non-STOP action for an amount strictly above the configured ₹50,000 threshold enters **PENDING** before execution.
- Approval or rejection persists with the case and a timestamp.
- After approval, the case is queued again and the worker rebuilds its state from persisted records.
- Approval does not bypass other safety decisions, including an open gateway circuit.
- The approval and action history remain visible to the operator.

### Measure the change

**As a product owner,** I want a baseline comparison so that I can decide whether broader testing is warranted.

Acceptance criteria:

- Each case receives consistent control or treatment assignment.
- Control follows a fixed retry baseline; treatment follows the RevenueGuard decision workflow.
- Results show sample sizes, recovery rates, lift, a statistical test, and a sample-ratio-mismatch check.
- Offline synthetic results are labelled separately from live operational metrics.

## 6. Key Product Decisions

### AI reasoning plus deterministic rules

ML estimates whether recovery is promising; the treatment agent diagnoses the case and proposes a strategy. Their outputs can vary. The policy engine applies hard constraints before execution, and the execution path rechecks approval. This lets recommendations adapt while keeping safety decisions predictable and auditable.

### Human approval above ₹50,000

A poor action can have greater consequences as the amount rises. The configured threshold adds deliberate review for non-STOP actions above ₹50,000. It is a prototype policy choice to test with merchants and risk teams, not a universal financial rule.

### Circuit breaker before retry

A local failure can be worth retrying; a rail-wide failure calls for restraint. Gateway health considers recent technical failures and sample size, then applies cooldown and probe behavior. The treatment strategy can defer while the rail is unhealthy, even after an approver confirms the case.

### Audit trail and experiment assignment

Persisted reason codes, decisions, actions, and approvals make individual cases reviewable. Stable per-case assignment makes the aggregate comparison reproducible. A future merchant experiment should assess customer-level assignment to reduce cross-case interference.

## 7. Success Metrics

| Type | Metric | Product question |
|---|---|---|
| Primary | Recovery rate among eligible failed payments | Does the workflow recover more payments than the baseline? |
| Supporting | Successfully recovered payment count and value | Is the lift commercially meaningful? |
| Supporting | Unsafe retries deferred or suppressed | Is gateway awareness reducing harmful attempts? |
| Supporting | Recommendation precision, recall, and F1 | Does triage identify recoverable cases accurately? |
| Supporting | Approval conversion and time to decision | Is human review effective without stalling cases? |
| Guardrail | Policy-violating automated actions | Target: **zero**; investigate every violation. |

Report live operational metrics separately from offline evaluation. A scheduled retry, queued notification, or approved case is not itself a successful recovery.

## 8. Experiment

**Control:** fixed retry behavior.

**Treatment:** RevenueGuard's decision workflow in the offline simulator, using ML triage, gateway context, and policy decisions.

The committed [evaluation summary](../evals/results/summary.json) covers **523 held-out synthetic events**. Simulated recovery outcomes are 151/401 for control (**37.7%**) and 58/122 for treatment (**47.5%**): **+9.9 percentage points** absolute lift, or **+26.3%** relative lift. The one-sided p-value is approximately **0.025**, and the sample-ratio-mismatch check passes its configured threshold. Triage F1 is **80.3%**.

**Evidence boundary:** This is an **OFFLINE SYNTHETIC evaluation** with simulated recovery outcomes. It does not demonstrate production payment recovery or end-to-end live LLM uplift. The two-sided 95% interval in the artifact crosses zero, so the one-sided result should not be described as two-sided 95% significance. A real merchant rollout would require production instrumentation, risk review, and a prospective experiment.

## 9. What I Would Test Next

1. **Retry timing:** compare immediate, cooldown-based, and gateway-recovery-triggered attempts while monitoring customer friction.
2. **Communication channel:** measure recovery and opt-outs across email, SMS, WhatsApp, and payment links where consent and delivery integrations allow.
3. **Approval threshold:** test whether different amount bands and failure types need different review paths; measure risk and delay.
4. **Gateway-health thresholds:** tune sample size, failure-rate trigger, cooldown, and reopening probes against false outage alarms.
5. **Customer-segment strategies:** test whether payment history and preferred channel help without excessive or unfair contact.

Each test needs a baseline, predefined success and guardrail metrics, and enough observations to support a decision.

## 10. Build Workflow

The build followed a product-to-evidence loop:

1. **Problem decomposition:** split payment recovery into intake, diagnosis, gateway context, recommendation, policy, approval, and measurement.
2. **Specification:** define operator decisions, observable case states, hard constraints, and what the demo could honestly prove.
3. **AI-assisted prototyping:** use AI assistance to accelerate implementation alternatives, interface copy, synthetic scenarios, and demo automation.
4. **Manual code review:** check payment integration boundaries, persistence, idempotency, approval paths, and product claims against code.
5. **Tests:** exercise API and worker behavior; inspect representative cases, approval transitions, and evaluation artifacts.
6. **Deployment:** connect the Next.js frontend, FastAPI backend, data services, and Razorpay test-mode configuration.
7. **Measurement:** compare baseline and treatment on held-out synthetic data, with the result labelled as such.
8. **Iteration:** use failure states and evidence gaps to improve the product, safeguards, documentation, and demo.

AI accelerated drafts and implementation options. The product judgments required my own reasoning: selecting the operations problem, deciding which actions needed blocking or review, choosing the prototype approval rule, defining meaningful evaluation metrics, and keeping synthetic lift distinct from production impact.
