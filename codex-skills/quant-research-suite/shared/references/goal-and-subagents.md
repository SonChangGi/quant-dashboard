# Workflow Contract: Shape, Act, Track, and Prove

This reference defines optional structured compatibility workflow objects,
assurance levels, review gates, and ownership boundaries. Load it only through
the explicit compatibility, machine-audit, or exact high-risk-recovery routes
defined by `core/context-routing.md`. It does not govern the ordinary native
Quant Plan, Quant Developer, or Quant Goal path.

Path notation follows `core/context-routing.md`: `<quant-shared-root>` is the
resolved installed `quant-research-shared` directory or source `shared`
directory. Commands and references below are relative to that root and never
depend on the caller's current working directory.

## Contents

- [Manual invocation boundary](#manual-invocation-boundary)
- [Routing and sole ownership](#routing-and-sole-ownership)
- [Assurance and delivery selection](#assurance-and-delivery-selection)
- [Constraint handling](#constraint-handling)
- [Shared workflow objects](#shared-workflow-objects)
- [Review pipeline](#review-pipeline)
- [Frozen snapshots, staleness, and repair](#frozen-snapshots-staleness-and-repair)
- [Goal lifecycle and local evidence ledger](#goal-lifecycle-and-local-evidence-ledger)
- [Parallelism and integration](#parallelism-and-integration)
- [Authority](#authority)

## Manual invocation boundary

The role names in this contract do not activate public skills. Each Quant skill
applies only when the current user request explicitly invokes that exact skill
through its literal `$` selector. If the host replaces that token, accept only
current-user, same-request metadata produced by that `$` selection. A role
owner, Plan Packet, Story Envelope, active Goal, worker instruction,
checkpoint, or earlier invocation is not authority to activate another skill.

An explicitly invoked parent may use ordinary host workers under this contract
without activating Quant Developer. Another Quant skill participates only when
the current user directly invoked it too. Persistent Goal state preserves
evidence and lifecycle, not future-turn skill activation.

The workflow is strong where evidence matters and small where it does not:

1. **Shape** — make the decision and acceptance criteria clear.
2. **Act** — implement one coherent change against the accepted scope.
3. **Track** — preserve meaningful progress and revisions when a durable Goal
   exists.
4. **Prove** — review one frozen result and close only against fresh evidence.

Persistence never expands scope or authority. A plan, Goal, ledger, story,
receipt, reviewer verdict, or subagent message is evidence, not permission.

## Routing and sole ownership

| Concern | Sole owner | Boundary |
| --- | --- | --- |
| Discovery, alternatives, proposed acceptance, and implementation plan | Explicitly invoked Quant Plan | Read-only; no implementation or Goal state |
| Local implementation, project-native checks, and change cleanup | The assigned implementation owner | Explicitly invoked Quant Developer when it owns the change, or an ordinary host implementer assigned by the current Goal parent; neither completes a parent Goal |
| Host Goal lifecycle, acceptance intake/revisions, checkpoints, blockers, review orchestration, and final completion | Explicitly invoked Quant Goal | Does not restate the implementation workflow |
| Agent-team topology and integration | Explicitly invoked Quant Developer when standalone; explicitly invoked Quant Goal when it is the current parent | Workers implement or inspect; the current parent retains one integration and review owner |
| Local source-control, remote source-control, destructive, secret-bearing, provider, and paid authority | The user plus the canonical authority policy | Never inferred from workflow state or ordinary permission to edit files |

When Quant Developer is explicitly invoked without a currently invoked Goal
parent or a Story Envelope reserving later parent review, it owns the requested
change-set and applicable review gate. When Quant Goal is explicitly active as
the parent workflow for the current request, it owns integration and
independent review; its ordinary host implementer, or Quant Developer when the
user explicitly invoked both, stops at Delivery Evidence. A persisted Goal
without a current `$quant-goal` invocation does not silently acquire those
current-turn responsibilities. This prevents duplicate review and implicit
cross-skill activation.

Quant Plan may commission a read-only plan critic when planning assurance
requires it. That critic reviews the proposed decision before mutation; it is
not a substitute for, or duplicate of, implementation review.

The optional Project Context Packet, Role Route, Team Run Packet, Surface
Evidence Receipt, Continuation Capsule, real-surface selector, and worker
recovery contract live in `references/agent-orchestration.md`. These objects
extend this workflow without creating another public skill or Goal owner.

## Assurance and delivery selection

Select risk assurance and delivery independently. Risk assurance is `light`,
`standard`, or `strict`; delivery is `local` or `release`. Carry both through
the Plan Packet, Story Envelope, Delivery Evidence, reviews, and checkpoints.
Raise risk assurance only when new evidence reveals greater consequence or the
user requests stronger proof. Record the reason for a change. Subagent use,
file count, line count, framework choice, public visibility, or release alone
does not raise risk assurance.

| Level | Activate when | Planning | Implementation proof | Independent review | Persistence |
| --- | --- | --- | --- | --- | --- |
| `light` | Narrow, reversible local work | Decision, assumptions, focused check, and one primary-planner self-critique | Direct deliverable inspection and focused project-native check | None | Host/conversation state |
| `standard` | Several related surfaces or a consumer-facing contract | Compatibility, affected verification, and one primary-planner self-critique | Project-native tests plus change cleanup and rerun | One surface-appropriate reviewer on a frozen snapshot | Host state; local ledger only when the selected compatibility contract requires it |
| `strict` | Security, privacy, regulated use, raw-data redistribution risk, a strong PIT/causal claim, high-consequence computation, migration, destructive work, or repeated failure | Required immutable Plan Packet with baseline, failure modes, recovery, and one independent plan critique | Applicable full verification, cleanup, and failure-path evidence | Architect review, adversarial QA, and one terminal critic | Host state by default; automatic ledger only inside an explicitly selected structured contract |

A `release` delivery overlay adds only the separately authorized remote
checkpoints and observable consumer or public readback required by acceptance.
It uses the selected `light`, `standard`, or `strict` local proof; it does not
automatically import the Strict review stack. Existing manifest and receipt
schemas may retain `assurance=release` as a legacy compatibility value. On that
optional path it continues to mean the historical Strict-plus-release contract;
do not select that legacy value for the generic default merely because delivery
is remote.

Long-running means that safe continuation is expected across sessions,
interruptions, external waiting, or independently resumable milestones, or the
user explicitly requests durable recovery. Long-running persistence does not
by itself raise implementation assurance or select a local ledger. The user or
an existing contract must explicitly select durable structured evidence.

If the selected proof cannot run, keep the affected claim `unverified` and give
the concrete reason. Do not create unrelated infrastructure merely to satisfy
the table.

## Constraint handling

Classify an obstacle before pausing work:

- a `hard blocker` prevents honest or authorized progress, such as fabricated
  data, access-control bypass, secret exposure, an unauthorized remote or
  destructive action, paid data, or missing evidence for a claim whose wording
  explicitly requires that evidence;
- an `adaptable constraint` limits a preferred path but permits another honest
  one, such as a missing free provider, non-PIT history, incomplete
  corporate-actions coverage, or a shorter usable period or universe;
- `quality debt` is a useful improvement that is outside current acceptance,
  such as an additional cross-check, longer forward collection, or stronger
  optional provenance.

Resolve an adaptable data constraint through eligible official/public free
sources, another free provider, free filings or derivation, a defensible free
proxy, forward-only collection, or a narrower period, universe, method, or
claim. Preserve an explicit limitation or degraded/unavailable state. Do not
offer paid data, a trial, expiring credit, payment setup, subscription, PAYG,
overage, or paid tier. Use `blocked` only after safe in-scope free alternatives
and useful non-data work are exhausted.

Rights and PIT requirements follow the selected use and claim. Unclear raw
redistribution rights block that publication lane, not an otherwise permitted
private analysis or free-source search. Historical PIT evidence is a hard gate
only for a point-in-time, as-known-then, look-ahead-free, survivorship-free, or
historically investable claim. A non-PIT retrospective may complete with the
relevant limitations stated.

## Shared workflow objects

The objects below are logical contracts. They may be concise Markdown, host
state, structured data, or a validated strict-runtime artifact. Do not require
JSON or a file when a human-readable object is sufficient.

### Plan Packet

Owned by Quant Plan and consumed, not recreated, by later work.

Include:

- objective and user-visible outcome;
- Project Context Packet reference or the sourced target facts needed by the
  decision;
- chosen decision and rejected alternatives only when they were viable;
- stable acceptance IDs and non-goals;
- constraints, discovered contracts, and protected surfaces;
- assurance level and the evidence supporting it;
- implementation sequence and dependency boundaries;
- verification and review strategy, including the direct evidence channel for
  each acceptance criterion;
- later authority checkpoints;
- known assumptions, limitations, and deferrals;
- a stable artifact reference or digest when a local ledger will bind it;
- for Strict review, one tuple containing the Plan revision or digest, the
  reviewed acceptance revision, and the critic verdict that names both.

Include a nonnumeric `decision_readiness` section only while a material
decision or contradiction remains. For each item record the sourced issue, why
it changes the selected work, the decision owner, and the condition that clears
it. Omit the section when no such item exists. Do not derive a score, threshold,
question count, or review-round count. A Plan Packet stays a draft and cannot
be frozen while an item remains unresolved. Do not freeze it until an explicit
scope decision clears the item and the excluded matter no longer changes
implementation or acceptance.

Quant Plan remains the author of the initial packet. Once a Goal binds the
packet, Quant Goal owns acceptance revision history. A later planning pass may
advise a revision, but it does not mutate Goal state.

For `strict` and legacy `assurance=release` compatibility, the primary planner
freezes a revision identity or content digest before the independent critic
reads it. The critic's verdict names that exact Plan revision and reviewed
acceptance revision. If it has blocking findings, the primary planner
integrates them coherently into a new revision and asks the critic to inspect
only that changed draft. Do not impose a fixed round count or bind a Plan
Packet, acceptance revision, or digest that differs from the reviewed tuple. If
the same material judgment conflict remains unresolved, preserve it as an
explicit user decision rather than manufacturing consensus. Only a revision
whose matching critic verdict is passed or contains non-blocking findings is an
approved immutable Plan Packet.

When the plan has material architecture, data/control-flow, migration,
security, or operational-topology risk, add an Architect to the plan Critic.
Both inspect the same immutable draft, then the primary planner joins their
non-overlapping findings into one revision. Do not require this second role for
every strict plan or manufacture fixed three-role consensus.

### Story Envelope

Owned by Quant Goal when a Goal delegates work, or by the standalone
integration owner when structured delegation is useful.

Include:

- parent objective or Goal reference and assigned acceptance IDs;
- assigned worker role, dependency or validation-coupled group, and integration
  owner when a team is used;
- bounded outcome, non-goals, target surfaces, and protected contracts;
- repository/workspace identity and relevant baseline reference;
- allowed write scope and prohibited overlap;
- applicable project-native checks, selected real-surface evidence channel,
  and expected return evidence;
- risk assurance, delivery target, and selected strict capabilities, if any;
- authority and stop boundaries;
- delivery outcomes: `ready_for_review`, `blocked`, or `failed`.

A worker cannot broaden this envelope, change acceptance, grant authority,
checkpoint the parent Goal, or declare overall completion.

Story and review scopes never authorize Git metadata or the structured Goal
state directory. Generic whole-project globs treat both as reserved implicit
exclusions; direct or metadata-shaped wildcard selectors fail closed.

Only `ready_for_review` enters the Story return-and-accept path. A `blocked` or
`failed` Delivery Evidence result is classified in the Goal checkpoint and
blocker history while the Story remains owned. A later acceptance revision
supersedes any open or returned Story bound to the prior revision; cancellation
or Goal supersession ends it through the host lifecycle. Do not invent a
second Story-completion command merely to mirror semantic Goal states.

### Delivery Evidence

Owned by the implementation role for the delivered change. That role is Quant
Developer only when the user explicitly invoked it; otherwise a currently
invoked Goal may assign an ordinary host implementer under the same return
contract.

Include:

- user-visible result and acceptance IDs addressed;
- worker role and Team Run or Story reference when delegated;
- changed and intentionally protected surfaces;
- project-native checks actually run, with result and relevant artifact;
- Surface Evidence Receipt fields for executable, rendered, generated, or
  published acceptance;
- cleanup and self-review result;
- unverified items, remaining defects, or blockers;
- the exact frozen delivery-snapshot identity;
- remote or public observations only when separately authorized and observed.

Delivery Evidence means ready for the applicable independent review. It is not
an implementation reviewer verdict or a Goal completion receipt.

### Review Verdict

Owned by the named read-only reviewer and accepted or rejected by the workflow
owner.

Include:

- reviewer role and review purpose;
- exact frozen-snapshot identity;
- contracts, the actual acceptance-ID subset, and surfaces inspected;
- exact portable path patterns and the current digest of that review scope when
  a structured ledger records the verdict;
- checks or artifacts examined;
- verdict: `passed`, `needs_repair`, or `blocked`;
- concrete findings and evidence;
- blockers and the conditions that would clear them.

A `passed` verdict may retain non-blocking informational findings. A verdict on
a stale snapshot is not evidence; `needs_repair` or `blocked` remains open until
the workflow owner maps the finding to repair and records a fresh verdict.
Architect, adversarial QA, and integration reviewers may bind only the
acceptance IDs they actually inspected. The terminal critic must bind every
current acceptance ID and the SHA-256 of the cycle-free Completion Evidence
Candidate it reviewed. That projection excludes the terminal gate, final
ledger-tail field, and finalization timestamp to avoid causal self-reference,
but retains all substantive completion claims, non-terminal gates, review
hashes, blockers, authority, and release evidence. The final receipt records a
later completion timestamp. The causal order is prerequisite review and
candidate evidence observation, then candidate completion, then terminal
review, then final completion; completion and read-only validation both fail
closed on a reversed timestamp.

### Checkpoint

Owned only by Quant Goal when a durable Goal exists.

Include:

- Goal and acceptance revision;
- acceptance criterion or milestone advanced;
- change, result, or decision;
- direct evidence and fresh Review Verdict references;
- blocker or unverified item;
- semantic state and next concrete action;
- authority state only for an action that is actually pending.

Record meaningful progress, not every command, test start, or subagent message.
Implementation, test completion, build, preview, commit, deployment,
publication, and public readback remain distinct facts.

When work is expected to stop before completion, bind a Continuation Capsule
containing the current revisions, workspace, story and worker state, fresh and
stale evidence, blocker, pending authority boundary, actions not to repeat, and
next action. The capsule does not reactivate any skill.

### Steering Record

A Steering Record is an optional contract for a durable Goal revision. Use it
only when the operation label improves recovery or auditability; a short
host-only Goal may revise acceptance in ordinary language. The structured
revision form is an optional `steering` array whose entries contain only
`op`, `source_ids`, and `target_ids`:

- `clarify` identifies acceptance whose wording was clarified;
- `add` maps newly introduced target IDs;
- `retire` identifies source IDs removed from the resulting revision;
- `split` maps source IDs into narrower target IDs;
- `merge` maps multiple source IDs into the resulting target IDs;
- `reorder` identifies criteria whose sequence changed;
- `replace` maps source IDs to explicit replacements.

Record the revision-level rationale and the Stories, evidence, or Review
Verdicts made stale. The revision hash covers optional steering when present;
older revisions may omit it unchanged. A Steering Record describes a change
but is not authority to delete or weaken acceptance. If steering changes the
user-visible objective, authority envelope, or cost boundary, leave the current
Goal untouched and resolve it through a host lifecycle operation that is
actually exposed before creating a new Goal; a Steering Record cannot supersede
it.

### Continuation Projection

On an explicitly invoked resume, derive the read-only Continuation Projection
at `result.continuation` from verified host and ledger state, the latest
Continuation Capsule, worker state, and the actual deliverable. It reports
`checkpoint`, `next_action`, `stories_by_status`, `current_blockers`,
`workspace_drift`, `stale_review_roles`, `completion_ready`, `ledger`, and
`workspace`. Reconcile it with the latest user direction before acting.

The projection reports `authority.status` as `not_recorded`. It is derived
output, not persisted Goal state, and does not infer approval, reactivate a
skill, repeat a mutation, or authorize remote, destructive, secret-bearing,
provider, or paid work. A pending action must obtain authority from the current
request and canonical policy.

### Completion Receipt

Owned only by the currently invoked Quant Goal, or by the standalone
integration owner when no current Goal parent exists and the handoff needs an
equivalent final summary.

Include:

- final objective and acceptance revision;
- acceptance-to-evidence mapping;
- final frozen-snapshot identity;
- required fresh Review Verdicts;
- unresolved limitations and explicitly deferred work;
- local, remote, provider, and public states without conflation;
- ledger tail or artifact digest when a local ledger is active;
- terminal critic verdict for `strict` and legacy `assurance=release`
  compatibility.

For a ledger-backed Goal, append the Completion Receipt before marking the host
Goal complete. `completion-ready` must reconstruct the Completion Evidence
Candidate from the final receipt and match it to the current terminal verdict;
adding or changing any included evidence after review makes that verdict stale.
A receipt proves only the claims and authority scope it names.

## Review pipeline

For a structured Goal, record only reviewer roles selected by its assurance
policy. Completion still fails closed on any durable unresolved blocking
finding in the current plan and acceptance revision, including evidence
created by an older runtime under an unselected role.

### Light

The implementation owner performs the focused check, inspects the deliverable,
and self-reviews. No independent reviewer is required.

### Standard

Run exactly one normal review boundary:

1. The implementation owner completes the coherent change and project-native
   checks.
2. Exercise the matching direct evidence channel when the acceptance has an
   executable, rendered, generated, or published surface.
3. The implementation owner runs a changed-surface cleanup/hygiene pass and
   reruns affected checks.
4. Freeze the snapshot.
5. Commission one reviewer appropriate to the dominant risk: architecture,
   product/UI, data/calculation, automation, or release.
6. Return blockers to the implementation owner for repair.
7. Rerun only the checks and review portions made stale by the repair.

Cleanup is bounded to changed paths and directly affected surfaces. Inspect
them for dead code, duplication, masking fallbacks, needless abstraction,
violations of discovered contracts, and missing relevant tests; cleanup does
not authorize an unrelated refactor.

An explicitly invoked standalone Quant Developer coordinates this boundary.
When Quant Goal is the explicitly invoked current parent, Quant Goal
coordinates it. Do not add a second generic “review everything” pass.

In the structured ledger, `integration_review` is the stable Standard gate
identifier, not the reviewer's specialty. Select the human-readable specialty
from the dominant risk—architecture, product/UI, data/calculation, automation,
or release—and preserve it in the Review Verdict's purpose and inspected
surfaces. Gate identity determines required completion evidence; specialty
determines what the one reviewer is qualified and instructed to examine.

If more than one independent high-risk surface requires its own reviewer, raise
the workflow to `strict` instead of multiplying Standard reviewers.

### Strict review and release delivery

Use one layered validation boundary:

1. The implementation owner completes applicable verification and cleanup.
2. Exercise applicable real-surface success, failure, and boundary behavior.
3. Rerun verification so the evidence covers the cleaned result.
4. Freeze the snapshot.
5. Run an Architect review and adversarial QA against the same snapshot.
   They may run in parallel only when independent and neither changes the
   product.
6. Join both verdicts. Return blockers to the implementation owner and repair.
7. Create a new snapshot and rerun every check or review invalidated by the
   repair.
8. After all required acceptance criteria have fresh evidence, run one
   terminal Critic for the Goal terminus or standalone completion handoff.

The roles are deliberately non-overlapping:

- **Architect** checks boundaries, design, data/control flow, product
  contracts, operational risk, and maintainability.
- **Adversarial QA** exercises the real surface, failure paths, boundary
  inputs, and regressions rather than rereading architecture.
- **Terminal Critic** checks acceptance coverage, evidence freshness,
  unresolved blockers, deferrals, and authority. It does not repeat the code
  review.

In standalone Strict work, and in the legacy `assurance=release` compatibility
path, the explicitly invoked Quant Developer coordinates that final handoff
without creating Goal or ledger state.

Run the terminal Critic once per Goal completion attempt, not per story.
Validation-coupled stories should share the final layered boundary
rather than each repeating the full stack.

The release delivery overlay adds only the separately authorized remote
checkpoints and final observable readback. It uses the selected risk-assurance
review boundary and does not add or imply another local review stack.

## Frozen snapshots, staleness, and repair

A frozen snapshot is the exact result reviewed by independent lanes. Identify
it with the strongest natural identity available:

- workspace and target identity;
- base revision or baseline when one exists;
- exact changed-file or artifact set;
- content digests for strict or ledger-backed evidence;
- generated artifact identity and relevant configuration;
- verification commands, results, and observation time.

A commit is useful but not required. Dirty worktrees, non-Git directories,
documents, notebooks, and generated artifacts may use a bounded file/artifact
manifest instead.

A Review Verdict becomes stale when a later change can affect its conclusion,
including:

- a reviewed source, configuration, dependency, lockfile, schema, generated
  artifact, or deliverable changes;
- acceptance, a protected contract, release target, or relevant authority
  boundary changes;
- the baseline or external state used by the verdict materially drifts;
- a repair changes a failure path or consumer surface covered by the review.

Formatting or metadata changes outside the reviewed contract do not require a
full rerun of every lane. In the structured ledger, any whole-workspace identity
change still makes the old receipt non-current. If the exact recorded review
scope digest remains unchanged, record a new snapshot-bound carry-forward
verdict that cites the latest relevant passed receipt. This is an explicit
revalidation, not silent reuse. A changed scope requires a real rerun; an
intervening `needs_repair` or `blocked` verdict must be resolved and cannot be
bypassed by carrying an older pass. For this rule, a verdict is relevant when
it has the same role, plan revision, and acceptance revision and its acceptance
IDs overlap; a newer overlapping non-pass blocks carry-forward even when one
review used a subset or superset. The carried source itself must still have the
same acceptance IDs and exact review-scope binding. The terminal critic is
never carried forward. Declared ignored paths are rehashed when current
verdicts are selected, so an ignored deliverable cannot retain a stale pass
merely because the Git workspace identity did not change.

Repair rules:

1. Convert every blocking finding into bounded work owned by the assigned
   implementation or repair owner.
2. Preserve the old verdict and evidence; do not rewrite history.
3. After repair, create a new frozen-snapshot identity.
4. Rerun cleanup and project checks whose assumptions changed.
5. Rerun each independent lane whose reviewed surface changed. Do not rerun an
   unaffected lane merely to increase the review count.
6. Run the terminal Critic only after every required verdict is fresh.

Every open or resolved blocking finding carries at least one concrete evidence
reference. Because one role has one current verdict, a passed repair verdict
must cover the union of acceptance IDs attached to that role's outstanding
findings and explicitly resolve every open finding ID as blocking; a partial
pass or severity downgrade cannot hide the remainder.

Timeout alone is not worker failure or stale evidence. Inspect the worker or
artifact state before cancelling or reassigning.

## Goal lifecycle and local evidence ledger

The host Goal is canonical for lifecycle. When available, it owns creation and
only the lifecycle states and operations the current host actually exposes.
Never manufacture an unsupported host state in a local file.

Outside an explicitly selected structured compatibility or machine-audit path,
no local ledger is created automatically. A `strict` label, long duration,
release delivery, task complexity, or repeated failure alone is not a selection.
Within a selected path, a local ledger is required only when:

- an existing Goal already depends on that exact ledger contract;
- the user explicitly requests machine-audited or co-located portable evidence;
- the user explicitly requests recovery or resumable state through that exact
  contract; or
- a preserved legacy manifest contract already requires it.

A release delivery overlay alone does not require a ledger. The legacy
manifest-bound `assurance=release` compatibility path retains its existing
ledger requirement.

The ledger is canonical only for append-only evidence history: acceptance
revisions, checkpoints, story handoffs, reviewer verdicts, blocker
classification, redacted authority evidence or checkpoint references, and
completion receipts. It never stores approval itself and does not override the
host lifecycle.

Recommended meaningful event kinds are:

- `goal_bound`;
- `plan_bound`;
- `acceptance_revised`;
- optional typed steering bound to its acceptance revision;
- `checkpoint_recorded`;
- `continuation_capsule_recorded`;
- `story_issued`, `story_returned`, and `story_accepted`;
- `review_recorded`;
- `blocker_classified`;
- `completion_ready`;
- `host_state_observed`;
- `goal_cancelled` or `goal_superseded`.

Use a hash-linked append-only stream when the available runtime supports it.
Do not create an event for every command. On a later explicitly invoked resume,
reconcile the host Goal, latest accepted ledger event, current Continuation
Capsule, actual deliverable, in-flight worker state, and latest user direction
before repeating work, then derive the `result.continuation` projection with
`authority.status` `not_recorded` described above. Active host state or a
pending capsule alone does not activate a Quant skill.

If host and ledger disagree, report the divergence and repair the evidence
binding; never let the ledger silently change host state. If the required
ledger writer is unavailable or damaged, safe local work may continue when
authority and scope permit, but any completion claim that selected ledger-backed
recovery, portability, machine audit, or preserved strict/release proof remains
`unverified` until the ledger is repaired or the user explicitly changes the
acceptance boundary.

The legacy manifest-bound Goal runtime remains an optional strict compatibility
extension. Its immutable intent, workspace-drift, story, receipt v3, and hash
contracts apply only when explicitly selected or already in use. Do not force
that extension merely because the lightweight host companion ledger is active.

The bundled companion implementation is
`<quant-shared-root>/scripts/goal_ledger.py`. Its default state root is
`$CODEX_HOME/state/quant-goals/<project-fingerprint>/<goal-id>`. A
project-local state directory is allowed only after the user explicitly
selects a co-located evidence archive and the directory is already ignored by
Git. That option supports append-only evidence packaging, manual machine audit,
and crash recovery only while the project and state retain the same verified
binding. The state root is bound to realpath, device, and inode; the project is
bound to its resolved identity. Renaming, copying, moving to another path or
machine, or resuming against a copied workspace is intentionally unsupported
and fails closed. Here “portability” means preserving or transporting an
evidence package for manual audit, not relocated execution. Resumable relocation
would require a separate explicit rebind protocol and is outside this runtime.
The runtime accepts complex acceptance, checkpoint, story, review, and host
observations as JSON artifact paths; it does not encode free-form structured
payloads in shell arguments.

`completion-ready` verifies the current acceptance mapping, stories, blockers,
Review Verdicts, evidence receipt v3, plan and acceptance revisions, workspace
identity, and the terminal-bound Completion Evidence Candidate digest. It
records a receipt and event but never changes the host Goal. Quant Goal
completes the host Goal separately and then records the observed host result.
Resume reports divergence rather than making either side overwrite the other.

## Parallelism and integration

Use specialists or workers only when the work is independent, bounded, and
worth the coordination cost.

The full Team Run Packet, role router, context sharing, evidence-channel,
worker recovery, integration, and continuation protocol is canonical in
`references/agent-orchestration.md`; this section records only the invariants
required by the Goal and review contracts.

Use the hash-bound `agent-team-execution` capability only when structured
host-team proof is selected. Keep legacy `multi-agent-write` for its existing
single-root Story runtime, and do not record the same handoff through both.

- Read-only research and reviews may run in parallel.
- Multiple concurrent write workers require isolated worktrees and one named
  integration owner. Otherwise keep one write owner active in a workspace at a
  time, even when proposed scopes appear disjoint.
- Each isolated writer receives a Story Envelope with disjoint targets or an
  explicit sequencing dependency.
- Overlapping write scopes remain under one owner and are sequenced rather
  than parallelized.
- Workers return Delivery Evidence and never mutate Goal state.
- The integration owner inspects results and resolves conflicts.
- Validation-coupled stories join in the canonical workspace before the
  applicable independent review boundary.
- Parallel work does not raise assurance by itself.
- Do not create worktrees merely for read-only specialists or a single writer;
  use them when concurrent writes are worth their coordination cost.

The companion ledger itself is deliberately single-root and permits only one
active write Story for its bound workspace. When isolated worktrees run
concurrently, the host and named integration owner coordinate their logical
Story Envelopes; workers do not point one ledger at multiple roots. The
integration owner brings accepted results into the canonical workspace and
records or accepts their structured evidence serially. This preserves parallel
implementation without inventing multi-root authority or weakening workspace
binding.

Do not introduce tmux, mailboxes, heartbeats, global hooks, automatic commits,
merges, or cherry-picks as a generic requirement. Use a persistent worker
runtime only when the selected host and task actually need it, and never let
that runtime become a second Goal owner.

## Authority

The detailed local source-control, remote source-control, provider,
destructive, secret-bearing, and paid-action policy lives only in
`core/authority.md`. Paid data is permanently ineligible, not an approval
boundary or fallback. This workflow preserves those boundaries and records
relevant decisions, but never grants them.
