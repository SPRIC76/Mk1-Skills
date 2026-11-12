# -*- coding: utf-8 -*-
# Version 0.1.0.0 | Deps: python 3.9+ stdlib only | Parent: promptaudit/SKILL.md | Path: promptaudit/scripts | Filename: drift.py | Created: 2026-11-08 23:59 ET
"""Does a copy of an instruction file still match its master? Read-only.

WHAT: compares COPY with MASTER line by line, line endings and surrounding blank lines aside,
counts the lines that differ, prints the first ones, and for each --phrase says whether the copy
and the master hold it. --after TEXT drops the copy's lines up to and including the first line
containing TEXT (a header or an import line the master does not have). --master-block STARTS
reads MASTER as a fenced block: only the lines between the first line that starts with STARTS
and its closing fence (for a capture file that wraps the master in a text fence).
WHEN: whenever two files are meant to be byte-copies of one master, and after every refresh.
RETURNS: exit 0 when identical, 1 when they differ; the last line starts with RESULT:.
NEVER: edits either file. A difference is reported, not reconciled: the owner decides which side is right.
"""
from __future__ import annotations

import argparse, difflib, re, sys


def lines(path):
    return open(path, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").split("\n")


def trim(ls):
    while ls and not ls[0].strip():
        ls = ls[1:]
    while ls and not ls[-1].strip():
        ls = ls[:-1]
    return ls


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("copy"); p.add_argument("master")
    p.add_argument("--after", default=None)
    p.add_argument("--master-fence", action="store_true", help="MASTER is a file whose block sits in the first fenced region")
    p.add_argument("--phrase", action="append", default=[])
    p.add_argument("--show", type=int, default=10)
    a = p.parse_args(argv)
    c, m = lines(a.copy), lines(a.master)
    if a.after:
        i = next((k for k, x in enumerate(c) if a.after in x), None)
        if i is None:
            print("RESULT: BAD INPUT no line in the copy contains %r" % a.after)
            return 2
        c = c[i + 1:]
    if a.master_fence:
        s = next((k for k, x in enumerate(m) if re.match(r"^`{3,}\w*\s*$", x)), None)
        if s is None:
            print("RESULT: BAD INPUT the master holds no fenced block")
            return 2
        fence = re.match(r"^(`{3,})", m[s]).group(1)
        e = next((k for k in range(s + 1, len(m)) if m[k].startswith(fence) and not m[k][len(fence):].strip()), len(m))
        m = m[s + 1:e]
    c, m = trim(c), trim(m)
    sm = difflib.SequenceMatcher(None, m, c, autojunk=False)
    diff = [(t, m[i1:i2], c[j1:j2]) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]
    n = sum(max(len(x), len(y)) for _, x, y in diff)
    for t, x, y in diff[: a.show]:
        print("  %s master: %s" % (t, (x[0][:110] if x else "<none>")))
        print("  %s copy:   %s" % (" " * len(t), (y[0][:110] if y else "<none>")))
    ct, mt = "\n".join(c), "\n".join(m)
    absent = []
    for ph in a.phrase:
        inm, inc = ph in mt, ph in ct
        print("  phrase %-4s copy=%-3s master=%-3s %s" % ("ok" if inm == inc else "DIFF", "yes" if inc else "no", "yes" if inm else "no", ph[:70]))
        if inm and not inc:
            absent.append(ph)
    if n == 0 and not absent:
        print("RESULT: OK copy and master identical (%d lines)" % len(m))
        return 0
    print("RESULT: DRIFT %d differing line(s); %d of %d phrase(s) in the master are missing from the copy" % (n, len(absent), len(a.phrase)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
