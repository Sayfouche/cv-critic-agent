# CV Critic Agent — CLAUDE.md

## What this project is

Multi-agent CV audit system (2 critics + 1 strategist). Three implementations sharing the same output contract: Node.js plain, CrewAI script, CrewAI native. Default provider: Mistral. Fallback: Anthropic. API on Render, Next.js UI on Vercel (`agentic-ai.saifallah.dev`).

**Active work:** Phase 5 — Access gate with human-in-the-loop approval (see `docs/PHASE5_ACCESS_GATE.md`).

## Commands

```bash
# Install (server + dev)
pip install -e '.[server,dev]'

# Run tests
python -m pytest

# Run specific test file
python -m pytest tests/test_crypto.py -v

# Lint
ruff check src/ tests/
ruff format src/ tests/

# Run API locally
python -m cv_critic_agent --serve --host 127.0.0.1 --port 8000

# CLI (mock run)
python -m cv_critic_agent
```

## Project structure

```
src/cv_critic_agent/
├── api.py                    FastAPI app (entrypoint for --serve mode)
├── access_requests/
│   ├── models.py             AccessRequest dataclass + state machine
│   ├── store.py              JSON-on-disk store with Fernet PII + fcntl + atomic_consume_run (S5)
│   └── router.py             POST/GET /api/access-requests/* endpoints (S4)
├── admin/
│   └── router.py             Admin magic-link + listing endpoints (S4)
├── budget/
│   └── tracker.py            Daily output-token tracker + 80/100% alerts (S5)
├── notifier/
│   ├── telegram.py           send_owner_pending, send_budget_alert
│   └── email.py              send_requester_approved/rejected/admin_magic_link
├── security/
│   ├── crypto.py             sign_token / verify_token (HMAC-SHA256)
│   ├── pii.py                Fernet encrypt/decrypt
│   ├── logging_filter.py     Masks emails in logs
│   ├── limiter.py            Module-level slowapi singleton
│   ├── session.py            verify_session (S5)
│   └── security_middleware.py Turnstile verify + SecurityHeadersMiddleware
├── telegram_webhook_router.py POST /api/telegram/webhook (S4)
├── run_manager.py            In-memory run state + SSE queues
├── workflow.py               CrewAI native workflow
└── crew.py                   Agent/Task definitions
```

## Architecture conventions — MUST follow

1. **No env reads in modules.** Every secret (bot_token, api_key, hmac_secret, fernet_key) is passed as an explicit function argument. Only `api.py` reads `os.environ`, at startup. This makes every module testable without patching env.

2. **Fail-soft on external I/O.** Telegram, Resend, Turnstile calls return `False` / `None` on any error — they never raise to the caller. The caller decides whether to retry or alert. Never let a notification failure crash a user request.

3. **Tests: `unittest` style.** Negative-first. One transition per test. Group in classes by concern (`SendOwnerPendingTests`, `LazyTTLTests`, etc.). Use `IsolatedAsyncioTestCase` for async tests.

4. **Async for all HTTP I/O** (httpx). Mock pattern: `_RecordingClient` that captures `url`/`json`/`headers`. Injected via `http_client_factory=` parameter. No real HTTP in any test.

5. **PII never in plaintext on disk** or in logs. Fernet at rest (`pii.py`). Logging filter masks emails. `name`, `company`, `email`, `motive` are always encrypted; `ip`, `status` stay indexable.

6. **State always passed via `request.app.state`.** Endpoints read `getattr(request.app.state, "field", default)`. Tests override state after `TestClient(app)` creation.

7. **Commit style:** `feat(scope): short title — detail (Sprint Id)`, body in bullets, `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.

## Phase 5 — Sprint status

| Sprint | Status | Content |
|--------|--------|---------|
| S1 | ✅ done | Crypto, PII, logging filter, Turnstile, slowapi, headers |
| S2 | ✅ done | AccessRequest model + state machine + Store |
| S3 | ✅ done | Notifier: Telegram + Resend email |
| S4 | ✅ done | Decision endpoints + admin magic link |
| **S5** | ✅ done | Real run gate (session_token + IP binding + quota + budget cap) |
| S6 | ⏭️ next | UI pages (form, status poll, access-granted, admin) |
| S7 | ⏭️ | Polish + telemetry + README |

**Test count:** 267 green (S1–S5).

## Sprint 4 — Endpoints to build

```
POST   /api/access-requests            captcha + rate-limit + store + notify
GET    /api/access-requests/{id}/status   public status poll (no PII)
GET    /api/access-requests/{id}/decide   HMAC decision link (approve/reject)
POST   /api/telegram/webhook           validates owner chat_id, handles callbacks
POST   /api/admin/login                sends magic link to owner email
GET    /api/admin/session/{token}      redeems magic link → admin session token
GET    /api/admin/requests             list (requires X-Admin-Session header)
PATCH  /api/admin/requests/{id}        approve / reject / revoke (admin)
```

## Token conventions

All tokens use `security.crypto.sign_token(payload, secret, ttl_seconds)`.

| Token | `sub` value | TTL | Used by |
|-------|-------------|-----|---------|
| Decision (approve) | `"decide"` + `"accept": 1` | 7 days | Telegram/email decide URL |
| Decision (reject) | `"decide"` + `"accept": 0` | 7 days | Telegram/email decide URL |
| Session (requester) | `"session"` | 24 h | `/access-granted/{token}` UI page |
| Admin magic link | `"admin-magic"` | 30 min | Email link → admin session |
| Admin session | `"admin-session"` | 24 h | `X-Admin-Session` header or cookie |

## Environment variables

| Variable | Used by | Notes |
|----------|---------|-------|
| `HMAC_KEY` | crypto tokens | raw string, encoded to UTF-8 bytes |
| `FERNET_KEY` | PII encryption | Fernet.generate_key() output |
| `TURNSTILE_SECRET` | captcha verify | Cloudflare Turnstile server-side secret |
| `TELEGRAM_BOT_TOKEN` | notifier | from BotFather |
| `TELEGRAM_OWNER_CHAT_ID` | notifier | integer as string |
| `RESEND_API_KEY` | email | Resend.com API key |
| `RESEND_FROM_ADDRESS` | email | verified sender address |
| `OWNER_EMAIL` | admin login | owner's email for magic link |
| `CV_CRITIC_BASE_URL` | decision URLs | API origin (Render URL) |
| `CV_CRITIC_UI_URL` | session URLs | UI origin (Vercel URL) |
| `ACCESS_REQUESTS_DIR` | store | path for JSON files (default: `data/access_requests`) |
| `BUDGET_DIR` | budget tracker | path for per-day JSON files (default: `data/budget`) |
| `MAX_TOKENS_PER_DAY` | budget cap | daily output-token cap before real→mock degradation (default: 200000) |
| `MAGIC_KEY` | (future) | separate key for admin magic links if desired |

## Security notes

- **Replay protection**: `decided_at` is set on first decision; subsequent decide calls return current status idempotently.
- **Token tampering**: `accept` (1/0) is encoded inside the signed token, not as a bare URL param.
- **Honeypot**: `website` field in `POST /api/access-requests` — silent 200 if filled.
- **Owner verification (webhook)**: `is_owner_callback(from_id, owner_chat_id)` — always string-compare.
- **Admin oracle protection**: `POST /api/admin/login` always returns `{"sent": true}` regardless of whether the email matches.
