# Runtime capability: agent-team execution

This is an optional internal execution protocol, not a fourth public skill and
not a persistent project property. It gives an explicitly invoked
`$quant-developer` or `$quant-goal` a machine-checkable handoff when multiple
host-native agents can perform genuinely independent work. Ordinary subagent
use does not activate it and team use alone does not raise assurance.

Use the host's subagent mechanism. Do not add tmux workers, a mailbox,
heartbeats, a provider runtime, or another scheduler. A timeout is not proof of
failure: inspect the host worker state before retrying or reassigning work.

## Ownership and authority

- One workflow owner creates the Team Run Packet.
- One named integration owner serially accepts and integrates worker results.
- Workers receive bounded assignments and return Delivery Receipts. They do
  not alter the packet, Goal state, acceptance, authority, or cost scope.
- A Goal-owned team remains subordinate to Quant Goal. A standalone team
  remains subordinate to Quant Developer.
- Structured artifacts describe and prove work; they never authorize commit,
  merge, cherry-pick, push, deploy, publication, destructive action, secret
  access, or paid action.
- Existing Goal state v2, Story Envelope v1, and Story Receipt v1 contracts are
  unchanged. Team assignments are not Goal Stories and must not be written into
  the legacy single-write-story state machine.

## Safe concurrency

Model assignments as a directed acyclic graph. Every dependency must exist,
the integration order must contain every assignment exactly once, and
dependencies must precede their consumers.

- Read-only workers may run concurrently.
- Same-workspace writers must be dependency ordered; only one may write at a
  time. The first same-workspace writer uses a hash-bound `packet` baseline
  reference; each later writer uses an `assignment_final` reference to its
  immediate write predecessor. Delivery resolves that reference to actual v2
  snapshot bytes, so an immutable packet never predicts a future hash.
- Isolated writers may run concurrently only with disjoint write scopes.
- Ambiguous wildcard overlap fails closed.
- Every changed path must be inside the assignment's write scope and outside
  its protected scope.
- The integration owner alone applies results to the canonical workspace and
  runs the joined verification.

## Proof chain

The optional structured path is:

```text
Team Run Packet
→ worker Delivery Receipts
→ Team Integration Receipt
→ existing snapshot-bound review and completion workflow
```

`team-run-packet.schema.json` v2 binds the canonical JSON SHA-256 of the parent
objective, project, baseline, risk assurance (`light`, `standard`, or `strict`),
delivery (`local` or `release`), assignment DAG, acceptance IDs, write and
protected scopes, expected check and evidence IDs, each assigned workspace
identity and baseline reference, stop conditions, and integration order. Risk
and delivery remain independent, so `standard` plus `release` is valid. The
runtime continues to read schema-v1 packets; v1 `assurance=release` means the
explicit legacy Strict-plus-release compatibility path, while other v1
assurance values imply local delivery. Compute
`objective_sha256` with the shared `goal_primitives.digest(objective_string)`
canonical-JSON primitive, not a raw-text hash. The packet includes the full
hash-verified issuance snapshot and a version-2 snapshot policy containing one optional
`excluded_root` for colocated Goal/team proof state plus the union of protected
patterns. Its content hash is the immutable authority-free assignment
boundary. POSIX-relative paths are the portable protocol form; Windows drive,
UNC, and backslash paths fail closed.

Packet assignment objectives, non-goals, stop conditions, and activation prose
pass the shared refusal-aware paid-data guard. Delivery and Integration Receipt
proof summaries pass the same guard after hashing, so resealing cannot turn a
paid-data instruction or success claim into valid evidence. Explicit refusals
such as `Do not use paid data` remain valid.

In a Git workspace, a selected `excluded_root` must be Git-ignored; tracked or
visible state cannot be hidden from the snapshot. In a non-Git workspace the
same root is excluded directly by the shared snapshot primitive.

Packet issuance can be checked against live roots before workers start:

```text
python3 shared/scripts/team_protocol.py packet --packet <packet.json> --project-root <project-root> --workspace-root <issuance-workspace-root>
```

Assignments that must be proven together share a `validation_group`. A ready
Team Integration Receipt must accept every member of each such group and bind
their joined result to its one canonical frozen snapshot. A worker snapshot is
never sufficient for a validation-coupled claim.

`worker-delivery-receipt.schema.json` binds one worker result to the packet,
project, assignment, full baseline snapshot and full final snapshot. The
delivery command requires `--worker-root` for a ready result, recomputes its
workspace binding and final v2 snapshot, and recomputes the inline
baseline-to-final path delta. A result is
`ready_for_integration` only when:

- every assigned acceptance ID has passed evidence;
- every expected check and evidence ID is present and passed;
- cleanup passed and no blocker or unverified item remains;
- changed paths obey the assignment boundary; and
- every returned patch, bundle, report, or artifact hash is verified against
  actual bytes under an explicit artifact root.

UTF-8 artifact bytes receive the central literal-secret scan. Binary and commit
bundle artifacts are explicitly unscannable and require passed external
secret-scan evidence that references both the artifact and a separately
validated text report.

`team-integration-receipt.schema.json` echoes the named integration owner and
binds the exact Delivery Receipt hashes, their dispositions, integrated paths,
joined evidence, acceptance coverage, conflict state, and pre/post canonical
snapshot. Its pre-snapshot must equal the packet baseline. A ready receipt is
valid only when `--workspace-root` independently recomputes the same project
binding and post-snapshot with workspace snapshot version 2, then recomputes
the full baseline-to-post delta and requires exact equality with canonical
changed paths. It is
`ready_for_review`, not complete. Independent review still reads the final
integrated frozen snapshot under the assurance matrix. A blocked or failed
integration names at least one concrete blocker; a ready integration retains
none. Every accepted result and required acceptance claim cites passed
evidence anchored to the post-integration frozen-snapshot hash.

Validate artifacts with:

```text
python3 shared/scripts/team_protocol.py packet --packet <packet.json> --project-root <project-root> --workspace-root <issuance-root>
python3 shared/scripts/team_protocol.py packet --packet <packet.json> --structural-only
python3 shared/scripts/team_protocol.py delivery --packet <packet.json> --delivery <delivery.json> --artifact-root <artifact-root> --worker-root <worker-root>
python3 shared/scripts/team_protocol.py integration --packet <packet.json> --delivery <delivery.json> --integration <integration.json> --artifact-root <artifact-root> --workspace-root <canonical-root>
```

Ready delivery validation deliberately fails without both `--artifact-root`
and `--worker-root`; ready integration fails without `--artifact-root` and
`--workspace-root`. Blocked or failed deliveries may be structurally inspected
without those live roots.

For a completion-eligible typed handoff, retain the issuance baseline and every
ready worker root until final integration validation, then require the live
handoff lane:

```text
python3 shared/scripts/team_protocol.py integration \
  --packet <packet.json> \
  --delivery <delivery.json> \
  --integration <integration.json> \
  --artifact-root <artifact-root> \
  --workspace-root <canonical-post-root> \
  --project-root <canonical-project-root> \
  --baseline-root <preserved-issuance-root> \
  --worker-root <assignment-id>=<worker-root> \
  --require-live-handoff
```

The mapping must contain exactly one root for every ready Delivery Receipt.
This lane recomputes the packet project and issuance baseline, each ready
worker's workspace binding and final snapshot, and the canonical post-snapshot.
When canonical paths changed, the preserved issuance root and canonical
post-root must be distinct physical directories. The default API and CLI
integration path remains structural-plus-canonical validation for compatibility;
it is not a substitute for the live handoff lane when typed completion selects
this capability.

Because one shared directory retains only its latest bytes, multiple
`same_workspace_sequential_write` deliveries cannot all be re-read at their
individual final snapshots during completion. The structural compatibility
lane still validates their dependency and receipt chain, but a
completion-eligible live handoff must combine them into one compound
shared-workspace assignment or give each writer an isolated retained root.

Protocol timestamps are causal: packet creation is no later than delivery,
dependency delivery is no later than its consumer, and every delivery is no
later than integration. Packet, delivery, integration, and completion times
must also be no more than five minutes ahead of the validator clock. The
bounded allowance tolerates ordinary clock skew without allowing a
future-dated bundle to manufacture freshness. JSON proof inputs reject
duplicate object keys before canonical hashing.

These local hashes prove internal consistency and preserved-byte continuity;
they are not an external timestamp, signature, or independent attestation. A
trusted local owner who can replace every artifact can author a new coherent
history. Host Goal observations, an already-preserved ledger chain, and remote
provider evidence add independent anchors when that stronger claim is part of
acceptance.

Evidence gate: `team_integration`. The typed Team Integration Receipt already
validates every worker Delivery Receipt, artifact, cleanup result, and joined
snapshot, so this capability does not duplicate that proof under the legacy
`handoff_review` gate. The legacy `multi-agent-write` capability retains its
own handoff-review gate.
