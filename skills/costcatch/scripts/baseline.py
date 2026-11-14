# Version 1.0 | Deps: Python 3 stdlib | Parent: Cursor's harness token-efficiency prompt (step 1, "map the harness and measure the baseline") | Path: costcatch/scripts | Filename: baseline.py | Created: 2026-10-06 13:39 ET
"""Read ~/.claude/projects/**/*.jsonl (Claude Code's own session logs) and
report what requests cost on this machine. Read-only; prints JSON.

Counted once: a request by requestId, a compaction by its uuid, Claude Code's
cost tally by its sessionId - resumed and forked sessions repeat their parent's
history, and counting it twice doubled the first pass.
Cost: tokens x list price (prices.py, from Anthropic's model table read
2026-11-05; 5-minute writes 1.25x input, 1-hour writes 2x). Claude Code's own
tally is printed beside it as a check."""
import argparse, collections, datetime, glob, json, os, re, sys

# $ per million tokens: input, output, cache read; the table is prices.py.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prices import PRICES, price, tiered, fable_share, FABLE_FLAG
BANDS = (50_000, 100_000, 200_000, 400_000, 700_000)

ap = argparse.ArgumentParser()
ap.add_argument("--since", help="YYYY-MM-DD or YYYY-MM-DDTHH:MM, UTC: requests on or after it")
ap.add_argument("--until", help="same form: requests before it")
ap.add_argument("--root", default=os.path.expanduser("~/.claude/projects"))
ap.add_argument("--top", type=int, default=12)
args = ap.parse_args()
def utc(s):
    return s and datetime.datetime.fromisoformat(s.rstrip("Z")).replace(tzinfo=datetime.timezone.utc)


since, until = utc(args.since), utc(args.until)


def when(d):
    t = d.get("timestamp")
    try:
        return datetime.datetime.fromisoformat(t.replace("Z", "+00:00")) if t else None
    except ValueError:
        return None


def size(c):
    if isinstance(c, str):
        return len(c)
    if isinstance(c, list):
        return sum(len(x.get("text", "")) if isinstance(x, dict) else len(str(x)) for x in c)
    return len(json.dumps(c))


reqs = {}                    # requestId -> row
compactions = set()
tallies = {}                 # cost-state sessionId -> last totalCostUSD (sessions active in the window)
tally_seen, sess_of, active = {}, {}, set()
tool_chars, tool_calls = collections.Counter(), collections.Counter()
tool_big = collections.Counter()   # results over 20k chars, by tool
first_parts = []             # per main session: attachments before the first reply + that reply's context
seen_tool = set()
for path in glob.glob(os.path.join(args.root, "**", "*.jsonl"), recursive=True):
    sub = os.sep + "subagents" + os.sep in path
    proj = os.path.relpath(path, args.root).split(os.sep)[0]
    names, pre_att, first_done = {}, collections.Counter(), False
    try:
        fh = open(path, encoding="utf-8")
    except OSError:
        continue
    with fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t, at = d.get("type"), when(d)
            recent = (not since and not until) or (at is not None and (not since or at >= since) and (not until or at < until))
            if t == "assistant":
                m = d.get("message") or {}
                u, rid = m.get("usage") or {}, d.get("requestId")
                for b in m.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        names[b.get("id")] = b.get("name", "?")
                if not (u and rid):
                    continue
                cc = u.get("cache_creation") or {}
                row = {"model": m.get("model", "?"), "sub": sub, "proj": proj, "at": at,
                       "in": u.get("input_tokens", 0) or 0, "out": u.get("output_tokens", 0) or 0,
                       "read": u.get("cache_read_input_tokens", 0) or 0,
                       "w5": cc.get("ephemeral_5m_input_tokens", 0) or 0,
                       "w1h": cc.get("ephemeral_1h_input_tokens", 0) or 0}
                if not cc:
                    row["w5"] = u.get("cache_creation_input_tokens", 0) or 0
                if not first_done and not sub:
                    first_done = True
                    first_parts.append((proj, row["in"] + row["read"] + row["w5"] + row["w1h"], dict(pre_att)))
                if recent and (rid not in reqs or row["out"] >= reqs[rid]["out"]):
                    row["sid"] = d.get("sessionId")
                    reqs[rid] = row
                    active.add(d.get("sessionId"))
            elif t == "attachment" and not first_done and not sub:
                a = d.get("attachment") or {}
                pre_att[a.get("type", "?")] += len(json.dumps(a))
            elif t == "user" and recent:
                c = (d.get("message") or {}).get("content")
                for b in c if isinstance(c, list) else ():
                    if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") not in seen_tool:
                        seen_tool.add(b.get("tool_use_id"))
                        n = names.get(b.get("tool_use_id"), "?")
                        n = "mcp:" + n.rsplit("__", 1)[-1] if n.startswith("mcp__") else n
                        k = size(b.get("content"))
                        tool_chars[n] += k
                        tool_calls[n] += 1
                        if k > 20_000:
                            tool_big[n] += 1
            elif t == "system" and d.get("subtype") == "compact_boundary" and recent:
                compactions.add(d.get("uuid"))
            elif t == "cost-state":
                tally_seen[d.get("sessionId")] = d.get("totalCostUSD") or 0
                if d.get("sessionId") not in sess_of:
                    sess_of[d.get("sessionId")] = path

tallies = {k: v for k, v in tally_seen.items() if k in active}
rewrites = collections.Counter()
sess_cost = collections.Counter()
cost = collections.Counter()
by = collections.defaultdict(collections.Counter)
band_cost, band_n = collections.Counter(), collections.Counter()
unpriced = collections.Counter()
for r in reqs.values():
    p = price(r["model"])
    if not p:
        unpriced[r["model"]] += 1
        continue
    pin, pout, pread = tiered(r["model"], p, r["in"] + r["read"] + r["w5"] + r["w1h"])
    parts = {"cache_read": r["read"] * pread, "cache_write_1h": r["w1h"] * pin * 2,
             "cache_write_5m": r["w5"] * pin * 1.25, "output": r["out"] * pout, "input": r["in"] * pin}
    usd = {k: v / 1e6 for k, v in parts.items()}
    total = sum(usd.values())
    cost.update(usd)
    for key in ("model", "proj"):
        by[key][r[key]] += total
    by["who"]["subagent" if r["sub"] else "main"] += total
    if r["sub"]:
        by["sub_model"][r["model"]] += total
    sess_cost[r["sid"]] += total
    w = r["w5"] + r["w1h"]
    if w >= 50_000:
        rewrites["n"] += 1
        rewrites["tokens"] += w
        rw = (r["w5"] * pin * 1.25 + r["w1h"] * pin * 2) / 1e6
        rewrites["usd"] += rw
        by["rewrite_by"]["%s %s" % ("subagent" if r["sub"] else "main", r["model"])] += rw
    ctx = r["in"] + r["read"] + r["w5"] + r["w1h"]
    band = next(("<%dk" % (b // 1000) for b in BANDS if ctx < b), ">=%dk" % (BANDS[-1] // 1000))
    band_cost[band] += total
    band_n[band] += 1

T = sum(cost.values())
ctxs = sorted(r["in"] + r["read"] + r["w5"] + r["w1h"] for r in reqs.values())
fp = sorted(x[1] for x in first_parts)
recent_first = [x for x in first_parts][-40:]
att_first = collections.Counter()
for _, _, parts in recent_first:
    att_first.update(parts)
out = {
    "since": args.since, "until": args.until, "requests": len(reqs), "compactions": len(compactions),
    "cost_usd_list_price": round(T, 2),
    "cost_usd_claude_code_tally_dedup": round(sum(tallies.values()), 2),
    "cost_by_part": {k: round(v, 2) for k, v in cost.most_common()},
    "fable_share": fable_share(by["model"], T),
    "cost_by_who": {k: round(v, 2) for k, v in by["who"].most_common()},
    "cost_by_model": {k: round(v, 2) for k, v in by["model"].most_common()},
    "subagent_cost_by_model": {k: round(v, 2) for k, v in by["sub_model"].most_common()},
    "rewrites_50k_plus": {"n": rewrites["n"], "tokens": rewrites["tokens"], "usd": round(rewrites["usd"], 2),
                          "by": {k: round(v, 2) for k, v in by["rewrite_by"].most_common()}},
    "tally_check": [(k[:8], round(sess_cost[k], 2), round(v, 2)) for k, v in sorted(tallies.items(), key=lambda x: -x[1])[:6]],
    "cost_by_project": {k[-60:]: round(v, 2) for k, v in by["proj"].most_common(args.top)},
    "context_per_request": {"median": ctxs[len(ctxs) // 2] if ctxs else None,
                             "p90": ctxs[int(len(ctxs) * .9)] if ctxs else None},
    "cost_by_context_band": {b: (round(band_cost[b], 2), band_n[b]) for b in
                              ["<%dk" % (b // 1000) for b in BANDS] + [">=%dk" % (BANDS[-1] // 1000)]},
    "first_request_tokens": {"median": fp[len(fp) // 2] if fp else None, "min": fp[0] if fp else None,
                              "sessions": len(fp)},
    "first_request_injected_chars_last40_avg": {k: v // max(len(recent_first), 1) for k, v in att_first.most_common(args.top)},
    "tool_result_chars": [(n, c, tool_calls[n], tool_big[n]) for n, c in tool_chars.most_common(args.top)],
    "unpriced_requests": dict(unpriced),
}
json.dump(out, sys.stdout, indent=1, default=str)
sys.stderr.write("RESULT: %d requests, %d compactions, list-price cost $%.2f (Claude Code tally $%.2f), Fable %.0f%% of it%s\n"
                 % (len(reqs), len(compactions), T, out["cost_usd_claude_code_tally_dedup"], out["fable_share"]["share"] * 100,
                    " - FLAG: over %.0f%%, check which tasks your routing gives it" % (FABLE_FLAG * 100) if out["fable_share"]["flagged"] else ""))
