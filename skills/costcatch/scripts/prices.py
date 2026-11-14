# Version 1.0 | Deps: Python 3 stdlib | Parent: costcatch (baseline.py, attribute.py, window_cost.py) | Path: costcatch/scripts | Filename: prices.py | Created: 2026-11-05 16:33 ET — the one price table the three scripts share; Haiku 5.5 with its long-prompt tier; Sonnet 5.5's cache read corrected to $0.10
"""$ per million tokens: (input, output, cache read), Anthropic list prices read on
platform.claude.com (models overview, pricing) on 2026-11-05. Cache writes derive from
input: 5-minute writes 1.25x, 1-hour writes 2x (Haiku 5.5's 5-minute write is $0.125,
which is 1.25 x $0.10). Order matters: a longer id sits before the shorter id it
begins with, so claude-opus-5-5 is matched before claude-opus-5.

LONG: Haiku 5.5 reprices a whole request whose prompt (input + cache reads + cache
writes) is over 100K tokens: $0.50 input, $2.50 output, $0.05 cache read."""

PRICES = {
    "claude-opus-5-5": (4.0, 20.0, 0.20), "claude-fable-5-1": (10.0, 50.0, 0.25),
    "claude-sonnet-5-5": (2.0, 10.0, 0.10), "claude-haiku-5-5": (0.10, 0.50, 0.01),
    "claude-opus-5": (5.0, 25.0, 0.50), "claude-sonnet-5": (2.0, 10.0, 0.20),
    "claude-haiku-4-5": (1.0, 5.0, 0.10),
}
LONG = {"claude-haiku-5-5": (100_000, (0.50, 2.50, 0.05))}


# The top model (Fable) is meant only for the tasks a routing table gives it; a report flags it when
# it is over this share of the window's cost (the owner's pick, 2026-11-05).
FABLE_FLAG = 0.25


def fable_share(cost_by_model, total):
    """{"usd", "share", "flag_above", "flagged"} for the Fable models in cost_by_model (model id -> dollars)."""
    usd = sum(v for k, v in cost_by_model.items() if k.startswith("claude-fable"))
    share = usd / total if total else 0.0
    return {"usd": round(usd, 2), "share": round(share, 3), "flag_above": FABLE_FLAG, "flagged": share > FABLE_FLAG}


def price(model):
    """(input, output, cache read) for a model id, or None when unpriced."""
    for k, v in PRICES.items():
        if model == k or model.startswith(k + "-"):
            return v
    return None


def tiered(model, p, prompt_tokens):
    """p, or the long-prompt tier of p when the model has one and the prompt is over its line."""
    for k, (line, tier) in LONG.items():
        if (model == k or model.startswith(k + "-")) and prompt_tokens > line:
            return tier
    return p
