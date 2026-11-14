---
name: verifox
description: Verifox - verify your own work empirically before reporting it, using a project's feature map (every capability from the user's and developer's face, how it is reached and operated, what it must and must not do, its evidence grade) for the working tree, any commit, and what production serves. Use before saying done, fixed, working, ready or complete, or passing on a helper's success report; when the user says Verifox; when asked what a project can do, how a user reaches it, or what an operator configures; when comparing branches, commits or production; when a change touches a user-facing path; when unsure which convention to follow; and when the feature map is stale or missing. Not for how code works (a code-search tool), what depends on what or what a change breaks (a dependency-graph tool), or vetting, absorbing or rebuilding someone else's work (a tool that vets outside work). Carries featuremap.py (optional Jev client).
metadata:
  version: "1.0.0.0"
  optional_dependency: a Jev client, not included in this pack, installed beside this folder as jev-client/scripts/jev.py - for --judge and the decision at --record only; everything else runs without it, and those two say by name when it is missing
  owner: SPRIC76
  enforcement: load-bearing (this file) + runtime-enforced (scripts/featuremap.py)
---

# Verifox — verify before done


An agent reporting on its own work is the least reliable witness available: it knows
what it intended, which is exactly the thing under test. Verification is the step
that converts a claim into evidence a third party can re-read. Reading the diff
again is not that step.

Three halves, and none works alone. The **feature map** is materialized memory of
what exists and how a user reaches it — without it, every session rediscovers the
app and verifies whatever it happened to notice. **Verification** drives that reach
path and reads the outcome back — without it, the map is a document that describes
an app nobody confirmed still behaves that way. **Pattern conformance** keeps the
codebase honest as memory — because an agent writes what its neighbors wrote, so
a bad neighbor is contagious and a good pattern can drift somewhere it was never
designed for.

The aim underneath all three: make the codebase able to tell a stranger the truth
about itself, so that the easiest path through it is also the correct one. An agent
with no engineering background and no context will take the shortest concrete
action available. That is not a flaw to design around — it is the lever.

## Any agent, any workflow

This folder is a skill in the Agent Skills format: any agent that reads SKILL.md
can use it, and nothing here assumes one host, one editor or one install path.
The scripts need Python 3.10 or later and nothing else, and run from wherever the
folder sits. The map stands alone, beside any other skill or none. The one optional dependency is named in the frontmatter, and
without it only the two Jev readings are skipped, each saying so.

## In the chain

This is the verify step in a longer procedure, and each neighbor is optional:
it runs alone, and a step whose neighbor is not installed is done by hand.

- **Comes after:** a tests-that-can-fail discipline, once the checks for the
  work exist and can fail; a rendered-page measuring discipline, when a
  page's measured numbers come back as evidence; and a statechart-and-model-
  checking step, when a concurrency or ordering law comes back held or broken.
  Its pass grades the model, never the code: the code stays ASSERTED until a
  driver reproduces the counterexample (DRIVEN bug) or reads back the fix.
- **Hands off to:** a rendered-page measuring discipline, when the work is a
  page; a native-calibration check, when verified work added or retired a
  scaffold and its ledger must say so; and a workflow-capture step, when a
  verified piece needs its resource row.
- **Returns:** to a skill-packaging standard, when the work is a skill that
  fails its checks or its listing reads back wrong.

## Fire this before the sentence, not after

The trigger is the moment you are about to write *done*, *fixed*, *working*,
*ready*, *should work now*, or *complete*. If no evidence artifact exists for the
feature you touched, you have not finished — you have stopped.

## A helper's success report is a claim, not evidence

When a subagent, a peer session, a workflow or a tool hands back *done*, *fixed* or
*tests pass*, you hold its claim — ASSERTED at best — not your evidence. It is the
same unreliable witness, one step removed. Before you repeat it:

1. **Read what it actually changed**: `git status` and `git diff` (against the ref it
   started from) in the folder it worked in, and the files it names. A commit message
   is part of the claim.
2. **Read the observable yourself**: re-run the test it says passed and read the
   count, including skipped; open the page, output or file it says it produced.
3. **If it touched tests, check the floor did not drop** — a new skip, a removed
   assertion, a loosened threshold (a test-floor guard reads the diff for these). "All tests
   pass" over a diff that skips the failing one is the case this rule exists for.
4. **Report its work at the grade you verified** and name what you did not re-check.
   Its word never becomes DRIVEN or TESTED by being repeated.

## Three bars, and they are not the same bar

| Bar | Question | Where the answer lives |
|---|---|---|
| **Specified** | Does it do what it was specified to do? | ticket, spec, the map's Contract field |
| **Intended** | Does it do what the operator actually wanted? | their words in the request, verbatim — and `--judge` asks Jev whether each entry's observable would show them met |
| **Expected** | Does it do what any reasonable user would expect? | your judgment, stated out loud |

Check all three. **When they disagree, that is the finding** — report the
disagreement and which one you built to. Passing the spec while missing the intent
is the most common way verified work is still wrong, and it is invisible to any
test suite, because the suite was written from the same misreading.

## Evidence grades — say which one you hold

| Grade | Means | May be claimed |
|---|---|---|
| **DRIVEN** | The feature was operated the way a user operates it and the observable outcome was read back | only with the artifact named: status code, DB row, URL, rendered text, exit code, log line, screenshot |
| **TESTED** | An automated test exercises it **and** that test has been proven able to fail | only with the re-injection probe recorded — a tests-that-can-fail discipline covers how |
| **ASSERTED** | The code was read and looks right | always available, never sufficient |
| **UNKNOWN** | Never checked | the honest default for everything else |

**The rule with teeth: for the feature you changed, ASSERTED alone may not be
reported as working.** Drive it or test it, or say plainly that you did not.

## The loop

1. **Read the map** for the feature you are about to touch — its reach path,
   preconditions, contract, and current grade. No map: run
   `python scripts/featuremap.py --init` and fill the feature you touched.
2. **Change the code.**
3. **Drive the reach path as a user does** — the map's own steps, not a shortcut
   through internals. Calling the handler directly proves the handler runs, not
   that the button reaches it. See `reference/verification-protocol.md` per surface.
4. **Drive the settings and the config, not only the happy path.** A setting is
   verified when its *effect* is observed somewhere else, never when it merely
   saves and re-renders. Drive both states, confirm the default, and name the
   permutations you did not drive.
5. **Capture the proof as a record, not a glance** — structured, stored, dated,
   tied to a commit. `reference/proof-capture.md` has the layout.
6. **Analyze it against the last capture and against the bar.** A capture nobody
   compares is a souvenir. The delta is where regressions, timing drift and
   silent scope loss show up, and it is where real numbers come from: a driven run
   already knows its duration, its counts and its errors, so metrics and telemetry
   are a by-product of verification rather than a separate project.
7. **Check the negative contract** — what it must *not* do. A checkout that charges
   twice passes every does-it-check-out test.
8. **Check you built it the way this codebase builds things**, and that you did not
   carry a pattern somewhere it was never designed for. You wrote what your
   neighbors wrote; confirm the neighbors were right. See
   `reference/pattern-conformance.md`. If you had to invent a convention because
   none was findable, that is the finding — write the rule with its canonical
   example rather than leaving the next agent to copy you.
9. **Record the grade, the artifact, the date and the commit** in the map.
10. **Run `python scripts/featuremap.py --check`** and reconcile what it reports —
    drift your change introduced, any feature whose proof is now older than the
    code it certifies (**evidence that predates its implementation is not
    evidence**), and any anti-pattern that grew past its ceiling.
11. **Report the reading, the conditions, and what you did not cover.**

## Both faces, any commit, and what production serves

The requirement, 2026-09-23: map everything from both the user's face and the
development face, in production and in development, retroactively and as live, and
across any branches that exist, for comparison's sake.

| Question | Command (`scripts/featuremap.py … --project <dir>`) | What it reads back |
|---|---|---|
| What can it do, for a user and for a developer? | `--list [--face user\|dev]` | every capability with its face, surface, location and grade |
| What could it do at a commit, a tag, another branch? | `--list --ref <ref>` | the same, read out of git into a temporary folder — never checked out |
| What does one have that the other lacks? | `--compare <A> [<B>]` (one ref: against the working tree) | capabilities added, removed, re-faced or moved; authored entries added, removed or regraded |
| What is production actually running? | `--live` | the commit range production serves, then what development has that production lacks |
| Would the observable show the intent met? | `--judge` | Jev's reading per entry — one request, pinned, never a gate until calibrated |

The **user face** is what a person reaches: pages, controls, regions, shortcuts, and
any endpoint the client code calls. The **developer face** is what an operator
reaches: CLI commands, scripts, environment variables **by name — never a value**,
deploy services, CI workflows, and endpoints no client file calls. `--live` requests
only the GET paths a map entry declares plus one file production serves verbatim,
never follows a redirect, and is only as current as the last fetch — which it
prints. A file a ref snapshot could not see is named, never skipped quietly.

## The Intended bar, through Jev

`--judge` asks Jev one question per entry, all in one request: would reading back
this observable show whether the intent was met? `--record` asks the same question
of each passing DRIVEN or TESTED capture as it is stored, against the observable
just read back, and keeps the decision in the capture. So every proof gets a Jev
decision without anyone remembering to ask (before that, on 2026-09-29, Jev was
asked a handful of times a day). Write `intent:` as the outcome the operator wanted, not the
story of how the work came about, or there is nothing to hold the observable
against. It asks through the optional Jev client this file's `optional_dependency`
names, installed beside this one, which holds the pin, the lint and the key; how to
ask Jev anything lives with that client, not here. Without it, `--judge` and
`--record` say so by name and ask nothing, and everything else runs. The two thresholds belong to this skill's code and stay unvalidated
placeholders until `reference/jev-calibration.md` records the operator's own data. Jev decides
and code routes: a NO sends the entry back to be re-authored, a torn answer goes
to a person, a YES holds. Until then that routing fails nothing; Jev's answer is
never a message for a user to read.

## Production grade is the bar, and it is a floor with a name

Production-grade is not a feeling. Before output is called that, each of these holds
or is reported missing: the changed feature is DRIVEN or TESTED, never ASSERTED; its
negative contract was checked; its settings were driven in both states; the proof is
captured, analyzed against the previous capture, and newer than the code; and the
report names its own bound. Anything short of that ships with the gap stated.

## Done is not completed

*Done* is the operator stopping for now. *Completed* is their word, not yours — never
write it about their work. What you may write is what you verified, how, and the
bound: **an unbounded pass claim is the defect.** "Checkout verified DRIVEN on
Chrome at 1920 wide with one item; not checked: multiple items, declined card,
mobile width" is a report. "Checkout works" is not.

## What this skill never does

Accept a green run as evidence the run could have gone red (a tests-that-can-fail
discipline owns that). Judge a rendered appearance by eye or by stylesheet
(measuring the rendered page owns that — this skill sends you there and does not
restate it). Let a script overwrite the human-authored half of a map, or claim
coverage of a stack the extractor could not parse — an extractor that skips what it
cannot read reports a clean map over an unmapped app, which is the worst output
available.

## Files

- `reference/feature-map-schema.md` — every field, and the reason each exists
- `reference/verification-protocol.md` — how to drive and read back per surface: web UI, settings and config, CLI, API, background job, data
- `reference/proof-capture.md` — the proof store, what a capture record must carry, how to analyze across captures, and the metrics a driven run yields for free
- `reference/pattern-conformance.md` — why an anti-pattern spreads rather than sits, the two failure directions (contagion, and a good pattern drifting out of scope), the ratchet, and writing a rule for an agent with no context
- `reference/jev-calibration.md` — the one question Verifox asks Jev, its two thresholds, how they get validated on the operator's own data, and the first readings (the client's rules are the client's own)
- `scripts/featuremap.py` — `--init`, `--check` (drift + stale proof + unparsed surfaces + anti-pattern spread + pattern drift, exits non-zero so a hook can refuse on it), `--write` (derived block only), `--reaim` (move each hand-mapped `code:` or `entry:` range whose lines moved to where they are now, stamped `@ <commit>`, and name each range it leaves and why; a one-line pointer whose own line was rewritten is found by what the code derives for it and marked REWRITTEN, or named `rewritten: re-aim by hand`, which fails `--check`), `--record` (append a capture and analyze it against the last one), `--ratchet` (lower a ceiling to what is present; it will never raise one), `--list` / `--compare` (both faces, any ref), `--live` (what production serves), `--judge` (the Intended bar, through Jev). `--help` says what every flag does; a whole `--record` call (`--feature`, `--grade`, `--result`, `--observable`, `--how`, `--bound`, `--conditions`, `--metric`, `--artifact`) is in `reference/proof-capture.md`, and a whole `--live` call (`--url`, `--fingerprint`, `--probe`, `--branch`) in `reference/feature-map-schema.md`
- `templates/FEATURE-MAP.md` — the instance a project gets

