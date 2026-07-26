---
name: "quant-plan"
description: "Plan or audit a software, data, research, or web project before mutation by clarifying the real objective, inspecting the current repository and runtime, researching primary sources, protecting existing contracts, comparing viable approaches, and producing an evidence-backed implementation plan. Use for planning, research, architecture decisions, audit-only requests, migrations, or new-project shaping; do not use it to implement, commit, deploy, or mutate external systems."
---

# Quant Plan

## Outcome

Turn an objective into an approved, executable plan grounded in:

1. the user's actual purpose and priorities;
2. the current repository, runtime, public state, and data contracts;
3. relevant primary-source research;
4. explicit non-goals, risks, acceptance criteria, and release gates.

This skill is read-only by default. A plan is not implementation authorization.

## Required references

Resolve the shared suite directory before working:

1. Prefer `../quant-research-shared` beside the installed skill.
2. In the source checkout, use `../../shared`.
3. If neither exists, state that the shared suite resources are unavailable and continue with a conservative read-only audit.

For an installed suite, run
`python3 <shared>/scripts/validate_installed.py` before relying on it. If the
install manifest is missing or validation fails, stop mutation and remote work;
continue only with conservative read-only diagnosis.

Read these files completely:

- `references/operating-principles.md`
- `references/cost-and-authority.md`
- `references/data-automation.md`
- `references/research-and-planning.md`
- `references/goal-and-subagents.md`
- `templates/quant-project.example.json`
- `templates/approved-plan.example.md`

When UI, dashboard, chart, table, copy, or web architecture is in scope, also read:

- `references/web-design-source.md`
- the canonical `web-design.md` resolved by that reference.

## Modes

Choose exactly one mode from the user's request.

### Audit only

Use when the user asks to inspect, diagnose, compare, or review without asking for changes.

- Do not edit files.
- Do not create branches, commits, PRs, deployments, migrations, credentials, or paid resources.
- Read local source, tests, workflows, generated artifacts, and public state when relevant.
- Report confirmed evidence separately from inference and recommendation.

### Plan

Use when the user asks for a plan, architecture, migration sequence, or implementation proposal.

- Perform the audit first.
- Research only what could materially change the decision.
- Produce an approved-plan-shaped response. Write a planning file only when the
  user explicitly requested that local artifact.
- Stop before mutation unless the user separately authorizes implementation.

### New project

Use when the repository is new or absent.

- Clarify the product result, users, inputs, outputs, data rights, automation, and deployment constraints.
- Reuse general patterns, not project-specific data or formulas.
- Propose a project-owned `.codex/quant-project.json`.
- Do not force React, FastAPI, Supabase, Vercel, or any other stack without a demonstrated need.

## Workflow

### 1. Establish scope

- Identify the target repository or project.
- Restate the objective in outcome language.
- Record explicit priorities, protected behavior, non-goals, release boundary, cost boundary, and time constraints.
- Default the cost boundary to zero spend. A paid action may appear in the plan
  only when a direct user instruction requested that specific paid action before
  any agent proposal; otherwise mark cost-capable commands prohibited and offer
  a no-cost alternative. Do not plan an agent-initiated upgrade or paid fallback.
- Auto-renewing or free-to-paid trials, payment method registration, plan
  upgrades, paid overage or pay-as-you-go use, exceeding a verified free quota,
  paid add-ons, and Spend cap disablement are paid actions and are prohibited
  unless a direct prior user request names the exact bounded paid action;
  free-plan cost hard stops must remain enabled.
- Do not propose a prohibited paid action as a solution.
- Ask only questions whose answers would materially change the plan and cannot be discovered safely.

### 2. Inspect current state

Prefer the shared inventory tool:

```bash
python3 <shared>/scripts/project_inventory.py --root <project-root>
```

Verify at minimum:

- repository root, remote, branch, HEAD, worktrees, dirty files, and divergence;
- purpose and current public URL;
- source, frontend, backend, Python, data, JSON, schema, test, workflow, and deployment paths;
- generated-data freshness fields and publication path;
- data-source registry, provider rights, per-source dates, coherent cutoff,
  collection/validation/analysis artifacts, schedules, retries, concurrency,
  last-good behavior, and public readback;
- visible controls and their actual input-to-result path;
- chart/table contracts and responsive/accessibility expectations;
- current local, preview, API, CI, Pages, and public state as separate facts.

Do not start from a stale or detached worktree merely because it is convenient.

### 3. Establish the project contract

If `.codex/quant-project.json` exists, validate and use it.

```bash
python3 <shared>/scripts/validate_project.py \
  --root <project-root> \
  --manifest <project-root>/.codex/quant-project.json
```

If it does not exist:

- derive a proposed manifest from the example;
- keep it in the plan or a temporary artifact unless the user asked to create files;
- never include secrets, tokens, private data, or volatile run identifiers.

The contract must isolate this project's:

- purpose and result semantics;
- protected analysis, data, schema, workflow, and public paths;
- source registry, coherent-cutoff rule, raw/normalized artifacts, data manifest,
  failure/degraded policy, and source-to-public pipeline;
- source receipt, canonical analysis-input, result-manifest/artifact, public-byte,
  and browser-adoption identity links without changing protected result JSON;
- analysis entrypoints and parameter mapping;
- frontend and chart/table behavior;
- automation schedules and freshness markers;
- active workflow hash, required job/step IDs, and a fail-closed zero-cost
  preflight that precedes collection, analysis, migration, or deployment;
- deployment targets and fallback route.
- zero-spend policy and any user-requested paid scope. Never place payment data,
  secret values, or a reusable billing authorization in the manifest. A manifest
  can record policy but cannot grant paid authority.

### 4. Research with evidence discipline

Use research only when it improves the decision.

- For technical claims, use official documentation, specifications, source repositories, or primary research.
- For papers, prefer the paper or publisher record over summaries.
- For current products, pricing, limits, licenses, provider rights, or security guidance, verify current sources.
- Do not use popularity as architecture evidence.
- Label each material statement as confirmed evidence, inference, or recommendation.
- Record source URL, date accessed, scope, and what decision it supports.
- Respect copyright and license restrictions.

For broad work, optional read-only specialist passes may cover:

- repository and contract audit;
- external research;
- plan critique.

Use specialists only when available, permitted, and useful. The primary agent must read the evidence and synthesize the final plan.

### 5. Compare approaches

Include at least:

- preserve-current-architecture option;
- minimal-change option;
- larger migration option only when justified.

For each, compare:

- product completeness;
- stability and failure recovery;
- analysis/data contract risk;
- implementation and maintenance cost;
- verified no-cost feasibility, recurring quota/retention/egress exposure, and
  any command that would be blocked without a prior specific paid request;
- provider rights and security;
- local preview and public deployment path;
- rollback/fallback.

### 6. Produce the plan

Use `templates/approved-plan.example.md`.

The plan must contain:

- objective and user-visible outcome;
- current-state evidence;
- protected contracts and prohibited changes;
- chosen approach and rejected alternatives;
- file/module scope;
- frontend/backend/data/automation/release boundaries;
- per-source collection → validation → coherent cutoff → authoritative analysis
  → result validation → staging → publication → deployment → public readback;
- ordered implementation steps;
- deterministic tests and browser QA;
- local-preview checkpoint;
- explicit approval gates;
- a zero-spend command gate before every remote/provider write and a separate
  paid-action gate only if the user requested that exact paid action;
- rollback and GitHub Pages or existing-production fallback when applicable;
- acceptance criteria and evidence required for completion.

### 7. Critique before handoff

Perform a second, skeptical pass:

- Does the plan solve the user's purpose or only add technology?
- Does any step silently change analysis, data meaning, schema, schedule, or public contract?
- Could an input appear functional without changing the authoritative result?
- Could local tests or a preview be mistaken for public completion?
- Is the plan mixing projects or copying one project's semantics into another?
- Are costs, secrets, provider rights, and destructive actions gated?
- Does the automation plan prove latest valid public analysis, or only that a
  workflow/build exists?
- Do required-source, optional-source, stale, schema, analysis, publish, and
  readback failures all preserve last-good state correctly?
- Could retries, schedules, storage, egress, or retention create an unrequested
  future charge?
- Could an auto-renewing trial, saved payment method, plan upgrade, overage,
  add-on, or disabled Spend cap create a charge after the current session?

Fix the plan before presenting it.

## Handoff

End with:

- the recommended plan;
- unresolved choices requiring user authority;
- exact point where mutation would begin;
- a concise invocation for `$quant-goal` if the user approves.

Do not claim implementation, deployment, or public verification from planning evidence.
