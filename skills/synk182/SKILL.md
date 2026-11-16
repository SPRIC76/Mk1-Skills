---
name: synk182
description: >-
  Synk182 (Synk): keeps two copies of a project in agreement without losing
  work - the user's copy and a working copy such as a sandbox or upload, a
  mounted or cloud-synced folder, a git worktree, another machine's copy, or a
  deployed copy of something developed elsewhere. Compares every file across
  the full similarity spectrum from identical to superset, proposes each change
  with its evidence, backs up into ARCHIVE/ before writing, verifies every
  write six ways and rolls back on failure. Only an exact hash match skips
  review. Use whenever the user says synk, s182, synk182 or synk it; asks to
  sync, mirror, push or pull files between two folders or machines; asks which
  copy is newer; says files are different, out of date or missing on one side;
  or when docs/PULSE.json records drift. Not
  for redundancy inside one copy (a consolidation tool), git merges or the
  rules of working in a repo (git, a repo-rules skill), or what two versions
  can do rather than what their files hold (a verification tool).
license: Freeware
compatibility: Python 3.10 or later (standard library only) to run the bundled engine; the workflow itself needs no script.
metadata:
  version: "3.4"
  updated: "2026-11-16"
---

# Synk182 — The Symphonous Strategist
 Formerly **nothing**
> *Formally a link between sink, and sync. "Who thinks this shi don't stink? let that sync in" signed- A. Blinken.*

**Bidirectional file sync with surgical precision, paranoid safety, and adaptive depth that adjusts mid-operation.**

Keeps two copies in agreement. Writes nothing until you approve, and backs up each file first.

Works in any agent that reads a `SKILL.md`, on its own; the engine needs only Python 3.10 or later.

## Three Fixed Rules

1. Mandatory review for >60% similar (only 100% hash match skips review)
2. 60% threshold for intelligent merge
3. >100% superset/subset = ultra-careful handling, maximum scrutiny

## When the Request Is Ambiguous

| Level | Phrases | Action |
|-------|---------|--------|
| 🟢 Immediate | "sync my project/files", "synchronize", "keep in sync" | Activate |
| 🟡 Confirm | "update my project files" | Clarify: Synk or direct edits? |
| 🔴 Clarify | "files are different", "don't see my file" | Offer Synk |
| ❌ Not Synk | Create/edit single files, move within dir, redundancy inside one copy (a consolidation tool), branch merges (git), repo and worktree rules (your repository's own rules), what a version can do rather than what its files hold (a verification tool) | — |

**Name the two copies first.** Say which is the user's copy (authority) and which is the working copy, in the user's words. Most sync damage starts with the two being swapped.

## Similarity Spectrum

| Range | Relationship | Action | Review |
|-------|-------------|--------|--------|
| >100% | Superset/subset | Ultra-careful merge | ⚠️ MAXIMUM |
| 100% | Identical (hash) | Nothing to do | None (only case) |
| 60-99% | High similarity | Intelligent merge | Mandatory |
| <60% | Low similarity | Manual/skip | Variable |
| — | Binary, not identical | Choose a side or keep both | Manual |
| — | Only on one side | Copy after approval | Standard |

## Six-Layer Verification

| # | Layer | Catches |
|---|-------|---------|
| 1 | Existence | Missing files, deletions |
| 2 | Hash (SHA-256) | Any content change — **gatekeeper**: match = skip 3-6 |
| 3 | Size | Truncation, corruption |
| 4 | Timestamp | Stale versions (2-second tolerance for filesystem rounding) |
| 5 | Line count | Partial writes |
| 6 | Content diff | Specific changes |

## Adaptive Depth

### Tier 1: Baseline from the last run
| Condition | Rigor |
|-----------|-------|
| `synk_last_run` < 24h, no signals | **Quick** — hash check only, skip unchanged |
| 1-7 days, minor signals, or no record of a last run | **Standard** — full six-layer on all files |
| >7 days or drift signals | **Thorough** — six-layer + relationship analysis + merge candidates |

The last run is read from `docs/PULSE.json`, which Synk writes only when asked (`--pulse`). With no such file, start at Standard.

### Tier 2: Adaptive Mid-Scan
**Downshift:** Quick scan finds 95%+ identical → summary report, skip detailed diff.
**Upshift:** Quick scan finds >10 non-identical files → escalate to Thorough.
Standard scan finds superset relationships → escalate to Thorough for those clusters.

**Report shifts:** `🔄 Rigor adjusted: Quick → Standard (15 files differ)`

### Tier 3: Signals left by other tools (optional)
Only where other tools share the project's `docs/PULSE.json`; see Optional integration. Signals only raise rigor, never lower it.

## Safety

**Backup before every write:** each file an apply will overwrite is copied first into `[user copy]/ARCHIVE/synk-[timestamp]/<side>/` with `manifest.json`, `rollback.md` and `apply-report.json`. Files that did not exist are recorded so rollback deletes them. Just before each copy the destination is held against its backup; one created, edited or removed since the backup was taken is refused and left as it is.
**Full-project backup:** before a large or first sync, copy the whole project aside first — the engine backs up per file, not per project.
**Auto-rollback:** any item that fails a verification layer after copying — or raises anything while being verified — is restored from the backup on the spot, and reported; a rollback that fails is reported with the backup to restore by hand, and the run exits 1.
**Never through a link:** nothing is written, deleted, restored or backed up through a junction or link, and no source is read through one; each is refused with the link named.
**Nothing writes without approval:** the dashboard and the plan are read-only.

## Workflow

1. **Inventory** — Scan both copies, fingerprint all files. The scan skips `.git`, `node_modules`, build output, caches and the copy root's `ARCHIVE` (Synk's own backups); it never follows a junction or link, and it names on the dashboard, with its reason, anything it could not compare. Exact rules, case folding included: [references/ENGINE.md](references/ENGINE.md)
2. **Compare** — Classify by tier + direction (with adaptive depth adjustment); two copies that hold the same lines with different line endings are classed `line_endings`, each side's convention named, never as a merge (endings that differ line by line inside the same mix are said to differ within the file); two copies that differ only in a UTF-8 byte-order mark are said so, the side carrying it named
3. **Propose** — Dashboard: `🔄 ✓12 identical | ⚠️2 superset | 🔀3 merge | ⏎1 line endings | ➕3 new`; show diffs for every merge and superset
4. **Execute** — After approval: backup → copy or merged write → verify (six layers) → roll back failures → log
5. **Report** — `🔄 Synced: [n] | Verified: ✓ | Archive: [path]`; with `--pulse`, the run is recorded in `docs/PULSE.json`

## Scripts

**`scripts/synk_engine.py`** — the engine behind the workflow. Read-only unless told to apply.

```bash
python scripts/synk_engine.py USER_COPY WORKING_COPY                    # dashboard
python scripts/synk_engine.py USER_COPY WORKING_COPY --plan plan.json   # numbered plan, nothing written
python scripts/synk_engine.py USER_COPY WORKING_COPY --diff path/in/project.md    # --diff=-name for a name that starts with a dash
python scripts/synk_engine.py USER_COPY WORKING_COPY --apply plan.json --approve 2,5 [--pulse]
```

- **Plan items** carry a `direction`; a merge, superset or line-ending pair stays `null` until the user decides, and an approved `null` item is skipped and the run exits 1.
- **Refusals:** an item whose path leaves either copy, names a device or a form Windows reserves, lies in a skipped folder, passes through a link, or whose destination changed since `--plan` is refused before any backup or write, and the run exits 1. An item already applied is reported, not failed.
- **`--approve new`** approves every one-sided file at once (show the list first); it leaves out `docs/PULSE.json` and names each item it refuses.
- **`--pulse`** records the run in `USER_COPY/docs/PULSE.json`, keeping every other key, and never touches a PULSE that does not parse.
- Everything the engine writes is LF on every platform. The same operations are available from Python as `SynkEngine(...)`.

Every edge case, word for word: [references/ENGINE.md](references/ENGINE.md). Read it before applying a plan by hand or when a run refuses an item.

## Merge Strategies

**Standard (60-99%):** Shared base → user-unique + working-unique → merged → diff for review.
**Superset (>100%):** Identify superset → identify delta → assess intent → present with preview → **never auto-resolve**.
**Configs (JSON/YAML):** Structural key-value diff → user version as authority.

## Anti-Patterns
- Syncing build artifacts (node_modules, bin/, obj/)
- Auto-resolving superset merges
- Syncing mid-edit (verify saved first)
- Assuming newer = better
- Swapping which copy is the user's
- Copying secrets (`.env`, keys) into a copy the user did not mean to hold them
- Consolidating during sync (a consolidation tool's job)
- Skipping verification layers

## Optional integration

Synk182 needs nothing else. Where other tools share the project's `docs/PULSE.json` (its companions in The Triad, DevCom5 and Solid8, or any tool that follows the same protocol), `--pulse` leaves signals for them and Synk reads theirs; with none of them, or no PULSE file, nothing waits on these signals and Synk runs at its own tiers. Protocol: [references/TRIFECTA_PROTOCOL.md](references/TRIFECTA_PROTOCOL.md).

**Emits:** `sync_completed` → DevCom5 | `sync_conflict` → DevCom5 | `environment_diverged` → DevCom5 | `new_files_synced` → Solid8
**Consumes:** `drift_detected` (DevCom5) → at least Standard | `consolidation_complete` (Solid8) → new baseline, full comparison | `stale_project` (DevCom5) → Thorough | `docs_created` (DevCom5) → include the new docs in the next comparison
**PULSE writes:** `synk_last_run`, `synk_drift_detected`, `synk_files_changed`

*Synk has no prior alias. It has always been Synk. That's the joke.*
