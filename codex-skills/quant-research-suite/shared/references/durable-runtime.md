# Durable Goal runtimes

## Contents

- [Host-aligned evidence companion](#host-aligned-evidence-companion)
- [Legacy compatibility contract](#legacy-compatibility-contract)
- [State boundary](#state-boundary)

The host application's Goal is always canonical for lifecycle. The suite
contains two optional local runtimes with different contracts. Load this
reference only through the explicit compatibility, machine-audit, or exact
high-risk-recovery routes in `../core/context-routing.md`; `strict`,
long-running, release, complexity, or failure alone never selects either
runtime.

1. `goal_ledger.py` is the host-aligned evidence companion after a user or
   existing contract explicitly selects machine audit, exact recovery,
   co-located evidence portability, or preserved ledger compatibility. Within
   that selected path it supports `strict`, clearly long-running, and legacy
   `assurance=release` Goals. A generic label or release overlay alone does not
   require it. The companion is manifest-free by default, supports Git and
   non-Git work, accepts revisions, and never changes host state.
2. `goal_runtime.py` is the preserved legacy manifest-bound runtime. Its
   schema-v2 state, immutable intent, single write owner, story receipts, and
   receipt-v3 completion behavior remain compatibility contracts.

Planning, ordinary implementation, and native host-only Goals do not create
either state, even when they are long-running or high consequence. If the shared
runtime is unavailable, generic planning and local implementation continue;
only the explicitly selected structured proof is unavailable.

Host and local state persist evidence, not skill activation. A later turn
enters the Quant Goal workflow only when the user explicitly invokes
`$quant-goal` again for that request. Neither runtime installs a global Stop
hook, resumes a public skill automatically, or treats a saved Goal, checkpoint,
ledger, receipt, worker message, or Continuation Capsule as invocation
authority.

Commands below use `<quant-shared-root>` as defined by
`../core/context-routing.md#shared-root-resolution`. Resolve it from the active
public skill location and verify the named script exists; do not infer it from
the current working directory.

## Host-aligned evidence companion

By default, `goal_ledger.py` stores state outside the project:

```text
$CODEX_HOME/state/quant-goals/<project-fingerprint>/<goal-id>/
  goal-ledger-state.json
  goal-ledger.jsonl
  plans/
  stories/
  reviews/
  receipts/
```

The user may explicitly select a project-local evidence archive only when it is
already ignored by Git. It supports append-only packaging, manual machine audit,
and crash recovery under the same verified project/state binding. It does not
support rename, copy, cross-path, or cross-machine resume: project and state
realpath identity, plus state device and inode, are intentionally fail-closed.
Transporting that directory is evidence portability for manual inspection, not
relocated execution. A future relocation feature would need an explicit rebind
protocol. Non-Git projects use a realpath-based project fingerprint and keep
default state outside the project.

After the companion has been explicitly selected, initialize from an acceptance
JSON artifact and, for its `strict` or legacy `assurance=release` mode, an
immutable reviewed Plan Packet:

```bash
python3 <quant-shared-root>/scripts/goal_ledger.py init \
  --root <project-root> \
  --goal-id <local-goal-id> \
  --host-goal-id <host-goal-id> \
  --project-id <project-id> \
  --objective <objective> \
  --acceptance <acceptance.json> \
  --assurance <level> \
  [--delivery <local|release>] \
  --activation-reason <reason> \
  [--plan <reviewed-plan>] \
  [--manifest <existing-schema-v2-manifest>] \
  [--require-capability remote-release]
```

The command reports the resolved state directory. Subsequent commands take
`--state-dir` explicitly:

Initialization accepts only a non-terminal observed host state. If the host
Goal is already `completed`, `cancelled`, or `superseded`, `init` rejects the
request before creating the state directory or any ledger artifact. Continue
with a new host Goal generation, or use a separately designed explicit import
workflow that preserves the terminal Goal history; ordinary initialization
never reopens a terminal Goal.

For current release delivery, use `--delivery release` together with the
`remote-release` capability. This adds the release gate while preserving the
selected `light`, `standard`, or `strict` risk assurance. Omitting `--delivery`
keeps older Goal state readable by inferring the axis from its assurance and
capabilities.

```bash
python3 <quant-shared-root>/scripts/goal_ledger.py resume ...
python3 <quant-shared-root>/scripts/goal_ledger.py revise-acceptance \
  --revision <revision.json> [--plan <revised-plan>]
python3 <quant-shared-root>/scripts/goal_ledger.py checkpoint \
  --checkpoint <checkpoint.json>
python3 <quant-shared-root>/scripts/goal_ledger.py continuation-capsule \
  --capsule <continuation-capsule.json>
python3 <quant-shared-root>/scripts/goal_ledger.py story-issue \
  --envelope <story-envelope.json>
python3 <quant-shared-root>/scripts/goal_ledger.py story-return \
  --receipt <story-receipt.json>
python3 <quant-shared-root>/scripts/goal_ledger.py story-accept \
  --story-id <story-id>
# Terminal critic only; omit --evidence-candidate for other reviewers.
python3 <quant-shared-root>/scripts/goal_ledger.py review-record \
  --review <review-receipt.json> \
  --evidence-candidate <evidence-receipt-v3-candidate.json>
python3 <quant-shared-root>/scripts/goal_ledger.py completion-ready \
  --receipt <evidence-receipt-v3.json>
python3 <quant-shared-root>/scripts/goal_ledger.py observe-host \
  --observation <host-observation.json>
```

On resume, expose a read-only Continuation Projection in
`result.continuation`, derived from verified state. It is not persisted in the
state schema. It contains `checkpoint`, `next_action`, `stories_by_status`,
`current_blockers`, `workspace_drift`, `stale_review_roles`,
`completion_ready`, `ledger`, `workspace`, and `authority`. Existing top-level
resume result keys remain unchanged. The nested `authority.status` is always
`not_recorded`: neither the projection nor stored state persists approval,
broadens scope, or authorizes a mutation. The currently invoked workflow must
reconcile it with host state, the actual workspace, and latest user direction.

Typed steering is optional. A revision artifact may add:

```json
{
  "steering": [
    {
      "op": "clarify|add|retire|split|merge|reorder|replace",
      "source_ids": [],
      "target_ids": []
    }
  ]
}
```

When present, the companion persists the array in the acceptance revision and
includes it in that revision's hash. Existing artifacts and revisions may omit
it unchanged. The operation and IDs describe the accepted revision; they do
not grant authority or by themselves justify weaker acceptance. A change to
objective, authority, or cost is incompatible with the current active Goal.
Preserve the ledger history, leave the host Goal untouched, and require
resolution through a host lifecycle operation that is actually exposed before
creating a new Goal; the local runtime cannot supersede it.

When the receipt selects structured `agent-team-execution` proof, the same
`completion-ready` call also supplies the packet, every delivery, integration
receipt, artifact and canonical workspace roots, the preserved issuance
baseline root, and one retained `assignment-id=worker-root` mapping per ready
delivery. The complete invocation and live-handoff constraints are canonical
in `capabilities/agent-team-execution.md`.

The companion records only meaningful events. Every event is hash-linked,
workspace-bound, and crash-journalled. Plan and acceptance revisions remain
append-only. Story and Review Verdict artifacts are immutable; a repair gets a
new returned receipt or review ID. Each Story is bound to the plan revision,
acceptance revision, acceptance IDs, and issued write/protected scopes.
Acceptance revision supersedes open or returned Stories from the prior
revision rather than accepting stale work.

The host ledger uses workspace snapshot version 2. Non-Git identities include
regular directory entries, symlink identity, and file permission mode so a
behavior-changing executable-bit or directory-link change invalidates stale
proof. Git snapshots additionally include the active Story scopes so an
ignored-but-declared deliverable remains part of the workspace identity. The
runtime rejects project-scope symlinks that could redirect a bounded write
outside the project. The legacy runtime continues to use the original
version-1 snapshot shape so existing Goal state remains byte-compatible on
resume.

Review Verdicts bind the current plan revision, acceptance revision, acceptance
ID subset, workspace hash, exact portable review-scope patterns, and their
current digest. The runtime rehashes that scope whenever it selects a current
verdict, including ignored-but-declared paths. A whole-workspace change may use
a new carry-forward receipt only when the latest relevant verdict passed and
the exact scope digest is unchanged. Scope changes and intervening blocking
verdicts require fresh review; the terminal critic cannot carry forward. The
terminal critic alone must cover every current acceptance ID and must receive
`--evidence-candidate`. The runtime
canonicalizes that receipt-v3 draft into a cycle-free Completion Evidence
Candidate: it excludes only the terminal gate, final ledger-tail field, and
finalization timestamp while retaining objective, scope,
plan/acceptance/workspace bindings, acceptance claims, every non-terminal gate,
current non-terminal review hashes, blockers, cost authority, and release
evidence. The final receipt timestamp may therefore follow the terminal review;
the runtime requires every candidate evidence observation and prerequisite
Review Verdict to precede the candidate timestamp, the terminal verdict to
follow both, and every current verdict to precede the final receipt timestamp.
Candidate observations include gate `checked_at`, zero-cost authority
`evidence_checked_at`, and schema-defined data identity timestamps retained in
the reviewed receipt.
The terminal Review Verdict binds the candidate SHA-256. Evidence receipt v3
keeps its existing schema; a host-ledger
proof uses the extensible evidence `extensions.goal_ledger` object to bind every
required gate to that same snapshot and each independent-review gate to its
stored Review Verdict.

`role` is the stable assurance-gate identity. The optional
`reviewer_specialty` is a separate portable ID such as `implementation`,
`data_quality`, or `release_verification`; it records the reviewer's actual
discipline without creating or satisfying another gate. When present it is
receipt-hashed, copied into the ledger review projection, checked during
artifact verification, and required to match across carry-forward. Existing
schema-v1 Review Verdicts may omit it unchanged. A specialty may not reuse a
gate-role name.

`completion-ready` requires current acceptance evidence, no open or
review-blocked story, no unresolved required blocker, all assurance-level
reviews on the same current snapshot, and a valid receipt v3. For Strict and
legacy `assurance=release` Goals it rebuilds the same candidate projection from
the final receipt and rejects any digest that differs from the current terminal
verdict. It writes the receipt and `completion_ready` event only. Quant Goal
separately completes the host Goal and then records the actual observation.
Resume reports host/ledger divergence and never repeats a host mutation
automatically.

Immutable artifacts are written before their binding event. If interruption
leaves an unbound artifact, an identical retry adopts it; a different retry
moves the prior bytes into the internal `orphaned/` evidence archive before
writing the current artifact. This preserves crash evidence without allowing a
stale orphan to block safe retry. The resolved state root is identity-bound and
post-initialization symlink substitution is rejected.

State, receipts, and observations never store or grant provider, secret,
destructive, remote, or paid authority. Paid data remains permanently
ineligible and cannot be introduced through a Goal revision, receipt, or
compatibility manifest.

The host-aligned companion is single-root and permits one active write Story in
its bound workspace. Concurrent writers may use isolated worktrees only under a
host-level integration owner and only when separate local-SCM branch/worktree
authority is already recorded. Without that authority, use one writer or
serialize the work in the current workspace. Workers return Delivery Evidence
without sharing or retargeting this ledger; the integration owner records
accepted integrated work serially in the canonical workspace.

## Legacy compatibility contract

This section describes the preserved runtime and does not redefine the host
Goal lifecycle. A manifest-free local Goal supports read-only research only.
Bind a validated schema-v2 project manifest before this runtime performs
project mutation or uses a write story; this makes protected contracts and
capability evidence reviewable without generating manifests for unrelated
projects.

## State boundary

Store runtime files outside the project or in an already-gitignored directory:

```text
<state-dir>/
  goal-state.json
  ledger.jsonl
  stories/
  receipts/
```

The state is a cache of intent and evidence. It never grants repository,
provider, release, destructive, secret, or paid authority.

`stories/` and `receipts/` must be real directories directly inside the
resolved state directory. The runtime rejects symbolic-link parents and
symbolic-link artifacts instead of following them outside the state boundary.
The fixed lock, state, ledger, and pending-transaction files are likewise
required to be regular files and are opened without following their final
symlink component.

Within this compatibility runtime, objective and acceptance are immutable after
initialization because they are hash-bound. Correct work that still fits the
bound intent through stories and checkpoints. If the host Goal accepts a
revision that changes this local intent, retain the old ledger and initialize a
new local runtime binding instead of rewriting history.

Initialize:

```bash
python3 <quant-shared-root>/scripts/goal_runtime.py init \
  --root <project-root> \
  --state-dir <state-dir> \
  --goal-id <id> \
  --project-id <project-id> \
  --objective <exact-objective> \
  --acceptance <id=text> \
  --assurance <level> \
  [--plan <approved-plan>] \
  [--manifest <manifest>] \
  [--require-capability <id>]
```

Resume before work and after interruption:

```bash
python3 <quant-shared-root>/scripts/goal_runtime.py resume \
  --root <project-root> \
  --state-dir <state-dir>
```

Each event/state update is journalled before the append. Resume may finish an
already journalled transaction or repair only an exact canonical prefix of that
journalled event left at the physical ledger tail. It does not truncate an
unrelated, earlier, or unbound corrupt tail. Read-only verification never
performs this recovery. A valid but conflicting no-newline event is also
rejected without first normalizing or otherwise mutating the ledger.

- `pass`: project binding, plan/manifest, ledger, and workspace match.
- `review_required`: drift is confined to the sole open write story; the primary
  owner must inspect it before checkpointing or acceptance.
- `blocked`: identity, ledger, protected/out-of-scope state, or ownership does
  not match.

After an explicit recovery review:

```bash
python3 <quant-shared-root>/scripts/goal_runtime.py checkpoint \
  --root <project-root> \
  --state-dir <state-dir> \
  --kind recovery-review \
  --summary "Inspected and accepted the bounded interrupted state"
```

Checkpoint cannot override project, plan, manifest, ledger, protected-path, or
out-of-scope drift.

## Story handoff

Use subagents only when independent work improves speed or audit quality. Issue
a story envelope, then accept the worker receipt only after primary integration
review:

```bash
python3 <quant-shared-root>/scripts/goal_runtime.py story-issue \
  --root <project-root> \
  --state-dir <state-dir> \
  --envelope <story-envelope.json>

python3 <quant-shared-root>/scripts/goal_runtime.py story-accept \
  --root <project-root> \
  --state-dir <state-dir> \
  --receipt <story-receipt.json>
```

One overlapping write owner is allowed. Advisory and read-only specialists
cannot claim workspace mutation. Workers return `ready_for_review`, never
overall completion. Envelopes and receipts have `external_effects=none` and
`cost_class=no_billable_action`.

A `mode=write` story additionally requires the Goal to bind a currently valid
schema-v2 project manifest whose effective capabilities include
`repo-mutation`. `multi-agent-write` remains a ledger-derived runtime fact; it
is not persisted in the project manifest and grants no authority by itself.

## Legacy local runtime completion

Validate the final capability receipt first, including its goal binding. Then:

```bash
python3 <quant-shared-root>/scripts/goal_runtime.py complete \
  --root <project-root> \
  --state-dir <state-dir> \
  --receipt <evidence-receipt-v3.json>
```

This command marks only the preserved local `goal_runtime.py` state complete.
It does not complete, mutate, or record completion of the canonical host Goal.
Its structured result therefore reports
`completion_scope=legacy_runtime_only` and
`host_goal_completion_recorded=false` while retaining the legacy local
`status=complete` compatibility value.

Local runtime completion requires no open stories, exact
project/objective/ledger binding, and all goal acceptance IDs. The runtime does
not commit, push, merge, deploy, schedule, migrate, publish, browse, call a
provider, or mutate host lifecycle state.

The final `status_changed` event binds `final_receipt_sha256`,
`pre_completion_ledger_tail_sha256`, and `goal_intent_sha256`. The legacy
`receipt_sha256` payload key is retained as an identical compatibility alias.
Later verification checks the stored final receipt against both receipt hash
fields and checks that its goal binding names the pre-completion ledger tail.
New events also record `completion_scope=legacy_runtime_only` and
`host_goal_completion_recorded=false`; their summary explicitly states that the
host Goal was not changed.
