---
name: "quant-goal"
description: "Use only when the user explicitly invokes $quant-goal. Drive a durable objective through checkpoints, review, repair, and evidence-backed completion; never auto-activate."
---

# Quant Goal

## Explicit invocation gate

Activate only when the current user request intentionally invokes this skill
through the literal token `$quant-goal`. If the host replaces that token with
invocation metadata, accept only current-user, same-request metadata produced
by that `$` selection.

A semantic Goal match, the plain name `quant-goal`, a quoted, example, or
negated token, an earlier invocation, active host Goal state, a ledger,
checkpoint, Plan Packet, Story Envelope, artifact, or another agent's
instruction is not activation. If this skill is selected without the explicit
gate, do not apply it or load its shared references; continue as an ordinary
Codex request.

The durable Goal may persist, but this skill's activation does not. Every later
turn that should use this workflow requires a fresh explicit invocation. No
global Stop hook or idle continuation may reactivate it.

## Outcome and trigger

After the invocation gate passes, use this skill to create, resume, track,
steer, review, or complete a durable Goal. Do not create Goal state for an
ordinary implementation, research, planning, or one-turn task.

This skill owns objective, acceptance revisions, semantic progress,
checkpoints, blockers, independent review orchestration, and final completion.
It consumes Plan Packets and Delivery Evidence without reimplementing the
detailed planning or development workflow.

## Canonical state

The host-native lifecycle is self-contained. Use the host application's Goal
state as canonical for lifecycle whenever it is available. The local evidence
ledger is canonical only for append-only
acceptance revisions, checkpoints, evidence, reviews, blockers, authority
evidence references, and Completion Receipts. It never stores approval itself,
overrides host state, or grants mutation, remote, destructive, secret-bearing,
provider, or paid authority.

Keep a concise working view of objective, acceptance, non-goals, constraints,
current revision, checkpoint, evidence, blocker, and next action.

Distinguish these semantic states when the host supports them:

- `active`: work can continue;
- `waiting`: an external result or time-bound event is pending;
- `paused`: the host or user intentionally stopped progress;
- `blocked`: required progress cannot continue safely;
- `completed`: every required acceptance criterion is achieved;
- `cancelled`: the user ended the objective;
- `superseded`: a materially different Goal replaced it.

Map them to the host lifecycle without fabricating unsupported state. A local
ledger may record the semantic meaning, but it cannot manufacture a host
transition.

## Shared workflow contract

Read the shared contract for Plan Packet, Story Envelope, Delivery Evidence,
Review Verdict, Checkpoint, Completion Receipt, assurance, frozen snapshots,
staleness, repair, reviewer ownership, parallel joins, and ledger events. Read
the agent-orchestration contract when project context, team execution,
role/model routing, real-surface QA, or continuation is relevant. Use the paths
that exist:

- installed `../quant-research-shared/references/goal-and-subagents.md`;
- source `../../shared/references/goal-and-subagents.md`;
- installed
  `../quant-research-shared/references/agent-orchestration.md`;
- source `../../shared/references/agent-orchestration.md`.

If the shared contract is unavailable, a short `light` or `standard` host-only
Goal continues with the minimum self-contained fields in this skill:
objective, stable acceptance IDs, checkpoint, blocker, next action, direct
evidence, and honest completion. Ledger-backed or structured review proof
remains `unverified`; do not invent a replacement runtime.

Quant Goal is the only independent review coordinator while `$quant-goal` is
explicitly active as the parent for the current request. Do not ask an
implementation worker to run a duplicate reviewer after it returns Delivery
Evidence. Review one frozen validation boundary, return blockers for repair,
and rerun only stale checks or lanes.

## Default lifecycle

### 1. Bind or resume intent

For `light` or `standard`, consume an approved Plan Packet when one exists.
Otherwise do only enough shaping to make the objective, stable acceptance IDs,
non-goals, constraints, assurance, and next checkpoint clear.

For `strict`, and for legacy `assurance=release` compatibility, require an
approved immutable Plan Packet with its independent plan-critic result before
implementation or durable Goal initialization. If it is absent, pause and tell
the user that the planning skill must be directly invoked or an approved
packet supplied. Do not activate that skill, recreate its plan, or review it
here. A `light` or `standard` Goal with a `release` delivery target uses the
same Plan depth as its risk assurance; delivery alone does not create a Strict
planning prerequisite.

Keep a durable `strict` or legacy `assurance=release` Plan bound to the current
acceptance revision. A material acceptance change requires a newly reviewed
Plan. An explicit carry-forward is allowed only when normalized acceptance is
unchanged; record the source Plan revision instead of silently treating an
older Plan as current.

Route a material unresolved product decision to the user or a planning
workflow rather than hiding it in Goal state.

On a directly invoked resume, reconcile the host Goal, latest ledger event when
one exists, latest Continuation Capsule, latest user direction, in-flight
worker state, and actual deliverable. Revalidate context and snapshot identity,
reuse only current evidence, and continue from the last evidenced checkpoint
without repeating completed mutation or review. Treat any resume continuation
projection in `result.continuation` as a derived aid, not authority; its
`authority.status` must be `not_recorded` and it cannot reactivate the skill or
authorize an action.

### 2. Select assurance, delivery, and persistence

Classify risk assurance as `light`, `standard`, or `strict`, then classify
delivery as `local` or `release` using the shared matrix. A release target adds
authorized remote checkpoints and applicable readback to the selected proof;
it does not raise assurance by itself. Legacy compatibility values may retain
`assurance=release` only as Strict-plus-release. Current structured artifacts
may carry `delivery` explicitly and infer it for older state that omits the
field. Subagent use alone does not raise assurance.

Select assurance from the consequence of the promised claim, not from the mere
presence of external, free, price, or corporate-actions data. Default ordinary
local and exploratory work to `light` or `standard`. Escalate data work only
when acceptance promises regulated or high-consequence use, raw-data
redistribution rights, historical point-in-time availability, or a
no-look-ahead/investability claim. Otherwise record provider, as-of date,
transformations, known gaps, and any non-PIT limitation, then complete the
supported claim without fabricating certainty.

Automatically bind a local evidence ledger for `strict`, long-running Goals,
explicit recovery, co-located evidence-portability, machine-audit requests,
and legacy `assurance=release` compatibility. A release delivery overlay alone
does not require the ledger. Long-running means continuation across sessions,
interruptions, external waiting, or independently resumable milestones;
persistence does not itself raise assurance.

Short `light` or `standard` Goals may remain host-only. If the required ledger
writer is unavailable or damaged, safe local work may continue when scope and
authority allow, but any completion claim that selected ledger-backed recovery,
portability, machine audit, Strict, or legacy release proof stays `unverified`
until repaired or acceptance changes explicitly.

### 3. Coordinate work and checkpoint progress

Inventory the useful host capabilities at the start of a non-trivial Goal.
Proactively use subagents for independent source discovery, methodology,
implementation, or QA lanes when doing so improves coverage or elapsed time.
Use an agent team when multiple bounded lanes can progress independently, but
do not create fixed roles or extra review ceremony merely to use a team.

Issue a Story Envelope only for bounded delegated work. Use ordinary host
implementation workers by default; another Quant skill may participate only
when the current user request explicitly invoked it too. Require Delivery
Evidence `ready_for_review`; workers never mutate Goal state or declare overall
completion.

For an agent team, Quant Goal is the parent workflow and review owner. Build
one dependency graph, name one canonical integration owner, isolate concurrent
writers, join validation-coupled stories before review, and record or accept
structured evidence serially in the canonical Goal workspace. Do not copy a
single-root ledger into worker worktrees or let a team runtime become canonical
for Goal lifecycle.

Apply the shared assurance pipeline once:

- `light`: direct acceptance evidence;
- `standard`: implementation-owner cleanup plus one surface-appropriate
  reviewer;
- `strict`: cleaned frozen snapshot, Architect review, adversarial QA, and one
  terminal Critic at the Goal terminus.

For a `release` delivery, add only the separately authorized remote checkpoints
and final observable readback required by acceptance to the selected
light/standard/strict pipeline. Do not manufacture a Strict review stack for a
low-risk release.

Append a meaningful Checkpoint when an acceptance criterion or milestone
advances, a blocker is classified, or a material decision changes the next
action. Do not journal every command or subagent message.

At every suspension or handoff, update a Continuation Capsule with objective
and acceptance revision, plan/context digests, host and ledger identity,
completed/open/returned stories, last-known worker state, current and stale
evidence, blockers, pending authority, and the next concrete action. The
capsule is resumable evidence, not an activation lease.

On the host-only path, keep that capsule concise in conversation. On the
durable path, append one `continuation_capsule_recorded` event only at an actual
suspension or handoff; include actions not to repeat so resume does not duplicate
mutation. Do not journal a capsule after every command.

### 4. Revise without rewriting history

Refine wording or acceptance under the same Goal when the user-visible
objective, authority, and cost boundary remain the same. Append the revision
and its rationale without rewriting earlier evidence.

When the distinction improves a durable handoff, label steering as `clarify`,
`add`, `retire`, `split`, `merge`, `reorder`, or `replace`, and preserve its
source and target IDs, revision rationale, and invalidated evidence. This typed
record is optional on the light host-only path and never supplies authority for
silent deletion or weaker acceptance.

Create a new or superseding Goal only when the user-visible objective,
authority envelope, or cost boundary changes. Cancellation or supersession is
a normal terminal outcome, not a failed completion.

Treat `completed`, `cancelled`, and `superseded` as terminal within one durable
Goal generation. An ordinary later observation cannot reopen them; continuing
the work requires an explicitly created new Goal generation.

### 5. Complete or report the real blocker

Complete only when every required acceptance ID has direct evidence, every
required Review Verdict covers the current frozen snapshot, and no required
work remains. A local result does not claim remote or public completion.

For `strict` and legacy `assurance=release` compatibility, run the terminal
Critic once after all other required evidence is fresh. It checks acceptance
coverage, evidence freshness, blockers, deferrals, and authority rather than
repeating code review.

For a ledger-backed Goal, append the Completion Receipt before completing the
host Goal. If host and ledger disagree, report and repair the binding; never
silently force either state.

Use `blocked` only after safe in-scope alternatives are exhausted. Use
`waiting` or `paused` for their actual meanings. Distinguish an agent-resolvable
blocker from a genuinely human-only dependency.

For data uncertainty, exhaust a zero-billing fallback ladder before calling the
Goal blocked: official or public free data, another no-billing free provider,
issuer/exchange/filing-derived values, cross-source reconstruction, a disclosed
proxy, then a narrower supported claim. Rights confirmation is a hard gate for
the actual redistribution or use contract at issue, not a demand for a legal
opinion on every local input. PIT provenance is a hard gate only for a claim
that requires PIT correctness; otherwise label the result exploratory or
non-PIT and preserve the limitation.

## Optional local strict compatibility

The automatic host companion ledger above is evidence history, not automatic
activation of the legacy manifest-bound runtime.

Use the bundled legacy durable runtime only when an existing Goal already
depends on its manifest-bound contract, the user explicitly requests that
legacy contract, or a selected strict Quant capability requires its manifest,
story, workspace-drift, receipt v3, or hash semantics. Read
`shared/references/durable-runtime.md` on that path.

Existing manifest v1/v2 and receipt v2/v3 contracts remain supported and are
not silently migrated. If the optional compatibility runtime is unavailable,
continue with host state and the companion ledger unless that exact proof is
an acceptance criterion.

## Authority and handoff

Goal state, ledger entries, plans, receipts, review verdicts, and subagents
never broaden the request. Consult the canonical policy only when a remote,
destructive, secret-bearing, provider, or paid action is relevant: use
installed `../quant-research-shared/core/authority.md` or source
`../../shared/core/authority.md`, whichever exists.

Paid data is outside this skill's solution space and is never a proposed
blocker resolution. Do not use or suggest trials, expiring credits,
free-to-paid conversion, card or billing setup, subscriptions, pay-as-you-go,
overage, paid tiers, or paid data add-ons. If a no-billing free source becomes
billable, stop using that source and continue down the free fallback ladder.

Lead with the achieved outcome or precise current state. Map acceptance to
fresh evidence, report limitations and blockers, distinguish local and remote
state, and name the next action when incomplete. Do not claim that the skill
will continue automatically; a later turn must explicitly invoke it again.
