# Capability: backend or control plane

Activate only when server-side validation, authorization, persistence,
orchestration, or long-running execution is needed.

- Preserve the project's authoritative computation boundary. Introduce a
  separate worker only when the task needs one.
- Validate schemas and identities at boundaries; make mutating requests
  idempotent and retries conflict-safe.
- Browser code receives no provider, GitHub, database service-role, or other
  server secret.
- Expose queued/running/succeeded/failed/stale separately. Health/readiness does
  not claim job/result success.
- Verify callbacks and stored results against project, run, config, code,
  schema, data date, and artifact identities that the project uses.
- Preserve an existing fallback when it is an evidenced project contract.
  Do not invent a static fallback for every backend or new project.

Evidence gates: `integration`, `security`.
