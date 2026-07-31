# Capability: scheduled automation

Apply this rail for recurring or event-driven work. It does not imply analysis,
data collection, or publication; use those rails separately when present.

- Select only controls material to the actual runner and requested outcome. For
  a calendar trigger, verify its active host or branch when applicable,
  timezone, calendar, and source-availability lag.
- Where duplicate, overlapping, late, timed-out, or retried runs are possible,
  verify the relevant idempotency, concurrency, retry, retention, recovery,
  backfill, and last-good behavior.
- Put fail-closed zero-cost or quota preflight before each actual
  remote/provider action.
- Distinguish only the stages that exist, such as trigger, collection,
  computation, publication, deployment, and readback.
- If runs can race to advance shared current state, prove that required failure
  and older late runs cannot displace the newer valid result.
- A workflow file or successful trigger is not evidence that the scheduled
  outcome is current.
