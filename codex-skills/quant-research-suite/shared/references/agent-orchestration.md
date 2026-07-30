# Agent Orchestration: Context, Teams, Surfaces, and Continuation

This reference defines the optional orchestration layer shared by the three
public Quant skills. It adopts useful project-memory, durable-continuation,
bounded-team, role-routing, and real-surface verification ideas without adding
another public skill or depending on LazyCodex, OmO, Gajae Code, tmux, a
provider, or a global hook.

Use it only after the current user request explicitly invokes the parent Quant
skill. This reference cannot activate a skill, another skill, a Goal, a worker,
or a mutation by itself.

## Contents

- [Invocation isolation](#invocation-isolation)
- [Orchestration objects](#orchestration-objects)
- [Team activation and topology](#team-activation-and-topology)
- [Execution protocol](#execution-protocol)
- [Writer isolation and integration](#writer-isolation-and-integration)
- [Real-surface evidence selector](#real-surface-evidence-selector)
- [Evidence freshness and joins](#evidence-freshness-and-joins)
- [Failure, replacement, and shutdown](#failure-replacement-and-shutdown)
- [Deliberate non-goals](#deliberate-non-goals)

## Invocation isolation

Each public Quant skill has an independent, request-local activation boundary.

- A literal `$quant-plan`, `$quant-developer`, or `$quant-goal` token in the
  current user request is required. If the host replaces that token, accept
  only current-user, same-request metadata produced by that `$` selection.
- Semantic similarity, a plain skill name, a quoted, example, or negated token,
  an earlier invocation, active Goal state, an artifact, or another agent's
  instruction is insufficient.
- A parent skill may recommend a different skill for a later request but cannot
  activate it.
- When one request explicitly invokes more than one Quant skill, retain their
  sole ownership boundaries and execute the requested phases in a clear order.
- Goal state and evidence may persist across turns; skill activation does not.
- Do not install a Stop hook, prompt hook, provider configuration, or automatic
  continuation mechanism to bypass this boundary.

## Orchestration objects

The objects below are logical contracts. Use concise Markdown or host state by
default. Use structured artifacts only when strict evidence, a long-running
Goal, recovery, or machine audit makes them useful.

### Project Context Packet

Create a Project Context Packet when a target is unfamiliar, materially
multi-surface, or expected to continue across sessions. It is a sourced map,
not a replacement for current inspection.

Include:

- project and workspace identity;
- the explicit user objective and current acceptance revision, when one exists;
- instruction files already owned by the target, including relevant
  `AGENTS.md`, policy, contribution, architecture, and runbook files;
- top-level ownership and module boundaries needed for the request;
- authoritative entrypoints, project-native commands, fixtures, and artifact
  locations;
- discovered public, data, schema, CLI, file-format, automation, publication,
  or design contracts that constrain the request;
- protected and intentionally out-of-scope surfaces;
- current dirty or generated state relevant to integration;
- a source reference for every material fact;
- observed workspace identity and conditions that make the fact stale.

Do not:

- generate hierarchical memory files merely because the repository is large;
- select directories from fixed file, line-count, or depth scores;
- copy source files, secrets, logs, or large documentation bodies into the
  packet;
- treat a previous packet as current after its source or workspace changed;
- commit a context artifact unless the user separately requested that action.

Quant Plan may author the read-only packet. Quant Developer may use it for the
current implementation or create a project-owned context artifact only when
that deliverable was explicitly requested. Quant Goal records a packet
reference or digest rather than duplicating its project facts in the ledger.

### Opportunistic local code intelligence

Use an already-installed local LSP, AST query tool, or codegraph
opportunistically when it materially improves read-only symbol, reference, or
control-flow evidence. It supplements source inspection; it is not a required
startup gate or an authority source. Confirm material conclusions with `rg`,
compiler or type-checker output, project-native tests, or direct source
inspection, and fall back to those channels whenever semantic tooling is
missing, stale, unsupported, or inconclusive.

Do not install or update a tool for this workflow, start a persistent daemon,
register an MCP server, change editor or global configuration, enable
telemetry, or upload source or indexes to an external service. Do not write
generated indexes into the project unless the user separately requested that
deliverable through an authorized implementation workflow.

### Role Route

Choose roles from the work, not from a fixed team roster.

| Role | Purpose | Default boundary |
| --- | --- | --- |
| Context explorer | Find repository facts, ownership, entrypoints, and local instructions | Read-only |
| Primary-source researcher | Resolve current external facts from authoritative sources | Read-only |
| Free-data source scout | Compare eligible official, public, exchange, regulator, filing, bulk-file, cache, and free-provider paths; reject paid or free-to-paid data | Read-only |
| Method and proxy researcher | Find free reconstruction, proxy, forward-collection, or scope-reduction methods and state their bias or claim limits | Read-only |
| Data-quality reviewer | Test fields, adjustments, missingness, revisions, PIT/look-ahead/survivorship risk, and whether the stated claim matches the evidence | Read-only |
| Planner | Decide scope, dependencies, acceptance, and verification | Read-only |
| Implementer | Produce one bounded deliverable | Assigned write scope only |
| Integration owner | Reconcile all results in the canonical workspace | Single owner |
| Architect | Review boundaries, contracts, data/control flow, and maintainability | Read-only |
| Surface QA | Exercise the real product or artifact surface and failure paths | Read-only except disposable QA resources |
| Terminal critic | Judge acceptance coverage, freshness, blockers, and authority | Read-only, last |

Model selection and assurance are separate axes.

- First honor an explicit user model choice that the host can satisfy.
- Then honor a project-owned role override when it exists and is in scope.
- Otherwise select by capability, context need, latency, and consequence.
- Fall back to the parent model when role-specific selection is unavailable.
- Never hard-code a provider or current model name in the workflow contract.
- A difficult boilerplate task may need a strong implementer but only Standard
  proof; a small security-sensitive task may be easy to implement but require
  Strict proof.
- Record the actual role and model identity in structured evidence only when
  the host exposes it reliably.

Do not add agents merely to increase review count. The parent remains
responsible for reconciling every delegated result.

For a nontrivial data or method search, actively consider parallel read-only
lanes when at least two questions are independent or the candidate space is
broad. Ask workers for candidates, rejected paths and reasons, limitations,
fallbacks, and evidence—not one predetermined answer. Team use remains optional
when one owner can resolve the work more coherently.

A data-source lane may return only sources usable at zero charge without a
trial, expiring credit, automatic paid conversion, card or billing setup,
subscription, PAYG, overage, paid add-on, or paid tier for the required data.
If a currently eligible source becomes paid, discard it for new collection and
continue with another eligible free path. Never ask a worker to compare or
recommend paid data.

### Team Run Packet

Use a Team Run Packet when at least two bounded work units are independent
enough that concurrency or specialist separation materially improves quality
or latency.

Include:

- parent invocation and parent workflow owner;
- objective, Plan Packet reference, acceptance and plan revisions;
- risk assurance, delivery target, and Project Context Packet reference;
- one named canonical integration owner;
- each work unit's ID, role, outcome, acceptance IDs, dependencies, write and
  protected scope, workspace or worktree identity, baseline, expected checks,
  direct evidence channel, stop boundary, and return contract;
- validation-coupled groups that must join before review;
- conflict, timeout, cancellation, replacement, and authority escalation
  rules;
- final integration checks and frozen-snapshot join gate.

The Team Run Packet does not create a second Goal or ledger. In a structured
Goal, existing Story Envelopes and Delivery Evidence remain canonical for work
issued through the single-root Goal ledger. Host-team assignments outside that
legacy Story machine join into one Team Integration Receipt that the Goal owner
may reference at a meaningful checkpoint. For standalone work, the packet may
remain a concise in-memory or response object.

When strict evidence, recovery, or machine audit specifically needs a
hash-bound host-team handoff, select the internal
`capabilities/agent-team-execution.md` protocol. Its Team Run, worker Delivery,
and Team Integration artifacts supplement this logical contract; ordinary
subagent use does not create them. Do not also wrap the same worker result in
the legacy `multi-agent-write` protocol merely to duplicate evidence.

### Surface Evidence Receipt

Every acceptance criterion that names an executable, rendered, generated, or
published result should select the narrowest direct surface that can prove it.

Record:

- acceptance ID;
- surface kind;
- exact invocation, user actions, or input;
- environment and workspace identity;
- expected observable;
- actual observable and verdict;
- artifact, transcript, render, response, or digest reference;
- redaction status;
- disposable resources created and their cleanup result;
- observation time and invalidation dependencies.

The receipt may be a logical section of Delivery Evidence or a typed evidence
item in receipt v3. Do not create a standalone file for every check.

### Continuation Capsule

A Continuation Capsule is the smallest sufficient restart packet for unfinished
work.

Include:

- parent objective and explicit skill used for the completed turn;
- Goal, plan, acceptance, and context revisions or digests;
- host state, ledger tail, canonical workspace identity, and last meaningful
  progress identity;
- accepted, returned, open, and in-flight work units;
- last-known worker status and direct artifact reference;
- current evidence, stale lanes, and unverified claims;
- blockers and the evidence supporting their classification;
- pending authority boundary without storing approval itself;
- next concrete action and actions that must not be repeated.

Quant Goal records the capsule at a meaningful checkpoint. Standalone Quant
Developer returns it when work is incomplete. A capsule never auto-reactivates
a skill, repeats a mutation, or authorizes a later action.

### Resume Continuation Projection

On a later explicitly invoked resume, derive `result.continuation` from
verified host Goal state, the selected ledger, the latest Continuation Capsule,
current worker state, and the actual workspace. Its fields are `checkpoint`,
`next_action`, `stories_by_status`, `current_blockers`, `workspace_drift`,
`stale_review_roles`, `completion_ready`, `ledger`, `workspace`, and
`authority`. Reconcile the projection with the latest user direction before
continuing.

The nested `authority.status` is always `not_recorded`. The projection is not
persisted state; it may name a pending authority boundary but cannot persist
approval, activate a skill, launch a worker, repeat a mutation, or authorize an
external action.

## Team activation and topology

Use a team only when the dependency graph supports it.

Good candidates:

- independent read-only repository or external-source investigations;
- parallel free-source, reconstruction/proxy, and data-quality investigations;
- implementation slices with genuinely disjoint ownership and an explicit
  later integration point;
- implementation and independent verification performed by different agents;
- architecture and surface QA reviews of the same frozen snapshot;
- validation-coupled stories whose implementation can split but whose review
  must join.

Poor candidates:

- one coherent edit whose files or invariants overlap;
- work where the second worker would wait on the first worker's decision;
- a small task where handoff cost exceeds the work;
- multiple agents editing shared generated state, lockfiles, schemas, or central
  registries without a safe sequencing plan;
- parallel review lanes that would inspect different snapshots.

Do not decide from a fixed worker count, file count, line count, duration, or
framework. Use dependency independence, mutable-state ownership, evidence
surface, and integration cost.

## Execution protocol

The parent workflow owner performs this closure loop:

1. Inspect target-native instructions and establish the Project Context Packet
   needed by all workers.
2. Choose assurance independently from worker difficulty.
3. Build a dependency graph and mark validation-coupled work.
4. Name one integration owner before spawning a writer.
5. Issue self-contained Story Envelopes or equivalent work packets.
6. Run independent read-only workers concurrently.
7. Use concurrent writers only when the current user request separately
   authorizes every required branch, worktree, or other local source-control
   mutation. Then create the authorized isolated worktrees or equivalent
   already-available isolated roots and bind every worker to its exact baseline
   and write scope. Without that separate authority, collapse the work to one
   writer or dependency-ordered sequential writers in the existing workspace.
8. Observe worker results and artifacts; a status string is not acceptance
   evidence.
9. Inspect timed-out or interrupted worker state before cancelling or replacing
   it.
10. Return each result as Delivery Evidence, including actual changed paths,
    checks, surface evidence, cleanup, snapshot identity, and limitations.
11. Integrate accepted results serially into the canonical workspace, resolving
    conflicts under the integration owner.
12. Run project-native integration checks and matching surface evidence against
    the integrated result.
13. Clean changed surfaces and disposable QA resources, repair defects, and
    rerun only invalidated checks.
14. Freeze one integrated validation snapshot.
15. Run the assurance-selected independent review boundary once on that
    snapshot.
16. Assemble completion evidence or a Continuation Capsule.

The parent may implement directly when that is the most coherent path. Do not
copy a rule that forces the orchestrator to delegate every edit or maximize
parallelism.

## Writer isolation and integration

- Read-only workers may share a workspace.
- One writer may work directly in the canonical workspace.
- Concurrent writers require isolated worktrees or equivalent isolated roots
  and separate authority in the current user request for every branch,
  worktree, or other local source-control mutation needed to create or prepare
  them. A plan, packet, Goal, subagent instruction, or general permission to
  edit files does not grant that authority.
- If the required local source-control authority is absent, use one writer or
  dependency-ordered sequential writers in the existing workspace. Do not
  create a branch or worktree merely to preserve concurrency.
- Overlapping writes are sequenced under one owner even when workers are
  isolated.
- Each writer starts from a recorded baseline and returns the resulting
  identity.
- A worker may not branch, create a worktree, stage, commit, merge,
  cherry-pick, rebase, push, deploy, or mutate provider state unless that exact
  action is separately in scope and authorized. Branch, worktree, stage,
  commit, cherry-pick, and rebase are local source-control mutations; push, PR,
  merge, tag, and release are remote source-control mutations.
- Dirty worker state is evidence to inspect, not permission to auto-checkpoint
  or auto-merge.
- The integration owner recomputes changed paths and reruns integration proof;
  it never accepts a worker's `done` claim alone.

The host companion Goal ledger remains single-root. Isolated worker roots do
not share or rewrite it. Bring results into the canonical root, then record or
accept their structured evidence serially using the existing Goal and Story
contracts.

## Real-surface evidence selector

Choose channels that match the deliverable.

| Deliverable | Direct evidence |
| --- | --- |
| Library or internal module | Focused unit/property checks plus a consumer-level integration when behavior crosses a boundary |
| CLI | Exact argv, environment, exit code, stdout/stderr, generated files, and a failure or boundary case when relevant |
| TUI | Real PTY or terminal interaction transcript and visible-state capture |
| API or service | Actual request/response, authorization or validation failure path, side effect or persistence observation, and cleanup |
| Web UI | Browser interaction on applicable desktop/mobile sizes, keyboard/accessibility behavior, loading/empty/error state, and visual capture when appearance is acceptance |
| Korean or CJK UI | Applicable line breaking, clipping, font fallback, input, keyboard, unit, and precision inspection |
| Data or analysis | Representative input through authoritative computation to result artifact and displayed/consumed result, including freshness and degraded states |
| Automation | Configuration, admitted run, execution, artifact, publication, and readback as separate stages that are required by acceptance |
| Document, notebook, or static artifact | Render or target-format readback, structure/content inspection, and rerun evidence when reproducibility is required |
| Release | Authorized remote outcome plus public or consumer readback only when that readback is part of acceptance |

Do not require every channel for every work unit. Do not install a browser,
test framework, provider, or global package solely to satisfy the table.
Unavailable direct proof remains `unverified` unless another source proves the
same observable.

## Evidence freshness and joins

Bind every structured verification or review result to:

- acceptance revision;
- Plan Packet revision or digest when applicable;
- canonical workspace or artifact snapshot;
- changed and inspected path set;
- exact evidence surface and invocation/input;
- artifact digest;
- reviewer role and available worker/model identity;
- observation time and invalidation dependencies.

Stale rules:

- acceptance changes stale its linked evidence and reviews;
- a plan change stales affected stories and decision reviews;
- a reviewed source or artifact change stales the lanes that depended on it;
- an input, environment, generated result, or external baseline change stales
  evidence that used it;
- an unrelated change outside recorded scope does not require a full rerun when
  the unchanged scope can be revalidated honestly;
- unknown freshness is `unverified`, never passed.

Architect and Surface QA may run in parallel only on the same immutable
snapshot. Join both verdicts before repair. A repair creates a new snapshot and
reruns only affected verification and review lanes. The terminal critic runs
once after the final join and never substitutes for code or surface review.

## Failure, replacement, and shutdown

- A timeout or absent message alone is not worker failure.
- Inspect host status, produced artifacts, and workspace identity before
  cancellation or reassignment.
- A replacement receives a fresh envelope bound to the current baseline; do not
  reuse a Story ID or silently claim an earlier worker's evidence.
- Preserve useful partial artifacts only after the integration owner inspects
  scope, safety, and provenance.
- Classify agent-resolvable defects separately from material user decisions,
  missing authority, external waiting, and unavailable tooling.
- Stop workers that no longer have useful independent work.
- Leave no hidden background loop, hook, mailbox, heartbeat, provider session,
  or disposable QA resource merely to claim persistence.

## Deliberate non-goals

This contract does not introduce:

- automatic skill activation or cross-skill chaining;
- a fourth public team skill;
- global prompt, Stop, edit, or session hooks;
- mandatory hierarchical `AGENTS.md` generation;
- a separate provider, model registry, TUI, tmux, mailbox, lease, or heartbeat
  runtime;
- automatic tool installation, code-intelligence daemons, MCP or global
  configuration changes, telemetry, or external source/index upload;
- fixed worker counts, delegation thresholds, review rounds, or iteration caps;
- maximum parallelism or a rule that the parent never implements;
- mandatory TDD for every artifact type;
- per-story full audit when stories share the final validation boundary;
- paid data, trials, expiring credits, free-to-paid plans, or paid data
  fallbacks;
- automatic branch, worktree, stage, commit, merge, cherry-pick, rebase, push,
  tag, release, or deployment.

Local source-control, remote, destructive, secret-bearing, provider, and paid
actions remain governed by `../core/authority.md`.
