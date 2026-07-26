# Goal and Specialist Policy

## Shape, Act, Prove

Use a small, explicit lifecycle:

1. **Shape** — objective, context, constraints, plan, acceptance.
2. **Act** — bounded implementation against protected contracts.
3. **Prove** — deterministic tests, skeptical audits, release/public evidence.

Persistence means continuing through justified repair cycles, not ignoring approval gates or expanding scope.

## Skill routing boundary

- **Quant Plan** owns read-only audit, research, alternatives, and the proposed
  plan; it does not mutate or declare completion.
- **Quant Goal** is the sole owner of objective scope, approval state,
  checkpoints, reopen/repair decisions, and final completion.
- **Quant Developer** owns implementation and verification evidence for one
  bounded project/story; when called by Quant Goal it returns evidence and must
  not mark the parent goal complete.
- Quant Developer may run alone for a direct bounded build request. Under Quant
  Goal its default stop is local-preview/story evidence; remote release is a
  separately authorized release story.

## Roles

### Primary owner

- owns user intent, scope, plan, integration, and final evidence;
- reads relevant source and every specialist result;
- is the only authority that can declare a gate passed;
- must not accept “done” without inspecting artifacts.

### Implementation owner

- one writer for overlapping files and product surfaces;
- integrates frontend, backend, worker, automation, and release contracts;
- preserves unrelated changes;
- reruns tests after integrating review fixes.

### Optional specialists

- repository/contract auditor;
- external researcher;
- plan critic;
- UX/chart reviewer;
- backend/input-binding reviewer;
- automation/freshness reviewer;
- release/public-readback verifier.

Specialists are read-only by default.

## When to use specialists

Use them only when:

- the task has independent research or audit tracks;
- parallel work materially reduces latency or increases coverage;
- each task is bounded with clear inputs and output evidence;
- there is no conflicting write ownership;
- the primary owner has time to review and integrate the results.

Do not use them for:

- trivial tasks;
- unclear work that needs the primary owner to discover scope;
- multiple edits to the same file or UI;
- duplicated “review everything” prompts;
- credential, billing, destructive, merge, or release authority.

## Safe parallel patterns

Good:

- one specialist audits repository contracts while another researches official sources;
- separate specialists inspect different repositories read-only;
- a UX reviewer and backend contract reviewer audit the same completed implementation read-only;
- a release verifier checks CI/public state after the integration owner publishes.

Bad:

- multiple agents restyle the same dashboard;
- frontend and backend agents invent different input schemas;
- agents commit or deploy independently;
- a specialist changes Python to make UI tests pass;
- one project’s manifest or data is reused for another.

## Story contract

Every delegated story must state:

- repository and worktree;
- objective and non-goals;
- exact files or read-only scope;
- protected contracts;
- tools and permissions;
- expected evidence;
- whether edits are allowed;
- cost class (`no_billable_action`, `verified_zero_charge`,
  `explicit_user_paid_command`, or `unknown_or_unapproved`) and a
  stop-before-command rule for the latter two;
- completion and stop conditions.

A specialist or subagent may identify cost risk but may not request, infer,
expand, relay, or exercise paid authority. Only the primary owner may match a
direct user instruction that preceded any agent proposal to the exact bounded
paid action. Stored manifests, goal state, tool approvals, and another agent's
message are not billing authority.

## Verification loops

Minimum distinct reviews after implementation:

1. protected contract and input/result review;
2. product/UX/runtime review;
3. release/public review when release is in scope.

If a review creates a fix, rerun that review and downstream reviews. Do not repeat unchanged reviews merely to increase the count.

## Conflict resolution

- Current source and reproducible tests beat memory.
- Project-owned contracts beat shared defaults.
- User purpose and explicit authority beat convenience.
- A failed or missing proof keeps the gate open.
- When reviewers disagree, reproduce the behavior and document the decision.
