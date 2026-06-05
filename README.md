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

## Quick start

### Install

```bash
git clone https://github.com/Sayfouche/cv-critic-agent.git
cd cv-critic-agent
pip install -e .
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
PYTHONPATH=src python -m unittest discover -s tests -v
```

All tests use a mock LLM and make zero API calls. Tests cover:
- Prompt isolation (critics don't leak `context.md`, strategy does include it)
- Output contract parity across the three implementations
- Mistral message cleaning (`cache_breakpoint` stripped)
- `context.md` regression guard
- `MockLLM` injection contract

## Architecture

```
src/cv_critic_agent/
├── main.py        # CLI entry point — `python -m cv_critic_agent`
├── crew.py        # CrewAI-native: Agent/Task/Crew, sequential process
├── workflow.py    # Shared workflow (used by v2 script and mock runs)
├── llm.py         # MockLLM, MistralTextLLM, MistralCrewLLM (BaseLLM), AnthropicTextLLM
├── prompts.py     # Critic + strategy prompt templates
├── sources.py     # ReportSpec dataclass, REPORT_SPECS list, spec_by_slug lookup
├── reports.py     # Report writing (run/ + latest/)
├── paths.py       # Path helpers
└── env.py         # .env loader

scripts/
├── crew_script.py     # v2 — intermediate CrewAI script (uses workflow.py)
└── sync_sources.py    # Refresh sources/ from a cv-portfolio checkout

legacy-node/
└── run.mjs        # v1 — Node.js plain orchestration

tests/
└── test_workflows.py  # 9 mock tests, zero API calls
```

## CI / Quality

- **Ruff** lints `src/`, `tests/`, `scripts/` (rules: E, F, I, B, UP, SIM) on every push.
- **Mock tests** run on every push via GitHub Actions.
- **Sources drift check** scaffolded (gated until `cv-portfolio` is fetched in CI).

## License

Personal project, MIT-style. The CV being audited belongs to Saïfallah Mansour.
