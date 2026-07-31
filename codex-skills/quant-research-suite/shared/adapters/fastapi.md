# Adapter: FastAPI

FastAPI is an optional server boundary. Swagger UI is developer documentation,
not the end-user product.

- Use typed request/response schemas, explicit validation, stable error states,
  idempotency keys for mutation, authorization, and timeouts.
- Orchestrate the existing authoritative analysis worker rather than translating
  its formulas into the API layer.
- Separate health/readiness from queued/running/succeeded/failed/stale jobs.
- Bind accepted results to project, request/effective config, run, code/schema,
  data date, and artifact identity.
