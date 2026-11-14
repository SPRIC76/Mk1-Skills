#!/usr/bin/env python3
# Version 1.0.0 | Deps: Python 3.10+, Java 11+, tla2tools.jar (TLA+ tools v1.7.4) | Parent: statecraft 1.0.0 | Path: statecraft/scripts | Filename: check.py | Created: 2026-10-21 03:30 ET
"""Run every model check in a model folder and say, law by law, what held and what broke.

USAGE
    python scripts/check.py <model-folder> [--jar <tla2tools.jar>] [--json <out.json>] [--timeout <s>]

WHAT A MODEL FOLDER HOLDS
    One or more .tla files and one .cfg per check. Each .cfg opens with comment lines:
        \\* expect: broken | holds     what this check should show (required)
        \\* spec: <File>.tla           the module TLC runs (required)
        \\* why: <one line>            what this variant stands for (optional)
    The law names come from the cfg's own INVARIANT and PROPERTY lines.

WHAT IT REPORTS
    Per check: HOLDS (states, depth), BROKEN (the law, then the counterexample as numbered
    steps), or ERROR (TLC could not run it). Then per law: whether it was ever seen to break.
    A law that holds but was never seen to break in any check is NOT TRUSTED: a check that
    cannot fail proves nothing. Ends with one RESULT: line.

EXIT
    0  every check showed what it expected, and every law that holds was seen to break
    1  a finding: a check showed the opposite of what it expected, or a law never seen red
    2  could not run: no Java, no jar, a missing spec, or TLC itself failed

IT NEVER
    Downloads anything, writes inside the model folder (TLC runs in a temporary copy),
    or calls a law proven for code: a model that holds says the MODEL obeys the law.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

# The TLA+ tools release this skill was calibrated on (TLC2 2.19, rev 5a47802). A newer jar may
# word its output differently; the parser below reads both v1.7 and v1.8 wording.
PINNED = ("v1.7.4", "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88")
GET = ("curl -L -o ~/.agents/tools/tla2tools.jar "
       "https://github.com/tlaplus/tlaplus/releases/download/%s/tla2tools.jar   "
       "(sha256 %s)" % PINNED)


def find_jar(given):
    for p in (given, os.environ.get("TLA2TOOLS_JAR"),
              os.path.join(os.path.expanduser("~"), ".agents", "tools", "tla2tools.jar")):
        if p and os.path.isfile(p):
            return p
    return None


def read_cfg(path):
    head, laws = {}, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*\\\*\s*(expect|spec|why)\s*:\s*(.+?)\s*$", line)
            if m:
                head[m.group(1)] = m.group(2)
                continue
            m = re.match(r"\s*(INVARIANTS?|PROPERTY|PROPERTIES)\s+(.+?)\s*$", line)
            if m:
                laws += m.group(2).split()
    return head, laws


def parse(out):
    """TLC's own words -> (verdict, law, steps, states, depth). Reads v1.7 and v1.8 wording."""
    # The last count is the final one: a long run also prints the running count on Progress lines.
    states = (re.findall(r"([\d,]+) distinct states found", out) or [None])[-1]
    depth = (re.findall(r"depth of the complete state graph search is (\d+)", out) or [None])[-1]
    num = lambda v: int(v.replace(",", "")) if v else None
    steps = [m.group(1) for m in re.finditer(r"^State \d+: <([A-Za-z_][\w]*(?:\([^)]*\))?)", out, re.M)]
    m = re.search(r"Invariant (\w+) is violated", out)
    if m:
        return "BROKEN", m.group(1), steps, num(states), num(depth)
    if re.search(r"Temporal properties were violated", out):
        return "BROKEN", "(a temporal property)", steps, num(states), num(depth)
    if re.search(r"Action property (\w+)", out) and "violated" in out:
        m = re.search(r"Action property (\w+)", out)
        return "BROKEN", m.group(1), steps, num(states), num(depth)
    if re.search(r"Deadlock reached", out):
        return "BROKEN", "(deadlock)", steps, num(states), num(depth)
    if "Model checking completed. No error has been found." in out:
        return "HOLDS", None, [], num(states), num(depth)
    return "ERROR", None, [], None, None


def run_one(jar, folder, cfg, spec, timeout):
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "m")
        shutil.copytree(folder, work)
        cmd = ["java", "-XX:+UseParallelGC", "-cp", jar, "tlc2.TLC", "-config", cfg,
               "-workers", "auto", "-deadlock", "-metadir", os.path.join(tmp, "meta"), spec]
        try:
            p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "ERROR", None, [], None, None, "timed out after %ds - bound the model" % timeout
        out = p.stdout + p.stderr
        v = parse(out)
        tail = "" if v[0] != "ERROR" else "\n".join(
            l for l in out.splitlines() if l.strip() and "JAVA_TOOL" not in l)[-600:]
        return v + (tail,)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder")
    ap.add_argument("--jar")
    ap.add_argument("--json")
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args(argv)

    def done(code, line):
        print("RESULT: %s - %s" % ({0: "ok", 1: "finding", 2: "could not run"}[code], line))
        return code

    if not os.path.isdir(a.folder):
        return done(2, "no model folder at %s" % a.folder)
    cfgs = sorted(f for f in os.listdir(a.folder) if f.endswith(".cfg"))
    if not cfgs:
        return done(2, "no .cfg in %s; each check is one .cfg" % a.folder)
    if not shutil.which("java"):
        return done(2, "no Java on PATH; TLC needs Java 11 or later")
    jar = find_jar(a.jar)
    if not jar:
        print("No tla2tools.jar. Get the pinned one once, outside any project:\n  " + GET)
        return done(2, "no tla2tools.jar (--jar, TLA2TOOLS_JAR, or ~/.agents/tools/tla2tools.jar)")

    rows, seen_red, held, mismatch, errors = [], set(), {}, [], []
    for cfg in cfgs:
        head, laws = read_cfg(os.path.join(a.folder, cfg))
        expect, spec = head.get("expect"), head.get("spec")
        if expect not in ("broken", "holds") or not spec:
            errors.append(cfg)
            print("%s: ERROR - opens without '\\* expect: broken|holds' and '\\* spec: <File>.tla'" % cfg)
            continue
        if not os.path.isfile(os.path.join(a.folder, spec)):
            errors.append(cfg)
            print("%s: ERROR - its spec %s is not in the folder" % (cfg, spec))
            continue
        verdict, law, steps, states, depth, tail = run_one(jar, a.folder, cfg, spec, a.timeout)
        row = {"check": cfg, "why": head.get("why", ""), "expect": expect, "verdict": verdict,
               "laws": laws, "broken_law": law, "steps": steps, "states": states, "depth": depth}
        rows.append(row)
        if verdict == "ERROR":
            errors.append(cfg)
            print("%s: ERROR - TLC did not finish:\n%s" % (cfg, tail))
            continue
        if verdict == "BROKEN":
            seen_red.add(law)
            print("%s: BROKEN %s after %d steps (%s)" % (cfg, law, len(steps) - 1 if steps else 0,
                                                    head.get("why", "")))
            for i, s in enumerate(steps[1:], 1):
                print("    %d. %s" % (i, s))
        else:
            for l in laws:
                held.setdefault(l, []).append(cfg)
            print("%s: HOLDS %s - %s distinct states, depth %s (%s)" % (
                cfg, ", ".join(laws), states, depth, head.get("why", "")))
        if (verdict == "BROKEN") != (expect == "broken"):
            mismatch.append(cfg)
            print("    ^ expected %s" % expect.upper())

    never = sorted(l for l in held if l not in seen_red)
    for l in never:
        print("NOT TRUSTED: %s holds in %s but no check here ever broke it. Add a broken variant "
              "and see it go red first." % (l, ", ".join(held[l])))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"folder": os.path.abspath(a.folder), "jar": os.path.basename(jar),
                       "checks": rows, "never_seen_red": never}, f, indent=2)
    if errors:
        return done(2, "%d check(s) could not run: %s" % (len(errors), ", ".join(errors)))
    if mismatch or never:
        return done(1, "%d check(s) showed the opposite of what they expected, %d law(s) never seen red"
                    % (len(mismatch), len(never)))
    return done(0, "%d check(s) as expected; every law that holds was seen to break first" % len(rows))


if __name__ == "__main__":
    sys.exit(main())
