# Quant Research frontend foundation

This directory is the reusable delivery layer for the Quant Research
dashboards. It owns presentation contracts and analysis-run orchestration; it
does not own or reimplement any project's Python calculation.

## Choose the integration mode first

| Project behavior | Integration |
| --- | --- |
| The page filters or selects an already generated result | Static result adapter; no analysis API |
| A user changes inputs that must create a new Python result | Control API plus the project's existing Python worker |
| The calculation currently runs in browser JavaScript | Keep that engine until deterministic Python parity is proven |

`display` and `result_selector` controls must never submit a run. Only
`analysis` controls enter `draftConfig → pendingRun → boundResult`.

## Packages

- `packages/ui`: compact controls, cards, tables, disclosures, and theme
- `packages/shell`: canonical navigation and page shell
- `packages/charts`: chart frame, external exact-value readout, selection
- `packages/contracts`: control, run, artifact, and binding schemas
- `packages/data-client`: static/API transport and isolated session state
- `packages/project-registry`: stable platform ids and public-summary mappings
- `packages/testing`: shared contract and interaction fixtures
- `templates/dashboard`: starting point for a new dashboard
- `apps/reference-dashboard`: executable contract and visual reference

Project-specific series meanings, table columns, result schemas, and analysis
logic remain in the project repository.

## Visible copy contract

Page and section supporting prose is absent by default. `PageHeader` and
`SectionHeading` accept only an optional `supportingCopy` object with a stable
project-owned `copyId`, one of the four approved intents, and a concrete reason.
There is no placeholder description in the dashboard template.

Do not put project wording in a shared package. Each project keeps its retained
visible-copy allowlist and rendered-state fixtures in its own repository.
Standard pointer, click, tap, and keyboard instructions belong in semantics
such as `aria-keyshortcuts`, screen-reader-only copy, or a closed help
disclosure; interaction tests assert the resulting state and ARIA, not an exact
Korean sentence.

Use the dependency-free root `scripts/copy-audit.mjs` with a project-local
config after the canonical design-prompt branch is integrated. It accepts
rendered HTML fixtures from React/TypeScript or static HTML apps and a secondary
source-scan mode. Mark retained prose with
`data-copy-role`, `data-copy-id`, `data-copy-intent`, and
`data-copy-reason`; mark accessibility and operations channels with
`data-copy-channel="sr-only|operations"`. Mark input errors and changing
loading/error/run states with `data-copy-channel="validation|runtime-status"`
and test their `aria-live` and recovery behavior separately.

The dashboard template includes `copy-audit.config.json` with a source fallback
and an empty retained-copy allowlist. When creating an app, change the
`projectId` and add rendered fixtures for its default, selected, loading, empty,
degraded, and error states. Do not add another project's wording to that file.

## Local validation

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm run check
```

To inspect the reference UI:

```bash
pnpm --filter @quant-research/reference-dashboard dev
```

The analysis panel is closed by default. The reference app demonstrates state
separation and binding behavior; its sample result is not production data.

## Adopting the frontend

Until these packages have an immutable tagged release, a project may vendor
only the presentation seam it needs. The vendored snapshot must include:

1. upstream package version;
2. upstream source hashes;
3. each copied file's SHA-256;
4. a build-time aggregate fingerprint check.

Do not use sibling-worktree `file:` dependencies or cross-origin runtime
imports. Once a release exists, replace the snapshot with a lockfile- and
integrity-pinned package.

Static projects must keep same-origin, GET-only, fail-closed data loaders and
must prove generated JSON is byte-identical before and after the frontend
build. Analysis projects must additionally prove every input reaches the
existing Python argument and that the returned artifact is bound to the
server-issued run/config/data/code identities.

## Preview and API

`vercel.json` builds only the reference frontend. In Vercel, set this
repository's project root to `platform`; Preview is for UI review and does not
replace GitHub Pages production data.

The FastAPI service lives in `services/control-api`. It validates and
dispatches jobs but never runs long analysis in the request process. Production
uses the Supabase-backed durable store and a separately authenticated GitHub
Actions worker. See its README and `infra/supabase` before enabling it.

No Supabase secret or legacy service-role key, GitHub token, provider
credential, or owner run token may appear in a browser bundle, public JSON, or
`NEXT_PUBLIC_*`/`VITE_*` variable.
