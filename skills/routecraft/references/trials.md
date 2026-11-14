# Building a trial

A trial answers one question: does this rung do this category's work at least as well, for less?
It is small, fixed and pinned, so last month's result can be reproduced exactly.

## A trial set

Put each category's set in `routing/trials/<category>/`:

- `cases.jsonl`: one line per case, `{"case": "id", "input": "...", "held_out": true|false}`.
  Take cases from the user's own past work: a fixed bug with its test, a review where the
  bug is known, a picture a person already marked, a plan that later held or broke.
  A route needs at least 20 held-out cases to settle, so aim for 40 or more in all. Mark
  about half `held_out: true`; only those decide a route, the rest are for tuning prompts,
  so nothing is tuned to the deciding cases.
- **Prefer hard cases.** If every side passes every case, the trial only measures cost
  and says little about quality. Add cases that at least one side fails.
- **Say what is checked.** A case built from a past fix must either state what its hidden
  check tests, or hand the model the tests and forbid editing them. Otherwise every side
  fails the same cases and the trial measures the case, not the model. When two sides miss
  the same cases, inspect those cases before spending more.
- **Check each case before spending on it:** it fails before the fix and passes after.
- **Name the form of the job.** A fix with its tests in hand and a fix from a written
  report alone are different jobs; record which one a route was measured on, and trial the
  one the user actually does.
- `check`: how a case passes, as code wherever possible (a test command, a type check, a
  count, a diff against an answer key). Where a judgment is needed, a judge model that is
  not the model under test scores against a written rubric, and a person rules where judge
  and code disagree.
- `PINNED.md`: the exact model ids, effort levels, prompt version and date the trial used.

## Running it

Run every case 3 times on the current rung and on the candidate rung, with the same
prompt and tools. Write one result line per run (or per retry inside a run) to a file per rung:

```json
{"case": "fix-017", "run": 0, "pass": true, "cost": 0.031, "held_out": true}
```

`cost` is what that attempt spent, from the provider's usage numbers. Lines with the same
case and run are retries: the run passes if any retry passed, and costs all of them. A
case passes when at least 2 of its 3 runs pass.

- **Spend caps per case cause false misses.** Rerun every case that stopped on its cap,
  with more room, before scoring it.
- **Hard cases need longer time limits.** Mark a run that times out or stops at its budget
  `"timeout": true`, with its worst-case cost: it is left out of the pass rate, counted in
  cost, and rerun with more room next round.

Then let the script decide:

```
route compare code-routine \
  --current routing/trials/code-routine/rung4.jsonl \
  --candidate routing/trials/code-routine/rung3.jsonl \
  --candidate-rung 3 --apply --reason "10 first-try passes in a row"
```

Without `--apply` it only reports. With it, a win moves the route and logs the change;
a loss keeps the route and stamps the trial date.

## Estimating cost before you run

Cost per attempt is about (input tokens x input price + output tokens x output price) / 1,000,000.
Run two cases first as a pilot, read their real token counts from the provider's usage
numbers, then multiply by cases, rungs and expected retries. If the total would pass the
monthly cap that `route status` shows, run fewer routes this month, costliest-to-get-wrong first.

## Order of trials

Run first the routes where a wrong pick costs most: the strongest, costliest rungs (a
cheaper rung may do as well) and any check that gates money or publishing. Then routes
graded Unknown. Then the monthly sweep of stale routes.

## Before any paid trial

- **Check the billing source.** Run paid trials only on a subscription, or on an API key
  the user has confirmed is billed to their own credit account, with automatic top-up off.
  Refuse otherwise, and stop on the first refusal from the provider.
- **One runner per spend ledger.** Two trials writing to the same ledger at once can both
  pass the cap. Give each job its own lock name, so a scheduled run never commits another
  job's half-finished work.
- **Queued is not running.** Report a trial as running only when a scheduler or a live job
  is actually running it.

## Keep it honest

- Change one thing per trial: the rung, or the prompt, or the check, never two.
- Never edit a held-out case to make a model pass it.
- A failure a person catches in real work becomes a new case before anything else changes.
- Record the trial's total cost in the result, so the cap stays visible.
