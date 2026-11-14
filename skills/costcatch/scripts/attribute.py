# Version 1.0 | Deps: Python 3 stdlib | Parent: baseline.py 1.0 | Path: costcatch/scripts | Filename: attribute.py | Created: 2026-10-06 13:45 ET
"""Per session file, in order: each request deduplicated by requestId (first
seen wins, so a fork's copied history is attributed once). A write of 50k+
tokens is tagged:
  cold_start   first request of its session file (every subagent starts here)
  compaction   a compact_boundary since the previous request
  model_switch the previous request in this file used another model
  idle_1h / idle_5m  previous request more than 60 / 5 minutes earlier
  unknown      none of the above
The cap ceiling: for cap C, sum over requests of max(0, context - C) x read price.
It ignores the work an earlier compaction would lose, so it is an upper bound."""
import argparse, collections, datetime, glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prices import price, tiered
ap = argparse.ArgumentParser()
ap.add_argument("--since", help="YYYY-MM-DD or YYYY-MM-DDTHH:MM, UTC: requests on or after it")
ap.add_argument("--until", help="same form: requests before it")
ap.add_argument("--root", default=os.path.expanduser("~/.claude/projects"))
args = ap.parse_args()


def utc(s):
    return s and datetime.datetime.fromisoformat(s.rstrip("Z")).replace(tzinfo=datetime.timezone.utc)


since, until, root = utc(args.since), utc(args.until), args.root


def when(d):
    try:
        return datetime.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError):
        return None


seen = set()
cause_n, cause_usd = collections.Counter(), collections.Counter()
caps = {120_000: 0.0, 150_000: 0.0, 200_000: 0.0}
cold = collections.defaultdict(lambda: [0, 0, 0.0])   # who -> [n, tokens, usd]
for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
    who = "subagent" if os.sep + "subagents" + os.sep in path else "main"
    prev_model, prev_at, compacted, first = None, None, False, True
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
            t = d.get("type")
            if t == "system" and d.get("subtype") == "compact_boundary":
                compacted = True
                continue
            if t != "assistant":
                continue
            m = d.get("message") or {}
            u, rid, at = m.get("usage") or {}, d.get("requestId"), when(d)
            if not (u and rid):
                continue
            model = m.get("model", "?")
            if rid in seen:   # copied from a fork already read: counted there, but this session moves on
                first, compacted, prev_model, prev_at = False, False, model, at or prev_at
                continue
            seen.add(rid)
            p = price(model)
            cc = u.get("cache_creation") or {}
            w5 = cc.get("ephemeral_5m_input_tokens", 0) if cc else (u.get("cache_creation_input_tokens", 0) or 0)
            w1h = cc.get("ephemeral_1h_input_tokens", 0) if cc else 0
            ctx = (u.get("input_tokens", 0) or 0) + (u.get("cache_read_input_tokens", 0) or 0) + w5 + w1h
            if p and at and (not since or at >= since) and (not until or at < until):
                p = tiered(model, p, ctx)
                for c in caps:
                    caps[c] += max(0, ctx - c) * p[2] / 1e6
                if w5 + w1h >= 50_000:
                    gap = (at - prev_at).total_seconds() / 60 if prev_at else None
                    cause = ("cold_start" if first else "compaction" if compacted
                             else "model_switch" if prev_model and prev_model != model
                             else "idle_1h" if gap and gap > 60 else "idle_5m" if gap and gap > 5 else "unknown")
                    usd = (w5 * 1.25 + w1h * 2) * p[0] / 1e6
                    cause_n["%s %s" % (who, cause)] += 1
                    cause_usd["%s %s" % (who, cause)] += usd
                if first:
                    cold[who][0] += 1
                    cold[who][1] += ctx
                    cold[who][2] += (w5 * 1.25 + w1h * 2) * p[0] / 1e6
            first, compacted, prev_model, prev_at = False, False, model, at or prev_at

json.dump({"rewrite_causes": {k: [cause_n[k], round(cause_usd[k], 2)] for k, _ in cause_usd.most_common()},
           "cap_read_ceiling_usd": {"%dk" % (c // 1000): round(v, 2) for c, v in caps.items()},
           "cold_starts": {k: {"n": v[0], "avg_tokens": v[1] // max(v[0], 1), "write_usd": round(v[2], 2)} for k, v in cold.items()}},
          sys.stdout, indent=1)
print()
sys.stderr.write("RESULT: %d large rewrites named, $%.2f\n" % (sum(cause_n.values()), sum(cause_usd.values())))
