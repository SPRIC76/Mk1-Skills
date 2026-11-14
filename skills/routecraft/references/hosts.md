# Applying a route on your host

Hosts change their settings often. Read your host's current docs before wiring; the
notes below are starting points as of late 2026, not guarantees.

## The pointer line

Add one line to the instructions file the host loads in every session, so the table is
used without anyone remembering it:

> Model routing. Script: `python /abs/skill/scripts/route.py --dir /abs/project/routing`. At the start of a session run it with `status` and act on anything due. Before a task, run it with `route <category> --task <task-id>` and use that model and effort. After the task's check, run it with `record <category> --task <task-id> --outcome pass|fail --cost <usd> --gap "<what failed>" --same-gap yes|no` and follow its RESULT line.

Replace `/abs/skill` and `/abs/project` with the real absolute paths before writing the line.

Keep it to that one line. Some hosts cap the size of their instructions field, and a
fixed list of "this model does this job" rules beside it would disagree with the table as
soon as a trial moves a route. If the file already has such a list, replace it with the
pointer line rather than keeping both, and ask the user first if it is a file they wrote.

Common places for that file (project level first; a user-wide file affects every project,
so ask before writing one):

| Host | Project instructions file |
|---|---|
| Claude Code | `CLAUDE.md` |
| Codex CLI and other agents that follow the AGENTS.md convention | `AGENTS.md` |
| Gemini CLI | `GEMINI.md` |
| Cursor | a rule file under `.cursor/rules/` |
| Any other host | its system prompt or project rules field |

## Setting the model and effort

- **A host with sub-agents** (for example Claude Code): give each sub-agent its model and
  effort in its definition, or pass them when you start it, so the main session stays on
  its own rung and hands each part to the route the table gives.
- **A command-line agent with config profiles or a model flag** (for example Codex CLI or
  Gemini CLI): start the sub-task with that model and effort, through a profile or a
  command flag; read the host's docs for the exact names.
- **A host with a model picker only**: the agent says which route the table gives, and
  the user or a rule file picks it. Record the result the same way.
- **Calling a provider's API directly**: pass the exact model id, and the provider's own
  effort or thinking setting (named differently by each provider: an effort level, a
  reasoning effort, or a thinking budget). Read the provider's current API reference for the names.
- **Batch work** (`bulk` category): most providers offer a cheaper batch route for work that
  can wait; use it when the category's latency allows.

## Hosts that cannot switch models

The table still helps: it says when the current model is above or below what the task
needs, and the ledger still records outcomes, so trials can run later on a host that can.
