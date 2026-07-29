# Data Collection, Analysis, and Publication Contract

## Contents

- [Activation and scope](#activation-and-scope)
- [Outcome](#outcome)
- [Project-owned source registry](#project-owned-source-registry)
- [Authoritative pipeline](#authoritative-pipeline)
- [Required identities and timestamps](#required-identities-and-timestamps)
- [Schedule contract](#schedule-contract)
- [Partial failure and recovery](#partial-failure-and-recovery)
- [Verification matrix](#verification-matrix)
- [Existing and new projects](#existing-and-new-projects)
- [Completion evidence](#completion-evidence)

## Activation and scope

Use this full contract only for scheduled collection, public publication, raw
redistribution, or an explicitly selected strict reproducibility path. Do not
require it for a local/private exploration, one-time notebook, prototype, or
non-PIT retrospective analysis. Those use the lighter
`capabilities/external-data.md` contract.

All selected data sources must remain eligible under the permanent free-only
policy in `core/authority.md`: no paid data, trial, expiring credit,
free-to-paid conversion, payment method, subscription, PAYG, overage, paid
add-on, or paid tier. If a source becomes paid for the required use, stop new
collection and switch to a free source, free derivation or proxy, or a narrower
honest result. Paid data is never a fallback or approval option.

This contract proves the automated and public claims actually selected. It does
not manufacture a PIT claim. Require historical PIT lineage only when
acceptance claims point-in-time, as-known-then, look-ahead-free,
survivorship-free, or historically investable results. Otherwise preserve and
display the applicable non-PIT limitations.

## Outcome

Automate the full chain from approved source data to a publicly verified result
without mixing projects, fabricating data, weakening analysis, or confusing a
successful workflow step with a fresh webpage.

The authoritative computation remains the project-owned Python/worker entrypoint
unless the user explicitly approves an analysis change.

## Project-owned source registry

Each active automated or public data pipeline must own a non-secret registry
for every source it uses:

- stable source ID, provider, endpoint or collector entrypoint;
- required, optional, benchmark, or fallback role;
- data fields and economic meaning supplied;
- provider-rights basis and public-display boundary;
- authentication **secret names only**, never values;
- provider timezone, market/session calendar, expected release window and lag;
- a machine-readable `allowed_lag_seconds` ceiling and the project
  calendar/release-window evaluator used to derive the latest expected date;
- a machine-readable `maximum_source_age_seconds` ceiling measured against the
  successful run time, so a receipt cannot make old data look current by merely
  lowering its self-reported expected date;
- rate limit, timeout, bounded retry and cache policy;
- raw snapshot path, normalized artifact, schema/version and precision;
- source `as_of`, collection timestamp and provenance/hash fields;
- missing, partial, stale, revision and fallback policy.

Every run records all required-source receipts and an explicit status for each
optional, benchmark or fallback source. A succeeded optional source is bound to
the source manifest like a required source; a degraded, unavailable or skipped
source remains in collection evidence and may be omitted from the analysis input
only under the project's explicit degraded-result contract. Silent omission is
not allowed.

Each succeeded-source receipt records `source_as_of`,
`expected_source_as_of`, `coherent_through`, calculated
`observed_lag_seconds`, and the manifest-owned `allowed_lag_seconds`. Required
sources also record `observed_age_seconds` and the manifest-owned absolute age
ceiling. They fail closed when either calculated lag or absolute age exceeds its
allowance. The run
`data_as_of` is the minimum required `coherent_through`, and freshness evidence
records the calendar evaluator and evaluation time. A non-succeeded optional
source must record reason, impact, fallback state, and—if used—the last-good
source date. It may publish only under an explicit degraded policy, with
`publication_state=degraded` bound through the result and browser evidence.
A source whose policy is `fail-closed` cannot be silently downgraded.

Do not merge source registries, credentials, calendars, fallback rules, or data
semantics across projects merely because the infrastructure is shared.

## Authoritative pipeline

Treat these as separate, observable gates:

1. **Collect** — fetch each source into an immutable or content-addressed raw
   snapshot; record provider response state and source `as_of`.
2. **Validate** — enforce the rights needed for the selected publication or
   redistribution, plus schema, types, units, dates, duplicates, coverage,
   null limits, the claim-selected revision/PIT policy, and source-specific
   quality rules.
3. **Normalize** — create the existing canonical analysis input without changing
   formulas or silently filling unavailable values.
4. **Coherent cutoff** — derive the latest mutually valid data boundary from
   required sources, market calendars and release lags. “Fetched most recently”
   is not automatically “latest valid”.
5. **Analyze** — invoke the existing authoritative Python/worker entrypoint with
   canonical requested/effective inputs and the validated data-manifest hash.
6. **Validate result** — verify schema, finite values, dates, invariants,
   determinism where required, result identity and artifact bytes/SHA-256.
7. **Stage** — write versioned result artifacts and a candidate manifest without
   replacing the last-good public pointer.
8. **Publish** — update the public artifact/current pointer only after every
   required upstream gate passes.
9. **Deploy** — build or publish the frontend when needed; a code-only deployment
   must not imply that data or analysis refreshed.
10. **Public readback** — fetch the public HTML and authoritative data/result
    artifact, then verify project ID, data `as_of`, result/run identity, schema,
    code/data/artifact hashes and representative values.

A single workflow may implement several stages, but its evidence must still
distinguish them.

## Required identities and timestamps

Keep these roles distinct:

- per-source `source_as_of`;
- `collected_at`;
- coherent analysis `data_as_of`;
- `calculated_at`;
- `staged_at`;
- `published_at`;
- public `verified_at`;
- project ID, run ID, result key;
- requested and effective config hashes;
- input, data and result schema versions;
- code version, data-manifest hash and result artifact SHA-256.

The frontend adopts a result only when its project and result identity match.

Use sidecar manifests when the protected project result JSON cannot change:

- the source/data manifest lists each required source's relative artifact path,
  byte size, SHA-256, source date and collection time, plus the canonical
  analysis-input path, size and hash;
- the analysis-request manifest stores canonical requested/effective config
  objects, recomputed hashes, fallback state, input-schema version/hash,
  data-manifest hash and canonical analysis-input hash;
- an analysis-input validation capture binds the exact input and schema hashes,
  validator command/version, authoritative entrypoint hash, workflow commit,
  pass result, and check time; malformed JSON or an invalid capture blocks
  completion;
- the result manifest binds project/run/date, code and schema versions,
  requested/effective configuration, analysis-request, data-manifest and
  analysis-input hashes, and the unchanged result artifact's path, size and
  hash;
- project-owned JSON-pointer assertions bind identity fields already present in
  the unchanged result JSON (for example project, run or data date); do not add
  or rename result fields merely to satisfy a generic template;
- a browser binding capture records the public result URL/hash and the rendered
  frontend URL/hash together with the adopted project/run/date/result identity;
- a browser-captured DOM fragment must expose the standard
  `data-quant-result-binding` marker and matching project, run, date, result,
  result-manifest, requested/effective config and input-schema attributes.
- captured public-pointer bytes before and after publication bind the last-good
  generation to the selected candidate; deterministic ordering evidence must
  show both that an older late-finishing candidate loses and that a failed
  candidate leaves the previous pointer unchanged. Bind the isolated test
  namespace, exact command, exit code and captured output bytes/SHA-256; a
  receipt-authored success boolean alone is not completion evidence.

These sidecars strengthen delivery evidence without rewriting project-owned
analysis formulas, Python, result schemas or existing public JSON contracts.

## Schedule contract

For every automated schedule, record:

- workflow file and exact job/entrypoint;
- workflow head commit and authoritative analysis-entrypoint bytes/SHA-256;
- cron expression, cron timezone and business/market timezone;
- calendar and holiday behavior;
- expected source-availability window and allowed lag;
- idempotency key and duplicate-run behavior;
- concurrency group and cancellation policy;
- timeouts, retryable versus permanent errors and retry ceiling;
- manual dispatch/backfill mode and its separate authority;
- required secret names and provider prerequisites;
- retention, storage growth and zero-spend bounds;
- last-good and recovery behavior;
- owner, alert/evidence destination and public readback target.

Verify that the schedule exists on the active default branch and is enabled.
Workflow-file presence or a parsed cron string is not proof that scheduled runs
execute successfully.

For completion, hash the active workflow file and capture a provider run record
that binds the schedule event, default branch, full head commit, run ID/URL,
successful required job, successful cost-preflight and collection/analysis step
IDs, completed-step count and completion time. A skipped/conditional required
job, manual dispatch, disabled schedule, different branch or future-dated record
cannot prove scheduled automation.

The analysis code version must equal the scheduled workflow head SHA. Required
cost-preflight and pipeline steps must have both `outcome=success` and
`conclusion=success`. Required jobs and steps must not declare
`continue-on-error` at all—not even `false` or an expression—because expression
evaluation can turn a failed preflight into a successful final conclusion.

## Partial failure and recovery

- Required-source failure: do not publish a new authoritative result.
- Optional-source failure: publish only when the project contract allows a
  degraded result and the missing contribution is explicit.
- Stale source: apply the project's allowed-lag rule; never relabel it as current.
- Schema failure: fail closed for the affected pipeline.
- Rights failure or uncertainty: fail closed for unsupported public display or
  raw redistribution, not for an otherwise permitted private analysis. Try an
  eligible free source, permitted aggregation or derivation, private output, or
  narrower claim before declaring the whole objective blocked.
- Provider revision: preserve provenance and use the project's frozen-history or
  backfill policy.
- Analysis or artifact failure: retain the last-good public pointer.
- Publish or readback failure: keep the candidate non-current, restore or retain
  last-good, and report the exact failed gate.
- Retry: bounded, idempotent, and unable to create conflicting current results.
- An older or slower run that completes after a newer valid run must not overwrite
  the newer public/current pointer; compare cutoff/result generation and use an
  atomic conditional publish.

Do not replace a valid historical value with `0`, an empty result, an invented
fallback, or an unrelated source.

## Verification matrix

At minimum, use deterministic fixtures or safe dry runs for:

- each source success plus one required-source failure;
- optional-source degraded behavior when supported;
- stale, malformed, duplicate, missing and revised observations;
- calendar boundary, weekend/holiday and release-lag behavior;
- same data/config determinism;
- changed input or changed data-manifest identity reaching the result;
- failed analysis leaving last-good public state unchanged;
- duplicate schedule/run idempotency and concurrency;
- an older run finishing after a newer run cannot replace the newer current
  result;
- candidate artifact hash mismatch;
- code deploy without data refresh;
- end-to-end source → analysis → staged artifact → public readback.

Live provider checks complement fixtures; they do not replace them.

## Existing and new projects

For an existing project:

- audit and preserve current collectors, schedules, workflows, schemas, Python
  entrypoints, public paths and last-good behavior before changing delivery;
- repair only proven defects within the authorized scope;
- compare pre/post schedule and public-data evidence.

For a new project:

- define the source registry, use-specific rights, cutoff, schemas, schedules,
  failure states, result identity, public path and free-only fallback before
  enabling automation;
- start with a manual end-to-end run and public readback;
- enable the schedule only after deterministic and failure-path tests pass.

## Completion evidence

Automation is complete only when evidence proves:

- every required source was valid for the coherent cutoff;
- authoritative analysis consumed the matching validated artifact;
- the versioned result passed result validation;
- publication changed only the intended project and target;
- the public page and data artifact read back with the expected identity/date;
- failure tests preserved last-good behavior;
- the recurring path is enabled, bounded and compliant with the cost contract.

The completion validator must recompute source artifacts, canonical analysis
input, source/data manifest, analysis-request manifest and canonical requested/
effective config hashes, result manifest, authoritative result, captured
public-result, captured frontend and browser-binding hashes and sizes. It must
also hash the active workflow and inspect the captured workflow-run record.
These checks prove internal consistency of supplied captures; provider
authenticity still depends on the integration owner obtaining them directly
from the live provider/public readback and retaining command or tool provenance.
Locally invented JSON, hashes, run IDs or HTTP claims are never independent live
proof.
