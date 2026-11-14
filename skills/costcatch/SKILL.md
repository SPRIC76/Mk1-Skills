---
name: costcatch
description: >-
  Costcatch - audit what an agent harness costs to run, read from Claude Code's own
  session logs (~/.claude/projects): the baseline over a window, where the spend goes
  (cache reads, cache rewrites, output, subagents, context size, tool output, the
  static prefix), what caused each big cache rewrite (compaction, idle, model switch,
  cold start), the levers ranked by saving and quality risk, and one lever tested by
  replay or a timed trial against the window before it. Use when asked what the agents
  cost, why a chat or a week was expensive, where the tokens or usage limits go, whether
  to cap compaction, change the subagent model or the cache TTL, or to rerun the harness
  audit or measure a trial. Not for the cost of an app that calls the Claude API itself
  (an API cost review), nor for proving a change works (a verification tool).
metadata:
  version: "1.0.0.0"
  updated: "2026-11-13"
---

# Costcatch — what the harness costs, and where to cut

Shows where your agent's money goes.

You can't cut a cost you haven't measured. The session logs already hold every
request's token counts, so the audit starts from them, not from a guess or from the
app's running total.

## Any agent, any workflow

The scripts read Claude Code's logs with the Python 3 standard library and only read:
they write nothing and send nothing. Any agent that can run Python can use them. They
print JSON to stdout and one `RESULT:` line to stderr. The method in the five steps
fits any harness that logs each request's usage.

## The five steps

**1. Map and baseline.** Run `scripts/baseline.py --since <date>` for the window, by
default the last 14 days. Read:
- the cost by part: cache read, 5-minute and 1-hour writes, output, input;
- who spends: main chats against subagents, and the subagent cost by model;
- the cost by context band, and the median and p90 context;
- the first request's size and what was injected before it: the static prefix;
- tool-result characters by tool.

The map is the list of what the harness loads into every request: the system prompt,
tools, MCP servers, skills listing, memory files and CLAUDE.md. A fresh `claude -p
"/context"` shows it per category at no cost. In Git Bash, set `MSYS_NO_PATHCONV=1`,
or the `/` becomes a Windows path.

**2. Attribute the rewrites.** Run `scripts/attribute.py` over the same window. Each
cache write of 50k+ tokens is named:
- cold start;
- compaction;
- model switch;
- idle over 1 hour, or over 5 minutes;
- unknown.

It also prints the cap ceiling: what cache reads above 120k, 150k and 200k cost.
That is an upper bound, because a cap also loses work.

**3. Rank the levers.** One table: layer, change, saving, quality risk, how to
validate, whose call. Output is not a lever: asking a model to write less trades
quality for pennies. A settings change is standing config, so it waits for the
owner's go.

**4. Test one lever (Rule 3: one change per run).**
- *Replay:* rerun one fully recorded task in a fresh headless chat with the lever on.
  Use a throwaway clone with no remote and outside calls sent to a dead port. The
  original's own checks are the quality gate. One task shows quality, not savings: a
  fresh chat pays to read the code again.
- *Trial:* the lever on for a week, then `baseline.py --since <start> --until <end>`
  against the week before, with the same `--until` arithmetic. Compare per request
  and per active chat, never totals, and read the chats that changed for lost work.

**5. Report.** The order: the map and baseline, ranked changes, changes made, test
plan, gaps. Every dollar figure is graded:
- **Measured:** from the logs.
- **Inferred:** worked out from measured figures.
- **Reported:** from docs, not tried here.

## The traps (each one cost a wrong first number)

| Trap | What happened | What the scripts do |
|---|---|---|
| Forks and resumes copy their parent's history | The first pass counted it twice and doubled the cost | Count a request once by `requestId`, a compaction once by `uuid` |
| A fork read before its parent | The parent's compaction looked like a cold start | A copied request still moves its session along (`selftest.py` case 14) |
| Claude Code's `cost-state` tally | It restarts with each app launch and has no timestamp: $88.88 against $819 measured | Printed beside the list-price figure only as a check, for sessions active in the window |
| The logs are not the bill | Compaction and background calls aren't logged: the replay's own total was 51% above its log | Every figure is a floor; say so |
| Typed prices | — | `PRICES` in each script, kept equal by `selftest.py` case 21. Update them from Anthropic's published model table (the claude-api skill caches it), never from memory |
| Git Bash `TZ=` | It silently prints UTC | `--since` and `--until` are UTC. Convert local time yourself and write both down |

## Scripts

| Script | Reads | Prints |
|---|---|---|
| `baseline.py [--since T] [--until T] [--root DIR] [--top N]` | every `*.jsonl` under `~/.claude/projects` | the map and baseline above |
| `attribute.py [--since T] [--until T] [--root DIR]` | the same | rewrite causes, cap ceilings, cold starts |
| `window_cost.py <session.jsonl> <from> <to>`, or `window_cost.py <folder>` | one session log between two UTC times, or a folder | requests, tokens, cost, peak context, compactions; for comparing one task's original against its replay |

`T` is `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`, in UTC.

