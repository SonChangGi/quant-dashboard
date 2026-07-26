# Approved Plan: [Project and objective]

## Objective

- User-visible outcome:
- Why it matters:
- Priority:

## Scope

- In scope:
- Non-goals:
- Explicitly protected:
- Release boundary:
- Cost policy: zero spend unless the user first requested a specific paid action
- Paid action requested, exact scope, ceiling, duration, and stop condition:
- Provider-rights boundary:

## Current-state evidence

| Evidence | Current fact | Source | Confidence |
| --- | --- | --- | --- |
| Repository |  |  | confirmed |
| Runtime |  |  | confirmed |
| Data/result |  |  | confirmed |
| Sources/cutoff |  |  | confirmed |
| Schedule/last-good |  |  | confirmed |
| Cost plan/quota |  |  | confirmed |
| Public state |  |  | confirmed |

## Research

| Source | Finding | Decision supported | Limitation |
| --- | --- | --- | --- |

## Decision

- Chosen approach:
- Why:
- Minimal alternative:
- Larger alternative:
- Rejected approaches:

## Project contract

- Analysis/data/result contract:
- Inputs and authoritative mapping:
- Frontend contract:
- Backend/control contract:
- Source registry and rights contract:
- Coherent-cutoff and data-manifest contract:
- Automation/freshness/failure contract:
- Collect → analyze → publish → public-readback contract:
- Deployment/fallback contract:
- Cost-command contract:

## Implementation stories

1. [Story]
   - Owner:
   - Files/modules:
   - Protected boundaries:
   - Dependencies:
   - Acceptance evidence:

## Verification

- Contract and baseline:
- Unit/integration/E2E:
- Input A/B and display invariance:
- Browser/visual/accessibility:
- Automation/freshness:
- Required/optional source failure and last-good:
- Schedule enablement/idempotency/concurrency/retry:
- Versioned staging and public identity readback:
- Zero-spend command evidence:
- Preview:
- Release/public readback:

## Approval gates

1. Implementation authorization:
2. Local-preview review:
3. Migration/backend deployment:
4. GitHub release/merge:
5. Production replacement:
6. Paid action: prohibited unless separately requested first with bounded scope

## Rollback and fallback

- Rollback:
- Existing-production fallback:
- Recovery checkpoint:

## Completion definition

- [ ] User-visible objective achieved
- [ ] Protected contracts verified
- [ ] Required tests and audits passed
- [ ] Required preview approved
- [ ] Authorized release and public readback complete
- [ ] Required source, freshness, analysis, publication, and schedule gates passed
- [ ] No unapproved costs, secrets, or scope expansion
