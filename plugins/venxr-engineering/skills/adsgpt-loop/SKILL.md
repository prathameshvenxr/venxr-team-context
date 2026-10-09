---
name: adsgpt-loop
description: Loop-driven development for the adsgpt / Venxr workspace. Runs a change as a bounded loop (frame, understand, blast radius, smallest edit, verify, decide) with a ledger, a hard stop after repeated failure, and the ponytail "laziest thing that works" ladder built in. Use for any code change, bug fix or behaviour change in the venxr_backend-* services, MCP services, skill_service, gateway, shared_components or frontend, and whenever the user says "loop", "iterate until it passes", "loop-driven", or "keep going until it's verified". Load adsgpt-engineering first for the area-specific rules and contracts.
---

# adsgpt loop

One change, run as a loop that ends on **evidence**, not on a feeling that it is done. It combines the
`adsgpt-engineering` rules (right layer, blast radius across repos, nothing silent) with the ponytail
discipline (the smallest change that works, no speculative code).

Rules of `adsgpt-engineering` always win: read-only by default, no commit/push unless asked, never edit an
applied migration, mention unrelated bugs instead of fixing them. This skill only adds the loop around them.

## 0. Frame (once, before any edit)
Write down, in four lines, and show the user:
1. **Goal** in one sentence, in the user's words.
2. **Done check**: the exact command or observable result that proves it (a test, a render, a grep that must
   be empty, a request/response). If none exists, the first task is to define one. No check, no loop.
3. **Budget**: default 3 attempts per step, 6 attempts in total. The user can change it.
4. **Repos in play**: every repo a change might touch (this workspace is many repos, many PRs, a deploy order).

## The loop
Run steps 1 to 6 in order. Step 6 decides whether to go round again.

### 1. Understand (read-only)
Open the reference for the area (see `adsgpt-engineering`), then trace the real flow in code end to end.
Say it back in 3 to 5 lines. If you cannot, you are not ready to edit. Trust code over docs: many docs are stale.

### 2. Blast radius
List every symbol, string, tool name, enum value, URL path, header or JSON key you will touch. Grep each across
**all** repos, not just the current one. Run the matching checklist in `references/contracts.md`.
Grep every caller of a function before changing it: fix the root cause once, in the shared place.

### 3. Pick the rung (ponytail ladder, stop at the first that holds)
1. Does it need to exist at all? Speculative need: skip it and say so in one line.
2. Already in this codebase? Reuse the helper, type or pattern that is there.
3. The standard library does it.
4. A native platform feature covers it (DB constraint, CSS, `<input type="date">`).
5. An already-installed dependency solves it. Never add one for what a few lines do.
6. It can be one line.
7. Only then: the minimum code that works.

No unrequested abstraction, flag, config, table, queue or node. Match the local style of the file you are in.

### 4. Edit (smallest diff, right layer)
Every changed line must trace to the request. No reformatting, no drive-by fixes, no new files unless required.
Leave a `ponytail:` comment on a deliberate shortcut with a known ceiling, naming the upgrade path.

### 5. Verify (run the done check)
Run it. Record the exact command and the actual output in the ledger. Reading code is not verification.
Where a service has no tests, write ONE focused check for the new logic or say plainly that verification was manual.
Hot files in `llm_service`: also run the nearest tests listed in `adsgpt-engineering` and the rulebook gate if
you touched create.

### 6. Decide
- **Pass** and the diff holds only requested lines: leave the loop (see Exit).
- **Fail**: classify before touching anything:
  - *Typo or slip* (the plan was right, the edit was wrong): fix it and go to step 5. Counts as an attempt.
  - *Misunderstanding* (the plan was wrong): go back to step 1 with what the failure taught you.
- **Second failure of the same idea: stop editing.** Re-read the flow, state in two lines what you misunderstood,
  then change the understanding, not the code. A third variant of the same idea is forbidden; ask the user.
- **Budget spent**: stop and report. Do not extend the budget on your own.

## Ledger (keep it visible; update every pass)
```
Goal:   <one line>
Check:  <command / observable>
Budget: <used>/<allowed>
#  step            what I did / expected                 actual result            verdict
1  understand      traced X -> Y -> Z                    n/a                      ok
2  edit+verify     <change>                              <exact output>           FAIL: <why>
3  edit+verify     <change>                              <exact output>           PASS
Unrelated issues noticed, left alone: <list or none>
```

## Exit conditions (any one ends the loop)
- **Done**: the check passes, the diff is minimal, and every line traces to the request.
- **Needs the user**: a product decision, money or security impact, an ambiguous request with two readings,
  a cross-repo rollout order, or any "should I push/merge/deploy" question. State the options and a recommendation.
- **Budget spent** or **two failures of one idea**: stop, report what is known and what is not.
- **Unrelated bug found**: write it in the ledger and keep going; never fix it in this change.

## Security gate (before you say done)
If the change touches auth, JWT or service keys, impersonation, gateway routing or headers, skill_service,
the sandbox, governance writes or risk tiers, secrets or env defaults, raw SQL, mail, or file/URL handling,
run the `adsgpt-security-reviewer` agent (or `/adsgpt-security-review`) on the diff and include its findings.
It is read-only. Do not argue findings down; either fix inside scope or list them for the user.

## Final report
Code first, then short. Per `adsgpt-engineering` "Done means":
- Files changed, per repo.
- What was verified, with the exact command and result, and what was **not** verified (say "not run" plainly).
- Rollout order across repos and any env var that must be set, per deployment (Venxr and Vajra, dev/staging/prod).
- The ledger summary and the unrelated issues left alone.

Credit: the ladder and the "laziest thing that works" stance are adapted from the ponytail skill (MIT).
