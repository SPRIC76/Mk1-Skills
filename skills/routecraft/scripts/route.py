#!/usr/bin/env python3
# route.py 0.1.5.0 | deps: Python 3.9+ standard library only | part of the Routecraft skill | created 2026-11-11 05:52 UTC - history in CHANGELOG.md
"""Keeps a model routing table honest: which model and effort each kind of task
gets, when a task steps up a rung, when a cheaper rung is tried, and when a
route may change. Code decides; nothing here calls a model.

Every command ends with one line that starts with RESULT:.

  route.py init      [--dir routing]                 create the table, ledger and change log
  route.py rung      add --model ID --effort E [--in USD --out USD] [--at N]
  route.py rung      remove --at N [--to M] --reason TEXT   drop a rung a trial showed is beaten
  route.py seed      --tier1 N --tier2 N --tier3 N [--tier4 N]   start every category on its tier's rung
  route.py set       CATEGORY [--rung N] [--tool NAME] [--evidence G] [--note TEXT] [--check TEXT]
  route.py cap       USD                              monthly trial spend cap
  route.py note      TEXT                             set the table's notes (for example the code-before-model rules)
  route.py route     CATEGORY [--task T]              which rung to run on (with --task, keeps that task's step-up)
  route.py record    CATEGORY --task T --outcome pass|fail [--cost USD] [--gap TEXT] [--same-gap yes|no]
  route.py compare   CATEGORY --current FILE --candidate FILE --candidate-rung N [--apply] [--reason TEXT]
  route.py status                                     every route, its evidence and what is due
  route.py validate                                   check the table for errors

The table lives in <dir>/routes.json (default ./routing). Set ROUTING_DIR or
pass --dir to point elsewhere.
"""
import argparse
import json
import math
import os
import random
import sys
from datetime import datetime, timezone

DEFAULT_RULES = {
    "fails_to_step_up": 2,       # same gap failing this many times moves the task up one rung
    "passes_to_try_down": 10,    # first-try passes in a row before a cheaper rung is trialled
    "down_tolerance_cases": 1,   # a cheaper rung may pass this many fewer held-out cases
    "stale_after_days": 30,      # a route with no trial for this long is due a sweep
    "min_held_out_cases": 5,     # a trial with fewer held-out cases cannot change a route
    "settle_cases": 20,          # held-out cases each side needs before a verdict can be Settled
    "settle_repeats": 3,         # runs of every case each side needs before a verdict can be Settled
    "agreement": 0.66,           # share of a case's runs that must pass for the case to count (2 of 3)
    "confidence": 0.90,          # interval used to call a difference real
}

MOVING_ALIAS_HINTS = ("latest", "-current", "default", "auto")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def result(msg, code=0):
    print(f"RESULT: {msg}")
    sys.exit(code)


def paths(d):
    return (os.path.join(d, "routes.json"), os.path.join(d, "ledger.jsonl"), os.path.join(d, "changes.jsonl"))


def load(d):
    p = paths(d)[0]
    if not os.path.exists(p):
        result(f"FAIL no table at {p}; run init first", 2)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(d, table):
    p = paths(d)[0]
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(table, f, indent=2)
        f.write("\n")
    os.replace(tmp, p)


def append(path, row):
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row) + "\n")


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    result(f"FAIL {path} line {n} is not JSON", 2)
    return rows


def rung_of(table, n):
    for r in table["ladder"]:
        if r["rung"] == n:
            return r
    return None


def top_rung(table):
    return max((r["rung"] for r in table["ladder"]), default=0)


# ---------------------------------------------------------------- commands

def cmd_init(a):
    os.makedirs(a.dir, exist_ok=True)
    tp, lp, cp = paths(a.dir)
    if os.path.exists(tp) and not a.force:
        result(f"KEEP table already exists at {tp} (use --force to replace)")
    seed = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "categories.json")
    cats = {}
    if os.path.exists(seed):
        with open(seed, encoding="utf-8") as f:
            for c in json.load(f):
                cats[c["id"]] = {
                    "rung": None, "tool": None, "start_tier": c["tier"], "effort_hint": c.get("effort", ""),
                    "check": c["check"], "evidence": "Unknown", "evidence_note": "", "last_trial": None,
                    "description": c["description"],
                }
    table = {"version": 1, "created": now(), "pinned": now()[:10], "rules": dict(DEFAULT_RULES),
             "cap_usd_per_month": None, "tiers": {}, "notes": "", "ladder": [], "categories": cats}
    save(a.dir, table)
    for p in (lp, cp, os.path.join(a.dir, "trials.jsonl")):
        open(p, "a", encoding="utf-8").close()
    os.makedirs(os.path.join(a.dir, "trials"), exist_ok=True)
    result(f"OK created {tp} with {len(cats)} categories and an empty ladder; add rungs next")


def cmd_rung(a):
    table = load(a.dir)
    if a.action == "add":
        if not a.model or not a.effort:
            result("FAIL rung add needs --model and --effort", 2)
        lad = table["ladder"]
        pos = a.at if a.at else len(lad) + 1
        if pos < 1 or pos > len(lad) + 1:
            result(f"FAIL --at must be 1..{len(lad) + 1}", 2)
        new = {"model": a.model, "effort": a.effort, "price_in": a.in_price, "price_out": a.out_price}
        lad.insert(pos - 1, new)
        # renumber, and move every category route that pointed at or above pos up by one
        for c in table["categories"].values():
            if c.get("rung") and c["rung"] >= pos:
                c["rung"] += 1
        for i, r in enumerate(lad, 1):
            r["rung"] = i
        save(a.dir, table)
        warn = " (warning: id looks like a moving alias; pin an exact id)" if looks_alias(a.model) else ""
        result(f"OK rung {pos} = {a.model} at {a.effort}; ladder has {len(lad)} rungs{warn}")
    if a.action == "remove":
        lad = table["ladder"]
        if not a.at or not rung_of(table, a.at):
            result("FAIL rung remove needs --at with a rung on the ladder", 2)
        if not a.reason:
            result("FAIL rung remove needs --reason naming the trial that beat it", 2)
        gone = rung_of(table, a.at)
        to = a.to if a.to else (a.at + 1 if a.at < len(lad) else a.at - 1)
        if to == a.at or not rung_of(table, to):
            result("FAIL --to must be another rung on the ladder", 2)
        target = rung_of(table, to)
        moved = []
        for k, c in table["categories"].items():
            if c.get("rung") == a.at:
                c["rung"] = to
                moved.append(k)
        lad.remove(gone)
        for c in table["categories"].values():
            if c.get("rung") and c["rung"] > a.at:
                c["rung"] -= 1
        for i, r in enumerate(lad, 1):
            r["rung"] = i
        save(a.dir, table)
        append(paths(a.dir)[2], {"ts": now(), "removed_rung": gone, "moved_to": target,
                                 "categories": moved, "reason": a.reason})
        result(f"OK removed {gone['model']} at {gone['effort']}; {len(moved)} routes moved to "
               f"{target['model']} at {target['effort']}; ladder has {len(lad)} rungs")
    result("FAIL unknown rung action", 2)


def looks_alias(model_id):
    m = model_id.lower()
    return any(h in m for h in MOVING_ALIAS_HINTS)


def cmd_seed(a):
    table = load(a.dir)
    starts = {"1": a.tier1, "2": a.tier2, "3": a.tier3, "4": a.tier4}
    starts = {k: v for k, v in starts.items() if v}
    for k, v in starts.items():
        if not rung_of(table, v):
            result(f"FAIL tier {k} start rung {v} is not on the ladder", 2)
    table["tiers"] = starts
    n = 0
    for c in table["categories"].values():
        t = c.get("start_tier")
        if t == "tool" or c.get("rung") or c.get("tool"):
            continue
        # a tier with no start rung falls back to the nearest defined tier below it
        k = str(t)
        while k not in starts and int(k) > 1:
            k = str(int(k) - 1)
        if k not in starts:
            continue
        start = starts[k]
        # if the same model has a rung at the category's suggested effort, start there instead
        model = rung_of(table, start)["model"]
        hint = c.get("effort_hint")
        better = [r["rung"] for r in table["ladder"] if r["model"] == model and r["effort"] == hint and r["rung"] >= start]
        c["rung"] = better[0] if better else start
        n += 1
    save(a.dir, table)
    result(f"OK seeded {n} categories from tiers {starts}; set tool categories with set --tool")


def cmd_set(a):
    table = load(a.dir)
    c = table["categories"].get(a.category)
    if c is None:
        c = table["categories"][a.category] = {"rung": None, "tool": None, "start_tier": None, "effort_hint": "",
                                               "check": "", "evidence": "Unknown", "evidence_note": "",
                                               "last_trial": None, "description": a.description or ""}
    if a.rung is not None:
        if not rung_of(table, a.rung):
            result(f"FAIL rung {a.rung} is not on the ladder", 2)
        c["rung"], c["tool"] = a.rung, None
    if a.tool is not None:
        c["tool"], c["rung"] = a.tool, None
    if a.evidence:
        if a.evidence == "Verified":
            result("FAIL only a compare trial sets Verified", 2)
        c["evidence"] = a.evidence
    if a.note is not None:
        c["evidence_note"] = a.note
    if a.check is not None:
        c["check"] = a.check
    if a.description is not None:
        c["description"] = a.description
    save(a.dir, table)
    where = f"tool {c['tool']}" if c.get("tool") else f"rung {c.get('rung')}"
    result(f"OK {a.category} -> {where}, {c['evidence']}")


def cmd_note(a):
    table = load(a.dir)
    table["notes"] = a.text
    save(a.dir, table)
    result("OK notes saved")


def cmd_cap(a):
    table = load(a.dir)
    table["cap_usd_per_month"] = a.usd
    save(a.dir, table)
    result(f"OK trial cap set to ${a.usd:.2f} a month")


def month_spend(d):
    month = now()[:7]
    return sum(float(x.get("cost") or 0) for x in read_jsonl(os.path.join(d, "trials.jsonl")) if x["ts"][:7] == month)


def cmd_route(a):
    table = load(a.dir)
    c = table["categories"].get(a.category)
    if not c:
        close = [k for k in table["categories"] if a.category.split("-")[0] in k]
        result(f"FAIL unknown category {a.category}; nearest: {', '.join(close) or 'none'}", 2)
    if c.get("evidence") == "Blocked" and not c.get("tool") and not c.get("rung"):
        result(f"BLOCKED {a.category}: {c.get('evidence_note') or 'no model or tool the user can reach'}", 3)
    if c.get("tool"):
        print(json.dumps({"category": a.category, "tool": c["tool"], "check": c["check"], "evidence": c["evidence"]}))
        result(f"ROUTE {a.category} -> tool {c['tool']} ({c['evidence']})")
    if not c.get("rung"):
        result(f"FAIL {a.category} has no rung yet; set one in routes.json or run setup", 2)
    rung, why = c["rung"], ""
    if a.task:
        prior = task_rows(read_jsonl(paths(a.dir)[1]), a.category, a.task)
        if prior and prior[-1]["next_rung"] != rung:
            rung, why = prior[-1]["next_rung"], f", stepped up for task {a.task}"
    r = rung_of(table, rung)
    if not r:
        result(f"FAIL {a.category} points at rung {rung}, which the ladder lacks", 2)
    out = {"category": a.category, "rung": r["rung"], "model": r["model"], "effort": r["effort"],
           "check": c["check"], "evidence": c["evidence"]}
    print(json.dumps(out))
    result(f"ROUTE {a.category} -> rung {r['rung']} {r['model']} at {r['effort']} ({c['evidence']}{why})")


def task_rows(ledger, category, task):
    return [x for x in ledger if x["category"] == category and x.get("task") == task]


def cmd_record(a):
    table = load(a.dir)
    _, lp, _ = paths(a.dir)
    c = table["categories"].get(a.category)
    if not c or not c.get("rung"):
        result(f"FAIL {a.category} is not routed", 2)
    ledger = read_jsonl(lp)
    prior = task_rows(ledger, a.category, a.task)
    rung = prior[-1]["next_rung"] if prior else c["rung"]
    r = rung_of(table, rung) or {}
    first_try = not prior
    rules = table["rules"]
    nxt, verdict = rung, ""
    if a.outcome == "pass":
        verdict = "DONE task passed"
    else:
        # count this fail plus the unbroken chain of same-gap fails before it on this rung
        streak = 1
        link = a.same_gap == "yes"
        for x in reversed([x for x in prior if x["rung"] == rung]):
            if not link or x["outcome"] != "fail":
                break
            streak += 1
            link = x.get("same_gap") == "yes"
        if streak >= rules["fails_to_step_up"]:
            if rung >= top_rung(table):
                verdict = f"ESCALATE same gap failed {streak} times on the top rung; a person decides"
            else:
                nxt = rung + 1
                n = rung_of(table, nxt)
                verdict = f"STEP-UP to rung {nxt} {n['model']} at {n['effort']} for the rest of this task"
        else:
            verdict = "RETRY on the same rung with the failure text"
    row = {"ts": now(), "category": a.category, "task": a.task, "rung": rung, "model": r.get("model"),
           "effort": r.get("effort"), "outcome": a.outcome, "first_try": first_try, "cost": a.cost,
           "gap": a.gap, "same_gap": a.same_gap, "next_rung": nxt}
    append(lp, row)
    due = try_down_due(table, read_jsonl(lp), a.category)
    extra = "; cheaper-rung trial is due" if due else ""
    result(verdict + extra)


def first_try_streak(ledger, category):
    """First-try passes in a row, newest first, counting one row per task."""
    firsts = [x for x in ledger if x["category"] == category and x.get("first_try")]
    n = 0
    for x in reversed(firsts):
        if x["outcome"] == "pass":
            n += 1
        else:
            break
    return n


def try_down_due(table, ledger, category):
    c = table["categories"][category]
    return (c.get("rung") or 0) > 1 and first_try_streak(ledger, category) >= table["rules"]["passes_to_try_down"]


def case_runs(rows):
    """{case: [(run passed, run cost), ...]}. Lines with the same case and run are retries of
    one run: the run passes if any retry passed, and costs all of them."""
    runs = {}
    for x in rows:
        if x.get("timeout"):
            continue  # no measured result: left out of the pass rate, still counted in cost
        key = (x["case"], x.get("run", 0))
        ok, cost = runs.get(key, (False, 0.0))
        runs[key] = (ok or bool(x.get("pass")), cost + float(x.get("cost") or 0))
    cases = {}
    for (case, _), v in sorted(runs.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        cases.setdefault(case, []).append(v)
    return cases


def case_passed(runs, agreement):
    if not runs:
        return False
    return sum(1 for ok, _ in runs if ok) >= agreement * len(runs) - 1e-9


def summarize(rows, agreement=0.66):
    cases = case_runs(rows)
    passed = sum(1 for v in cases.values() if case_passed(v, agreement))
    cost = sum(float(x.get("cost") or 0) for x in rows)
    finished = sum(1 for v in cases.values() for ok, _ in v if ok)
    per = cost / finished if finished else float("inf")
    return len(cases), passed, cost, per


def wilson(k, n, conf):
    if n == 0:
        return 0.0, 1.0
    z = {0.80: 1.2816, 0.90: 1.6449, 0.95: 1.96, 0.99: 2.5758}.get(round(conf, 2), 1.6449)
    p = k / n
    d = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, mid - half), min(1.0, mid + half)


def cost_gap_interval(cur, cand, conf, draws=2000):
    """Bootstrap interval of (current - candidate) cost per finished task, resampling cases
    in pairs. A fixed seed keeps the verdict reproducible."""
    names = sorted(set(cur) & set(cand))
    rng = random.Random(0)
    gaps = []
    for _ in range(draws):
        pick = [rng.choice(names) for _ in names]
        out = []
        for side in (cur, cand):
            cost = sum(c for n in pick for _, c in side[n])
            done = sum(1 for n in pick for ok, _ in side[n] if ok)
            out.append(cost / done if done else float("inf"))
        if math.isfinite(out[0]) and math.isfinite(out[1]):
            gaps.append(out[0] - out[1])
    if not gaps:
        return float("-inf"), float("inf")
    gaps.sort()
    lo = gaps[int((1 - conf) / 2 * len(gaps))]
    hi = gaps[min(len(gaps) - 1, int((1 + conf) / 2 * len(gaps)))]
    return lo, hi


def certainty(rules, cur_rows, cand_rows, adopt, quality_decides):
    """Settled: enough cases and repeats, and the measure that decided separates at the
    confidence level. Leaning: the decision rests on point estimates only. Unsettled: the
    measures disagree or there is nothing to separate."""
    conf, agree = rules.get("confidence", 0.90), rules.get("agreement", 0.66)
    cur, cand = case_runs(cur_rows), case_runs(cand_rows)
    n = len(cur)
    reps = min([len(v) for v in list(cur.values()) + list(cand.values())] or [0])
    k0 = sum(1 for v in cur.values() if case_passed(v, agree))
    k1 = sum(1 for v in cand.values() if case_passed(v, agree))
    lo0, hi0 = wilson(k0, n, conf)
    lo1, hi1 = wilson(k1, n, conf)
    g_lo, g_hi = cost_gap_interval(cur, cand, conf)
    big_enough = n >= rules.get("settle_cases", 20) and reps >= rules.get("settle_repeats", 3)
    if quality_decides:
        separated = (lo1 > hi0) if adopt else (lo0 > hi1)
    else:
        # cost decided with quality held: the cost gap must clear zero in the winner's favour
        separated = (g_lo > 0) if adopt else (g_hi < 0)
    detail = (f"pass {k0}/{n} [{lo0:.2f}-{hi0:.2f}] vs {k1}/{n} [{lo1:.2f}-{hi1:.2f}], "
              f"cost gap [{g_lo:+.4f} to {g_hi:+.4f}], {reps} runs per case")
    if big_enough and separated:
        return "Settled", detail
    tied = k0 == k1 and g_lo <= 0 <= g_hi
    if n < rules.get("min_held_out_cases", 5) or tied:
        return "Unsettled", detail
    return "Leaning", detail


def cmd_compare(a):
    table = load(a.dir)
    _, _, cp = paths(a.dir)
    c = table["categories"].get(a.category)
    if not c:
        result(f"FAIL unknown category {a.category}", 2)
    cur, cand = read_jsonl(a.current), read_jsonl(a.candidate)
    held = [x for x in cur if x.get("held_out", True)]
    held_c = [x for x in cand if x.get("held_out", True)]
    if {x["case"] for x in held} != {x["case"] for x in held_c}:
        result("FAIL the two result files do not cover the same held-out cases", 2)
    agree = table["rules"].get("agreement", 0.66)
    n, p0, c0, per0 = summarize(held, agree)
    n1, p1, c1, per1 = summarize(held_c, agree)
    n = min(n, n1)  # a case with only timed-out runs on either side has no verdict yet
    least = table["rules"].get("min_held_out_cases", 5)
    if n < least:
        result(f"FAIL only {n} held-out cases; a route needs at least {least} to change", 2)
    spent = sum(float(x.get("cost") or 0) for x in cur + cand)
    if a.apply:
        append(os.path.join(a.dir, "trials.jsonl"), {"ts": now(), "category": a.category,
                                                     "candidate_rung": a.candidate_rung, "cost": spent})
    cap = table.get("cap_usd_per_month")
    cap_note = f"; trial spend this month ${month_spend(a.dir):.2f} of ${cap:.2f}" if cap else ""
    if not a.apply:
        cap_note += f" (this trial's ${spent:.2f} is logged when you rerun with --apply)"
    tol = table["rules"]["down_tolerance_cases"]
    cand_rung = a.candidate_rung
    if not rung_of(table, cand_rung):
        result(f"FAIL rung {cand_rung} is not on the ladder", 2)
    cheaper = per1 < per0
    if cand_rung < (c.get("rung") or 10**9):
        adopt = p1 >= p0 - tol and cheaper
        quality_decides = False
        why = f"cheaper rung: {p1}/{n} vs {p0}/{n} passed, ${per1:.4f} vs ${per0:.4f} per finished task"
    else:
        # same or higher rung (for example a new model): must do at least as well AND cost less,
        # or pass strictly more cases than the current route
        adopt = (p1 >= p0 and cheaper) or p1 > p0
        quality_decides = p1 != p0
        why = f"candidate: {p1}/{n} vs {p0}/{n} passed, ${per1:.4f} vs ${per0:.4f} per finished task"
    sure, detail = certainty(table["rules"], held, held_c, adopt, quality_decides)
    if p0 == n and p1 == n:
        detail += "; every case passed on both sides, so the cases are too easy to say much about quality"
    why = f"{why}; {sure}: {detail}"
    ahead = adopt
    # only a Settled verdict moves a route, unless the person accepts a Leaning one
    adopt = adopt and (sure == "Settled" or (sure == "Leaning" and a.accept_leaning))
    print(json.dumps({"cases": n, "current_pass": p0, "candidate_pass": p1, "current_cost_per_task": per0,
                      "candidate_cost_per_task": per1, "adopt": adopt, "candidate_ahead": ahead, "certainty": sure}))
    if adopt and a.apply:
        before = c.get("rung")
        c["rung"] = cand_rung
        c["evidence"] = "Verified"
        c["evidence_note"] = why
        c["certainty"] = sure
        c["last_trial"] = now()[:10]
        save(a.dir, table)
        append(cp, {"ts": now(), "category": a.category, "from_rung": before, "to_rung": cand_rung,
                    "why": why, "reason": a.reason or ""})
        result(f"ADOPTED {a.category} moves rung {before} -> {cand_rung}; {why}{cap_note}")
    if not adopt and a.apply:
        c["last_trial"] = now()[:10]
        c["certainty"] = sure
        if c["evidence"] != "Verified":
            c["evidence"] = "Verified"
            c["evidence_note"] = f"current route held in trial: {why}"
        save(a.dir, table)
    if ahead and not adopt:
        result(f"KEEP candidate is ahead but only {sure}; add cases or repeats until it is Settled "
               f"(or rerun with --accept-leaning to move it now, graded Leaning); " + why + cap_note)
    result(("ADOPT (dry run; add --apply) " if adopt else "KEEP ") + why + cap_note)


def cmd_status(a):
    table = load(a.dir)
    _, lp, _ = paths(a.dir)
    ledger = read_jsonl(lp)
    stale_days = table["rules"]["stale_after_days"]
    today = datetime.now(timezone.utc).date()
    owed = 0
    print(f"{'category':24} {'rung':>4}  {'model @ effort':40} {'evidence':9} {'$/task':>8}  due")
    for k, c in table["categories"].items():
        r = rung_of(table, c["rung"]) if c.get("rung") else None
        me = f"{r['model']} @ {r['effort']}" if r else (f"tool: {c['tool']}" if c.get("tool") else "(unrouted)")
        due = []
        if c["evidence"] == "Blocked":
            due = []
        elif c["evidence"] != "Verified":
            due.append("trial owed")
        elif c.get("certainty") != "Settled":
            due.append(f"firm up ({c.get('certainty') or 'Leaning'})")
        if c.get("last_trial"):
            age = (today - datetime.strptime(c["last_trial"], "%Y-%m-%d").date()).days
            if age > stale_days:
                due.append(f"stale {age}d")
        if c.get("rung") and try_down_due(table, ledger, k):
            due.append("try cheaper")
        owed += 1 if due else 0
        rows = [x for x in ledger if x["category"] == k]
        done = len({x.get("task") for x in rows if x["outcome"] == "pass"})
        spent = sum(float(x.get("cost") or 0) for x in rows)
        per = f"{spent / done:.4f}" if done else "-"
        print(f"{k:24} {str(c.get('rung') or '-'):>4}  {me[:40]:40} {c['evidence']:9} {per:>8}  {', '.join(due)}")
    cap = table.get("cap_usd_per_month")
    spend = f"; trial spend this month ${month_spend(a.dir):.2f}" + (f" of ${cap:.2f}" if cap else " (no cap set)")
    result(f"OK {len(table['categories'])} categories, {len(table['ladder'])} rungs, {owed} with something due{spend}")


def cmd_validate(a):
    table = load(a.dir)
    errs, warns = [], []
    rungs = [r["rung"] for r in table["ladder"]]
    if rungs != list(range(1, len(rungs) + 1)):
        errs.append("ladder rungs must be numbered 1..N with no gaps")
    for r in table["ladder"]:
        if looks_alias(r["model"]):
            warns.append(f"rung {r['rung']} id '{r['model']}' looks like a moving alias; pin an exact id")
    for k, c in table["categories"].items():
        if c.get("rung") and not rung_of(table, c["rung"]):
            errs.append(f"{k} points at missing rung {c['rung']}")
        if not c.get("rung") and not c.get("tool") and c.get("evidence") != "Blocked":
            warns.append(f"{k} has no rung or tool")
        if c.get("evidence") in ("Reported", "Blocked") and not c.get("evidence_note"):
            warns.append(f"{k} is {c['evidence']} but names no source or reason in evidence_note")
        if c.get("evidence") not in ("Verified", "Reported", "Unknown", "Blocked"):
            errs.append(f"{k} evidence must be Verified, Reported, Unknown or Blocked")
        if not c.get("check"):
            errs.append(f"{k} has no pass check")
    if not table.get("cap_usd_per_month"):
        warns.append("no monthly trial cap set; run cap USD")
    for w in warns:
        print(f"warn: {w}")
    for e in errs:
        print(f"error: {e}")
    if errs:
        result(f"FAIL {len(errs)} errors, {len(warns)} warnings", 1)
    result(f"OK table valid, {len(warns)} warnings")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.environ.get("ROUTING_DIR", "routing"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("rung"); p.add_argument("action", choices=["add", "remove"]); p.add_argument("--model")
    p.add_argument("--effort"); p.add_argument("--in", dest="in_price", type=float)
    p.add_argument("--out", dest="out_price", type=float); p.add_argument("--at", type=int)
    p.add_argument("--to", type=int); p.add_argument("--reason"); p.set_defaults(fn=cmd_rung)
    p = sub.add_parser("seed")
    for t in (1, 2, 3, 4):
        p.add_argument(f"--tier{t}", type=int, required=t == 1)
    p.set_defaults(fn=cmd_seed)
    p = sub.add_parser("set"); p.add_argument("category"); p.add_argument("--rung", type=int)
    p.add_argument("--tool"); p.add_argument("--evidence", choices=["Reported", "Unknown", "Blocked", "Verified"])
    p.add_argument("--note"); p.add_argument("--check"); p.add_argument("--description"); p.set_defaults(fn=cmd_set)
    p = sub.add_parser("cap"); p.add_argument("usd", type=float); p.set_defaults(fn=cmd_cap)
    p = sub.add_parser("note"); p.add_argument("text"); p.set_defaults(fn=cmd_note)
    p = sub.add_parser("route"); p.add_argument("category"); p.add_argument("--task"); p.set_defaults(fn=cmd_route)
    p = sub.add_parser("record"); p.add_argument("category"); p.add_argument("--task", required=True)
    p.add_argument("--outcome", choices=["pass", "fail"], required=True); p.add_argument("--cost", type=float)
    p.add_argument("--gap", default=""); p.add_argument("--same-gap", choices=["yes", "no"], default="no")
    p.set_defaults(fn=cmd_record)
    p = sub.add_parser("compare"); p.add_argument("category"); p.add_argument("--current", required=True)
    p.add_argument("--candidate", required=True); p.add_argument("--candidate-rung", type=int, required=True)
    p.add_argument("--apply", action="store_true"); p.add_argument("--reason")
    p.add_argument("--accept-leaning", action="store_true"); p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("validate"); p.set_defaults(fn=cmd_validate)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
