# Strict cost evidence and authority envelope

This reference defines machine-readable cost evidence for manifest-v1,
receipt-v2, receipt-v3, remote-release, scheduled-automation, and the explicit
strict dashboard profile. It is not a preflight or receipt requirement for
ordinary local, non-billable work.

## Contents

- [Activation](#activation)
- [Permanent paid-data exclusion](#permanent-paid-data-exclusion)
- [Action inventory](#action-inventory)
- [Classification evidence](#classification-evidence)
- [Trusted paid-authority envelope](#trusted-paid-authority-envelope)
- [Canonical hashes](#canonical-hashes)
- [Recurring automation](#recurring-automation)
- [Reporting](#reporting)

The canonical human authority policy and paid-action taxonomy live only in
`shared/core/authority.md`. Apply that policy before using this evidence
contract. A manifest, receipt, Goal file, local quote, validator input, tool
approval, or subagent output cannot create or broaden authority.

## Activation

Use this contract only when:

- a selected remote/provider capability derives the `cost` gate;
- an existing manifest or receipt schema requires the structured fields; or
- the user explicitly requests strict machine-validated cost evidence.

Otherwise report any relevant authority boundary in prose and do not build a
cost receipt.

## Permanent paid-data exclusion

The `explicit_user_paid_command` compatibility classification described below
never applies to data access, a data feed, data license, subscription, trial,
credit, quota extension, add-on, or paid tier. Do not inventory paid data as a
candidate action or ask for its approval. Eligible data must remain zero-charge
without payment setup, later conversion, PAYG, overage, or a paid continuity
dependency. If a source becomes paid for the required use, classify new
collection as ineligible and use a free replacement, free derivation or proxy,
or a narrower honest result.

Legacy receipts may retain historical paid-action fields for schema
compatibility. They do not override this prohibition or make a paid data action
executable.

## Action inventory

Structured cost preflight records an `actions[]` inventory. Each shell command,
API call, browser mutation, provider request, deployment, workflow dispatch, or
recurring schedule that can affect a remote/provider resource is a separate
action. One local action or one verified provider must not classify an entire
release.

Each action records:

- a stable ID and local or remote/provider classification;
- service, account/project, resource/SKU, and normalized redacted action;
- classification and allow/block decision;
- current plan, price, quota, credit/trial, and overage evidence;
- the closed paid-transition booleans required by the active schema;
- finite run, retry, concurrency, compute, storage, egress, retention, and
  monetary ceilings;
- cadence, end condition, hard stop, and rollback where applicable;
- one remote scope ID;
- trusted authority-envelope reference only for a user-requested paid action;
- a canonical action-envelope SHA-256.

Missing, unclassified, or unhashed remote actions block the structured cost
gate. `no_billable_action` is reserved for a purely local action that cannot
contact, mutate, dispatch, retain, or consume a provider resource.

## Classification evidence

A remote/provider action is recorded as one of:

- `verified_zero_charge`, with current plan/quota evidence and hard stops;
- `explicit_user_paid_command`, only for an eligible non-data action with
  trusted prior-user authority and bounded paid scope; or
- `unknown_or_unapproved`, which remains blocked.

For `verified_zero_charge`, use current official or account-visible evidence,
retain a non-secret capture, bind its bytes and timestamp to the exact action
and run identity, and perform preflight before the remote mutation. Follow the
age limit and required fields of the active schema. A receipt-authored
description is not a live capture.

Do not run a cost-capable command merely to discover price or trigger an
approval dialog. Use read-only plan, quota, pricing, or dry-run checks.

## Trusted paid-authority envelope

Locally writable fields cannot prove that a direct user instruction preceded an
agent proposal or attempted action. For an eligible non-data paid action, a
machine validator may accept a paid classification only when a trusted host
runtime supplies an immutable envelope outside agent and repository write
control. No envelope can authorize paid data.

The envelope binds:

- runtime/session and direct user-message identity and time;
- ordering before agent proposal and attempted action;
- service, account/project, resource/SKU, and normalized action;
- one-time or recurring scope, ceilings, duration, and stop condition;
- a canonical SHA-256 or runtime signature.

The validator compares this envelope with the exact action receipt. If the host
cannot supply it, the human conversation may still describe the blocker, but
machine completion of the paid cost gate remains blocked.

## Canonical hashes

Compute each action SHA with `canonical-json-v1` over the action object while
omitting its `canonical_action_envelope_sha256` field. Compute the receipt-level
SHA over the complete ordered `actions[]` value. UTF-8, sorted object keys,
Unicode preservation, finite JSON numbers, and no insignificant whitespace are
required. Adding, removing, reordering, or changing an action invalidates the
cost gate.

Cost-gate evidence must bind the same receipt-level SHA. Command evidence must
match the redacted executable action and runtime outcome. The active schema and
validator remain the authority for exact field names and compatibility aliases.

## Recurring automation

A schedule is a continuing remote and cost decision. Bind cadence, end
condition, calls, compute, storage, retention, egress, retry, and concurrency
ceilings. Recheck applicable quota before each run and fail closed when current
pricing/quota evidence is missing or a hard stop would be exceeded.

Retries, backfills, fallbacks, or delayed cleanup remain separate actions and
cannot bypass the inventory or ceilings. Preserve an existing no-cost/public
fallback only when it is part of the selected project contract.

## Reporting

A structured cost receipt reports the policy ID, complete action inventory,
classification evidence, recurring bounds, canonical hashes, hard-stop result,
and any trusted authority-envelope match. Report `unknown_or_unapproved` and do
not execute when the required evidence is unavailable.
