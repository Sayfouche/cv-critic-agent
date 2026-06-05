# Phase 5 — Access gate with human-in-the-loop approval

> Status: **planned**, no code yet. This doc is the architectural decision
> record (ADR) before any line is written. It exists because the security
> posture matters more than the feature itself.

## 1. Why this phase

After Phase 4 (Render + Vercel deploy), the public UI at
[agentic-ai.saifallah.dev](https://agentic-ai.saifallah.dev) only exposes
**mock runs**. Real runs are gated behind an `X-API-Token` header that no
public user can know. This is safe but defeats the demo: a curious recruiter
clicks the button and sees fake markdown, not the real agent at work.

Phase 5 opens real runs to the public while keeping cost and abuse under
control. The mechanism: a **human-in-the-loop approval flow**.

1. Requester fills a form (name, company, email, motive).
2. Owner (Saifallah) is notified on Telegram **and** by email, with one-click
   Approve / Reject links.
3. Owner clicks → requester receives an approval email with a session link.
4. Requester clicks → can run 3 real runs in the next 24h.

The design is also a portfolio piece in its own right: it demonstrates HMAC
token design, transactional email, Telegram bot integration, captcha
verification, magic-link admin auth, rate limiting, and cost-cap with
graceful degradation.

## 2. Threat model

### Assets

| Asset | Why it matters |
|---|---|
| Mistral API budget | Real money per run (~$0.025/run). Cost-DoS is the most realistic attack. |
| PII of requesters (name, email, company, motive) | GDPR. Reputation. |
| Owner's Telegram chat ID | Privacy. Spam vector. |
| The approval power | The whole gate collapses if it can be forged. |
| Server secrets (HMAC keys, bot token, Resend key, Fernet key) | Compromise = total bypass. |

### Adversaries

| Adversary | Capability | Motivation | Likelihood |
|---|---|---|---|
| Bot crawler | Automated POSTs to public endpoints | Spam, brute force | ⭐⭐⭐ Very high |
| Curious user | Browser dev tools, network inspection | Probe for skip-the-gate paths | ⭐⭐ High |
| Hostile competitor | Knows runs hit Saifallah's Mistral budget | Burn the budget | ⭐ Medium |
| Targeted attacker | Knows owner's email and Telegram handle | Phish approval links | ⭐ Low but serious |
| Compromised owner channel | Owner's email or Telegram is taken over | Auto-approves anything | ⭐ Very low, massive impact |
| Insider (future self) | Builds the system, has access to logs | Accidental PII leak in commits / logs | ⭐⭐ Medium |

### Out of scope

- Nation-state actors, advanced persistent threats
- Physical attacks on the Render / Vercel infrastructure
- Side-channels in CPython itself

## 3. Defenses by attack surface

### Surface A — Public form `POST /api/access-requests`

| Threat | Defense |
|---|---|
| Bot flood | Cloudflare Turnstile, server-side `siteverify` (not just widget). Reject if `success=false` or `score<0.5`. |
| Per-IP scan | `slowapi` rate-limit: 3 requests / IP / hour, 30 / IP / day. In-memory store (Render is single-instance). |
| Global DoS via storage growth | Hard cap: 500 requests / day total. Returns 503 beyond. |
| Disposable email | Block via the open-source `disposable-email-domains` list (~50k domains). |
| Honeypot | Hidden field `website` — if filled, drop silently with 200. |
| HTML/XSS injection in `motive` | React's default escaping in admin panel. Never `dangerouslySetInnerHTML` on user input. |
| Email header injection | Strict regex + `email-validator` Python lib. |
| GDPR | TTL: 7d on pending, 90d on decided. `DELETE /api/access-requests/{id}` with email-confirmation flow. |

### Surface B — Owner decision (Telegram + email + admin panel)

| Threat | Defense |
|---|---|
| Forged decision link | URL token = `HMAC-SHA256(secret, request_id \| accept \| expires_at)`. Verified with `hmac.compare_digest` (timing-safe). |
| Replay attack | Once `decided_at` is set, further decision attempts are ignored idempotently. |
| Link expiration | 7-day TTL. After that, status flips to `EXPIRED` and the link returns 410. |
| Spoofed Telegram callback | Webhook handler validates `callback_query.from.id == TELEGRAM_OWNER_CHAT_ID`. Anyone else: silent drop. |
| Telegram bot token leak | Stored in Render env vars only. Never logged, never in git. Rotation procedure documented. |
| Compromised owner email | **Optional V2:** require both Telegram AND email click to set `APPROVED` (env flag `MFA_OWNER=true`). |
| Admin token in URL | ❌ No `?token=` in URL — it leaks to logs, browser history, Referer headers. Instead: magic-link flow. POST `/api/admin/login` → email sent to owner with a one-time URL → click sets a `HttpOnly Secure SameSite=Strict` cookie valid 24h. |

### Surface C — Requester session token (after approval)

| Threat | Defense |
|---|---|
| Email interception | Token = `HMAC-SHA256(secret, email \| request_id \| expires_at)`. Tied to the requester's email — the token alone is not a bearer credential. |
| Link sharing / theft | **IP binding**: the first call to `/access-granted/<token>` records the source IP. Subsequent calls from a different IP are rejected. |
| Quota | 3 runs per 24h, **enforced server-side before** the Mistral call. |
| Global cost DoS | `MAX_TOKENS_PER_DAY=200000` env var. Beyond, real runs degrade silently to mock + Telegram alert "budget cap hit". |
| Token re-emission | A given access-request id yields exactly one session token. Re-issuance requires a new access request. |

### Surface D — OAuth LinkedIn (V2 only)

| Threat | Defense |
|---|---|
| CSRF on callback | Random `state` parameter, bound to an HMAC cookie. Strict verification on callback. |
| Open redirect | `redirect_uri` hard-coded server-side. Never read from query string. |
| Session cookie theft | `HttpOnly Secure SameSite=Lax`. Short TTL. |
| LinkedIn token persistence | We read `/v2/me` once at login, store only `linkedin_verified=true` + verified name. The OAuth access token is discarded. |

### Surface E — Storage (PII + secrets)

| Threat | Defense |
|---|---|
| Disk read by attacker if breached | Render disks are container-isolated, not publicly addressable. Defense in depth: encrypt `email` and `motive` fields at rest with **Fernet** (key in env). |
| Logs containing PII | Logging filter masks emails (`m****@x.com`). Never log `motive`. |
| Backup exposure | No backups on Render free tier → accepted risk for a demo. |
| Secrets in env | Render env vars are encrypted at rest by the platform. Git pre-commit hook: `git secrets --scan`. |
| Secret rotation | `rotate-secrets.py` script regenerates HMAC + Fernet keys and signals "all existing tokens invalidated". |

### Surface F — Real run execution

| Threat | Defense |
|---|---|
| Cost runaway | Hard `max_tokens=5000` per agent × 3 agents = 15k/run max. Plus the global daily budget cap. |
| Prompt injection (relevant when V2 accepts user CV upload) | Sandbox the user-supplied content in `<USER_CONTENT>...</USER_CONTENT>` tags. System prompt instructs the model to treat content inside as data, never as instructions. |
| Filesystem path traversal | Reports always written to `reports/<uuid>/`. No user-controlled segment in the path. |
| Crash leaving inconsistent state | `RunState.status` set to `failed` in the exception handler. Background cleanup of orphaned runs every hour. |

## 4. Decisions taken

| # | Decision | Choice |
|---|---|---|
| 1 | Captcha provider | **Cloudflare Turnstile** (free, unlimited, less aggressive UX than hCaptcha, already on our DNS stack) |
| 2 | Admin panel auth | **Magic link by email** (single user = me, zero passwords to manage) |
| 3 | Owner MFA (require Telegram **and** email click) | **No in V1** (friction outweighs risk). V2 option behind a flag. |
| 4 | Encrypt PII at rest (Fernet) | **Yes**. 5 lines of code, defense in depth, CV-valuable ("PII encrypted at rest"). |
| 5 | Session token: IP-binding vs cookie | **IP-binding in V1**. Cookies would require CORS + cross-origin cookie config across `agentic-ai.saifallah.dev` and `cv-critic-agent-api.onrender.com` — not worth it for this scale. |
| 6 | Data retention | 7d pending, 90d decided. Daily cron auto-deletes. GDPR `DELETE` endpoint with email confirmation. |
| 7 | Mistral budget cap | **$5/day** (~200k output tokens). Telegram alert at 80% and 100%. Graceful degradation to mock beyond. |

## 5. Explicit non-goals (over-engineering avoided)

- ❌ WebAuthn / passkey for admin — magic link is enough for a single owner.
- ❌ 2FA owner via SMS — adds cost (Twilio) and friction with no real gain.
- ❌ Append-only audit log on object storage — overkill for a demo.
- ❌ Custom WAF — Cloudflare in front of Vercel + Render's own protections suffice.
- ❌ External pen-test — premature.
- ❌ SOC2 / ISO compliance — this is a demo, not a B2B SaaS.

## 6. Implementation plan (7 sprints, ~4 working days)

```
Phase 5 — Access-request gate with real runs
│
├─ Sprint 1 ─── Security foundations ────────────────── ~½ day
│   ├─ crypto.py (HMAC sign/verify, timing-safe compare, expiry encoded)
│   ├─ pii.py (Fernet encrypt/decrypt for email + motive fields)
│   ├─ logging_filter.py (mask emails in all log lines)
│   ├─ security_middleware.py (Turnstile verify + slowapi + security headers)
│   ├─ Render secrets: HMAC_KEY, FERNET_KEY, TURNSTILE_SECRET, MAGIC_KEY
│   └─ tests/test_security.py (10 negative tests: forge, replay, captcha bypass, …)
│
├─ Sprint 2 ─── AccessRequest storage ───────────────── ~½ day
│   ├─ AccessRequest dataclass + status enum
│   ├─ store.py (JSON on Render disk with atomic file lock)
│   ├─ TTL: 7d pending, 90d decided (lazy cleanup on read + daily cron)
│   ├─ GDPR DELETE endpoint with email confirmation
│   └─ tests: concurrency, TTL, Fernet round-trip
│
├─ Sprint 3 ─── Notifier layer ──────────────────────── ~½ day
│   ├─ notifier/telegram.py (send + inline keyboard Approve/Reject)
│   ├─ notifier/email.py (Resend, HTML + plain templates)
│   ├─ Bot creation @cv_critic_agent_bot via BotFather
│   ├─ Render secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_CHAT_ID, RESEND_API_KEY
│   └─ tests: 4 messages mocked (owner pending, requester approved, requester rejected, budget alert)
│
├─ Sprint 4 ─── Decision endpoints ──────────────────── ~½ day
│   ├─ POST /api/access-requests (captcha + rate-limit + store + notify)
│   ├─ GET /api/access-requests/{id}/status (public, status only)
│   ├─ GET /api/access-requests/{id}/decide?token=&accept= (HMAC, idempotent)
│   ├─ POST /api/telegram/webhook (validates owner chat_id)
│   ├─ Admin magic link: POST /api/admin/login + GET /api/admin/session/{token}
│   ├─ GET /api/admin/requests (list + batch actions)
│   └─ tests: replay, forged tokens, idempotence, expired
│
├─ Sprint 5 ─── Real run gate ───────────────────────── ~½ day
│   ├─ Modify POST /api/runs to accept session_token instead of X-API-Token
│   ├─ verify_session: HMAC + IP binding + quota + global budget cap
│   ├─ atomic increment runs_used
│   ├─ budget_tracker.py (daily tokens consumed, Telegram alerts 80%/100%)
│   ├─ Graceful degradation to mock if budget cap hit
│   └─ tests: forge, expired, IP mismatch, quota exceeded, budget cap
│
├─ Sprint 6 ─── UI ──────────────────────────────────── ~1 day
│   ├─ /access-request (form + Turnstile widget)
│   ├─ /access-request/[id]/status (polling 5s + contact email shown)
│   ├─ /access-granted/[token] (landing → POST run with session_token)
│   ├─ /admin/login + /admin/requests (batch panel)
│   ├─ Home page: two CTAs "Mock run (instant)" / "Request real run (manual approval)"
│   └─ Manual E2E + screenshots
│
└─ Sprint 7 ─── Polish + telemetry ──────────────────── ~½ day
    ├─ Telegram budget alerts (80%, 100%)
    ├─ Daily cron: cleanup expired, alert if too many pending undecided
    ├─ README + fiche technique: documented security section
    ├─ Production smoke test
    └─ cv-portfolio update (data.ts, skills, fiche technique)
```

## 7. CV-valuable skills delivered by this phase

| Skill | Where it shows |
|---|---|
| HMAC token signing & verification with timing-safe compare | `crypto.py` |
| Fernet symmetric encryption for PII at rest | `pii.py` |
| Server-side captcha verification (Cloudflare Turnstile) | `security_middleware.py` |
| Telegram Bot API with inline keyboard callbacks | `notifier/telegram.py` |
| Transactional email (Resend) with HTML + plain templates | `notifier/email.py` |
| Rate limiting with slowapi | middleware |
| Magic-link (passwordless) authentication | admin login flow |
| Threat modeling (this doc) | `/docs/PHASE5_ACCESS_GATE.md` |
| Cost cap with graceful degradation | `budget_tracker.py` |
| GDPR-compliant data retention and deletion | TTL + DELETE endpoint |

## 8. Open questions for V2

- LinkedIn OAuth for verified-identity enrichment (badge "✓ LinkedIn verified" in the admin panel). Blocks on LinkedIn app approval (~2–5 days).
- Owner MFA: require both Telegram inline button AND email click for `APPROVED`. Behind env flag, off by default.
- Multi-target real runs (Chantier C — generalisation): the access gate must then carry which CV the requester wants critiqued.
- Append-only audit log (e.g., signed JSONL on S3) for compliance-grade traceability.

## 9. References

- OWASP ASVS Level 2 (we map most controls)
- RFC 6238 (HOTP/TOTP — not used, but for reference on time-bound tokens)
- Cloudflare Turnstile siteverify docs
- Telegram Bot API: inline keyboards & callback queries
- Resend transactional email API
- Python `cryptography.fernet`: symmetric encryption primitives
