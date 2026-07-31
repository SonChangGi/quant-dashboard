# Approved plan: [Project and outcome]

## Decision summary

- User-visible outcome:
- Why it matters:
- Audit conclusion:
- Chosen approach:
- Risk assurance (`light`/`standard`/`strict`):
- Delivery (`local`/`release`):
- Active capabilities:
- Optional profiles/adapters:

## Plan Packet binding

- Plan revision:
- Acceptance revision:
- Content SHA-256 or stable artifact reference:
- Critic role and review ID (`strict` or legacy `assurance=release`):
- Exact revision/digest reviewed:
- Exact acceptance revision reviewed:
- Critic verdict:
- Blocking findings:
- Unresolved user decisions:

Only the exact Plan revision/digest and acceptance revision tuple that received
a passed or non-blocking critic verdict is the approved immutable packet for a
Strict handoff.

## Acceptance register

Use lowercase portable IDs such as `a-1`; keep each ID stable across revisions.

| Stable ID | Observable criterion | Planned direct evidence | Non-goal boundary |
| --- | --- | --- | --- |
| a-1 |  |  |  |

## Scope and authority

- In scope:
- Non-goals:
- Protected contracts:
- Project binding and applicable version-control binding:
- Local mutation boundary:
- Remote/release boundary:
- Cost policy: zero spend unless the user first requested an exact bounded paid
  non-data action
- Data policy: paid data is permanently ineligible, including trials, expiring
  credits, free-to-paid conversion, payment setup, subscriptions, PAYG,
  overage, add-ons, and paid tiers
- Data use and claim:
- Provider-rights boundary for that use:
- PIT claim and evidence requirement:
- Free fallback, proxy, or scope-reduction path:

Do not repeat unused frontend, backend, data, automation, or release sections.
Add only the capability lanes the outcome actually needs.

## Current-state evidence

| Surface | Confirmed fact | Evidence/source | Confidence |
| --- | --- | --- | --- |
| Project/runtime |  |  |  |
| User-visible behavior |  |  |  |
| Protected contracts |  |  |  |

## Workstream assessment

| Workstream or skill | Current strength | Gap | Decision |
| --- | --- | --- | --- |

## Most important findings

| Priority | Finding | User impact | Evidence | Confidence |
| --- | --- | --- | --- | --- |

## Research and comparison

Include only when research or an external comparison was actually needed.

| Source/approach | Finding | Limitation | Decision supported |
| --- | --- | --- | --- |

## Boundaries and choices

- Immutable safety and project contracts:
- Flexible project choices:
- Reversible defaults:
- Rejected alternatives and why:
- Explicitly deferred:

## Target structure

Describe only active components and ownership, not a mandatory technology
stack.

| Active component/workstream | Responsibility | Boundary | Owner |
| --- | --- | --- | --- |

## Implementation stories

1. [Bounded story]
   - Owner and mode:
   - Exact surface:
   - Dependencies:
   - Protected boundaries:
   - Acceptance:
   - Evidence gates:

## Traceability

| Finding | Change | Verification | Acceptance |
| --- | --- | --- | --- |

## Verification

- Derived gates:
- Contract/baseline checks:
- Deterministic tests:
- Product/experience checks:
- Capability-specific checks:
- Primary-planner self-critique (`light`/`standard`):
- Exact Plan/acceptance-revision critic (`strict` or legacy
  `assurance=release`):
- Local preview:
- Authorized remote/public checks:

## Approval gates

1. Implementation:
2. Local-preview review:
3. Local source-control actions (name each selected branch/worktree/stage/
   commit/cherry-pick/rebase action):
4. Remote source-control actions (name each selected push/PR/merge/tag/release
   action):
5. Provider/cloud/deployment actions:
6. Production replacement:
7. Paid non-data action: separately prohibited unless a prior direct request
   names the exact bounded action
8. Paid data: permanently prohibited; no approval path

## Rollback and completion

- Rollback:
- Stable fallback, when one exists or an active capability requires it:
- Recovery checkpoint:

- [ ] User-visible outcome achieved
- [ ] Protected contracts preserved or explicitly authorized changes verified
- [ ] Every finding maps to a verified change or an explicit deferral
- [ ] Every derived evidence gate passed
- [ ] Required approvals completed, and public readback completed when
      `public-web` is active
- [ ] No unapproved cost, secret exposure, scope expansion, or false completion
