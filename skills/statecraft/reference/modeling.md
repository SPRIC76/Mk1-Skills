`Version 1.0.0 | Parent: statecraft 1.0.0 | Path: statecraft/reference | Filename: modeling.md | Created: 2026-10-21 03:36 ET`

# Modeling the risky part

## Contents
- Choosing the tool
- Writing the model
- The model folder
- Reading a counterexample
- Pitfalls that cost a run (each one happened)

## Choosing the tool

| The question | Default | Why |
|---|---|---|
| Can two things happening at once, retries, timeouts or expiry break a rule? (locks, leases, queues, sync, multi-step writes, multi-agent handoffs, notification and checkout flows) | **TLA+ with TLC** | Explores every interleaving of the steps you model, within the bounds you set. `scripts/check.py` runs it |
| Can this Rust code panic, overflow or hit undefined behavior on any input? | **Kani** (`cargo kani`) | Checks the real code with no second language. Write `#[kani::proof]` harnesses beside the code |
| The same for C | **CBMC** | The same idea for C |
| The model would cost more than the risk | **Property-based tests** (Hypothesis, fast-check) | Random inputs against a stated law. Weaker than a model check, but cheap |

Say which one you chose and why in one line of the handoff. Only `check.py` (TLA+) is
scripted here. For Kani or CBMC, keep the same loop: show it red on the shipped code, then
green on the fix, and state the bound (Kani's `#[kani::unwind]`).

## Writing the model

1. **Read the code first,** at one commit. Each shared thing it reads or writes becomes a
   variable: a file, a row, a flag, a remote ref.
2. **One action per step that touches shared state.** Where the code reads and then writes
   in two statements, make that two actions. That gap is where races live. Head each action
   with a comment naming the function and the line it stands for.
3. **Time is ticks.** An expiry or timeout is a constant number of ticks, and a `Tick`
   action moves the clock. Keep the bound small, around 2 to 4 ticks.
4. **Laws are invariants.** Write each one in plain words as a comment, then as a formula.
   One law per name, so a counterexample names exactly one rule.
5. **The shipped code is the first variant.** Put the fix behind a constant (`Safe`,
   `AtomicClaim`) so one spec models both, and each `.cfg` picks one.
6. **Bound everything that can grow.** A counter, a log or a sequence with no cap makes the
   search endless. Guard the action (`Len(log) < MaxLog`) and say so in a comment.

## The model folder

```
<model-folder>/
  Spec.tla          the model; every action cites the code it stands for
  MC.tla            optional: concrete sets and functions a .cfg cannot spell
  statechart.md     the picture, with findings marked
  <law>.cfg         one check per law against the shipped code ("expect: broken" or "holds")
  Fixed_<law>.cfg   the same law against the fix ("expect: holds")
```

Each `.cfg` opens with its header, which `scripts/check.py` reads:

```
\* expect: broken
\* spec: MC.tla
\* why: two sessions claim in the same second (cmd_claim writes two files)
```

Run all of it with `python scripts/check.py <model-folder>`. The run copies the folder to a
temporary place, so nothing is written beside your code.

## Reading a counterexample

TLC prints the shortest path it found to a broken state: every step's action, then every
variable after it. Turn that into plain steps for the person ("A starts to claim. A second
later, B claims. Both are told they hold the lock."). Then:

1. Paint it red on the statechart.
2. **Drive it against the real code.** Write a short script that forces that order: pause
   one actor between the two writes the model split, run the other, then read back what the
   real code reports. A reproduced counterexample is the strongest evidence this skill can
   hand over. A counterexample that is not reproduced may be the model's mistake. Say which
   it is.

## Pitfalls that cost a run (each one happened)

- **An unbounded log** (`main` growing on every landing) made a 3-actor model run past
  10 minutes. Capping it at 2 finished in 9 seconds with 733,058 states.
- **A law that counts idle actors** reported a "second writer" that had never claimed
  anything. Count only the actors that believe they hold the thing.
- **A law scoped wider than the resource** reported a release on one machine as stealing
  another machine's separate lock. Scope each law to the resource it protects.
- **Equal timestamps hide a race.** Two writes in the same second can look consistent. Give
  the model a `Tick` between steps, or it will not find the second-boundary case.
