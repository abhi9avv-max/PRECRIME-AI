# PRECRIME AI

> **Find the failure. Prove the cause. Verify the fix.**

PRECRIME AI is an evidence-based SIEM detection-failure investigator designed for SOC analysts and security engineers investigating why an expected security alert did not appear.

**NON-NEGOTIABLE DEFINITION**:
- PRECRIME AI is **NOT** crime prediction, predictive policing, an AI chatbot, or a generic cybersecurity telemetry dashboard.
- It is an evidence-to-fix verification loop that identifies the **EARLIEST** evidence-supported failure in the log-to-alert pipeline, preserves uncertainty when telemetry is missing or conflicting, requires a recorded human review, and verifies recovery through an automated retest.
- All diagnostic logic is **100% deterministic backend Python code**. There are **zero LLM or AI API calls** anywhere in the system.
- All remediation actions are strictly **SIMULATED**; no external or production security system is altered.

---

## Assumptions

The following minimal operational assumptions were made during development:
1. **Pipeline Stage Lineage**: The security detection lifecycle is modeled as six sequential prerequisite stages: `event_generation` → `collection` → `parsing` → `rule_evaluation` → `alert_generation` → `delivery_visibility`. A failure at any upstream stage prevents downstream stages from functioning; downstream absence after an upstream failure is classified as `NOT REACHED` rather than a downstream failure.
2. **State Machine Strictness**: Gated authorization requires an analyst to record an explicit `ACCEPT` review before a simulated remediation can be approved. A rejected remediation transition is terminal. Retesting creates an immutable, distinct test run linked to the original parent run.
3. **Recovery Checks (RC1–RC5)**: True recovery requires passing all five checks:
   - **RC1**: Retest is a new run with matching scenario linked to parent.
   - **RC2**: Original run evidence hashes (`sha256`) remain completely unchanged.
   - **RC3**: The originally failed stage transitions to `PASS`.
   - **RC4**: All downstream stages transition to `PASS`.
   - **RC5**: The expected alert is verified delivered at `DEL-1`.
4. **Third-Party Integrations**: The Wazuh adapter is read-only and validates API authentication and TLS verification. Evidence collection from live Wazuh managers is marked as "not implemented" to prevent misleading synthetic vs live attribution.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 PRECRIME AI Frontend (Vite + React)         │
│  Screen 1: New Investigation & History                      │
│  Screen 2: Pipeline Trace (6 Stages, Evidence Modal)       │
│  Screen 3: Diagnosis Finding & Gated Fix Review             │
│  Screen 4: Retest & Comparison Report (RC1-RC5 Checks)     │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────┐
│                  FastAPI Backend (/api)                     │
│  ├── /investigations       (CRUD & Report Export JSON/MD)   │
│  ├── /runs                 (Initial Run & Retest Execution) │
│  ├── /diagnoses /reviews   (Human Acceptance State Machine) │
│  ├── /scenarios            (12 Cases; NO Ground Truth)      │
│  ├── /evaluation /metrics  (12-Case Benchmark Suite)        │
│  └── /integrations/wazuh   (Live Connection Verification)   │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────┐ ┌─────────────▼───────────────┐
│ Diagnostic Engine (Pure)    │ │ Persistence Layer (SQLite)  │
│  - stages.py                │ │  - investigations           │
│  - engine.py (Prereq & Cross)│ │  - test_runs & evidence     │
│  - recovery.py (RC1..RC5)   │ │  - diagnoses & remediation  │
│  - remediation.py           │ │  - audit_events & evaluation│
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## Environment Variables

Ship with `.env.example`. Copy to `.env` if custom parameters are required:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./precrime.db` | SQLAlchemy connection string |
| `PERSISTENCE_MODE` | `persistent` | Set to `ephemeral` for stateless container hosting |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed frontend origins |
| `WAZUH_API_URL` | `https://wazuh-manager.example.com:55000` | Wazuh API URL for connection check |
| `WAZUH_API_USER` | `wazuh-user` | Wazuh API user |
| `WAZUH_API_PASSWORD` | `secret` | Wazuh API user password |
| `WAZUH_VERIFY_TLS` | `true` | Enforces TLS certificate validation |

---

## Exact Run Commands

### 1. Backend Service

**PowerShell (Windows)**:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Bash (Linux / macOS)**:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Application

**PowerShell / Bash**:
```bash
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:5173`. The Vite proxy redirects `/api` calls directly to `http://localhost:8000`.

### 3. Automated Tests

**Backend Pytest**:
```bash
cd backend
python -m pytest tests/ -q
```

**Frontend Vitest**:
```bash
cd frontend
npm test
```

**Full End-to-End Journey Verification**:
```bash
cd backend
python tests/verify_journey.py
```

---

## Demo Script: `parsing_failure.a` Walkthrough

To verify the end-to-end evidence-to-fix verification loop:
1. Open the UI at `http://localhost:5173`.
2. Under **Start SIEM Detection-Failure Investigation**:
   - Title: `Missing user_name extracted field`
   - Telemetry Source: `Synthetic Demo`
   - Scenario Family: `PARSING_FAILURE`
   - Variant: `Variant A (Dev)`
   - Click **Start Investigation** (obvious primary button).
3. **Screen 2: Pipeline Trace**:
   - Observe the 6-stage node flow:
     - `Event Generation`: **PASS**
     - `Collection`: **PASS**
     - `Parsing`: **FAIL** (`Parser failed to extract required fields: ['user_name']`)
     - Downstream stages (`rule_evaluation`, `alert_generation`, `delivery_visibility`) evaluate to **NOT REACHED**.
   - Click the **Parsing** node to open the Evidence Drawer. Inspect the raw payload and notice `extracted_fields` has `src_ip` and `event_id`, but lacks `user_name`. Note the SHA-256 hash.
   - Click **Continue to Diagnosis**.
4. **Screen 3: Diagnosis & Fix**:
   - View Finding: `FAILURE_LOCALIZED` at stage `parsing`.
   - Click the supporting evidence reference pills to inspect raw checkpoint evidence.
   - Read the proposed simulated fix: `SIMULATED: no real system is modified. Update the decoder pattern to extract missing fields: [user_name].`
   - Notice the **Approve Simulated Fix** button is disabled.
   - Enter your reviewer name (e.g., `Analyst Alice`) and click **Accept Diagnosis**.
   - Now click **Approve Simulated Fix**. The remediation state transitions to `APPROVED` and execution status to `SIMULATED_APPLIED`.
   - Click **Continue to Retest**.
5. **Screen 4: Retest & Report**:
   - Click **Run Retest**.
   - View the **Before / After Comparison**:
     - Parsing transitions from `FAIL` → `PASS` (Recovered).
     - Downstream stages transition from `NOT REACHED` → `PASS`.
   - Verify the **Recovery Checks (RC1 – RC5)** checklist:
     - RC1 (Lineage): PASS
     - RC2 (Immutability of original hashes): PASS
     - RC3 (Remediated stage recovery): PASS
     - RC4 (Downstream pipeline integrity): PASS
     - RC5 (End-to-end alert delivery): PASS
   - Overall badge shows **VERIFIED** in green.
   - Click **Export JSON** or **Export Markdown** to download the comprehensive investigation report.

---

## Honest Limitations

1. **Synthetic Telemetry Baseline**: In demo mode, all checkpoint records are generated from structured synthetic fixtures. They accurately simulate detection failure patterns but do not represent live network traffic.
2. **Small Test Set**: The validation suite evaluates 12 reference scenario cases (6 development and 6 held-out).
3. **Simulated Remediation**: No production SIEM decoders, collectors, or rule files are altered. Remediation actions provide actionable templates and simulated state changes only.
4. **No Production Accuracy Claims**: Metrics are computed dynamically over the 12 synthetic cases. They prove deterministic engine correctness, not statistical generalization across unseen enterprise telemetry.
5. **Wazuh Live Evidence Collection**: The Wazuh adapter tests live authentication and TLS reachability only. Full telemetry harvesting from Wazuh indices is not implemented.
6. **No Binary Classification Metrics**: Precision, Recall, F1, and ROC-AUC are intentionally omitted; SIEM detection failure triage does not constitute a binary classification problem.

---

## Deployment Preparation

### Frontend (e.g. Vercel)
- Set environment variable `VITE_API_BASE_URL` to the public URL of your deployed backend.
- The repository includes `frontend/vercel.json` configuring standard SPA URL rewrites to `/index.html`.
- Build command: `npm run build`
- Output directory: `dist`

### Backend (e.g. Render, Railway, Fly.io)
- Verify the current terms of your chosen hosting provider (do not assume services remain indefinitely free).
- Start command:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- Environment variables:
  - `CORS_ORIGINS`: Your Vercel frontend URL (e.g. `https://precrime-ai.vercel.app`)
  - `DATABASE_URL`: `sqlite:///./precrime.db` or PostgreSQL connection string (e.g. `postgresql://user:pass@host/db`)
  - `PERSISTENCE_MODE`: Set to `ephemeral` if hosting on a stateless container without persistent volume disks. The health check endpoint (`/api/health`) will visibly report an ephemeral banner.
