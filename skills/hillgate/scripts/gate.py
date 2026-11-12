# -*- coding: utf-8 -*-
# Version 0.1.0.0 | Deps: python 3.9+ stdlib only | Parent: hillgate/SKILL.md | Path: hillgate/scripts | Filename: gate.py | Created: 2026-11-08 23:59 ET
"""The gate of a hill-climbing loop, outside the agent's edit surface.

WHAT: five read-only subcommands over plain files.
  fingerprint OUT PATH...  hash the harness files (runner, grader, case file, lockfile) into OUT
  verify FP                exit 1 and name each file that changed since the fingerprint
  noise RESULTS            baseline repeats -> per-run score spread -> the noise floor
  decide --before B --after A [--noise D] [--min-delta M] [--max-cost-increase PCT] [--fingerprint FP]
                           KEEP or REVERT one change, or STOP when a harness file moved
  budget --round T --total N [--bmin 1 --bmax 4]   cosine-annealed edit budget for round T
  rule --text "..." (--ids a,b | --cases FILE)      reject a change that names a case or runs long
WHEN: after every round of a loop (decide), before the first round (noise, fingerprint), before
every run (verify), and whenever an agent proposes a rule (rule).
RETURNS: result rows are JSON lines {"case","split":"train"|"test","rep":0,"pass":true,"cost":0.0}.
Every subcommand ends in one RESULT line; exit 0 on KEEP/OK/ACCEPT, 1 on REVERT/STOP/REJECT/changed.
NEVER: edits a harness file, a case file or a result file; calls a model; decides to keep on a
single flip or on train movement alone. Thresholds are arguments, not defaults tuned to anyone's data.
"""
from __future__ import annotations

import argparse, hashlib, json, math, os, re, statistics, sys
from collections import defaultdict


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def rows(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                r["case"]; r["pass"]
            except Exception:
                raise SystemExit("RESULT: BAD INPUT %s line %d is not a result row (needs case and pass)" % (path, n))
            r["pass"] = 1.0 if r["pass"] in (True, 1, "1", "true", "pass") else 0.0
            r["split"] = r.get("split", "train")
            r["rep"] = r.get("rep", 0)
            out.append(r)
    return out


def rates(rs):
    by = defaultdict(list)
    for r in rs:
        by[r["case"]].append(r["pass"])
    return {c: sum(v) / len(v) for c, v in by.items()}


def splits(rs):
    return {r["case"]: r["split"] for r in rs}


def cost(rs):
    return sum(float(r.get("cost", 0) or 0) for r in rs)


def cmd_fingerprint(a):
    fp = {p: sha(p) for p in a.paths}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(fp, f, indent=1, sort_keys=True)
    print("RESULT: OK fingerprinted %d file(s) into %s" % (len(fp), a.out))
    return 0


def cmd_verify(a):
    fp = json.load(open(a.fp, encoding="utf-8"))
    bad = []
    for p, h in sorted(fp.items()):
        if not os.path.isfile(p):
            bad.append(p + " (missing)")
        elif sha(p) != h:
            bad.append(p + " (changed)")
    for b in bad:
        print("  " + b)
    if bad:
        print("RESULT: STOP %d harness file(s) changed since the fingerprint; show the diff and wait for the owner" % len(bad))
        return 1
    print("RESULT: OK %d harness file(s) unchanged" % len(fp))
    return 0


def cmd_noise(a):
    rs = rows(a.results)
    by = defaultdict(list)
    for r in rs:
        by[r["rep"]].append(r)
    per_run = []
    for rep in sorted(by):
        rt = rates(by[rep])
        per_run.append(sum(rt.values()) / len(rt))
    if len(per_run) < 2:
        print("RESULT: NEED-REPS one repeat cannot show noise; run the unchanged baseline at least twice (five is better)")
        return 1
    sd = statistics.stdev(per_run)
    floor = a.k * sd
    print("  runs=%d mean=%.4f sd=%.4f" % (len(per_run), statistics.mean(per_run), sd))
    print("RESULT: OK noise floor %.4f (%g x sd over %d runs); a gain must clear it" % (floor, a.k, len(per_run)))
    return 0


def cmd_decide(a):
    if a.fingerprint:
        fp = json.load(open(a.fingerprint, encoding="utf-8"))
        moved = [p for p, h in fp.items() if not os.path.isfile(p) or sha(p) != h]
        if moved:
            print("RESULT: STOP harness file(s) changed (%s); show the diff and wait for the owner" % ", ".join(moved))
            return 1
    b, c = rows(a.before), rows(a.after)
    rb, ra, sp = rates(b), rates(c), {**splits(b), **splits(c)}
    common = [k for k in rb if k in ra]
    if not common:
        print("RESULT: BAD INPUT before and after share no case")
        return 1
    has_test = any(sp[k] == "test" for k in common)

    def score(r, keys):
        return sum(r[k] for k in keys) / len(keys) if keys else 0.0

    train = [k for k in common if sp[k] == "train"]
    test = [k for k in common if sp[k] == "test"] if has_test else train
    d_train = score(ra, train) - score(rb, train) if train else 0.0
    d_test = score(ra, test) - score(rb, test)
    regress = [k for k in common if ra[k] <= rb[k] - 0.5]
    fixes = [k for k in common if sp[k] == "train" and ra[k] >= rb[k] + 0.5] if has_test else \
            [k for k in common if ra[k] >= rb[k] + 0.5]
    cb, ca = cost(b), cost(c)
    inc = ((ca - cb) / cb * 100.0) if cb > 0 else 0.0
    tag = "" if has_test else " (no held-out split: process, not a claim)"
    summary = "train %+.3f test %+.3f noise %.3f fixes %d regressions %d cost %+.1f%%%s" % (
        d_train, d_test, a.noise, len(fixes), len(regress), inc, tag)
    for k in regress:
        print("  regressed: %s (%.2f -> %.2f)" % (k, rb[k], ra[k]))
    if regress or d_test < -a.noise:
        print("RESULT: REVERT regression; " + summary)
        return 1
    if has_test and d_train > a.noise and d_test <= a.noise:
        print("RESULT: REVERT overfit, train moved and held-out did not; " + summary)
        return 1
    if d_test > max(a.noise, a.min_delta) and fixes:
        if a.max_cost_increase is not None and inc > a.max_cost_increase:
            print("RESULT: REVERT cost, the gain does not pay for the extra spend; " + summary)
            return 1
        print("RESULT: KEEP; " + summary)
        return 0
    print("RESULT: REVERT no gain clears the noise floor and the smallest delta worth shipping; " + summary)
    return 1


def cmd_budget(a):
    t = max(0, min(a.round, a.total))
    n = math.ceil(a.bmin + (a.bmax - a.bmin) * 0.5 * (1 + math.cos(math.pi * t / a.total)))
    print("RESULT: OK round %d of %d may bundle %d independently attributable edit(s)" % (a.round, a.total, n))
    return 0


def cmd_rule(a):
    ids = set(x for x in (a.ids or "").split(",") if x)
    if a.cases:
        ids |= {r["case"] for r in rows(a.cases)}
    text = a.text
    hits = [i for i in sorted(ids) if re.search(r"(?<![\w-])" + re.escape(i) + r"(?![\w-])", text)]
    words = len(text.split())
    if hits:
        print("RESULT: REJECT the rule names case(s) %s; describe the behavior, not the case" % ", ".join(hits))
        return 1
    if a.max_words and words > a.max_words:
        print("RESULT: REJECT %d words, over the %d allowed; one mechanism per rule" % (words, a.max_words))
        return 1
    print("RESULT: ACCEPT %d words, no case named" % words)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("fingerprint"); x.add_argument("out"); x.add_argument("paths", nargs="+"); x.set_defaults(f=cmd_fingerprint)
    x = s.add_parser("verify"); x.add_argument("fp"); x.set_defaults(f=cmd_verify)
    x = s.add_parser("noise"); x.add_argument("results"); x.add_argument("--k", type=float, default=2.0); x.set_defaults(f=cmd_noise)
    x = s.add_parser("decide"); x.add_argument("--before", required=True); x.add_argument("--after", required=True)
    x.add_argument("--noise", type=float, default=0.0); x.add_argument("--min-delta", type=float, default=0.0)
    x.add_argument("--max-cost-increase", type=float, default=None); x.add_argument("--fingerprint"); x.set_defaults(f=cmd_decide)
    x = s.add_parser("budget"); x.add_argument("--round", type=int, required=True); x.add_argument("--total", type=int, required=True)
    x.add_argument("--bmin", type=int, default=1); x.add_argument("--bmax", type=int, default=4); x.set_defaults(f=cmd_budget)
    x = s.add_parser("rule"); x.add_argument("--text", required=True); x.add_argument("--ids"); x.add_argument("--cases")
    x.add_argument("--max-words", type=int, default=0); x.set_defaults(f=cmd_rule)
    a = p.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
