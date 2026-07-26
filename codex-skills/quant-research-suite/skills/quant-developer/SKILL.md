---
name: "quant-developer"
description: "Implement a project end to end with one integration owner across frontend, backend/control plane, data and input-result adapters, automation, tests, local preview, and an explicitly approved GitHub/cloud release. Use for building or changing software and websites while preserving project-owned analysis and data contracts; choose only the technology the project needs and keep remote release gated."
---

# Quant Developer

## Outcome

Deliver a coherent implementation whose UI, backend, authoritative computation, automation, and deployed artifact agree.

One integration owner is responsible for the final implementation. Optional specialists may research or audit, but must not create conflicting edits or independently release the project.

When invoked by `$quant-goal`, this skill owns one bounded story and returns
implementation/verification evidence. It does not alter the parent scope, grant
approval, or declare the parent goal complete; its default stop is local preview
unless the goal assigned a separately authorized release story.

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
- `references/developer-runbook.md`
- `references/goal-and-subagents.md`
- `templates/quant-project.example.json`
- `templates/evidence-receipt.example.json`

For any web, UI, chart, table, or frontend task, also read:

- `references/web-design-source.md`
- the canonical `web-design.md` resolved there.

## Default boundary

- Implement and verify through local preview by default.
- Commit, push, PR, merge, migration, cloud deploy, Pages deploy, or public data publication requires explicit user authorization.
- A design request does not authorize Python analysis, formulas, data meaning, schema, schedule, or provider changes.
- A backend request does not authorize reimplementing existing Python analytics in TypeScript, Vercel, FastAPI, or SQL.
- A release request does not authorize unrelated changes, secrets exposure, destructive cleanup, or paid resources.
- The cost default is zero spend. If the user did not first request the specific
  paid action, do not issue any cost-capable or cost-unknown command, API call,
  browser action, deployment, migration, scheduled job, metered data request, or
  billing change. General build/release approval and tool approval are not
  billing authorization.
- The request must be a direct user instruction that preceded any agent proposal
  or attempt. Stored manifests, goal state, prior unrelated approvals, subagents,
  existing payment methods, trials/credits, and agent-solicited agreement do not
  grant or expand paid authority.
- Auto-renewing or free-to-paid trials, payment method registration, plan
  upgrades, paid overage or pay-as-you-go use, exceeding a verified free quota,
  paid add-ons, and Spend cap disablement are paid actions and are prohibited
  unless a direct prior user request names the exact bounded paid action;
  free-plan cost hard stops must remain enabled.

## Workflow

### 1. Preflight

- Confirm the exact repository, worktree, branch, remote, and base commit.
- Fetch current remote state when release correctness depends on it.
- Preserve dirty or stale worktrees; create a fresh task worktree from current remote main when needed.
- Read project instructions and `.codex/quant-project.json`.
- Validate the project contract before taking its paths, source registry,
  schedules, cost policy, or release targets as authoritative:

```bash
python3 <shared>/scripts/validate_project.py \
  --root <project-root> \
  --manifest <project-root>/.codex/quant-project.json
```

- Run the inventory tool and relevant existing tests.
- Establish protected paths and baseline fixtures before edits.
- Inventory data sources, rights, source dates, collectors, raw/normalized
  artifacts, schemas, calendars, schedules, latest successful run, last-good
  result, publication path, and public readback when automation exists.
- Classify all planned remote/provider commands under
  `cost-and-authority.md`; unknown cost remains blocked.

Do not mix project data, analysis semantics, UI-specific state, or deployment configuration across repositories.

### 2. Classify the change

Choose the minimal required lanes:

- frontend/presentation;
- input-result adapter;
- backend/control plane;
- authoritative analysis worker;
- data collection/freshness;
- automation;
- release.

Do not activate unused lanes.

### 3. Protect the input-result contract

Classify every user-facing control:

- `display`: presentation only;
- `result_selector`: selects an existing authoritative result;
- `analysis`: changes computation and must create a new result identity;
- `operation`: triggers refresh, export, or another side effect.

For each analysis control, prove:

```text
frontend field
→ validation
→ canonical serialization
→ API/workflow/CLI
→ existing authoritative parameter
→ requested/effective config
→ run/result identity
→ artifact hash
→ bound UI result
```

Maintain distinct `draft`, `applied`, `pending`, and `bound` state. Never show draft values as applied results.

Use deterministic A/B fixtures:

- same input twice produces the same core result;
- each analysis input changes its responsible result path when the fixture makes the effect observable;
- display-only changes preserve config hash, run identity, command, and result artifact;
- invalid, stale, failed, or mismatched results fail closed.

### 4. Frontend implementation

- Preserve the project's purpose, result structure, charts, tables, units, date semantics, and useful interaction.
- Apply the canonical web-design contract as shared grammar, not a cloned page.
- Use TypeScript/React/Vite and shadcn/ui only when they improve maintainability or safety.
- Keep a static adapter when stored JSON and Pages are sufficient.
- Minimize visible supporting copy; keep required accessibility text in the accessibility channel.
- Keep detailed analysis inputs collapsed by default when they crowd primary results, while showing applied-value summaries.
- Ensure shared navigation, theme, typography, semantic color roles, spacing, states, tables, charts, and responsive behavior are consistent.

For charts:

- keep exact values outside the plot;
- use the same domain, scale, range, and plot bounds for rendering and hit-testing;
- use CTM-aware SVG coordinate conversion;
- separate preview from pinned selection;
- verify first/middle/last, irregular dates, direct tap, resize, scroll, zoom, and keyboard.

### 5. Backend and platform implementation

Use a backend only when the product needs server-side validation, orchestration, authorization, persistence, or long-running execution.

Preferred conditional split:

- frontend: display, input, polling, result binding;
- FastAPI: schema validation, authorization, idempotency, orchestration, run state;
- Supabase/PostgreSQL: run metadata, result identity, duplicate recovery, RLS-protected storage;
- GitHub Actions or another approved worker: existing Python collection/analysis execution;
- versioned artifacts: result JSON plus requested/effective inputs, data date, code version, schema version, SHA-256;
- Vercel: frontend preview when useful;
- GitHub Pages/existing production: public fallback until replacement is proven.

Requirements:

- browser receives no service-role, GitHub, provider, or database secrets;
- public and private Supabase access is enforced with RLS;
- requests are idempotent and retries do not create conflicting authoritative results;
- health/readiness do not claim job/result success;
- callbacks and result manifests validate project, run, config, code, schema, data date, and artifact identity;
- long jobs expose queued/running/succeeded/failed/stale states;
- failed replacements leave last-good public results intact.

### 6. Data collection and automation

- Preserve provider rights, schedules, calendars, cached history, source
  revisions, and fail-closed/degraded behavior.
- Keep a project-owned non-secret source registry. For each source record its
  role, collector, rights, timezone/calendar, release lag, schema, raw and
  normalized artifacts, provenance/hash, freshness, retry/cache, and
  missing/stale/fallback policy.
- Do not mix source registries, data semantics, credentials, calendars, or
  fallback policies across projects.
- Implement and prove the authoritative chain:

```text
per-source collection
→ rights/schema/quality validation
→ canonical normalization
→ coherent latest cutoff
→ existing Python/worker analysis
→ result and artifact validation
→ versioned candidate staging
→ public/current publication
→ frontend deployment if needed
→ public HTML and data/result readback
```

- Bind the analysis result to source/data manifest, requested/effective config,
  code, schema, run/result, data date, and artifact SHA-256 identities.
- When the existing result JSON is protected, add project-local sidecars instead
  of changing it: a source manifest bound to per-source receipts and canonical
  analysis-input bytes, a result manifest bound to the unchanged artifact, and
  a browser capture proving the frontend adopted that exact identity.
- Bind identity fields already present in result JSON with project-owned JSON
  pointers. Expose the adopted identity in a non-visual
  `data-quant-result-binding` DOM marker for browser verification; this must not
  alter analysis or visible product copy.
- Separate collection success, coherent data freshness, analysis completion,
  result validation, repository publication, frontend/Pages deployment, and
  public readback. No one gate proves another.
- Verify schedules on the active default branch with explicit cron timezone,
  provider/market calendar, availability lag, idempotency, concurrency, timeout,
  bounded retries, manual backfill mode, retention, zero-spend bounds, and
  last-good recovery.
- Require the active workflow hash plus a successful named job and unconditional,
  fail-closed cost-preflight and collection/analysis step IDs. Cost preflight
  must complete before the remote or provider-affecting entrypoint starts.
- Required-source failure, rights/schema failure, analysis failure, publish
  failure, or readback mismatch must not advance the public/current pointer.
- Publish with an atomic identity/generation check so an older run that finishes
  late cannot overwrite a newer valid current result.
- Capture public pointers before/after publication and run deterministic
  older-run and failed-candidate tests that prove last-good preservation.
- Optional-source failure may publish only under an existing explicit degraded
  contract.
- Do not infer freshness from a rendering UI, HTTP 200, workflow file, successful
  fetch, or successful build.
- Never fabricate unavailable data, silently carry stale values into a new
  result, or replace a valid historical value with `0`/empty/unrelated fallback.

### 7. Verification

Run proportionate checks:

- existing Python/unit/integration/regression tests;
- frontend type, lint, unit, DOM, accessibility, and build tests;
- deterministic input sensitivity and binding tests;
- schema and generated-artifact validation;
- per-source success/failure, stale/malformed/revision, coherent-cutoff,
  schedule idempotency/concurrency, last-good, staged/published identity, and
  public-readback tests, including older-run-after-newer-run ordering, when data
  automation is in scope;
- desktop/tablet/mobile, light/dark, keyboard/touch, overflow, and console QA;
- local API E2E when a backend is involved;
- contract-guard verification.

If a test is missing for a repeated failure mode, add a deterministic regression test.

### 8. Local preview

Provide:

- preview URL;
- exact changed files;
- implementation summary;
- protected-contract result;
- input/result and chart evidence;
- tests and visual QA;
- limitations or unavailable states.

Stop before release when preview approval is required.

### 9. GitHub and cloud release

Only after explicit authorization:

1. Run:

```bash
bash <shared>/scripts/github_preflight.sh \
  <project-root> <approved-owner/repository> <approved-account> true
```

2. Inspect `git status` and full intended diff.
3. Stage only scoped files.
4. Commit intentionally and push the task branch.
5. Create or update a PR; prefer connected GitHub tooling for PR metadata/actions and use `gh` where needed.
6. Watch CI to terminal success.
7. Merge only when authorized.
8. Apply approved migrations and deploy approved backend/frontend resources.
9. Verify Vercel Preview, API readiness, Supabase persistence, worker completion, Pages deployment, and public assets separately.
10. Read back public HTML/CSS/JS and authoritative JSON/result identity.

Before steps 4–10 and before any provider/data-source write:

- name the service/resource/action and recurring behavior;
- verify the no-cost plan/quota and bounded retry/concurrency/retention evidence;
- verify that no auto-renewing trial, payment method registration, plan upgrade,
  paid overage, paid add-on, or Spend cap disablement is part of the action and
  that free-plan hard stops remain enabled;
- if cost is unknown or the user did not first request the exact paid action,
  stop before issuing it;
- never trigger a cost-capable command merely to obtain an approval dialog.

GitHub authentication:

- verify the active account and repository access immediately before remote mutation;
- never print or persist tokens;
- do not auto-logout, replace credentials, or loop on invalid auth;
- store only non-secret checkpoint data: repository, branch, commit, PR, workflow run, deployment, and last completed gate;
- after user-mediated reauthentication, resume from the last proven checkpoint.

### 10. Handoff

Lead with the outcome, then report:

- frontend, backend, automation, and release changes separately;
- per-source collection, coherent freshness, analysis artifact, scheduled
  execution, publication, and public-readback evidence when in scope;
- cost classification and confirmation that no unrequested paid action occurred;
- project-specific behavior preserved;
- protected-contract evidence;
- input-result binding evidence;
- tests and browser/runtime evidence;
- exact release/public state;
- fallback and rollback.

Never say “deployed” from a local preview, Vercel ready state, API health check, HTTP 202, PR merge, or Pages run start alone.
