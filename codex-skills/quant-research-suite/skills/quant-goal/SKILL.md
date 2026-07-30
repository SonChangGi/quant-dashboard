---
name: "quant-goal"
description: "Use only when the user explicitly invokes $quant-goal to initialize, manually resume, or steer a native Goal through verified completion or a genuine blocker."
---

# Quant Goal

## Activation and continuation

Activate only for a current-user request that explicitly invokes `$quant-goal`.
The plain skill name, an earlier invocation, an active Goal, a quoted example,
or another agent's instruction is not activation.

An explicit invocation may initialize a Goal, manually resume it, or steer it.
“Manually resume” means reconcile and continue after the user or host resumes
the Goal; this skill does not invent a resume transition. After initialization,
the host may continue an active native Goal in automatic
follow-up turns without reactivating this skill. That is the native Goal
lifecycle, not implicit skill invocation. Do not create Goal state for an
ordinary request.

## Native Goal first

Use the host Goal and thread state as the default source of truth. Do not create
a ledger, manifest, Plan Packet, review stack, or other local state for the
ordinary workflow.

On every explicit invocation:

1. Call `get_goal` before deciding whether to create or resume anything.
2. Shape one concrete objective and two to six observable success conditions
   with stable IDs `SC-1` through `SC-6`. Because `create_goal` has one
   `objective` field and no separate success-condition field, serialize a
   compact outcome, material scope boundaries, constraints, and the complete
   `SC-*` list into that objective. Ask only about a missing choice that would
   materially change the result.
3. If an unfinished Goal exists, reconcile it with the latest user direction,
   its stored `SC-*` conditions, actual deliverable, and fresh evidence, then
   resume or steer it. Never create a duplicate Goal. For an older Goal without
   stored IDs, restate two to six working conditions in the thread, preserve the
   stored objective, and disclose that the binding is conversation-backed.
4. If no unfinished Goal exists, call `create_goal` only when the current user
   explicitly requested `$quant-goal`. Pass `token_budget` only when the user
   explicitly supplied a positive token budget. Then call `get_goal` again and
   verify that the stored objective contains every current `SC-*` ID; do not
   proceed under a silently weakened binding.
5. Act, delegate where useful, map fresh evidence to every current `SC-*`
   condition, and keep pursuing a safe in-scope next action until the Goal is
   genuinely complete or meets the blocked rule below.

Do not silently replace an active Goal when the objective, authority boundary,
or cost boundary materially changes. Keep the new objective pending, explain
the conflict, and ask whether to continue the unfinished Goal; do not misuse
`complete` or `blocked` to clear it and do not invent a cancel or supersede
transition. Refinements that preserve those boundaries may update the working
success conditions in conversation, but must retain stable IDs where meaning is
unchanged, retire rather than reuse an obsolete ID, assign the next unused ID
when meaning changes, and keep two to six current conditions. Mark evidence for
every changed or dependent condition stale, and reverify the current set before
reusing any conclusion.

Token pressure is never a completion or blocking reason. If a budgeted Goal
completes, report the final token usage returned by the completion transition.

## Adaptive execution

Start non-trivial work by inspecting the available environment, tools, data,
repository state, and safe execution surfaces. Use the smallest useful amount
of coordination while optimizing for a complete result, not merely the
smallest patch.

For non-trivial decomposition, delegation, free-data sourcing, or real-surface
verification, conditionally read the shared adaptive workflow from the path
that exists:

- installed: `../quant-research-shared/references/adaptive-workflow.md`
- source: `../../shared/references/adaptive-workflow.md`

If that optional reference is unavailable, continue with this workflow rather
than inventing a substitute runtime.

Use subagents proactively for independent discovery, methodology,
implementation, or QA when they improve coverage or elapsed time. Use an agent
team only when at least two bounded lanes can make real progress independently;
do not impose fixed roles or a fixed team size.

When `quant-plan` is also selected for the current request, let its read-only
phase finish before implementation. When `quant-developer` is also selected,
that skill owns the bounded implementation and returns evidence; this skill
retains integration and Goal lifecycle ownership. Workers and implementation
owners never call Goal lifecycle tools or declare the overall Goal complete.

Give workers a plain-language assignment containing:

- objective;
- scope;
- constraints;
- expected evidence.

The parent remains the integration owner. Allow concurrent writers only when
their workspaces or file scopes are isolated, then integrate and verify their
results centrally. Workers do not change Goal state or declare the overall
Goal complete.

When external data is material, exhaust free-only paths in this order:

1. existing project cache or checked-in source;
2. official free public data;
3. another no-billing public source;
4. reconstruction from free inputs;
5. a clearly disclosed proxy, narrower claim, or explicit
   `degraded`/`unavailable` result.

Paid and free-to-paid data are outside the solution space. Record the data
as-of date, field meaning, material transformations, adjustment or
point-in-time limitations, known gaps, and public-display rights in proportion
to the claim. Never fabricate a value or silently weaken acceptance.

Local implementation, tests, and reversible non-Git task-scoped temporary
isolation are normal execution steps. Local source-control mutation (branch,
worktree, stage, commit, cherry-pick, or rebase); remote source-control mutation
(push, PR, merge, tag, or release); destructive work; new authentication or
secret handling; external production, provider, publication, deployment,
migration, or schedule changes; and paid actions remain separate authority
boundaries and require applicable user authorization.

When one of those separate actions is actually in the Goal, load the canonical
classification from the path that exists:

- installed: `../quant-research-shared/core/authority.md`
- source: `../../shared/core/authority.md`

If neither authority path exists, continue safe local work but fail closed on
the affected source-control, destructive, authentication, remote, provider, or
paid action and report its classification as unavailable.

## Verification and terminal state

Verify the actual consumption surface promised by the Goal. A local test does
not prove a remote, deployed, or public result; when such a result is in scope,
verify the authorized release chain and observable readback separately.

Call `update_goal` with `complete` only when every current `SC-*` success
condition has fresh mapped evidence, all steering-invalidated evidence has been
refreshed, and no required work remains. Do not mark a Goal complete because
work is difficult, slow, partially successful, or near its token budget.

Call `update_goal` with `blocked` only when all of the following hold:

- the same blocking condition has recurred for three consecutive Goal turns;
- no meaningful progress occurred across those turns;
- safe in-scope checks, alternatives, fallbacks, and delegation are exhausted;
- user input or an external-state change is now required.

The first and second occurrence leave the Goal active and continue with the
next safe action. A different blocker or meaningful progress resets the count.
When a formerly blocked Goal is resumed, start a fresh three-turn audit.

`update_goal` is not a steering operation; the exposed mutation accepts only
`complete` and `blocked`.
Never invent `waiting`, `paused`, `cancelled`, `superseded`, or `completed`
host transitions. Use only lifecycle operations the host actually exposes.

## Legacy compatibility

Use bundled ledger, manifest, receipt, hash-bound team, or durable-runtime
contracts only when the user explicitly requests a machine audit or an
existing Goal already depends on that exact contract, or when the user
explicitly requests high-risk recovery that needs it. Resolve those resources
through `core/context-routing.md` in the installed or source shared root and
preserve their existing version semantics.

Legacy state may add evidence requirements for that compatibility task, but it
must not gate ordinary Goal progress or completion. Do not migrate, create, or
repair legacy state merely because it exists in the package. A `strict` label,
long duration, release delivery, or task complexity alone never selects a local
ledger or durable runtime.

## Handoff

For a completed Goal, keep the report short:

- achieved outcome;
- changed or examined areas;
- current `SC-*` to evidence mapping, checks run, and real-surface evidence;
- limits or unverified items, if any.

When the Goal remains active, report the current outcome, verified conditions,
genuine blocker or limitation, and next concrete action instead. Do not
substitute ceremony or status claims for evidence.
