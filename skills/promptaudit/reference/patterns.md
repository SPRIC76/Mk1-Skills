# Patterns and keep list

Derived from Anthropic's published prompt-audit guidance for current Claude models (read 2026-11-09, claude-api skill, `prompt-audit.md`, and the Claude Code memory page). Rewritten here as a portable checklist; for another vendor's model, swap the "native feature" column for that model's.

## Dated text

| Pattern | Why it no longer fits | Fix |
|---|---|---|
| Capitalised pressure: CRITICAL, MUST, NEVER many times in one file | Older models under-triggered; current ones over-apply, and when everything is critical nothing is | State the one or two real constraints plainly, with the reason |
| Hedges on real requirements: "try to", "if possible" | Read literally as permission to under-deliver | Say what is required |
| Trait claims: "you tend to be verbose" | Describes an older model | State the wanted behaviour |
| "Be thorough", "do not be lazy", "do not stop early" | Current models are proactive by default | Delete |
| "Think step by step", scratchpad or thinking tags, "think harder/less" | Native thinking and an effort setting replace them; a "do not think" rule cannot be followed where thinking is always on | Delete; use the effort control |
| "Plan before acting", "use the think tool to plan" | Causes over-planning on models that plan unprompted | Delete; lower effort if still too aggressive |
| Progress cadences ("every 3 tool calls"), word or bullet caps | Written for chattier models; caps starve reasoning | Qualitative length guidance, or delete |
| "Don't narrate", "hold all findings for the end" | Current models under-narrate when these are present | Remove, re-test, then add a line saying when text is wanted |
| Anti-formatting bans written against over-formatting models | Strip formatting the reader may want | Say when formatting helps |
| Assistant-turn prefill, "output ONLY valid JSON" stacks, forced tool choice | Rejected or superseded by structured outputs on current models | Use the structured-output feature |
| Retired model names, removed request parameters, stale beta headers | Error or silently ignored | Remove, with the retry code around them |
| Migration-relative phrasing: "now works differently" | A diff against a prompt the model never saw | Write the current rule as the only rule |
| Grader vocabulary: "you will be graded on" | Describes the scoring, not the requirement | State every requirement; never the grader |

## Over-specification

Step-by-step scripts for judgment work (keep numbered steps only where order is safety-critical); runs of prohibitions with no stated reason; a single gold example the model will copy in length and tone; bullet walls where prose carrying the reason would do; duplicated rules stated in two places; strategy coaching beside task rules; one session's stumble written as a permanent rule.

## Files that disagree or rot

Two instruction files ruling differently on the same point (a narrower file that explains its own scope, or names what it overrides, is an override, not a conflict; keep it). Named paths, commands or flags that no longer exist (check by reading, never by running). Hard-coded versions, dates, incident ids and history narrated in the file. Rules nothing enforces that could be a permission rule, hook or validator: a behavioural request is weaker than a check. Skill descriptions that only ever grow, one phrase per missed trigger.

## Whole-surface fit

What no single line shows. Copies that drifted from their master and now disagree (the model may pick either); everything loaded before the first word, imports included, against the platform's own size guidance; the per-turn listing cost of skills, connectors and plugins, and which of them no recent session used; hard stops written only as prose (CLAUDE.md-style files are context, not enforcement: put what must hold into permissions, hooks or code); a missed scheduled run that reads as a quiet day (add a status check for work waiting too long); a prompt baked into a scheduler's settings (move it to a file the repository owns); retired model ids and price tables inside tools. Keep-list reminder: a duplicate that agrees and causes no errors is not cruft.

## Tool descriptions

Judge on precision, not brevity. Under-described (vague one-liners, undocumented parameters, no when-not-to-use) gets more text. Over-steered (shouting, worked dialogue, "ALWAYS use X, NEVER Y", follow-up instructions smuggled into a description) gets moved or dialled back. Routing text in a skill's description may carry calibrated urgency; behaviour text should explain.

## Keep list

Audience, product, environment and quality bar; the reasons behind constraints. Exact scripts for destructive or auth steps. Tool parameter semantics, limits and failure modes. Prohibitions guarding a failure that still reproduces. Format-pinning examples for format-sensitive output. Working redundancy that does not disagree. A one-line role statement. A single closing recap of the key constraints. Text that adds guidance for the new model's own quirks: fit runs in both directions.
