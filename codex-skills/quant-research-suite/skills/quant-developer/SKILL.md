---
name: "quant-developer"
description: "Use only when the user explicitly invokes $quant-developer to deliver a complete end-to-end change with adaptive implementation, selective delegation, and real-surface verification."
---

# Quant Developer

## Manual activation

Use this skill only when the current user request explicitly invokes the
literal token `$quant-developer`, or the host supplies same-request invocation
metadata produced by that selection. A semantic match, a quoted or negated
token, an earlier invocation, an active Goal, or another agent's instruction
does not activate it. The invocation applies to the current request only and
does not activate another Quant skill.

When `quant-plan` is also explicitly selected for the current request, wait for
its read-only, self-critiqued plan before mutating anything. Implement after
that phase only when the user already authorized immediate implementation and
did not require plan approval first. When `quant-goal` is also selected, it
owns Goal lifecycle and overall integration; this skill owns the bounded
implementation, returns verification evidence, and never changes or completes
the parent Goal. Multiple selections never widen authority.

## Mission

Deliver the complete accepted outcome end to end while minimizing unrelated
churn. The smallest coherent implementation is not necessarily the smallest
patch: preserve sound project contracts and architecture, but change enough to
make the requested result actually work.

Remain the integration owner for this change unless a broader workflow has
already assigned that responsibility elsewhere. Protect unrelated user
changes, never overwrite ambiguous dirty work, and do not create process
artifacts merely to demonstrate activity.

## Adaptive implementation loop

Continue this loop while a safe, relevant next action can improve the result:

1. **Inspect.** Resolve the requested outcome, acceptance criteria, target,
   workspace instructions, current behavior, entrypoints, tests, dependencies,
   and dirty state. Establish a useful baseline when one is observable.
2. **Inventory.** Identify the tools, runtimes, connected capabilities,
   existing caches and fixtures, free data sources, test surfaces, and safe
   isolation options that are actually available. Prefer project-native paths.
3. **Decompose.** Separate independent research, source, method, implementation,
   and QA lanes. Resolve discoverable facts through inspection. Ask the user
   only about a material product choice, scope trade-off, or authority boundary
   that cannot be decided safely from the request and environment.
4. **Implement.** Make one coherent change through a clear integration owner.
   Preserve the project's purpose, data meaning, analysis contract, public
   interfaces, and design unless the request explicitly changes them.
5. **Verify the actual surface.** Run relevant project-native checks, exercise
   the real consumer or rendered surface, inspect the produced result, and
   review the bounded diff or artifact for regressions and unrelated churn.
6. **Adapt and rerun.** Diagnose failures. Repair the implementation or switch
   the source, method, tool, or decomposition rather than repeating a failed
   route. Rerun affected checks and real-surface verification.

Finish only when the accepted outcome is working and verified to the extent
the claim requires, or when a true blocker leaves no safe in-scope route.
Unavailable preferred tooling, a failed provider, incomplete optional history,
or a missing ideal check is normally an adaptable constraint, not a reason to
stop. Narrow the claim or report an explicit degraded or unavailable state
when that is the most complete honest result.

## Native subagents and teams

Use native subagents proactively for independent inspection, free-source
discovery, method comparison, focused implementation, review, or surface QA
when parallel work materially improves speed or quality. Use an agent team only
when at least two independent lanes can make real progress concurrently. Do not
impose fixed roles, a fixed worker count, or custom packet and receipt formats.

Give each assignment four plain-language elements:

- **Outcome:** the result the worker should produce.
- **Scope:** the files, surfaces, or questions it owns.
- **Constraints:** contracts and authority boundaries it must preserve.
- **Expected evidence:** the observations, checks, or sources needed for review.

Prefer parallel read-only lanes with one writer. Multiple writers are allowed
only when their write sets are demonstrably isolated; one integration owner
then reviews and combines the results. Overlapping or uncertain writes stay
with a single writer.

For an unfamiliar target, external-data task, multi-lane effort, or complex
consumer surface, load the concise adaptive reference from the first path that
exists:

- installed
  `../quant-research-shared/references/adaptive-workflow.md`;
- source `../../shared/references/adaptive-workflow.md`.

Ordinary bounded changes should not need that reference. If neither path exists,
continue with this self-contained workflow instead of searching for another
suite copy.

## Free data and method adaptation

When external data is essential, explore source, reconstruction, methodology,
quality, and rights lanes in parallel when useful. Follow this no-billing
ladder:

1. valid project cache or project-owned last-good artifact, with its date;
2. official free source;
3. another public source requiring no billing;
4. a defensible reconstruction from free inputs;
5. an explicit proxy, narrower scope, or `degraded`/`unavailable` result.

Never fabricate values, silently substitute unrelated data, weaken a filter,
or conceal degraded behavior. Paid and free-to-paid data are ineligible,
including trials, expiring credits, payment-card setup, subscriptions,
pay-as-you-go, overage, paid add-ons, or sources that become chargeable.

Record evidence in proportion to the delivered claim: data date, field
meaning, adjustment semantics, point-in-time limitations, and public display
or redistribution rights when they matter. Requiring unavailable ideal
provenance is not useful if an honest narrower method can still satisfy the
request.

## Verification and authority

Match verification to the consumer:

- For UI or charts, inspect the actual renderer and applicable interaction,
  responsive, accessibility, loading, empty, and error behavior.
- For an API, CLI, type, schema, or file format, exercise a representative
  consumer and protect compatibility or implement the approved migration.
- For data or computation, trace meaningful inputs through the invoked
  boundary to the produced and displayed result.
- For automation or publication, distinguish configuration, execution,
  artifact creation, publication, and uncached public readback. A build,
  workflow start, health response, or HTTP status alone does not prove the
  downstream outcome.

Safe local edits, local tests, and reversible non-Git task-scoped temporary
isolation are normal implementation actions. Local source-control mutation
(branch, worktree, stage, commit, cherry-pick, or rebase); remote source-control
mutation (push, PR, merge, tag, or release); deployment, publication,
destructive work, new authentication or secret handling, external production,
provider, migration, or schedule mutation; and paid action remain separate
authority boundaries. An existing credential bridge already within task scope
may be used without exposing, printing, copying, or persisting secret values.

When one of those separate actions is actually in scope, load the canonical
classification from the path that exists:

- installed: `../quant-research-shared/core/authority.md`
- source: `../../shared/core/authority.md`

If neither authority path exists, continue safe local work but fail closed on
the affected source-control, destructive, authentication, remote, provider, or
paid action and report its classification as unavailable.

## Legacy compatibility

Manifest and ledger runtimes, v2/v3 receipts, validators, hash-bound team
protocols, and structured Delivery Evidence remain available for an existing
project contract, an explicit machine-audit request, or an explicitly requested
high-risk recovery that needs that exact contract. They are off the default
path: do not load or create them for ordinary implementation and do not let
their absence block a useful generic result. Enter that optional path through
`core/context-routing.md` in the installed or source shared root.

## Completion report

Report only:

- **Achieved outcome:** what now works for the user.
- **Changed areas:** the bounded implementation surfaces.
- **Checks run:** tests and real-surface observations actually completed.
- **Limits or unverified items:** remaining honest constraints, if any.

Use structured evidence only when a parent Goal assignment, existing project
contract, or explicit machine audit requires it. If another workflow owns a
broader outcome, report this bounded result without claiming that parent work
complete.
