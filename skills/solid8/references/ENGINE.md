# Solid8 engine reference

What `scripts/denser_engine.py` does at each edge, read when running or checking the engine. The method and the three laws are in `SKILL.md`.

## Contents
- The same operations from Python, and the archive
- What the scan skips, groups and names
- `--json`, `--details` and the comparison cap
- `--pulse`

## The same operations from Python, and the archive

- `DenserEngine(target).scan()` → `.compare_all()` → `.generate_proposal()`; `.create_archive(files, archive_dir, reason)` copies originals with `manifest.json` and `rollback.md` before any merge or removal, and refuses (`LinkRefused`) when the archive folder, or a folder on the way to it or to an original under the target, is a junction or link, asked just before each original is read and each archive file is written; an archive folder outside the target is refused when it, or any folder above it, is one. That includes a folder under a system folder that is itself a link (on macOS, `/tmp` and `/var` are), so pass such a folder's resolved path. Before anything is made, a path that is absolute, holds `..` or lies outside the target raises `ValueError`, and a missing original `FileNotFoundError`.

## What the scan skips, groups and names

- Skips `.git`, `node_modules`, build output, caches, and every dot-prefixed folder or file; groups candidates by hash, by base name (version, copy and backup markers removed) within a folder, and by size, and pairs a version, copy or backup name with its base name in any other folder. A copy number has one to three digits, so `(2024)` is a year, not a copy. A junction or link inside the target, to a folder or a file, is named and never followed, so a loop cannot repeat files (a dangling one is named as such). A folder that cannot be listed or a file that cannot be read is named with the reason (`unreadable: N`, then each), never fingerprinted as empty; a file that becomes unreadable between the scan and the compare is named the same way, and its pairs get no tier. Each candidate file is read once per run, so a folder of hundreds of same-size files compares in seconds.

## `--json`, `--details` and the comparison cap

- A `--json` file that cannot be written (a missing folder, or a folder in its place), or an empty `--json` name, is answered with the reason and exit 1, after the report; a `--pulse` beside it still records the scan. `--details` takes a count of 0 or more. The proposal caps each cluster's comparisons at 50 (`comparisons_cap`; a near-duplicate cluster of hundreds of files would otherwise write tens of thousands), and a capped cluster says how many were left out (`comparisons_total`, `comparisons_left_out`); on the terminal, `--json` says how many were left out in all, and each cluster `--details` shows lists its first five comparisons and how many more it holds; `--pulse`'s map is capped the same way. Everything the engine writes (the proposal, the archive's files, `docs/PULSE.json`) is LF on every platform.

## `--pulse`

- `--pulse` writes `solid8_last_run` and `solid8_redundancy_map`, leaves a `redundancy_found` signal when anything is found, keeps every other key, and never touches a PULSE that does not parse or holds no JSON object, and says so; a PULSE saved with a UTF-8 BOM is read. A consumed signal (JSON `true`) older than seven days is pruned, one whose timestamp the protocol's grammar cannot read is pruned with a note, and an unconsumed one is never touched. A wrong-typed field (`"pending_signals": null`) is treated as empty with a note; when no PULSE exists one is created holding only `cross_skill`. When `docs` is a file, `docs` or `PULSE.json` is a junction or link, or the PULSE cannot be written, the scan still reports and says the PULSE was not written.
