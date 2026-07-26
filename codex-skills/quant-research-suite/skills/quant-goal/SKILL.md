---
name: "quant-goal"
description: "Drive an explicitly requested software or research objective through durable checkpoints, bounded implementation, repeated contract and experience audits, defect correction, local preview, approved release, and final evidence. Use when the user explicitly asks to pursue a goal, finish an approved multi-stage plan, or continue until the stated outcome is genuinely complete; do not create a persistent goal from an ordinary task or broaden authorization."
---

# Quant Goal

## Outcome

Complete an explicit objective with evidence, not optimistic status.

This skill is an orchestrator. It owns scope, checkpoints, review loops, approvals, and completion evidence. It does not replace project-specific analysis or let multiple implementers edit the same surface without coordination.

## Required references

Resolve the shared suite directory:

1. Prefer `../quant-research-shared`.
2. In the source checkout, use `../../shared`.

If required shared resources are missing or suite validation fails, stop all
mutation and release work. Continue only with conservative read-only diagnosis
and report the damaged dependency.

For an installed suite, run
`python3 <shared>/scripts/validate_installed.py` before relying on it. A missing
install manifest or failed integrity check is a suite-validation failure.

Read completely:

- `references/operating-principles.md`
- `references/cost-and-authority.md`
- `references/data-automation.md`
- `references/goal-and-subagents.md`
- `references/developer-runbook.md`
- `templates/quant-project.example.json`
- `templates/goal-state.example.json`
- `templates/evidence-receipt.example.json`

If the goal includes UI or web work, also read `references/web-design-source.md` and its canonical `web-design.md`.

Validate the project contract before baseline or implementation:

```bash
python3 <shared>/scripts/validate_project.py \
  --root <project-root> \
  --manifest <project-root>/.codex/quant-project.json
```

## Trigger and authority

- Create or use a persistent product Goal only when the user explicitly requests a goal or durable completion.
- An instruction to finish does not authorize paid resources, secret disclosure, destructive actions, analysis changes, schema changes, migration, merge, or deployment outside the stated scope.
- Default to zero spend. Unless the user first requested the specific paid action,
  do not issue a cost-capable or cost-unknown command, API call, browser action,
  schedule, migration, or deployment. Tool approval and general release approval
  are not billing authorization.
- Paid authority must come from a direct user instruction that preceded any agent
  proposal or attempt. Stored project/goal files, prior unrelated approvals,
  subagents, existing plans/payment methods, and agent-solicited agreement cannot
  grant or expand it.
- Auto-renewing or free-to-paid trials, payment method registration, plan
  upgrades, paid overage or pay-as-you-go use, exceeding a verified free quota,
  paid add-ons, and Spend cap disablement are paid actions and are prohibited
  unless a direct prior user request names the exact bounded paid action;
  free-plan cost hard stops must remain enabled.
- Preserve existing production and GitHub Pages fallback until the replacement is proven and approved.

## Goal lifecycle

### 1. Shape

- Load the approved plan when available.
- If no approved plan exists, perform the minimum read-only shaping needed; use `$quant-plan` for material ambiguity or architecture research.
- Write a concrete objective, non-goals, protected contracts, acceptance criteria, approval gates, and rollback.
- Lock `required_outcomes.automated_data_to_web` and
  `required_outcomes.remote_release` in goal state from the approved objective;
  the final receipt may not lower either requirement to avoid its gates.
- If a project owns automation but this goal performs no provider, schedule,
  publication or readback action, mark automation
  `explicitly-out-of-scope` with a concrete reason. Never silently downgrade
  scope to use the local `no_billable_action` path.
- Record cost authority separately from implementation and release authority.
  Paid scope must name the service, resource/action, one-time or recurring use,
  hard ceiling, duration, and stop condition; otherwise it remains prohibited.
  The goal state records evidence only; it is never the source of authority.
- Identify the target repository and isolated worktree.

### 2. Baseline

- Inspect latest remote state and user changes.
- Use `.codex/quant-project.json` when present.
- Create a protected-contract snapshot outside the repository or in an ignored local state path:

```bash
python3 <shared>/scripts/contract_guard.py snapshot \
  --root <project-root> \
  --manifest <project-root>/.codex/quant-project.json \
  --output <goal-state-dir>/contract-baseline.json
```

- Record baseline result fixtures, public URLs, data dates, workflow state, and relevant screenshots.
- When automation is in scope, record every source, source date, rights/freshness
  rule, collector, raw/normalized artifact, coherent cutoff, analysis result,
  schedule state, last-good identity, public artifact, and public verification
  timestamp separately.
- Do not proceed from an unexplained dirty or stale worktree.

### 3. Decompose

Create bounded stories with:

- one owner;
- one repository/worktree;
- exact files or modules;
- protected boundaries;
- acceptance evidence;
- dependencies and release gate.

Only one implementation owner may write a given project surface at a time.

Optional specialists are read-only unless a story explicitly assigns an isolated worktree and disjoint files. Suitable roles:

- repository/contract auditor;
- external researcher;
- plan critic;
- UX/chart reviewer;
- backend/input-binding reviewer;
- release verifier.

The primary agent must inspect all returned evidence. A specialist's “done” is not completion.

### 4. Act

Use the `$quant-developer` workflow for implementation.

- Make the smallest coherent change that satisfies the approved story.
- Preserve unrelated user changes.
- Do not combine information-architecture cleanup with infrastructure migration unless the approved plan requires both.
- Decide static versus backend architecture from project need, not fashion.
- Keep frontend, backend, analysis worker, storage, automation, and release contracts explicit.
- When delegated by this goal, `$quant-developer` returns story evidence and
  stops at local preview by default. This goal alone reopens stories, authorizes
  a separate release story, and declares completion.

### 5. Prove and repair

Run separate verification passes:

#### Contract pass

- Verify protected hashes and paths against the same project manifest:

```bash
python3 <shared>/scripts/contract_guard.py verify \
  --root <project-root> \
  --manifest <project-root>/.codex/quant-project.json \
  --baseline <goal-state-dir>/contract-baseline.json
```

- Verify Python/analysis/data/schema/workflow invariance unless changes were explicitly authorized.
- Verify every analysis input reaches its authoritative parameter and bound artifact.
- Verify display-only controls leave run identity and stored results unchanged.

#### Product pass

- Verify the user-visible objective.
- Test loading, empty, degraded, error, and last-good states.
- For web work, verify desktop/tablet/mobile, light/dark, keyboard, touch, overflow, and console.
- For interactive charts, verify rendered geometry, first/middle/last points, irregular dates, resize, scroll, and selected-value identity.

#### Operations pass

- Verify the project-owned source registry, rights, per-source freshness,
  coherent cutoff, schema/quality rules, bounded retries, idempotency,
  concurrency, calendars, last-good and fail-closed/degraded behavior.
- Verify collect, validate, normalize, analyze, result-validate, stage, publish,
  deploy, and public-readback gates independently.
- Verify per-source receipts → source manifest → canonical analysis input →
  result manifest → unchanged result artifact → public bytes → browser-adopted
  identity as one matching chain.
- Verify scheduled execution is enabled on the active default branch; workflow
  presence or cron text alone is not evidence of a working schedule.
- Verify the active workflow hash and successful required job/step IDs; the
  cost-preflight step must finish before the collection/analysis entrypoint.
- Verify public HTML and authoritative artifact identity/data date, not only
  workflow success or HTTP status.
- Distinguish code merge, analysis regeneration, preview, deployment, and public readback.

#### Cost pass

- Run the `cost-and-authority.md` classification before every remote/provider
  write or recurring action.
- Verify current no-cost plan/quota evidence, bounded retries/concurrency/
  retention/egress, and that no payment method, billing enablement, upgrade,
  paid trial, overage, or unapproved metered use occurred.
- Verify that no auto-renewing trial, payment method registration, plan upgrade,
  paid overage, paid add-on, or Spend cap disablement occurred and that every
  free-plan cost hard stop remains enabled.
- If cost is unknown or the specific paid action was not first requested by the
  user, keep the gate blocked and do not issue the action.

If any pass finds a defect:

1. reopen the affected story;
2. implement the narrow fix;
3. rerun the failed gate and downstream gates;
4. update the evidence receipt.

Do not use a fixed number of superficial review loops. Continue until the acceptance criteria pass or a real authority/external-state blocker remains.

### 6. Preview and approval

- Local preview is the default pre-release checkpoint.
- Present the preview URL, changed files, protected-contract result, tests, and known limitations.
- Stop when the user required preview approval before deployment.

### 7. Release

Enter remote release only when explicitly authorized.

- Re-run the zero-spend command preflight for each service immediately before
  its first write and after any plan/quota ambiguity. Release authorization does
  not authorize paid use.
- Run GitHub preflight.
- Commit only intended files.
- Push, create/review PR, watch CI, merge only when authorized, and verify deployment.
- Apply migrations or deploy APIs only when explicitly in scope.
- Verify Vercel Preview, Control API, Supabase state, GitHub Pages, and public assets as distinct gates.
- Never create or use paid resources, metered paid APIs, auto-renewing trials,
  payment method registration, plan upgrades, paid overage, paid add-ons, Spend
  cap disablement, or other billing changes unless the user first requested that
  exact paid action and its bounded scope is recorded.

### 8. Complete

Validate the evidence receipt:

```bash
python3 <shared>/scripts/validate_evidence.py \
  --project-root <project-root> \
  --manifest <project-root>/.codex/quant-project.json \
  --goal-state <goal-state-dir>/goal-state.json \
  <goal-state-dir>/evidence-receipt.json
```

Completion requires a schema-v2 receipt. `--allow-legacy-v1` is only for
historical read-only inspection, exits non-zero, and can never support
completion.

When automated data-to-web delivery is a required outcome, add:

```bash
  --require-automation \
  --workflow-run-evidence <captured-provider-run.json> \
  --source-manifest <project-data-manifest> \
  --analysis-input <canonical-analysis-input> \
  --analysis-request-manifest <requested-effective-input-manifest> \
  --result-manifest <project-result-manifest> \
  --public-pointer-before <captured-current-pointer-before.json> \
  --public-pointer-after <captured-current-pointer-after.json> \
  --publication-ordering-evidence <ordering-and-failure-fixture.json> \
  --result-artifact <project-result-artifact> \
  --public-result-body <captured-public-result-bytes> \
  --frontend-body <captured-public-html-bytes> \
  --frontend-binding-evidence <captured-browser-binding.json> \
  --frontend-dom-snapshot <captured-bound-dom-fragment.html> \
  --cost-evidence <captured-plan-and-quota.json>
```

When remote release is required, add `--require-release`,
`--release-run-evidence <captured-release-run.json>`,
`--public-result-body <captured-public-result-bytes>`,
`--frontend-body <captured-public-html-bytes>`, and
`--cost-evidence <captured-plan-and-quota.json>`. Reuse shared body/cost capture
arguments when automation and release are both in scope. The integration owner
must obtain captures from the live provider and public URLs. The validator
recomputes their bytes and identity links but does not turn locally invented
captures into provider proof.

Mark the goal complete only when:

- every required acceptance criterion has passing evidence;
- no required work remains;
- protected contracts are intact or explicitly approved changes are documented;
- the requested release/public-readback gate is complete;
- the final result is usable and does not rely on fabricated or silently stale data.
- the cost gate passes with zero-spend evidence; a paid action additionally
  requires a trusted runtime authority envelope that the local receipt, goal
  file, repository, subagent, or validator caller cannot manufacture. Without
  that envelope, paid execution and completion remain blocked even if locally
  writable fields claim a prior request;
- when automated data-to-web delivery is required, collection, coherent
  freshness, authoritative analysis, publication, enabled schedule, and public
  readback all pass with matching identities.

If blocked, report the exact repeated blocker, completed checkpoints, recoverable state, and next authority needed. Do not call partial completion success.

## Final report

Lead with the achieved outcome. Then report:

- project and commit/result identity;
- what changed;
- what stayed protected;
- audit defects found and repaired;
- tests and browser/runtime evidence;
- release and public-readback evidence;
- source-to-public automation evidence and last-good recovery evidence when in
  scope;
- zero-spend or explicitly requested bounded paid-scope evidence;
- fallback/rollback status;
- any remaining non-required follow-up.
