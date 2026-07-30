---
name: "quant-plan"
description: "Use only when the user explicitly invokes $quant-plan to audit current state or produce a quick or decision-complete implementation plan. Work read-only; never auto-activate or implement changes."
---

# Quant Plan

## Activation and scope

Activate only when the current user explicitly invokes `$quant-plan`. Do not
infer activation from a semantic match, a plain-text mention, an earlier turn,
an active Goal, or another agent's request. The invocation applies only to the
current user request.

Plan read-only. Inspect files, repositories, configuration, data, documentation,
and observed behavior, and run non-mutating checks when useful. Do not edit
files, install dependencies, create or update Goal state, or mutate local,
remote, provider, or production state.

When the current request also explicitly selects `quant-developer`, keep this
skill's phase read-only, finish and self-critique the selected plan first, then
hand implementation ownership to that selected skill. It may implement in the
same request only when the user already authorized immediate implementation and
did not require plan approval first. Otherwise stop after the plan; a later turn
must explicitly select the implementation skill again. When `quant-goal` is
also selected, that skill alone owns Goal state and overall lifecycle. Selection
of multiple skills never widens action, source-control, remote, or cost
authority.

## Workflow

Follow `Ground → Explore → Decide → Plan → Self-critique`.

### 1. Ground

State the intended outcome, audience, observable success criteria, relevant
constraints, and material non-goals. Identify the target environment and its
own instructions before choosing an approach.

### 2. Explore

Discover facts before asking questions. Inspect the target's source,
configuration, entrypoints, tests, generated artifacts, data paths, workflows,
and real consumer or publication surface in proportion to the request. Verify
unstable external facts with current primary sources, and distinguish observed
facts from inferences.

Proactively use available read-only subagents when independent repository,
source, method, or verification lanes would materially improve coverage or
speed. Run independent lanes in parallel when useful, give each a bounded
question and expected evidence, and reconcile their findings yourself. Use an
agent team only when at least two independent lanes can make real parallel
progress. Do not impose fixed roles, a fixed worker count, or a Team Run Packet.

For multi-lane work, external-data fallback, or real-surface evidence
selection, load the shared adaptive workflow that exists for the current
layout:

- installed:
  `../quant-research-shared/references/adaptive-workflow.md`
- source:
  `../../shared/references/adaptive-workflow.md`

This skill's read-only boundary always overrides shared `act`, edit, generated
artifact, temporary-isolation, or mutation language. In this planning phase,
interpret those mechanics as inspection, comparison, simulation in memory, or
proposed plan steps only. Do not load the reference for a narrow plan that is
already self-contained. If neither path exists, continue with this self-contained
workflow and report only the optional guidance as unavailable; do not search for
another suite copy.

### 3. Decide

Ask the user only about a high-impact preference or trade-off that materially
changes the result and cannot be discovered from the environment. Otherwise,
choose the strongest reasonable default, explain why it fits, and record it as
an assumption. Resolve competing options into one recommended approach rather
than handing unresolved design choices to the implementer.

### 4. Plan

Make the selected approach complete enough for its next reader. Include the
behavior and interfaces that change, relevant data flow, failure and degraded
behavior, verification, observable acceptance, compatibility, and rollout or
approval boundaries only where they matter. Preserve project-owned product,
analysis, data, and design contracts unless the requested change explicitly
includes them. Avoid unused infrastructure and process ceremony.

### 5. Self-critique

Challenge the draft for missing decisions, unsupported assumptions, ignored
constraints, unverified external claims, and acceptance that tests only an
intermediate artifact instead of the real consumer surface. Revise the plan
before handoff. Add an independent read-only critique only when consequence or
complexity makes it materially useful, not to satisfy a review count.

## Free data and evidence guardrails

Use only zero-billing data routes. Prefer, in order: a usable project cache or
snapshot; an official no-billing source; another lawfully accessible
no-billing public source; a method reconstructed from free inputs; then a
clearly disclosed proxy, narrower scope, degraded result, last-known-good
result, or explicit unavailable state. Paid and free-to-paid data are outside
the solution space. Exclude expiring trials or credits, card-required access,
automatic free-to-paid conversion, pay-as-you-go, overages, and paid
fallbacks.

Match provenance to the claim. Record the data date, source, fields and
adjustment or revision limitations needed to interpret the result. For public
display, verify the rights that govern the exact planned display or derived
output and avoid raw redistribution when permission is absent or unclear.
Require point-in-time evidence only for claims of historical availability,
look-ahead freedom, survivorship freedom, or revision safety; otherwise label
the limitation without making the stronger claim. Never fabricate values,
conceal staleness, bypass access controls, expose secrets, or weaken existing
degraded or unavailable semantics.

## Output modes

Choose the smallest mode that settles the request:

- `audit`: confirmed current-state findings, their impact, prioritized
  improvements, and material uncertainty or unverified claims. Give each
  material finding a reproducible evidence pointer such as a file and line,
  command result, URL and observation time, or inspected artifact, and label it
  `observed`, `inferred`, or `unverified`.
- `quick plan`: the outcome, selected approach, recommended defaults and
  assumptions, a focused action sequence, and observable checks.
- `implementation plan`: a decision-complete handoff covering relevant
  behavior and interfaces, data flow, edge cases and failure modes, tests and
  acceptance, compatibility, rollout, and approval boundaries.

Planning does not authorize implementation. Mark separate authority boundaries
for local source-control mutation (branch, worktree, stage, commit, cherry-pick,
or rebase); remote source-control mutation (push, PR, merge, tag, or release);
destructive actions; new authentication or secrets; external production,
provider, publication, deployment, migration, or schedule changes; and any paid
action.

When one of those boundaries is actually part of the plan, read the canonical
classification from the path that exists:

- installed: `../quant-research-shared/core/authority.md`
- source: `../../shared/core/authority.md`

Do not load the detailed taxonomy for an ordinary read-only plan. If a separate
boundary is in the plan but neither path exists, keep that action outside
executable scope and mark its detailed classification unverified.

## Optional legacy compatibility

Ordinary planning must not load or create a manifest, Goal ledger, receipt,
Story Envelope, or Team Run Packet. Only when the user explicitly requests
machine-audited legacy output, an existing project requires its Quant manifest
contract, or the user explicitly requests high-risk recovery that needs that
exact contract, load `core/context-routing.md` and, when applicable,
`references/goal-and-subagents.md` from the installed or source shared root.
Keep those existing contracts authoritative on that opt-in path and report
when the optional validator cannot run.
