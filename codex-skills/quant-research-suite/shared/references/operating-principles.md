# Quant Research Suite Operating Principles

These rules apply to every project, not only the current Quant Research dashboards.

## Priority order

1. User objective, authority, safety, and explicit non-goals.
2. Project-owned analysis, data, result, automation, URL, and deployment contracts.
3. Verified current repository, runtime, and public evidence.
4. Product completeness, stability, accessibility, and maintainability.
5. Shared design and platform patterns.
6. Framework preference or implementation efficiency.

## Project isolation

- Resolve exactly one target project before mutation.
- Use a project-owned manifest and dedicated worktree.
- Never copy data, formulas, result keys, provider assumptions, colors with domain meaning, schedules, or secrets between projects.
- Shared UI and infrastructure code may provide primitives; each project owns view models, analysis parameters, chart series, table columns, and deployment targets.
- In multi-project work, keep separate baselines, branches, commits, PRs, workflow runs, previews, and public readbacks.

## Protected contracts

Unless explicitly authorized, preserve:

- Python collection, analysis, strategy, ranking, weighting, backtest, and report behavior;
- formulas, thresholds, precision, units, dates, and result semantics;
- generated data and public JSON schemas;
- input-to-result behavior, CLI/API paths, and URL contracts;
- automation schedules, provider-rights gates, last-good behavior, and failure states;
- chart series, axes, units, table columns, and meaningful interactions;
- existing public and rollback routes.

Presentation code inside mixed analysis files is editable only with same-result fixtures and a narrow diff.

## Evidence classes

Never collapse these into one status:

1. source code changed;
2. tests passed;
3. local preview works;
4. preview host is ready;
5. migration is applied;
6. API is healthy;
7. job was accepted;
8. analysis completed;
9. result persisted and bound;
10. code merged;
11. Pages or production deployed;
12. public assets and data read back.

Report the exact gate reached.

## Safety and cost

- The default authority is zero spend. Read `cost-and-authority.md` and apply its
  command preflight before every remote/provider action.
- If the user did not first request the specific paid action, do not issue a
  command, API call, browser action, schedule, or deployment that can create a
  charge. Generic build/deploy/finish requests are not paid authorization.
- Unknown plan, quota, overage, or price means cost-capable and blocked until
  verified or explicitly requested.
- Never register a payment method, enable billing, upgrade a plan, start a paid
  trial, accept paid overage, or create/use a billable resource without the
  user's prior action-specific paid request.
- Auto-renewing or free-to-paid trials, payment method registration, plan
  upgrades, paid overage or pay-as-you-go use, exceeding a verified free quota,
  paid add-ons, and Spend cap disablement are paid actions and are prohibited
  unless a direct prior user request names the exact bounded paid action;
  free-plan cost hard stops must remain enabled.
- Never expose, print, commit, upload, or copy secrets.
- Browser clients receive only publishable credentials with server-enforced access controls.
- Do not fabricate unavailable data, bypass provider rights, or turn degraded results into apparent success.
- Preserve recoverable fallbacks. Do not remove production before replacement proof.

## Data-to-public automation

- Read `data-automation.md` when collection, freshness, analysis regeneration,
  scheduling, artifacts, or publication is in scope.
- Keep source collection, validation, coherent cutoff, authoritative analysis,
  result validation, staging, publication, deployment, and public readback as
  separate evidence gates.
- A workflow file, successful fetch, successful build, or HTTP 200 is not proof
  that the public page contains the latest valid analysis.
- Preserve source rights, per-project calendars and schemas, bounded retries,
  last-good behavior, and explicit degraded/unavailable states.
- Never move a public/current pointer until the matching project, data, config,
  code, schema, and artifact identities pass validation.

## Git and worktrees

- Inspect `git status`, branch, HEAD, remotes, worktrees, and remote default branch before edits.
- Preserve unrelated or unfinished user changes.
- Start risky or reviewable work in a dedicated worktree from current remote main.
- Do not use destructive reset or checkout operations to clean user work.
- Stage explicit paths when a worktree is mixed.
- Treat prior authentication as stale until preflight proves otherwise.

## Quality

- Prefer deterministic scripts and tests over prose assurances.
- Test the repeated failure mode, not merely implementation strings.
- Re-audit after fixes.
- Keep one implementation owner per overlapping project surface.
- A reviewer or specialist returns evidence; the integration owner decides and verifies.
- Stop at an authority gate rather than guessing.

## Communication

- Lead with outcome and concrete evidence.
- Separate confirmed facts, inference, recommendation, and unavailable evidence.
- State protected behavior and any known limitation.
- Do not claim public completion without public readback.
