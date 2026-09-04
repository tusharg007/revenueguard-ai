CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    razorpay_event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payment_id VARCHAR(255),
    order_id VARCHAR(255),
    raw_payload JSONB NOT NULL,
    received_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMPTZ,
    signature_valid BOOLEAN DEFAULT TRUE
);

CREATE TABLE recovery_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(50) UNIQUE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'detected',
    external_payment_id VARCHAR(255) NOT NULL,
    external_order_id VARCHAR(255),
    amount_paise INTEGER NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    failure_category VARCHAR(50) NOT NULL,
    failure_source VARCHAR(50) NOT NULL,
    failure_reason VARCHAR(255) DEFAULT '',
    error_code VARCHAR(100) DEFAULT '',
    customer_id VARCHAR(100) NOT NULL,
    customer_data JSONB NOT NULL,
    merchant_id VARCHAR(100) NOT NULL,
    recovery_probability FLOAT8,
    shap_reason_codes JSONB,
    experiment_arm VARCHAR(20),
    gateway_health_state VARCHAR(20),
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMPTZ,
    recovered_at TIMESTAMPTZ,
    recovered_amount_paise INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ
);
CREATE INDEX ix_recovery_cases_status ON recovery_cases(status);
CREATE INDEX ix_recovery_cases_event_type ON recovery_cases(event_type);
CREATE INDEX ix_recovery_cases_created_at ON recovery_cases(created_at);
CREATE INDEX ix_recovery_cases_experiment_arm ON recovery_cases(experiment_arm);

CREATE TABLE recovery_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(50) NOT NULL REFERENCES recovery_cases(case_id),
    action_type VARCHAR(50) NOT NULL,
    channel VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    input_state JSONB DEFAULT '{}'::jsonb,
    output_result JSONB DEFAULT '{}'::jsonb,
    cost_paise INTEGER DEFAULT 0,
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_recovery_actions_case_id ON recovery_actions(case_id);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(50) NOT NULL REFERENCES recovery_cases(case_id),
    action_id UUID REFERENCES recovery_actions(id),
    agent_name VARCHAR(100) NOT NULL,
    step VARCHAR(100) NOT NULL,
    input_summary TEXT DEFAULT '',
    output_summary TEXT DEFAULT '',
    reasoning TEXT DEFAULT '',
    guardrails_applied JSONB DEFAULT '[]'::jsonb,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_audit_logs_case_id ON audit_logs(case_id);

CREATE TABLE gateway_health_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank VARCHAR(50) NOT NULL,
    rail VARCHAR(50) NOT NULL,
    state VARCHAR(20) NOT NULL,
    success_rate FLOAT8 NOT NULL,
    technical_failure_rate FLOAT8 DEFAULT 0.0,
    sample_size INTEGER DEFAULT 0,
    snapshot_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    control_version VARCHAR(100) DEFAULT 'naive_retry_v1',
    variant_version VARCHAR(100) DEFAULT 'recovery_agent_v1',
    variant_split_pct INTEGER DEFAULT 20,
    min_sample_size INTEGER DEFAULT 1000,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE experiment_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id VARCHAR(100) NOT NULL REFERENCES experiments(experiment_id),
    case_id VARCHAR(50) NOT NULL REFERENCES recovery_cases(case_id),
    arm VARCHAR(20) NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_experiment_assignments_experiment_id ON experiment_assignments(experiment_id);

CREATE TABLE experiment_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id VARCHAR(100) NOT NULL REFERENCES experiments(experiment_id),
    metric VARCHAR(100) NOT NULL,
    control_value FLOAT8 NOT NULL,
    variant_value FLOAT8 NOT NULL,
    delta FLOAT8 NOT NULL,
    ci_lower FLOAT8 DEFAULT 0.0,
    ci_upper FLOAT8 DEFAULT 0.0,
    p_value FLOAT8 NOT NULL,
    is_significant BOOLEAN DEFAULT FALSE,
    sample_size_control INTEGER DEFAULT 0,
    sample_size_variant INTEGER DEFAULT 0,
    calculated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_experiment_results_experiment_id ON experiment_results(experiment_id);

CREATE TABLE recovery_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_id VARCHAR(100) UNIQUE NOT NULL,
    case_id VARCHAR(50) NOT NULL REFERENCES recovery_cases(case_id),
    payment_id VARCHAR(255) NOT NULL,
    amount_paise INTEGER NOT NULL,
    requested_action VARCHAR(50) NOT NULL,
    agent_recommendation TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'PENDING',
    requested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    approved_by VARCHAR(255),
    approved_at TIMESTAMPTZ,
    decision_channel VARCHAR(50)
);
CREATE INDEX ix_recovery_approvals_case_id ON recovery_approvals(case_id);

CREATE TABLE channel_bandit_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    segment VARCHAR(100) UNIQUE NOT NULL,
    bandit_state BYTEA NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
