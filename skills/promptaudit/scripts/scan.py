# -*- coding: utf-8 -*-
# Version 0.1.0.0 | Deps: python 3.9+ stdlib only | Parent: promptaudit/SKILL.md | Path: promptaudit/scripts | Filename: scan.py | Created: 2026-11-08 23:09 ET
"""Deterministic first pass of a prompt-surface audit. Read-only.

WHAT: finds the instruction text an agent loads (CLAUDE.md, AGENTS.md, rule files, skills,
subagents, commands), then runs the greppable signals of a dated-pattern audit: pressure
language, thinking scaffolds, retired model ids, request-parameter fossils, output caps,
paragraphs repeated across files, named paths that no longer exist, and history stacked in
a file's first line. Prints one finding per line with file:line, and ends in a RESULT line.
WHEN: first step of a prompt audit, and again after each change, so the count only falls.
RETURNS: exit 0 and findings; exit 1 with --fail-over N when findings exceed N.
NEVER: edits, deletes, moves or runs anything it reads. Does not judge whether a line is
load-bearing - that is the model's reading of the report, with the keep list in SKILL.md.
"""
from __future__ import annotations

import argparse, json, os, re, sys
from collections import defaultdict

SKIP = {".git", "node_modules", "__pycache__", "worktrees", "rollback", "upstream", "archive", "retired"}
NAMES = {"claude.md", "claude.local.md", "agents.md", "gemini.md", ".cursorrules", "skill.md",
         "copilot-instructions.md"}
DIRS = ("rules", "agents", "commands", "output-styles")  # under .claude/ or .cursor/

# (id, regex, why) - the signals of Anthropic's published prompt-audit, kept as data
SIGNALS = [
    ("pressure", r"\b(CRITICAL|IMPORTANT|MUST|ALWAYS|NEVER)\b[^\n]{0,60}", "emphasis in caps; current models over-apply it (state the one real constraint with its reason)"),
    ("hedge", r"\b(try to|if possible|ideally)\b", "a hedge on a real requirement reads as permission to under-deliver"),
    ("trait", r"\byou (tend to|often|sometimes) ", "trait claim about an older model; state the wanted behavior"),
    ("lazy", r"do not be lazy|don'?t be lazy|do not stop early|be thorough", "written for models that quit early; current models are proactive"),
    ("think", r"think step by step|take a deep breath|<scratchpad>|<thinking>", "thinking scaffold; replaced by native thinking and effort"),
    ("think-depth", r"think (harder|less)|don'?t overthink|do not overthink", "thinking depth belongs in effort, not prose"),
    ("cadence", r"every \d+ (tool calls|messages|turns)", "progress choreography written for chattier models"),
    ("cap", r"\bat most \d+ (words|sentences|bullets)|\bunder \d+ words", "numeric output cap tuned to an old model; starves reasoning"),
    ("suppress", r"don'?t narrate|no interim updates|hold all findings", "update suppressor; current models under-narrate with it"),
    ("format-ban", r"never use (bullets|headers|bold)|no (bullets|headers)\b", "anti-formatting rule written against over-formatting models"),
    ("tool-discourage", r"only use tools when|minimi[sz]e tool calls", "followed literally by current models; remove or say when to check sources"),
    ("prefill", r"assistant[- ]turn prefill|\bprefill\b", "assistant prefill 400s on current models; use structured outputs"),
    ("budget", r"budget_tokens|\"temperature\"|temperature=|top_p=|top_k=", "removed or rejected on current models"),
    ("forced-tool", r"tool_choice[^\n]{0,24}\"?(any|tool)\"?", "forced tool use 400s on the newest models"),
    ("grader", r"you will be graded|hidden tests?", "describe the requirement, never the grader"),
    ("migration-relative", r"\b(now works differently|no longer|also counts)\b", "a diff against a prompt version the model never saw"),
]
RETIRED = r"claude-(2|instant)[\w.-]*|claude-3[\w.-]*|claude-(opus|sonnet)-4-(1(-\d+)?|2025\d{4})"  # certain-retired only; the model confirms the rest against the vendor's live model page


def walk(root):
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x not in SKIP]
        parts = set(d.replace("\\", "/").split("/"))
        for f in fs:
            low = f.lower()
            ok = low in NAMES or (low.endswith((".md", ".mdc")) and parts & {".claude", ".cursor"} and any(x in parts for x in DIRS))
            if ok:
                yield os.path.join(d, f)


def read(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def paras(text):
    for i, block in enumerate(re.split(r"\n\s*\n", text)):
        norm = re.sub(r"\s+", " ", block).strip().lower()
        if len(norm) >= 160 and not norm.startswith(("---", "```", "|")):
            yield norm


def scan(root, target_ids=None):
    files = set(walk(root))
    for p in list(files):  # one level of @imports, inside the project only
        for m in re.finditer(r"^@([\w./-]+\.md)\s*$", read(p), re.M):
            q = os.path.normpath(os.path.join(os.path.dirname(p), m.group(1)))
            if q.startswith(root) and os.path.isfile(q):
                files.add(q)
    files = sorted(files)
    out, seen, per_file = [], defaultdict(set), {}
    for p in files:
        t = read(p)
        rel = os.path.relpath(p, root)
        per_file[rel] = len(t) // 4
        lines = t.split("\n")
        first = lines[0] if lines else ""
        if len(first) > 600 and not first.startswith("---"):
            out.append((rel, 1, "history-header", f"first line is {len(first)} chars; change history belongs in git"))
        in_fm = False
        for n, line in enumerate(lines, 1):
            if line.strip() == "---":
                in_fm = not in_fm if n <= 2 or in_fm else in_fm
            for sid, rx, why in SIGNALS:
                if re.search(rx, line, re.I if sid not in ("pressure",) else 0):
                    out.append((rel, n, sid, why))
            if re.search(RETIRED, line, re.I):
                out.append((rel, n, "retired-model", "names a retired model; remove the workaround or re-point it at the target"))
        for q in paras(t):
            seen[q].add(rel)
        for m in re.finditer(r"`([\w./-]+\.(?:md|py|json|ya?ml|mjs|js|ts|ps1|sh|txt))`", t):
            ref = m.group(1)
            if ref.startswith(("http", "~", "/")) or "*" in ref or "<" in ref:
                continue
            cand = [os.path.join(root, ref), os.path.join(os.path.dirname(p), ref)]
            if "/" in ref and not any(os.path.exists(c) for c in cand):
                ln = t[: m.start()].count("\n") + 1
                out.append((rel, ln, "stale-path", f"`{ref}` is named but not in the project (generated, placeholder or moved?)"))
    for q, where in seen.items():
        if len(where) > 1:
            out.append((sorted(where)[0], 0, "repeated-paragraph", f"same paragraph in {len(where)} files: {', '.join(sorted(where))}; say it once"))
    return out, per_file


def main(argv=None):
    ap = argparse.ArgumentParser(description="First pass of a prompt-surface audit (read-only).")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-over", type=int)
    a = ap.parse_args(argv)
    findings, per_file = scan(os.path.abspath(a.root))
    findings.sort(key=lambda f: (f[2], f[0], f[1]))
    if a.json:
        print(json.dumps({"files": per_file, "findings": [dict(file=f, line=n, id=i, why=w) for f, n, i, w in findings]}, indent=1))
    else:
        for f, n, i, w in findings:
            print(f"{f}:{n} [{i}] {w}")
    counts = defaultdict(int)
    for _, _, i, _ in findings:
        counts[i] += 1
    tail = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    bad = a.fail_over is not None and len(findings) > a.fail_over
    print(f"RESULT: {'FAIL' if bad else 'OK'} files={len(per_file)} findings={len(findings)} {tail}".strip(), file=sys.stderr if a.json else sys.stdout)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
