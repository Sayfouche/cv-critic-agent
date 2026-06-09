# CV Critic Agent

[![CI](https://github.com/Sayfouche/cv-critic-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Sayfouche/cv-critic-agent/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Multi-agent CV audit workflow — independent critics + strategy synthesizer — built three times to compare orchestration patterns: custom Node.js, intermediate CrewAI Python script, and CrewAI-native package.

## The problem

Self-reviewing your own CV is unreliable: you over-trust your own framing, you re-read what you wrote instead of what a recruiter sees. This repo runs a deliberate two-step process:

1. **Two independent critics** read only the public CV/portfolio/chatbot — they never see your internal decisions, so they react like a real recruiter.
2. **One strategy agent** reads `context.md` (your locked-in editorial constraints) plus the two critique reports — and turns them into a P0/P1/P2 plan that does not contradict your prior decisions.

Output is a versioned report folder per run, plus a `latest/` directory always pointing to the most recent run.

## Why three implementations?

This repo is also a deliberate migration study. The same workflow is implemented three ways, all producing the same output contract:

| Version | Path | What it shows |
|---|---|---|
| **v1 — Custom Node.js** | `legacy-node/run.mjs` | Plain orchestration with raw HTTP/SDK calls. Honest baseline, no framework. |
| **v2 — CrewAI script** | `scripts/crew_script.py` | Intermediate Python step using the shared workflow function before adopting CrewAI's Agent/Task/Crew API. |
| **v3 — CrewAI native** | `src/cv_critic_agent/` | Idiomatic CrewAI: roles, backstories, sequential process, automatic context passing between tasks via `context=[task_global, task_cv]`. |

All three share the same prompt templates, the same source-reading logic, and the same output contract — making the comparison apples-to-apples.

## Key technical decisions

### Mistral as default, Anthropic as fallback

Iteration on a CV critic is expensive if you pay Claude prices per run. Mistral is fast and cheap enough to run on every editorial change. Anthropic remains available for high-stakes runs:

```bash
CV_CRITIC_PROVIDER=mistral      # default
CV_CRITIC_MODEL=mistral-medium-latest
```

### Custom CrewAI BaseLLM adapter for Mistral

CrewAI's LiteLLM bridge forwards internal cache fields (`cache_breakpoint`) that the Mistral API rejects. Rather than wait upstream, `MistralCrewLLM` extends `BaseLLM` directly and sends only Mistral-supported fields. This keeps the CrewAI Agent/Task/Crew model intact while bypassing the broken bridge.

### Independent critics, contextual strategy

The two critic agents do **not** read `context.md`. That's intentional: critics simulate an outside view (recruiter, hiring manager, client) that has no access to your internal positioning notes. The strategy agent reads `context.md` to ensure its recommendations don't contradict frozen decisions (title, project narratives, scope boundaries).

A regression test guards this separation across all three implementations.

### Mock LLM for tests

`MockLLM` accepts an injectable `responses` dict, so tests can verify the pipeline behaviour without depending on prompt template internals or making any API calls. Tests cover prompt isolation, output contract parity across the three implementations, and Mistral message cleaning.

## Phase 5 — Access gate

Mock runs stay free for anyone. Real Mistral runs go through an approval gate: form → owner review (Telegram + email) → emailed session link. Full plan in [`docs/PHASE5_ACCESS_GATE.md`](docs/PHASE5_ACCESS_GATE.md).

### Flow

```
POST /api/access-requests        Turnstile + honeypot + rate-limit + PII Fernet-encrypted at rest
GET  /api/access-requests/{id}/status
GET  /api/access-requests/{id}/decide        HMAC link sent to owner (idempotent, 7 d TTL)
POST /api/telegram/webhook                   approve/reject from chat (owner chat_id verified)
POST /api/admin/login                        magic link to OWNER_EMAIL, oracle-safe
POST /api/runs   X-Session-Token             real run; IP-bind, quota, budget cap
POST /api/cron/cleanup   X-Cleanup-Secret    nightly TTL sweep + budget file rotation
```

### Token taxonomy

| Token | `sub` | TTL | Carrier |
|---|---|---|---|
| Decision link | `decide` + `accept: 0\|1` | 7 d | Owner Telegram / email |
| Requester session | `session` | 24 h | `X-Session-Token` header |
| Admin magic link | `admin-magic` | 30 min | Email link |
| Admin session | `admin-session` | 24 h | `X-Admin-Session` header / localStorage |

### Budget cap + degrade

`BudgetTracker` meters output tokens per UTC day. At 80 % and 100 % a Telegram alert fires once (idempotent). Past 100 % real runs degrade silently to mock — the response carries `degraded: true`. Default cap: 200 000 tokens (~$5/day on Mistral medium).

### What lives where

- `security/` — HMAC tokens, Fernet PII, slowapi limiter, Turnstile verify, security headers.
- `access_requests/` — dataclass + 6-state machine + JSON-on-disk store with fcntl + lazy TTL + `atomic_consume_run`.
- `notifier/` — Telegram (owner pending, budget alert) + Resend (approved, rejected, admin magic link). Every external call is fail-soft.
- `budget/` — daily tracker (fcntl + flush), wiring helper (`record_real_run`), 80/100 % alerts.
- `cron_router.py` — `POST /api/cron/cleanup` (constant-time secret compare, idempotent).

Backend: 288 unittest cases. No real HTTP in tests — every async client is injected via `http_client_factory=`.

## Quick start

### Install

```bash
git clone https://github.com/Sayfouche/cv-critic-agent.git
cd cv-critic-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[server]"
```

### Run with mock LLM (no API key required)

```bash
python -m cv_critic_agent --mock
```

### Run with real LLM

```bash
cp .env.example .env.local
# Edit .env.local — set MISTRAL_API_KEY (or ANTHROPIC_API_KEY)
python -m cv_critic_agent
```

### Run the other implementations

```bash
PYTHONPATH=src python scripts/crew_script.py --mock   # v2 (intermediate)
node legacy-node/run.mjs --mock                       # v1 (Node.js)
```

### Run the API and UI locally

```bash
# terminal 1 — FastAPI
python -m cv_critic_agent --serve --port 8000

# terminal 2 — Next.js UI
cd ui
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000. The current UI launches mock runs by default. The API already supports protected real runs with `CV_CRITIC_API_TOKEN`.

## Output contract

Every implementation produces the same files:

```
reports/<YYYY-MM-DDTHH-MM-SSZ>/
├── global.md           # External critic — full portfolio audit
├── printable-cv.md     # External critic — downloadable CV only
├── strategy.md         # Strategy synthesis with P0/P1/P2 plan
└── summary.md

reports/latest/         # Same four files, always pointing to most recent run
```

## Source files

The agent runs against snapshots of the target portfolio's source files (`sources/data.ts`, `sources/chatbot-knowledge.ts`, etc.). They are versioned in this repo so the agent stays runnable in isolation.

To refresh from a `cv-portfolio` checkout:

```bash
python scripts/sync_sources.py /path/to/cv-portfolio
python scripts/sync_sources.py /path/to/cv-portfolio --check   # exit 1 if drift
```

## Tests

```bash
python -m pytest
```

All tests use a mock LLM and make zero API calls. The Phase 5 endpoints stub HTTP via `http_client_factory=` injection — no Telegram / Resend / Turnstile traffic in CI. Coverage:
- Prompt isolation (critics don't leak `context.md`, strategy does include it)
- Output contract parity across the three implementations
- Mistral message cleaning (`cache_breakpoint` stripped)
- `context.md` regression guard
- `MockLLM` injection contract
- Phase 5: HMAC tokens, Fernet PII, state machine transitions, atomic run consume + IP-bind + quota, budget tracker concurrency + alert idempotence, cron cleanup auth + counts, every router endpoint negative-first.

## Architecture

```
src/cv_critic_agent/
├── api.py         # FastAPI app + lifespan reads env → app.state
├── main.py        # CLI entry point — `python -m cv_critic_agent`
├── crew.py        # CrewAI-native: Agent/Task/Crew, sequential process
├── workflow.py    # Shared workflow (used by v2 script and mock runs)
├── llm.py         # MockLLM, MistralTextLLM, MistralCrewLLM (BaseLLM), AnthropicTextLLM
├── prompts.py     # Critic + strategy prompt templates
├── sources.py     # ReportSpec dataclass, REPORT_SPECS list, spec_by_slug lookup
├── reports.py     # Report writing (run/ + latest/)
├── run_manager.py # Threaded run executor + SSE fan-out + budget callback hook
├── paths.py       # Path helpers
├── env.py         # .env loader
├── security/      # crypto (HMAC), pii (Fernet), limiter (slowapi), session, middleware
├── access_requests/   # models (6-state machine), store (fcntl + lazy TTL + atomic_consume_run), router
├── admin/         # router (magic-link login + listing + PATCH actions)
├── notifier/      # telegram.py (owner pending, budget alert) + email.py (Resend)
├── budget/        # tracker.py (per-day fcntl JSON + alert thresholds) + wiring.py (record_real_run)
├── telegram_webhook_router.py  # POST /api/telegram/webhook
└── cron_router.py # POST /api/cron/cleanup

scripts/
├── crew_script.py     # v2 — intermediate CrewAI script (uses workflow.py)
└── sync_sources.py    # Refresh sources/ from a cv-portfolio checkout

legacy-node/
└── run.mjs        # v1 — Node.js plain orchestration

ui/                # Next.js 16 (App Router) — 8 routes incl. access-gate flow + admin panel
```

## CI / Quality

- **Ruff** lints `src/`, `tests/`, `scripts/` (rules: E, F, I, B, UP, SIM) on every push.
- **Mock tests** run on every push via GitHub Actions.
- **Sources drift check** scaffolded (gated until `cv-portfolio` is fetched in CI).

## Deployment Plan

Detailed checklist: [`docs/deployment.md`](docs/deployment.md).

Recommended split:

- **API**: Render, Fly.io, or Railway running the Python package.
- **UI**: Vercel running `ui/`.

API start command:

```bash
python -m cv_critic_agent --serve --host 0.0.0.0 --port $PORT
```

API environment (core + Phase 5):

```bash
# Core
CV_CRITIC_PROVIDER=mistral
CV_CRITIC_MODEL=mistral-medium-latest
MISTRAL_API_KEY=...
CV_CRITIC_ALLOWED_ORIGINS=https://your-ui.vercel.app

# Phase 5 — access gate
HMAC_KEY=...                       # secrets.token_hex(32)
FERNET_KEY=...                     # cryptography.fernet.Fernet.generate_key()
TURNSTILE_SECRET=...               # Cloudflare Turnstile server secret
TELEGRAM_BOT_TOKEN=...
TELEGRAM_OWNER_CHAT_ID=...
RESEND_API_KEY=...
RESEND_FROM_ADDRESS=agent@cv-critic.example.com
OWNER_EMAIL=...
CV_CRITIC_BASE_URL=https://api.example.com
CV_CRITIC_UI_URL=https://ui.example.com
MAX_TOKENS_PER_DAY=200000
CV_CRITIC_CLEANUP_SECRET=...       # secrets.token_hex(24) — used by daily cron
```

UI environment:

```bash
NEXT_PUBLIC_API_URL=https://your-api.example.com
NEXT_PUBLIC_TURNSTILE_SITE_KEY=...
NEXT_PUBLIC_OWNER_EMAIL=...
```

Deployment order:

1. Deploy the API with only mock runs exposed and verify `/api/health`.
2. Deploy the UI and point `NEXT_PUBLIC_API_URL` at the API.
3. Provision Phase 5 secrets (HMAC, Fernet, Turnstile, Telegram, Resend). Without them the gate endpoints return 503 — mock runs keep working.
4. Schedule a daily `POST /api/cron/cleanup` (any cron service) with the `X-Cleanup-Secret` header.
5. Submit one access request end-to-end (form → Telegram → email link → real run) and verify the budget tracker increments + the alert fires at 80 %.

## License

Personal project, MIT-style. The CV being audited belongs to Saïfallah Mansour.
