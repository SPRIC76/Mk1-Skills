---
name: creditrun
description: >-
  Spends the month's credit, never a cent over. Use when a monthly API credit budget should go to a
  project's own work through headless Claude Code sessions, under a hard cap, with twice-weekly runs
  and a month-end sweep. Not for auditing harness cost.
metadata:
  version: "1.0.0.0"
  updated: "2026-11-13"
---

# Creditrun: use the month's credits, never a cent over

Spends the month's credit, never a cent over.

Credits that go unspent are lost. Credits that run over become real charges. This skill
fills the month with useful work on a project and stops short of the limit every time.

## Three locks, each enough on its own

1. **Auto-reload off** in the Claude Console. It is the only way the Console charges a card. Ask the
   person to confirm it once (the dashboard shows "Turn on auto-reload" when it is off).
2. **The Console's monthly spend limit**, under Spending. Only the person can set it. Set it at or
   below the credits.
3. **The script's cap** (`capUsd`, required: the script refuses to run without one), at least $10 under that limit. Each session gets
   Claude Code's own `--max-budget-usd`, never more than what is left. The worst case is booked
   before it starts, then replaced by the cost Claude Code reports, and the script stops for the
   month when the API refuses for credit. The ledger is one per machine
   (`~/.agents/credits/ledger.json`) and shared by every project, so the cap holds across them.
   Run the schedule on one machine per account, or give each machine its share as `capUsd`.

## Setting up a project

1. **Key.** Never ask for the key in chat, and never use or store one that appears there. If one is
   pasted, ask the person to delete it in the Console and make a new one. On Windows, write
   `save-key.ps1` below and have the person run it from a double-click
   (`powershell -NoProfile -ExecutionPolicy Bypass -File save-key.ps1`). Elsewhere, have them add
   `ANTHROPIC_API_KEY=` and the key as one line in `~/.agents/.env`. With the key in the environment,
   Claude Code bills the API credits, not a subscription.
2. **Jobs.** Write `credits.config.json` in the project root. Draw the jobs from the project's own
   docs, tests and tools, so each job runs real checks the project already has. Ask the person which
   kinds of work they want the credits to buy. Their words name the jobs.
3. **Files.** Write `credits.mjs` below into the project root, and add `.credits/` to `.gitignore`.
4. **Check without spending:** `node credits.mjs --dry` must print `Key present.` and a `RESULT: dry` line.
5. **Schedule.** On Windows, run `schedule.ps1` below from the project root. Elsewhere, use a daily
   cron line: `0 4 * * * cd <project> && node credits.mjs --daily >> .credits/run.log 2>&1`.

```json
{
  "capUsd": 195,
  "spreadUsd": 12,
  "runDays": ["Mon", "Thu"],
  "sweepDay": 27,
  "sweepMaxUsd": 40,
  "model": "claude-opus-5-5",
  "allowedTools": ["Bash(npm test *)", "Bash(npx vitest *)"],
  "jobs": [
    { "name": "audits", "prompt": "Audit the code against its design docs: what is designed but missing, built but contradicting the design, or built twice." },
    { "name": "diagnostics", "prompt": "Run the type check and the tests; trace every failure and slow path to its cause." }
  ]
}
```

`capUsd` has no default, because only the person knows their credits. `timeZone` is the machine's own
unless the config names one (an IANA name); it decides which day a run counts as.

## Pacing

`--daily` runs one job, in rotation, on `runDays` at `spreadUsd`. From `sweepDay` on, it runs
every day and splits what is left over the days remaining, at most `sweepMaxUsd` a job, up to the
cap. `--job <name>` runs one job now, `--usd <n>` sets its budget (never above what is left), and
`--dry` spends nothing. Sessions may only read, run the allowed tools and write under `.credits/`.
They never commit, push or edit tracked files. Their findings and proposed patches land in
`.credits/findings/` for the person or the project's agents to take up.

## Reading the month

The ledger lists every job with its project, job and dollars. The last line of every run is
`RESULT: <ran|rest|skipped|stopped|dry> <project>/<job> · this job $x · month $y of $cap · left $z`.
For a status, read the ledger and the findings, and say what the credits bought.

## Trials and sub-budgets

A trial, experiment or any spend with its own limit below the month's cap needs that limit
enforced in code on every run: pass `--usd`, or a wrapper that caps each run at the limit minus
what is already spent, minus one worst-case run of headroom, and halts when that is under a
dollar. The month's cap sits higher and will not stop it.

- **One process per ledger.** The ledger's lock covers threads inside one process only. Two
  processes writing at once overwrite each other's entries, so run their sessions one after
  another, or inside one process with workers.
- **A run with no reported cost** (a timeout, or a stop at its budget) keeps its booked worst
  case. Never settle it to $0; the real charge is unknown and may be the whole budget.
- **After every run**, check that `spentUsd` equals the sum of the entries; when it does not,
  stop and rebuild the entries from the runs' own records before spending again.

## credits.mjs

```js
// credits.mjs — spends a monthly API credit budget on a project's own jobs, never past the cap. Node 18+, no packages.
// Reads credits.config.json in the project root and writes findings to the project's .credits/ (add it to .gitignore).
// The ledger is one per machine, ~/.agents/credits/ledger.json, shared by every project, so the cap holds account-wide.
// Run: node credits.mjs [--job <name>] [--usd <n>] [--daily] [--dry]     Last line: RESULT: ...
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { basename, dirname, join } from "node:path";

const CONFIG = "credits.config.json";
const LEDGER = join(homedir(), ".agents", "credits", "ledger.json");
const PROJECT = basename(process.cwd());
const DEFAULTS = {
  spreadUsd: 12, sweepDay: 27, sweepMaxUsd: 40, runDays: ["Mon", "Thu"],
  timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone, model: "claude-opus-5-5", allowedTools: [], jobs: [],
};
const ASK = `Do not commit, push, open pull requests or edit tracked files. Write your findings to \
.credits/findings/<today>-<job>.md, worst first, each with its evidence (file:line, a command and its output, or a \
number). Put any change you propose as a unified diff in .credits/findings/<today>-<job>.patch. Say plainly what you \
could not check.`;
const BASE_TOOLS = ["Read", "Grep", "Glob", "Write(.credits/**)", "Edit(.credits/**)", "Bash(git log *)", "Bash(git diff *)", "Bash(git show *)"];

const arg = (n) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 ? process.argv[i + 1] : undefined; };
const flag = (n) => process.argv.includes(`--${n}`);

export function parts(now, timeZone) {
  const f = new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit", weekday: "short" });
  const p = Object.fromEntries(f.formatToParts(now).map((x) => [x.type, x.value]));
  const y = Number(p.year), m = Number(p.month);
  return { month: `${p.year}-${p.month}`, day: Number(p.day), days: new Date(Date.UTC(y, m, 0)).getUTCDate(), weekday: p.weekday };
}
export const left = (l, c) => (l.stopped ? 0 : Math.max(0, c.capUsd - l.spentUsd));
export function budgetFor(l, c, day, days) {
  const want = day < c.sweepDay ? c.spreadUsd : Math.min(c.sweepMaxUsd, left(l, c) / Math.max(1, days - day + 1));
  return Math.floor(Math.min(want, left(l, c)) * 100) / 100;
}
export function nextJob(l, c) {
  const names = c.jobs.map((j) => j.name);
  const mine = l.entries.filter((e) => e.project === PROJECT);
  const last = [...mine].reverse().find((e) => names.includes(e.job.replace(/ \(booked\)$/, "")));
  return names[(last ? names.indexOf(last.job.replace(/ \(booked\)$/, "")) + 1 : 0) % names.length];
}
export const isRunDay = (c, day, weekday) => day >= c.sweepDay || c.runDays.includes(weekday);

function key() {
  if (process.env.ANTHROPIC_API_KEY) return process.env.ANTHROPIC_API_KEY;
  const file = join(homedir(), ".agents", ".env");
  if (!existsSync(file)) return undefined;
  const line = readFileSync(file, "utf8").split(/\r?\n/).find((x) => x.startsWith("ANTHROPIC_API_KEY="));
  return line?.slice(18).trim().replace(/^"|"$/g, "") || undefined;
}
function load(month) {
  if (existsSync(LEDGER)) { const l = JSON.parse(readFileSync(LEDGER, "utf8")); if (l.month === month) return l; }
  return { month, spentUsd: 0, stopped: null, entries: [] };
}
function save(l) { mkdirSync(dirname(LEDGER), { recursive: true }); writeFileSync(LEDGER, JSON.stringify(l, null, 2)); }
const book = (l, e) => ({ ...l, spentUsd: l.spentUsd + e.usd, entries: [...l.entries, e] });
const unbook = (l) => ({ ...l, spentUsd: l.spentUsd - l.entries.at(-1).usd, entries: l.entries.slice(0, -1) });

function done(state, job, usd, l, c) {
  console.log(`RESULT: ${state} ${PROJECT}/${job ?? "-"} · this job $${usd.toFixed(2)} · month $${l.spentUsd.toFixed(2)} of $${c.capUsd} · left $${left(l, c).toFixed(2)}`);
  process.exit(state === "ran" || state === "dry" || state === "rest" ? 0 : 1);
}

function main() {
  if (!existsSync(CONFIG)) { console.log(`RESULT: failed no ${CONFIG} in ${process.cwd()}`); process.exit(1); }
  const c = { ...DEFAULTS, ...JSON.parse(readFileSync(CONFIG, "utf8")) };
  if (!c.jobs.length) { console.log(`RESULT: failed ${CONFIG} has no jobs`); process.exit(1); }
  if (!(typeof c.capUsd === "number" && c.capUsd > 0)) { console.log(`RESULT: failed set capUsd in ${CONFIG}, a number at least $10 under the Console's monthly spend limit`); process.exit(1); }
  const now = new Date();
  const t = parts(now, c.timeZone);
  let l = load(t.month);
  const name = arg("job") ?? nextJob(l, c);
  const job = c.jobs.find((j) => j.name === name);
  if (!job) { console.log(`RESULT: failed no job ${name}; jobs are ${c.jobs.map((j) => j.name).join(", ")}`); process.exit(1); }
  if (l.stopped) done("stopped", name, 0, l, c);
  if (flag("daily") && !isRunDay(c, t.day, t.weekday)) done("rest", name, 0, l, c);
  const usd = Math.min(Number(arg("usd") ?? budgetFor(l, c, t.day, t.days)), left(l, c));
  if (flag("dry")) { console.log(key() ? "Key present." : "Key MISSING."); done("dry", name, usd, l, c); }
  if (!(usd >= 1)) done("skipped", name, 0, l, c);
  const k = key();
  if (!k) { console.log("No ANTHROPIC_API_KEY in the environment or ~/.agents/.env."); done("skipped", name, 0, l, c); }

  // Book the worst case first: the ledger never counts less than may have been spent.
  const at = now.toISOString();
  l = book(l, { at, project: PROJECT, job: `${name} (booked)`, usd }); save(l);
  const run = spawnSync("claude", [
    "-p", `Job: ${name}. ${job.prompt}\n\n${ASK}`,
    "--model", c.model, "--max-budget-usd", usd.toFixed(2), "--output-format", "json",
    "--permission-mode", "acceptEdits",
    "--allowedTools", [...BASE_TOOLS, ...c.allowedTools].join(","),
    "--disallowedTools", "Bash(git commit *),Bash(git push *),Bash(gh *)",
  ], { env: { ...process.env, ANTHROPIC_API_KEY: k }, encoding: "utf8", shell: process.platform === "win32", maxBuffer: 64 << 20 });

  let cost;
  try { cost = JSON.parse(run.stdout).total_cost_usd; } catch { cost = undefined; }
  if (typeof cost === "number") l = book(unbook(l), { at, project: PROJECT, job: name, usd: cost });
  if (/credit balance/i.test(`${run.stdout}${run.stderr}`)) l = { ...l, stopped: `credit refused ${at}` };
  save(l);
  if (l.stopped) done("stopped", name, cost ?? usd, l, c);
  if (run.status !== 0) { console.error((run.stderr || "claude exited with an error").slice(-2000)); done("skipped", name, cost ?? usd, l, c); }
  done("ran", name, cost ?? usd, l, c);
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/").split("/").pop())) main();
```

## schedule.ps1

```powershell
# schedule.ps1 — registers a 4:00 AM task that runs `node credits.mjs --daily` in this project. -Remove takes it away.
# The script decides each morning whether to run (its runDays, and every day from sweepDay). Last line: RESULT: ...
param([switch]$Remove, [string]$At = "4:00AM")
$ErrorActionPreference = "Stop"
$Root = (Get-Location).Path
$Name = "Credit run - " + (Split-Path $Root -Leaf)
try {
  if ($Remove) { Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue; "RESULT: removed $Name"; exit 0 }
  if (-not (Test-Path (Join-Path $Root "credits.config.json"))) { throw "no credits.config.json in $Root" }
  New-Item -ItemType Directory -Force -Path (Join-Path $Root ".credits") | Out-Null
  $Run = Join-Path $Root ".credits\run.cmd"
  Set-Content -Path $Run -Encoding ASCII -Value @("@echo off", "cd /d `"$Root`"", "node credits.mjs --daily >> .credits\run.log 2>&1")
  $Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$Run`"" -WorkingDirectory $Root
  $Trigger = New-ScheduledTaskTrigger -Daily -At $At
  $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 3) -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger -Settings $Settings -Description "Spends the month's API credits on this project's jobs, under the shared cap." -Force | Out-Null
  $Env = Join-Path $env:USERPROFILE ".agents\.env"
  $Has = if ((Test-Path $Env) -and (Select-String -Path $Env -Pattern "^ANTHROPIC_API_KEY=" -Quiet)) { "key present" } else { "key MISSING" }
  "RESULT: registered $Name, daily $At ($Has)"
} catch { "RESULT: failed $($_.Exception.Message)"; exit 1 }
```

## save-key.ps1

```powershell
# save-key.ps1 — asks for an Anthropic Console API key in a hidden prompt and saves it as the one ANTHROPIC_API_KEY
# line in %USERPROFILE%\.agents\.env. Never shows, prints or sends the key. Last line: RESULT: ...
$ErrorActionPreference = "Stop"
try {
  $Secure = Read-Host "Paste your Anthropic API key (it stays hidden), then press Enter" -AsSecureString
  $Ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
  $Key = ([Runtime.InteropServices.Marshal]::PtrToStringBSTR($Ptr)).Trim()
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Ptr)
  if ($Key -notmatch '^sk-ant-api[0-9A-Za-z_-]+$') { "RESULT: refused - Console API keys start with sk-ant-api. Nothing was saved."; exit 1 }
  $Dir = Join-Path $env:USERPROFILE ".agents"; $File = Join-Path $Dir ".env"
  New-Item -ItemType Directory -Force -Path $Dir | Out-Null
  $Lines = @(); if (Test-Path $File) { $Lines = @(Get-Content $File | Where-Object { $_ -notmatch '^ANTHROPIC_API_KEY=' }) }
  Set-Content -Path $File -Encoding ASCII -Value ($Lines + "ANTHROPIC_API_KEY=$Key"); $Key = $null
  "RESULT: saved to %USERPROFILE%\.agents\.env"
} catch { "RESULT: failed $($_.Exception.Message)"; exit 1 }
```
