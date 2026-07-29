# Capability: scheduled automation

Activate for recurring or event-driven work. It does not imply analysis, data
collection, or publication; declare those separately when present.

- Verify the active default-branch schedule, timezone, calendar/availability
  lag, idempotency, concurrency, timeout, bounded retries, retention, manual
  recovery/backfill, and last-good behavior.
- Put fail-closed zero-cost/quota preflight before every remote/provider action.
- Distinguish schedule configuration, job start, collection, computation,
  publication, deployment, and readback.
- Prove required failure does not advance current state and an older late run
  cannot overwrite a newer valid run.
- A workflow file or successful trigger is not evidence that the scheduled
  outcome is current.

Evidence gates: `schedule`, `cost`.
