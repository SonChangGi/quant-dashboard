# Developer Runbook

## Contents

- [Full-stack ownership without architectural mixing](#full-stack-ownership-without-architectural-mixing)
- [Control taxonomy](#control-taxonomy)
- [Result binding](#result-binding)
- [Web quality](#web-quality)
- [Backend quality](#backend-quality)
- [Automation quality](#automation-quality)
- [Release quality](#release-quality)

## Full-stack ownership without architectural mixing

The integration owner may implement frontend, backend, automation, and release, but each layer keeps a separate contract.

| Layer | Owns | Must not own |
| --- | --- | --- |
| Frontend | Display, input editing, selection, polling, binding, accessibility | Authoritative financial/data analysis |
| Control API | Validation, auth, idempotency, orchestration, run state | Rewritten analysis formulas |
| Worker | Existing collection and authoritative computation | UI presentation state |
| Storage | Versioned run/result metadata and access policy | Silent fallback logic |
| Automation | Schedule, session calendar, freshness, publication | Fabricated data |
| Release | Git/PR/CI/deployment/public proof | Unapproved scope or costs |

The integration owner must read `cost-and-authority.md` before any remote or
provider write, and `data-automation.md` whenever collection, analysis refresh,
scheduling, artifact publication, or public freshness is in scope.

## Control taxonomy

### Display

- changes only presentation;
- must not change canonical config, run identity, command, or result artifact.

### Result selector

- selects an existing result, snapshot, date, or entity;
- every official surface must bind to the same result identity;
- invalid selection must not silently fall back to latest.

### Analysis

- changes authoritative computation;
- must propagate through validated canonical config to the existing engine;
- must create or resolve a matching result identity and artifact.

### Operation

- triggers a refresh, export, release, or side effect;
- must disclose the actual action and state;
- requires the appropriate authority gate.

## Result binding

Recommended result metadata:

- project ID;
- run ID and result key;
- requested and effective inputs;
- input schema version;
- data as-of;
- code version;
- result schema version;
- artifact URL/path and SHA-256;
- status and failure/degraded reason;
- created, completed, and published timestamps.

The frontend may adopt a result only when the expected identity matches the artifact.

## Web quality

- Result and data date first.
- Supporting copy defaults to zero unless it adds dynamic result, interpretation guardrail, nonstandard action, or required disclosure.
- Keep operational details in one disclosure.
- Preserve meaningful page-specific charts and tables.
- Verify real rendered geometry and behavior, not listener presence.
- Do not use TypeScript or components as a substitute for information architecture.

## Backend quality

- Validate at boundaries.
- Make requests idempotent.
- Separate requested, normalized, and effective inputs.
- Preserve authoritative worker entrypoints.
- Keep secrets server-side.
- Use RLS/least privilege.
- Treat health, dispatch, completion, persistence, and publication as separate states.
- Keep retry policies bounded and fail fast on invalid auth, permanent errors, and contract mismatch.

## Automation quality

- For scheduled or publicly published pipelines, maintain a project-owned
  registry for every required, optional, benchmark, and fallback source; do not
  impose the full registry on a local exploratory analysis.
- Use only data that remains zero-charge without trials, expiring credits,
  automatic paid conversion, payment setup, subscriptions, PAYG, overage, paid
  add-ons, or paid tiers. Paid data is never a fallback.
- Use the real provider timezone, release lag, and market/session calendar.
- Snapshot and validate raw source artifacts before normalization or analysis.
- Derive a coherent cutoff across required sources; latest fetch time alone is
  not a valid `data_as_of`.
- Prefer cached history plus a bounded repair window for brittle providers.
- Bind analysis to the validated data-manifest hash and existing worker
  entrypoint.
- Validate result schema, identity, finite values, dates and artifact bytes before
  staging.
- Publish a versioned candidate before changing the public/current pointer.
- Gate publication on the rights needed for the fields and output actually
  exposed, plus freshness, schema, result, and identity. Rights uncertainty
  blocks unsupported publication or raw redistribution, not a permitted private
  analysis or free-source fallback search.
- Keep last-good data when collection, analysis, publication, or readback fails.
- Record degraded/unavailable honestly and never invent replacement values.
- Bound schedules with idempotency, concurrency, timeout, retry, retention and
  zero-spend limits.
- Verify the enabled default-branch schedule, generated artifact, deployment, and
  public HTML/data readback separately.

## Release quality

- Authenticate and verify repository access just before remote actions.
- Run the zero-spend command preflight before remote/provider actions. If cost is
  unknown, stop before issuing it. Paid data remains ineligible even when a
  non-data paid action could otherwise be separately authorized.
- Create a focused branch only when the current user request separately
  authorizes that local source-control mutation. Otherwise keep one writer in
  the current workspace and produce a bounded focused diff without creating a
  branch or worktree.
- Run tests before push and observe CI after push.
- Keep migration, API, worker, preview, Pages, and public readback separate.
- Save non-secret checkpoints for recovery.
- Do not remove fallback until the replacement meets parity and quality criteria.
