---
name: hillgate
description: >-
  Proves a change helped before you keep it. The keep-or-revert gate for improving an AI agent's prompt, skill, tool descriptions or settings against a fixed set of test cases, one change per round. Use when an agent or person is tuning instructions or a harness and needs to decide whether a change really helped: it fingerprints the files that must not move, measures the noise floor, refuses overfitting to the cases that were read, rejects rules that name a test case, and returns KEEP, REVERT or STOP. Works with any model, agent or runner, with python 3.9+ and nothing else. Not for building the cases or the runner, not for finding dated text in prompts, and not for measuring token cost.
metadata:
  version: "1.0.0.1"
  updated: "2026-11-08"
  works-with: any agent that reads SKILL.md; scripts need python 3.9+ and nothing else
---

# Hillgate

Proves a change helped before you keep it.

A hill-climbing loop is an agent changing something, re-running a fixed set of cases, and keeping the change only if the score proves it. The loop fails in four ways: the agent edits the thing that grades it, a gain is just noise, the change fixes the cases the agent read and nothing else, and a rule memorizes a case. This skill is the part of the loop that refuses those four, in code the agent does not edit.

Where a platform already ships a hill-climb command, use that; these decisions follow the same rules, so the results compare.

## Result rows

Each run of a case is one JSON line: `{"case":"t1","split":"train","rep":0,"pass":true,"cost":0.012}`. `split` is `train` (the agent may read these transcripts) or `test` (held out; never opened by whoever proposes changes). `rep` numbers repeats; `cost` is optional. A case that passes on average counts as its pass rate across reps.

## Steps

1. **Fingerprint** the files no round may touch (runner, grader, case file, lockfile): `python scripts/gate.py fingerprint fp.json <paths>`. Before every run: `python scripts/gate.py verify fp.json`. A STOP means show the diff and wait for the owner; an agent never approves its own gate.
2. **Noise.** Run the unchanged baseline at least twice (five is better) and run `python scripts/gate.py noise baseline.jsonl`. The floor it prints is the smallest gain worth believing. If it exceeds the smallest gain worth shipping, add repeats or choose a calmer target before round one.
3. **Each round, one change.** Optional: `python scripts/gate.py budget --round T --total N` gives how many separable edits may be bundled (more early, one late). Check a proposed rule with `python scripts/gate.py rule --text "..." --cases cases.jsonl --max-words 40`: a rule that names a case is refused.
4. **Decide.** `python scripts/gate.py decide --before before.jsonl --after after.jsonl --noise <floor> --min-delta <smallest worth shipping> --fingerprint fp.json [--max-cost-increase <percent>]`. KEEP needs: no case lost, a held-out gain above the floor and the minimum, and at least one train case fixed. Train up with held-out flat is overfitting; any lost case is a regression; both revert. Without a held-out split the verdict says so: that result describes the process, not a claim.
5. **Report** the held-out change from the starting point, not the train change, with its noise floor and the cost.

## Boundaries

The gate never edits a file, runs a model or approves a harness change. Thresholds are the caller's: no default is tuned to anyone's data, so calibrate the floor and the minimum on your own cases before trusting a KEEP. Cost is a first-class metric: count the proposer's own spend and the rejected rounds.
