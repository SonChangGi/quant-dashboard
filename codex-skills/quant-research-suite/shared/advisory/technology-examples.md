# Advisory: technology examples

These are examples, never default requirements.

- TypeScript can make frontend data and state contracts safer; it does not
  remove excessive copy or guarantee correct analysis binding.
- React and component libraries can improve reusable interaction and visual
  consistency; plain HTML/CSS/JS may remain the more complete solution for a
  small static page.
- FastAPI can validate and orchestrate existing Python jobs; Swagger UI is not
  the customer interface.
- PostgreSQL/Supabase can persist run identity and state; static JSON remains
  appropriate for immutable public results.
- Vercel can provide frontend previews; GitHub Pages or another existing route
  may remain the stable production/fallback.

Adopt a tool only with a named problem, owner, failure model, verification, cost
boundary, and exit/rollback path.
