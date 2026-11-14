# Version 0.1 | Deps: Python 3 stdlib | Parent: baseline.py 0.3 | Path: costcatch/scripts | Filename: window_cost.py | Created: 2026-10-06 13:53 ET
"""Usage:
  window_cost.py <session.jsonl> <from ISO UTC> <to ISO UTC>
  window_cost.py <folder of session logs>
Prints requests, tokens by part, list-price cost, peak context and compactions.
Prices from prices.py, as baseline.py; a request counts once by requestId."""
import datetime, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prices import PRICES, price, tiered


def when(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


src = sys.argv[1]
lo = when(sys.argv[2]) if len(sys.argv) > 3 else None
hi = when(sys.argv[3]) if len(sys.argv) > 3 else None
files = [src] if src.endswith(".jsonl") else glob.glob(os.path.join(src, "**", "*.jsonl"), recursive=True)
reqs, comp = {}, 0
for f in files:
    for line in open(f, encoding="utf-8"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        at = d.get("timestamp")
        if lo and (not at or not (lo <= when(at) <= hi)):
            continue
        if d.get("type") == "system" and d.get("subtype") == "compact_boundary":
            comp += 1
        if d.get("type") != "assistant":
            continue
        m = d.get("message") or {}
        u, rid = m.get("usage") or {}, d.get("requestId")
        if u and rid:
            reqs[rid] = (m.get("model", "?"), u)
tot = {"in": 0, "out": 0, "read": 0, "w5": 0, "w1h": 0}
usd, peak = 0.0, 0
for model, u in reqs.values():
    p = price(model)
    cc = u.get("cache_creation") or {}
    r = {"in": u.get("input_tokens", 0) or 0, "out": u.get("output_tokens", 0) or 0,
         "read": u.get("cache_read_input_tokens", 0) or 0,
         "w5": cc.get("ephemeral_5m_input_tokens", 0) or 0, "w1h": cc.get("ephemeral_1h_input_tokens", 0) or 0}
    for k in tot:
        tot[k] += r[k]
    peak = max(peak, r["in"] + r["read"] + r["w5"] + r["w1h"])
    if p:
        p = tiered(model, p, r["in"] + r["read"] + r["w5"] + r["w1h"])
        usd += (r["in"] * p[0] + r["out"] * p[1] + r["read"] * p[2] + r["w5"] * p[0] * 1.25 + r["w1h"] * p[0] * 2) / 1e6
print(json.dumps({"requests": len(reqs), "tokens": tot, "usd": round(usd, 2), "peak_context": peak, "compactions": comp}))
