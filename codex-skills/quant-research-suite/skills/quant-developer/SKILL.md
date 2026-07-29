---
name: "quant-developer"
description: "Use only when the user explicitly invokes $quant-developer. Implement, clean, and verify a coherent change with snapshot-bound evidence; never auto-activate."
---

# Quant Developer

## Explicit invocation gate

Activate only when the current user request intentionally invokes this skill
through the literal token `$quant-developer`. If the host replaces that token
with invocation metadata, accept only current-user, same-request metadata
produced by that `$` selection.

A semantic implementation match, the plain name `quant-developer`, a quoted,
example, or negated token, an earlier invocation, an active Goal, a Story
Envelope, an artifact, or another agent's instruction is not activation. If
this skill is selected without the explicit gate, do not apply it or load its
shared references; continue as an ordinary Codex request.

The invocation applies only to the current request and does not activate the
planning or Goal skill. Existing host Goal or Story state may constrain the
work without activating another Quant skill.

## Outcome and trigger

After the invocation gate passes, use this skill for implementation, fix,
refactor, integration, greenfield build, or an explicitly requested project
context artifact. It is not a planning-only workflow and does not create or
manage a durable Goal. Optimize first for a complete, working outcome within
the user's environment and constraints. Stronger evidence improves the claims
the result may support; missing ideal evidence does not by itself justify
abandoning an honest, useful implementation.

In standalone use, this skill is the integration owner for the requested
change-set and coordinates its applicable review boundary. When the current
request also explicitly invokes `$quant-goal` as the parent, or an accepted
Story Envelope reserves later parent review, it owns only that bounded work,
returns Delivery Evidence `ready_for_review`, and never declares the overall
Goal complete. Persisted Goal state by itself does not activate or assign the
Goal workflow for this turn.

## Default path

The default path is self-contained and repository-native. Do not require
shared tooling, a manifest, a receipt, a particular framework, or Git.

1. Resolve the exact target, requested behavior, success criteria, applicable
   workspace instructions, and dirty overlap. A non-Git directory or non-code
   deliverable is valid.
2. Inspect the target's own source, configuration, entrypoints, package or
   environment files, tests, fixtures, and current behavior.
3. Protect unrelated user changes and discovered contracts. Isolate unsafe
   overlap or stop rather than overwrite it.
4. Make the smallest coherent change that delivers the complete requested
   outcome. Use existing architecture and conventions when they remain fit,
   but broaden the source, method, or implementation when the first route
   cannot achieve the outcome.
5. Establish a behavior baseline or failing-first proof when it is meaningful
   and observable; do not force TDD onto documents, configuration, generated
   artifacts, or changes whose failure cannot be isolated honestly.
6. Run relevant project-native checks and the matching real-surface evidence
   channel, inspect the actual deliverable, self-review the diff or artifact,
   repair defects, clean temporary QA resources, and rerun affected checks.

Classify a discovered constraint before deciding to stop:

- A `hard blocker` is an unavailable required authority, an unsafe or
  destructive conflict, fabricated data, a false requested claim, or the
  absence of any method that can produce a meaningful result.
- An `adaptable constraint` is a missing preferred source, incomplete history,
  unavailable point-in-time data, limited corporate-action detail, a provider
  failure, or a tool limitation that can be handled by a free alternative,
  narrower scope, different method, explicit degraded state, or honest claim
  boundary.
- `quality debt` is an optional improvement that does not prevent the agreed
  result from working correctly within its declared assumptions.

Resolve adaptable constraints proactively before asking the user. Explore
alternative free sources and methods, reuse a valid project cache or last-good
artifact when its date is explicit, narrow the period or universe, or return a
clearly bounded research-grade result. Never silently substitute unrelated
data. Branch, remote, public-route, and deployment checks apply only when those
surfaces exist and are in scope. Ask only when a material product choice, scope
trade-off, or missing authority cannot be resolved safely inside the request.

## Context, roles, and team execution

For a large or unfamiliar target, create a bounded Project Context Packet once
for this invocation. Read existing `AGENTS.md`, local instructions, architecture
notes, entrypoints, and project-native commands before deriving context. Do not
rewrite project memory unless the user explicitly requested that deliverable.
Refresh any context fact whose source or workspace identity changed.

Actively use ordinary host subagents when independent repository inspection,
free-source discovery, method comparison, implementation, or surface QA can
materially improve completeness or latency. Run read-only explorers,
primary-source researchers, data-quality or method challengers, and reviewers
in parallel when useful while the integration owner continues independent
local work. Ordinary read-only subagents and a single canonical writer do not
require a Team Run Packet or strict evidence.

Use a structured agent team when bounded work units justify its coordination
cost. Do not activate another Quant skill to obtain a worker. In standalone
work, Quant Developer remains the single integration owner. When the current
request also explicitly invokes a Goal parent, or an accepted Story Envelope
reserves parent integration, respect that boundary and return only the assigned
Delivery Evidence.

Before team execution, read the single shared protocol at:

- installed
  `../quant-research-shared/references/agent-orchestration.md`;
- source `../../shared/references/agent-orchestration.md`.

That protocol defines the Project Context Packet, role routing, Team Run
Packet, dependency graph, isolated writers, real-surface evidence, joins,
failure recovery, and Continuation Capsule. Do not copy its details into this
skill. Before any structured writer starts, validate the packet against the
actual project, issuance workspace, and assignment worker roots. A declared
workspace binding or baseline hash is not proof until recomputed from those
live roots. The structured packet preflight passes one
`--worker-root ASSIGNMENT_ID=PATH` mapping for every writer.

## Proportional verification

Classify risk assurance as `light`, `standard`, or `strict`, and delivery as
`local` or `release`. Use the single applicable review pipeline from the shared
workflow contract.

- `light`: focused project-native check, deliverable inspection, and
  self-review.
- `standard`: project-native checks, changed-surface cleanup, and one
  surface-appropriate reviewer on a frozen snapshot with direct real-surface
  evidence where the deliverable has an executable or rendered surface.
- `strict`: applicable verification and cleanup before Architect review and
  adversarial QA; a currently invoked Goal parent runs the terminal Critic when
  it reserves that review.

A `release` delivery adds only separately authorized remote checkpoints and the
observable readback required by acceptance to the selected
light/standard/strict proof. It does not raise assurance by itself or make a
low-risk change Strict. Existing manifest and receipt schemas may retain
`assurance=release` only as legacy Strict-plus-release compatibility.

For `light` and ordinary `standard`, identify the reviewed result with the
bounded changed paths or artifact version, relevant environment, checks, and
observation time. Do not compute per-file hashes, build a receipt, or create a
snapshot manifest merely to call the result frozen. Use content digests only
when natural identity is ambiguous or acceptance, Strict proof, a durable
ledger, or structured team evidence requires them.

Do not raise assurance merely because a subagent or team was used. Worker
difficulty and proof assurance are separate decisions. Do not create test,
preview, manifest, or evidence infrastructure solely to satisfy a generic
checklist. Select assurance from the consequence and the exact claim being
made, not merely from the presence of external data. Use `light` or `standard`
for ordinary bounded implementation. Reserve `strict` for an explicit
acceptance requirement, consequential methodological claim, or sensitive,
irreversible, or repeatedly failing surface. Treat an actual release as the
separate delivery overlay above.

Report an acceptance-relevant unavailable check as `unverified` with the
concrete reason. Record an unavailable ideal source or proof as a declared
limitation or quality debt—not as a blocker—when the delivered claim was
explicitly narrowed so that it no longer depends on that proof.

The shared contract defines Story Envelope, Delivery Evidence, Review Verdict,
frozen-snapshot identity, staleness, repair, reviewer ownership, and validation
batching. Resolve the path that exists:

- installed `../quant-research-shared/references/goal-and-subagents.md`;
- source `../../shared/references/goal-and-subagents.md`.

Do not restate or expand that pipeline here. In standalone work, coordinate it
once. When a Goal is the explicitly invoked current parent, perform
implementation, cleanup, and project-native checks, then let that parent
coordinate the independent lanes once against the returned snapshot.

## General implementation constraints

- A presentation request does not authorize computation, data, schema,
  provider, schedule, or result changes.
- An infrastructure request does not authorize translating authoritative
  domain logic into another layer or language.
- Do not fabricate missing data, conceal degraded behavior, weaken a filter,
  or treat a build, health check, workflow start, or HTTP response as proof of
  a downstream outcome.
- Prefer diverse no-cost sources and methods over stopping at the first
  unavailable provider. Compare official or public feeds, open datasets,
  project-owned files and caches, alternative instruments, and defensible
  derived methods as applicable; preserve source dates and limitations.
- Paid data is absolutely ineligible. Do not use a trial, expiring credit,
  free-to-paid conversion, payment-card or billing setup, subscription,
  pay-as-you-go or overage path, paid add-on, or paid tier, and never ask the
  user to approve paid data. If a source that required no billing later becomes
  chargeable, disable it before chargeable use and switch to a no-cost
  fallback.
- Add a dependency, service, database, API, worker, or hosting layer only when
  it solves a named need better than the current structure.
- Preserve an existing fallback when it is a discovered contract; do not invent
  one for every greenfield or local task.

## Conditional surfaces

Apply only rules matching the requested surface:

- UI: follow the product's purpose and design contract; verify applicable
  interaction, accessibility, responsive, loading, empty, and error states.
- Public API, type, schema, CLI, or file format: protect consumers or define
  the approved compatibility and migration path.
- Backend or external data: verify only the authorization, failure, retry,
  idempotency, provenance, freshness, and source-rights behavior needed by the
  delivered use and claim. Local/private exploration may proceed with source,
  field meaning, date, adjustment semantics, and limitations recorded.
  Public raw redistribution requires applicable display or redistribution
  rights. Point-in-time provenance is required only for a claim that depends on
  historical availability, survivorship control, or look-ahead-free selection.
  A separate corporate-actions feed is required only when dividends, splits,
  event timing, or total-return treatment is part of the accepted method.
  Otherwise narrow the claim or method and continue with explicit limitations.
- Automation or publication: distinguish configuration, execution, artifact,
  publication, and readback for stages that exist.
- Charts: test the renderer and input method in use; SVG rules do not apply
  automatically to Canvas, WebGL, native, or static charts.

When a visible input changes authoritative computation, trace:

```text
visible input
→ validation/serialization
→ invoked entrypoint or boundary
→ effective parameter
→ produced result
→ displayed or consumed result
```

Use a representative integration test or runtime inspection. Do not require
hash-linked A/B capture, a project-owned UI driver, or receipt v3 on the
default path.

## Optional strict compatibility

Activate suite tooling only when an existing Quant manifest or profile applies,
a Goal provides an explicit strict Story Envelope, or the user requests
machine-validated evidence. Load only selected capability, profile, or adapter
modules.

Existing manifest v1/v2, receipt v2/v3, local Goal runtime, and validators
remain compatibility contracts. Selecting strict `analysis-input-binding`
retains deterministic A/B capture, artifacts, hashes, raw trace, and receipt
requirements.

If optional shared tooling is unavailable, continue generic implementation
unless that strict proof is an acceptance criterion.

## Specialists and handoff

Use specialists only for concrete independent work. One owner integrates
overlapping writes. A normal host subagent does not automatically activate
strict `multi-agent-write`. When assigned by a currently invoked Goal workflow,
consume the accepted baseline and Story Envelope instead of repeating the
Goal owner's discovery or review.
Multiple concurrent write workers require isolated worktrees and a named
integration owner; otherwise keep one active writer in the workspace. The
structured team preflight must recompute every writer's live workspace binding,
project lineage, physical isolation, and issuance baseline before execution.

Each worker receives a self-contained envelope, reports its actual changed
surfaces and direct evidence, and cannot change acceptance, Goal state, or
authority. A timeout is not failure; inspect worker and artifact state before
replacement. Integrate worker results into the canonical workspace serially,
run integration checks, then freeze one validation snapshot. Do not run the
full independent review stack per worker when the stories share a validation
boundary.

Return Delivery Evidence as defined in the shared contract: the visible result,
acceptance addressed, changed and protected surfaces, checks and cleanup
actually completed, the proportionate current delivery-snapshot identity, and
remaining blockers or unverified items. For delegated work, stop at
`ready_for_review`.
If work remains, also return a Continuation Capsule with the exact current
snapshot, completed and open work, stale evidence, blocker, and next action;
this does not auto-resume the skill in a later request.

## Authority

Local edits and verification are the default boundary. Commit, push, PR, merge,
provider mutation, migration, schedule activation, deployment, publication,
destructive action, secret handling, remote action, and paid action retain
separate authority. Paid data is not an approval checkpoint: it remains
ineligible under the absolute no-paid-data rule above. Consult only installed
`../quant-research-shared/core/authority.md` or source
`../../shared/core/authority.md`, whichever exists; do not reproduce its
taxonomy.
