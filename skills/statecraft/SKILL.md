---
name: statecraft
description: Statecraft - draw a plain-language statechart of a flow or system (every state and path, bugs marked red, fixes green), then prove its laws with a model checker (TLA+ by default, Kani for Rust) so a race, retry or ordering bug shows up as the exact steps that break it. Use when the user says Statecraft, statechart, state machine, draw the states or flow, TLA+, formal verification, model check, prove it, invariant or laws; when code has concurrency, locks, leases, expiry, retries, idempotency, queues, sync between machines or agents, a multi-step write, or a user flow with many branches (notifications, checkout, sign-in, handoffs); when a bug happens only sometimes or under timing; and before trusting a fix to any of those. Hands each law's result to an evidence-grading step. Not for checking a feature works the way a user meets it (a verification tool), writing tests that can fail (a test-discipline tool), or architecture diagrams (a diagramming tool).
metadata:
  version: "1.0.0.0"
  created: "2026-10-21 03:38 ET"
  optional_dependency: "Java 11+ and tla2tools.jar (TLA+ tools v1.7.4, pinned in scripts/check.py) for the model checks; the statechart, the laws and the handoff need neither"
  enforcement: "load-bearing (this file) + runtime-enforced (scripts/check.py refuses to trust a law it never saw break)"
---

# Statecraft — see the states, prove the laws

Draws a flow, then proves it can't break.

Tests check the cases someone thought of. A model checker tries every order of events
inside a bound, so the rare interleaving that breaks a rule turns up as a short list of
steps. The statechart makes that legible: the person sees the flow, the bug sits on it
in red, and the fix sits beside it in green.

## Any agent, any workflow

This folder is a skill in the Agent Skills format. Any agent that reads SKILL.md can use
it. The statechart is Mermaid text, and `scripts/check.py` needs Python 3.10+, Java and
the TLA+ tools jar, nothing else. It runs alone. Every neighbor below is optional.

## In the chain

- **Hands off to:** an evidence-grading step, which records each law's result at its
  grade. This skill never grades and never says "done".
- **Hands off to:** a tests-that-can-fail step, when a counterexample should become a
  kept regression test in the project's own suite.
- **Comes after:** nothing required. It is often called from a verification pass that
  meets a concurrency or ordering risk it cannot drive.

## The loop

Copy this checklist into your progress and tick it off:

```
- [ ] 1 Target: the promise that hurts users most if broken and tests rarely reach
- [ ] 2 Statechart drawn in plain words, shown to the person
- [ ] 3 Laws written in plain words, then as invariants
- [ ] 4 Model of the risky part, each action citing file:line at one commit
- [ ] 5 Shipped code checked: each law seen BROKEN or HOLDS
- [ ] 6 Each counterexample in plain steps, painted red on the chart
- [ ] 7 Each counterexample driven against the real code
- [ ] 8 Fix modeled and checked: every law HOLDS, and was seen red first
- [ ] 9 Fix driven against the real code
- [ ] 10 Handoff to the grading step; model folder kept beside the code
```

1. **Pick the target.** One flow or one shared resource. Name what the user loses if it breaks.
2. **Draw the statechart** with `reference/statechart.md`. Show it to the person before
   modeling. A wrong picture caught here costs nothing.
3. **Write the laws** in the person's words ("never two writers"), then as invariants.
4. **Model only the risky part** with `reference/modeling.md`. One action per step that
   touches shared state, so a read-then-write is two actions.
5. **Check the shipped code first.** One `.cfg` per law, headed `\* expect: broken` or
   `\* expect: holds`, then run:
   ```bash
   python scripts/check.py <model-folder>
   ```
   It ends in a `RESULT:` line. Exit 0 means every check showed what it expected. 1 is a
   finding. 2 means it could not run.
6. **Read each counterexample** into plain steps and paint it red on the chart.
7. **Drive it.** A short script forces the same order against the real code and reads back
   what the code reports. Reproduced, it is a real bug. Not reproduced, suspect the model.
8. **Model the fix** behind a constant, and check it until every law holds. `check.py`
   marks a law **NOT TRUSTED** if no check in the folder ever broke it. Seeing a law go red
   on the broken variant is what makes its pass mean anything.
9. **Drive the fix** with the same script. It should now read back the good outcome.
10. **Hand off,** then keep the folder (spec, cfgs, chart, driver) beside the code it
    cites. When the cited lines change, rerun it.

## What each result is worth

| Result | Grade it supports | Why |
|---|---|---|
| A law holds in the model, after being seen red | the **model** is TESTED | the check was proven able to fail |
| The code matches the model | ASSERTED at most | the model is a hand-made abstraction of the code |
| A counterexample reproduced by a driver | the bug is DRIVEN | the real code was made to show it |
| A fix: model green, driver green | the fix is DRIVEN | both halves read back |

Always state the bound: the actors, the ticks, the caps, and what the model leaves out.
"Holds for 3 sessions, 4 ticks, 2 landings (733,058 states)" is a report. "Proven" is not.

## Setup

Java 11 or later, and the pinned jar placed once outside any project:
`~/.agents/tools/tla2tools.jar`, or point `TLA2TOOLS_JAR` or `--jar` at it. With no jar,
`check.py` prints the exact download and its sha256 and stops. It never fetches anything.

## Files

- `reference/statechart.md`: the Mermaid template, the red and green marking, keeping the chart true
- `reference/modeling.md`: choosing the tool, writing the model, the folder layout, reading a
  counterexample, and the pitfalls that each cost a run
- `scripts/check.py`: runs every `.cfg` in a model folder, law by law, with a `RESULT:` line
- `examples/lost-update/`: the smallest complete folder, with one law that breaks on the
  shipped code and holds on the fix

