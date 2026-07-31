# Adapter: Supabase

Supabase/PostgreSQL is optional persistence, not a universal project
requirement.

- Define migration ordering, rollback, ownership, retention, indexes, uniqueness
  and idempotency constraints before writes.
- Enable and test RLS for every browser-accessible table. Service-role keys stay
  server-only.
- Persist run metadata and identity without changing project-owned result
  semantics.
- A successful migration or row insert does not prove worker execution,
  frontend binding, publication, or public state.
- Verify free-plan quotas and retain cost hard stops before any cloud mutation.
