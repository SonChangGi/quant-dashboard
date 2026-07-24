# Supabase control-plane store

This migration creates the bounded metadata layer for analysis runs. It does
not replace the existing Python repositories, generated JSON, or GitHub Pages.

- `projects`: public capability metadata.
- `analysis_configs`: server-only canonical input identities.
- `analysis_runs`: server-only lifecycle and requested/normalized/effective
  input audit.
- `analysis_dispatch_outbox`: transactional dispatch intent, lease, retries,
  acknowledgment, and dead-letter evidence.
- `data_snapshots`: bounded summary and exact published artifact identity.
- `analysis_artifacts`: verified artifact URI, byte size, contract, and SHA.

The public views expose only active capabilities and verified published
artifacts. Raw run requests, errors, idempotency digests, and provider IDs stay
private. No browser write policy exists; the current Supabase secret key (or
legacy service-role key) is server-only.

`quant-public-snapshots` is readable and JSON-only. `quant-run-artifacts` is
private. Uploads rely on the server secret role and are not enabled for `anon` or
`authenticated`.

The control API can use this schema as its authoritative durable `RunStore`.
The server-secret-only RPCs provide:

- atomic create-or-replay behavior for `Idempotency-Key`;
- atomic run plus dispatch-outbox creation and callback acknowledgment;
- expiring multi-instance claims, bounded backoff, and retry exhaustion;
- immutable run/config identity checks;
- optimistic compare-and-swap updates and guarded state transitions;
- transactional publication of bounded snapshot and artifact identity.

Full result payloads are deliberately absent from JSONB. Only a project-bound
summary capped at 64 KiB is stored. After a restart, the API fetches the
immutable artifact and repeats byte-hash and semantic binding validation before
returning the bounded summary. GitHub Pages remains the display fallback, not a
mutable control identity.

The optional nonblocking dual writer exists only for migration experiments.
Production sets `QUANT_CONTROL_STORE=supabase`; the API refuses its process-local
in-memory store in production.
