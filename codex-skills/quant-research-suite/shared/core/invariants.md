# Core invariants

These rules apply to both the self-contained default workflow and every
optional compatibility path. A profile, manifest, Goal state, receipt,
subagent, tool approval, or previous run cannot weaken them.

## Scope and target

- Resolve the exact target and requested deliverable before mutation. Resolve
  repository, worktree, branch, provider, or public identity only when that
  surface exists and is relevant.
- Preserve unrelated user work. Do not edit a plausible neighbour when target
  identity or dirty overlap is ambiguous.
- Do not broaden a request merely because a tool, credential, manifest,
  framework, or optional runtime is available.

## Discovered contracts

- Protect contracts declared by the user or evidenced by the target project and
  current behavior unless the request explicitly changes them.
- A change to one surface does not authorize changes to adjacent computation,
  data, schema, interface, automation, provider, or release behavior.
- Shared patterns may provide reusable mechanics, but they do not transfer
  another project's domain assumptions, data, design, or operational policy.

## Evidence honesty

- Verify claims with evidence proportionate to their consequence.
- Report skipped, inferred, unavailable, queued, or blocked checks as such.
- Do not fabricate missing data, conceal degraded behavior, or claim that an
  intermediate signal proves a downstream result.
- Treat missing preferred data, non-PIT history, or incomplete coverage as an
  adaptable constraint when a free source, free reconstruction or proxy,
  narrower scope, or honest limitation can still satisfy the objective. Do not
  weaken the claim silently.
- A specialist provides review input. The integration owner accepts a
  change-set, and only a currently invoked Goal parent judges overall Goal
  completion. Persisted Goal state alone does not activate that workflow.

## Authority and safety

- Keep local, source-control, remote/provider, destructive, secret-bearing, and
  paid actions within their applicable authority boundary.
- Paid data is permanently ineligible, including trials, expiring credits,
  free-to-paid conversion, payment setup, subscriptions, PAYG, overage, paid
  add-ons, and paid tiers. It is not an approval or fallback option.
- Do not expose, persist, echo, upload, or commit secrets.
- Assurance changes verification depth, never scope or authority.
- Optional infrastructure is not a prerequisite for ordinary work. Add or
  activate it only for a demonstrated need or an explicit compatibility
  contract.
