---
name: routecraft
description: >-
  Sets up and runs a self-improving model routing table: which AI model and
  effort or thinking level each kind of task gets, from searches and code to
  review, writing, images, animation, 3D and computer use. Defaults to the
  newest model in each family; changes a route only when a benchmark or a
  trial on the user's own work shows another does as well for less, or
  better. Steps a task up a rung when its check fails twice on the same gap,
  and trials a cheaper rung after a streak of first-try passes. Use when the
  user asks which model or effort to use, wants to cut AI spend without losing
  quality, wants model routing, a model ladder, escalation rules or model
  trials, or asks whether to switch to a new model. Any provider, any agent
  host. Not for choosing software libraries, tuning one prompt, or benchmark
  news with no routing decision.
license: Freeware
metadata:
  version: "1.0.0.1"
  updated: "2026-11-12"
---

# Routecraft

Sends each task to the cheapest model that passes.

**Every task goes to the cheapest model and effort that passes that kind of task's own check.**
The default is the newest version of each model family. A route moves only on evidence:
a public benchmark to start, then a trial on the user's own work. The step rules run in
`scripts/route.py`, so nobody has to remember them.

Works in any agent that reads a `SKILL.md`. The script needs only Python 3.9 or later and
calls no model and no network. Everything it writes stays in one folder in the user's
project, `routing/` by default.

**Paths.** Run the script by its absolute path, and point it at the project's routing
folder with `--dir <absolute path>` or the `ROUTING_DIR` environment variable, so it works
from any working folder. Below, `route` stands for `python <absolute path to this skill>/scripts/route.py --dir <project>/routing`.
`--dir` goes before the command name.

## Two jobs

1. **Setup** (once, about 20 minutes): build the ladder and the table for this user's models.
2. **Use** (every task): look up the route, do the work, run its check, record the result, follow the RESULT line.

Plus **freshness**, which keeps the table current (see the last section).

## Setup

Make the technical calls yourself. Ask the user only for:
- **a spend cap for trials** (money is theirs to decide), and
- **permission before writing outside the project**, such as a global instructions file.

Steps:

1. **Inventory what the user can run.** List every model and tool they have access to, on
   every host they use. Read each provider's own model list or docs today for exact model
   ids, prices per million tokens, and the effort or thinking settings each model takes.
   Put on the ladder only models the host where the work runs can actually call (a host
   that only runs one provider gets only that provider's models, unless the user calls the
   other provider's API from a script). Name the rest in the table's `notes` as Blocked.
   Pin exact ids, never a moving alias such as one ending in `latest`
   (an alias can change underneath you, and the table would drift with no trace).
2. **Build the ladder, cheapest first.** One rung is one model at one effort level.
   Inside a model, effort rises before the model changes: small model low, small model
   medium, mid model medium, mid model high, large model high, and so on.
   Across providers, order by price for a typical task (input price plus output price
   per million tokens is a fair first guess) until trials say otherwise. Use each
   provider's own effort or thinking label as it is (for example `off`, `low`, `high`).
   Run `route init` once, then for each rung, cheapest first:
   `route rung add --model <exact-id> --effort <level> --in <usd> --out <usd>`
   Then store the user's cap: `route cap <usd per month>`.
3. **Seed the categories.** `init` loads the 22 categories in
   [references/categories.json](references/categories.json), each with a starting tier:
   1 small and fast, 2 mid, 3 large, 4 frontier (strongest available), or `tool` for work a
   non-chat tool does. Decide which rung each tier starts on (the cheapest rung of the
   model class that fits it), then:
   `route seed --tier1 <n> --tier2 <n> --tier3 <n> [--tier4 <n>]`
   A tier you leave out falls back to the tier below it. Where the tier's model also has a
   rung at the category's suggested effort, the category starts on that rung instead.
   No category starts on tier 4; it is the top of the ladder that hard tasks step up to.
   Change any single route with `route set <category> --rung <n>`, and point a `tool`
   category at the user's tool with `route set <category> --tool "<tool name>"`. A category
   the user has no model or tool for: `route set <category> --evidence Blocked --note "<what would unblock it>"`.
   Add a category the user's work needs with `route set <new-id> --rung <n> --check "<pass check>" --description "<what it covers>"`.
   Remove none without saying why; a category that never comes up costs nothing.
4. **Grade every route.** Where a public benchmark or the maker's own numbers back a route,
   `route set <category> --evidence Reported --note "<source, date>"`. Otherwise leave it
   `Unknown`. If you cannot reach any sources (no network), leave every route Unknown and
   say so; never cite a source you did not read. Only a trial on the user's own work makes
   a route `Verified`, and only `compare` can set it. See [Evidence](#evidence).
5. **Code before any model.** Save this with `route note "<the rules>"`, and follow it: an exact string
   goes to a search tool, arithmetic and counting go to code, and a check that code can run
   is never left to a model's opinion.
6. **Plan the first trials.** Pick the routes where a wrong pick costs most (usually hard
   coding, review, and anything that gates spend or publishing) and build their trial sets
   as [references/trials.md](references/trials.md) describes. Estimate each trial's cost
   (its section on cost shows how) and keep the total inside the user's cap; `compare`
   and `status` show this month's trial spend against the cap.
7. **Wire it into the host.** Add the pointer line to the instructions file the host always
   loads, with the real absolute paths filled in, so every session uses the table and
   checks what is due. See [references/hosts.md](references/hosts.md) for the line, where
   that file lives, and how each host sets a model and effort.
8. **Check and hand over.** Run `validate` and `status`, then show the user the table in
   plain words: each kind of work, who does it, how hard it thinks, and how sure we are.

## Use, on every task

1. **Name the category** from the table. A task that spans two takes the stronger route
   for its hard part and the cheaper one for the rest (for example, a large model plans,
   a mid model builds, a small model reads the test output).
2. **Look up the route:** `route route <category> --task <task-id>`. With the task id, a
   task that already stepped up stays on its higher rung. `BLOCKED` means nothing the user
   has can do it; say so.
   Run the work on that model at that effort, as a sub-agent or a model switch where the
   host allows it ([hosts](references/hosts.md)). Where the host cannot switch, say which
   route the table gives and carry on.
3. **Run the category's check.** The check is code wherever it can be: tests, a type
   check, a lint, a measured count, a render compared to a reference.
4. **Record it:**
   `route record <category> --task <task-id> --outcome pass|fail --cost <usd> --gap "<one line on what failed>" --same-gap yes|no`
   Use one task id for every attempt at the same task. `--same-gap yes` means this failure
   is the same problem as the previous failure on this task; on a first failure it is always `no`.
5. **Follow the RESULT line:**
   - `DONE`: finished.
   - `RETRY`: try again on the same rung, giving the model the failure text.
   - `STEP-UP`: the same gap failed twice; move this task to the named rung for the rest of it.
   - `ESCALATE`: the top rung failed the same gap twice; stop and bring it to the user.
   - `...cheaper-rung trial is due`: schedule a step-down trial (below).

A step-up during a task changes that task only. The table itself changes only through a trial.

## The step rules

| Rule | Default | What it means |
|---|---|---|
| Step up | same gap fails 2 times | the task moves one rung up for the rest of the task |
| Try down | 10 first-try passes in a row | the next trial also runs the rung just below the current one (rung 1 has nothing below it, so it never flags) |
| Down tolerance | 1 case | the cheaper rung may pass one fewer held-out case and still win, if it costs less per finished task |
| Stale | 30 days | a route with no trial for this long is due a sweep |

The numbers live in `routing/routes.json` under `rules`. They are starting values, not a
vendor's; tune them from the trials, and log each change with its reason.

**Cost is per finished task**, retries included: total spend divided by tasks passed.
A cheap model that needs three tries is not cheap.

## Changing a route

Only `compare` changes a route, and only on at least 5 held-out cases (`min_held_out_cases`
in the rules). Without `--apply` it is a dry run that changes and logs nothing; always
finish a trial with `--apply`, which records the trial's spend once, moves the route on a
win and stamps the trial date either way:

`route compare <category> --current cur.jsonl --candidate cand.jsonl --candidate-rung <n> --apply --reason "<why this trial ran>"`

- **A cheaper rung** wins when it passes at least as many cases, minus the tolerance, at a lower cost per finished task.
- **A new or stronger model** wins when it passes at least as many cases at lower cost, or passes strictly more.
- **Only a Settled win moves a route by default** (see [How certain a route is](#how-certain-a-route-is)).
  A candidate that is ahead but only Leaning stays a candidate; add cases or repeats and
  run again. Where the user wants it moved now, `--accept-leaning` moves it, graded
  Leaning, and `status` keeps asking to firm it up.
- The default stays the newest model in each family until a trial proves something else.
- Every adopted change is written to `routing/changes.jsonl` with the before and after pass counts, costs and intervals.

Change one category per trial, so a regression always points at one change.

## How certain a route is

Five held-out cases are enough to try a route, not to settle it. Every trial verdict
carries a certainty, shown beside the route:

- **Consensus.** Run each case 3 times; a case passes for a rung only on 2 of its 3 runs.
  One run is a reading, not a consensus. Write one line per run with a `run` number;
  lines that share a case and run are retries of that run.
- **Settled**: at least 20 held-out cases x 3 runs per rung, and either the winner's 90%
  Wilson interval of pass rate sits above the other's, or the pass rates tie and a 90%
  bootstrap interval of the cost difference per finished task (resampling cases) leaves
  out zero in the winner's favor.
- **Leaning**: the point estimates favor the winner, but the size or that separation is not met.
- **Unsettled**: a tie on both measures, too few cases, or a rung with no runs.

The numbers live in `rules` (`settle_cases`, `settle_repeats`, `agreement`, `confidence`);
`status` lists every route that is not yet Settled as "firm up".

Rules that came out of running it:

- **A tie at the ceiling.** When every rung passes every case, the cases are too easy to
  rank quality; cost per finished task decides, and the result says it is bounded by that
  ceiling. Harder cases come before more repeats.
- **No measured result is no verdict.** A run that timed out or stopped at its budget is
  marked `"timeout": true`: it is left out of the pass rate and counted at its worst-case
  cost. Give that case more time or budget next round instead of scoring it a fail.
- **Cases limit certainty before money does.** With too few held-out cases no budget
  reaches Settled; spend first on building cases, then on repeats.
- **One trial process per spend ledger**, each arm capped in code at the trial's limit
  minus what is already spent, so parallel runs never overwrite each other's spend.

## Matching effort levels across models

The ladder starts with effort rising inside a model before the model changes, but that
order is a first guess. A stronger model at a lower effort can match a weaker model at
its highest effort and cost less per finished task, because the highest efforts think for
much longer. Makers sometimes report one such pair; a pair is never proof for the levels
below it. Do not assume the higher price per token loses either: in practice a newer model
at low or medium effort has come out cheaper per finished task than an older model at
high effort, at the same pass rate. Only a trial at each matching level tells.

So when a new model joins, trial its effort levels against the top two or three levels of
the model below it, on the same held-out cases, and keep a table of which level matches
which. Where a stronger model's level does as well for less, the weaker model's level is
beaten: move its routes and drop it from the ladder, so step-ups skip it:

`route rung remove --at <beaten rung> --to <winning rung> --reason "<the trial that showed it>"`

Until that trial runs, keep both on the ladder and grade the reported pair Reported.

Read the trial by measured cost, not by rung order: in one small trial (4 cases, 1 run each,
graded Leaning) a stronger model at medium effort beat the incumbent's highest effort for about
a quarter less per finished task, and the stronger model one rung higher cost more on those
cases. A result that small is a lead, not a route. The rung above a new route is not
automatically a good step-up; trial it before trusting it as the step-up.

## Evidence

Every route carries one grade:
- **Verified**: a trial on the user's own work, run and read back.
- **Reported**: the maker's numbers or a third-party benchmark. Name the source and date.
- **Unknown**: nothing yet; a trial is owed.
- **Blocked**: the user cannot reach that model or tool (no plan, no access). Say what would unblock it.

Never promote a grade without the trial that earns it. Makers' own benchmark tables are
Reported, however confident they sound.

## Freshness

The table stays current because these run on their own where the host can schedule work
(a scheduled task, a cron job, or a CI schedule). Where it cannot, the pointer line has
every session start with `route status`, which names what is stale or due:

- **New release:** once a week, read each provider's model list. A new model enters as a
  candidate rung, and the categories it is likely to win get a trial. Until that trial,
  the newest version of a family replaces the older version on its existing rungs only
  when the maker states it is a drop-in at the same or lower price; grade it Reported.
- **Monthly sweep:** rerun the trial for every route `status` marks stale or due.
- **Every failure a person catches** becomes a new trial case for its category, so the same failure cannot ship twice.
- **Spend stays inside the cap** (the cap covers trials; everyday task spend shows per category in `status` as cost per finished task): before a trial, add up its estimated cost; if it would pass the cap, run the costliest-to-get-wrong routes first and report the rest as owed.

## Files

| File | Holds |
|---|---|
| `routing/routes.json` | the ladder, tier starts, rules, trial cap, notes, and every category's route, check and evidence |
| `routing/ledger.jsonl` | one line per attempt: category, task, rung, outcome, cost, gap |
| `routing/changes.jsonl` | every route change, with the trial result that justified it |
| `routing/trials.jsonl` | every trial's spend, for the monthly cap |
| `routing/trials/<category>/` | that category's cases and pass checks ([trials](references/trials.md)) |

## What not to do

- Route by habit or by a model's reputation alone; route by the table.
- Let a model grade itself; the judge is a different model, and code checks come first.
- Change several routes, rules or prompts in one trial.
- Use a moving model alias anywhere in the table.
- Spend past the user's cap, or write outside the project without asking.

