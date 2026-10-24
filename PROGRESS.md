# PRECRIME AI - Progress Log

## Phase B: API, State Machine & Persistence (Completed)
- **Done**:
  - Implemented SQLite database schema with SQLAlchemy models: `investigations`, `scenarios`, `test_runs`, `evidence_records`, `stage_results`, `diagnoses`, `remediation_actions`, `audit_events`, `evaluation_results`.
  - Implemented sensitive key redaction utility in `app/redaction.py`.
  - Implemented synthetic demo adapter in `app/adapters/demo.py` (labels all records SYNTHETIC, never exposes ground truth).
  - Implemented read-only Wazuh connection tester in `app/adapters/wazuh.py` with TLS verification and audit logging.
  - Implemented evaluation batch runner in `app/evaluation/evaluator.py` and empirical metrics generator in `app/evaluation/metrics.py`.
  - Implemented FastAPI routers for investigations, test runs, human review / remediation approval state machine, scenarios listing (no ground truth), evaluation batch trigger, metrics, and report export (JSON/Markdown).
  - Verified 19 backend tests in 1.11s: state machine transitions, 409 enforcement, ground truth separation, metrics correctness, error handling with audit event persistence, and redaction.
- **Next**:
  - Phase C: Frontend scaffold (React + TypeScript + Vite + Tailwind + shadcn/ui minimal components), 4 screens wired to real backend endpoints, StatusBadge, MetricsPanel, report download, and Vitest suite.
- **Exact Run Commands**:
  - `cd backend; python -m pytest tests/ -q`
- **Known Issues**:
  - None.
