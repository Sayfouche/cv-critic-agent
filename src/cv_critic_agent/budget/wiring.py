"""Runtime glue between BudgetTracker and the Telegram alert notifier.

`record_real_run` is the single entry point a run worker calls after a
real-mode run completes. It does two things:

1. Increments the daily token counter via ``tracker.add_tokens(n)``.
2. For every threshold percentage that just crossed for the first time
   today, fires ``send_budget_alert`` (fail-soft: a notifier error never
   raises to the caller).

The threshold-crossing logic lives in ``BudgetTracker.add_tokens``; this
module only wires it to the notifier. Tests inject an ``http_client_factory``
so no real HTTP fires.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cv_critic_agent.budget.tracker import BudgetState, BudgetTracker
from cv_critic_agent.notifier.telegram import send_budget_alert


async def record_real_run(
    tracker: BudgetTracker,
    n_tokens: int,
    *,
    bot_token: str,
    owner_chat_id: int | str,
    http_client_factory: Callable[..., Any] | None = None,
) -> tuple[BudgetState, list[int]]:
    """Record *n_tokens* of LLM output and fire alerts for crossed thresholds.

    Returns ``(state, alerts_fired)``. ``alerts_fired`` is the subset of
    thresholds whose Telegram notification succeeded (``send_budget_alert``
    returned True). A threshold is still marked as "sent" inside the
    tracker even if the Telegram call fails — that matches the fail-soft
    contract used elsewhere (we never re-fire an alert).
    """
    state, new_alerts = tracker.add_tokens(n_tokens)
    if not new_alerts or not bot_token or owner_chat_id in ("", None):
        return state, []

    fired: list[int] = []
    for pct in new_alerts:
        ok = await send_budget_alert(
            bot_token=bot_token,
            owner_chat_id=owner_chat_id,
            percentage=pct,
            tokens_used=state.tokens_used,
            daily_cap=tracker.daily_cap,
            http_client_factory=http_client_factory,
        )
        if ok:
            fired.append(pct)
    return state, fired
