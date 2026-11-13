# The Proof Pack — Verifox, Testcatch, Browsetest

Proves the work before anyone calls it done.

An **agent skill pack**: three skills with one aim. An agent verifies its own work before it says "done", and leaves evidence someone else can re-read. Each skill is a self-contained folder in the Agent Skills format (`SKILL.md`, with `scripts/`, `reference/` or `templates/` beside it where it needs them), so it works in any agent that reads `SKILL.md`, and each works installed alone.

| Skill | What it does | Core question |
|-------|--------------|---------------|
| **Verifox** | Proves your work before you call it done. | Did I drive it the way a user does, and read the result back? |
| **Testcatch** | Writes tests that actually go red when it breaks. | Would this test go red if the thing it guards broke? |
| **Browsetest** | Measures the page instead of trusting the screenshot. | Did I measure the rendered page, or guess from the stylesheet? |

Each skill works alone. Together, Verifox names what to check, and Browsetest and Testcatch keep that check honest.

## Install

Unzip the download and copy any one of `verifox/`, `testcatch/` and `browsetest/`, or all three, into a skills folder your agent reads. The shared location comes first:

- `~/.agents/skills/` for every project, or a project's own `.agents/skills/` for that project alone.

Some hosts read their own folder as well, or take an uploaded package. These are examples only, not a list of what is supported; any agent that reads `SKILL.md` folders can use the skills, from the folder its documentation names:

| Host (example) | Where the skill folders go |
|----------------|----------------------------|
| Codex | `~/.agents/skills/` or a repository's `.agents/skills/` |
| Claude Code | `~/.claude/skills/` or a project's `.claude/skills/` |
| Cursor | `~/.cursor/skills/` or a project's `.cursor/skills/` |
| A host that takes uploads (claude.ai, for example) | Zip each skill folder as `<name>.skill`, with `<name>/SKILL.md` at its root, and upload it |

## Requirements

- **Python 3.10+** for `verifox/scripts/featuremap.py` and `testcatch/scripts/floor_guard.py`. Standard library only.
- **git** for Verifox's comparisons and staleness check, and for Testcatch's floor guard.
- **Optional, not included:** a Jev client, which Verifox's `--judge` and its decision at `--record` use as a decision layer. Install one beside `verifox/` as `jev-client/scripts/jev.py`, with the key it reads. Without it, everything else runs, and those two say by name that they did not judge.

## What each one carries

- **Verifox:** a feature map of every capability, from the user's side and the developer's; four evidence grades (DRIVEN, TESTED, ASSERTED, UNKNOWN); a proof store; branch, commit and production comparison.
- **Testcatch:** re-injection probes, which put the defect back on purpose and watch the check fail; the mutation check before a test file is finished; and a floor guard that lists every place a change lowered the test floor (a new skip, a lost assertion, a loosened threshold, a CI step gone), with a ratchet ledger.
- **Browsetest:** layout, color, contrast and typography read from the live page, and a page's first load played frame by frame.

## License

Freeware: see each skill's `LICENSE`. Copyright (c) 2026 MK1 Enterprise. Free to download and use; please link to [mk1made.us](https://mk1made.us) rather than rehosting.

---

<p align="center"><a href="https://mk1made.us">Mk1 made</a></p>
