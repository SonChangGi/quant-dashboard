# Quant Research Platform Architecture v1

> Status: implementation contract
>
> Audited: 2026-07-24
>
> Scope: Quant Research Hub and the six completed dashboards

This document separates presentation, calculation, orchestration, and publication without replacing the existing Python analysis or GitHub Pages contracts.

## 1. Decision

Use a shared TypeScript frontend foundation for all dashboards. Add a control API only where a user can request a new analysis.

Do not force every project through FastAPI:

| Project | Current calculation boundary | Target |
| --- | --- | --- |
| DRAM Price | Python collection → validated static JSON | TypeScript UI + static result adapter |
| ETF Tracking | Python collection/analysis → validated static JSON | TypeScript UI + static result adapter |
| SOX | Python collection/analysis → validated static JSON | TypeScript UI + static result adapter |
| Best Factor | 11 inputs → GitHub Actions → existing Python CLI | First control-API and remote-worker pilot |
| Momentum Factor | preset or local job API → existing Python analysis | Adapt existing run identity behind the common API |
| Fear & Greed | published history + browser scenario engine | Preserve current engine until JS/Python parity is proven |

The existing GitHub Pages URLs and `/data/*.json` endpoints remain canonical public snapshots and permanent fallbacks during the migration.

## 2. Protected boundaries

- Python collection, normalization, scoring, ranking, portfolio, strategy, and backtest calculations remain the source of truth.
- Existing JSON fields, dates, units, precision, result identity, Pages paths, and automation schedules are not rewritten for frontend convenience.
- The API validates and dispatches. It does not reimplement a calculation and does not run long jobs in its web process.
- Large artifacts remain immutable files. The database stores identity, status, hashes, locations, byte sizes, and small summaries.
- A draft input never relabels a saved result.
- A failed, stale, or mismatched run never falls back to the latest result while presenting it as the requested run.

## 3. Repository shape

The Hub repository owns reusable delivery code:

```text
platform/
  apps/
    reference-dashboard/
  packages/
    ui/
    shell/
    charts/
    contracts/
    data-client/
    project-registry/
    testing/
  templates/
    dashboard/
  services/
    control-api/
  infra/
    supabase/
```

Each analysis repository continues to own its Python modules, workflows, generated results, and public URL. Existing frontends consume versioned shared packages gradually; project-specific view-models, chart renderers, table schemas, and analytical meanings remain local.

Until the shared packages have a tagged, immutable distribution, an existing
repository may vendor only the compatible frontend seam. That snapshot must
record the shared version, upstream source hashes, every vendored-file SHA-256,
and one aggregate fingerprint. Its build must verify the fingerprint and remain
independent: no `file:` dependency on another worktree and no runtime import
from another Pages origin. After a tagged package or release archive exists,
projects may replace the snapshot with a lockfile- and integrity-pinned release.
This changes delivery code only; it never moves a project calculation into the
shared package.

## 4. Control registry

Every visible control has exactly one kind:

| Kind | Meaning | Creates a run |
| --- | --- | --- |
| `display` | Sort, search, highlight, chart date, visible row count | No |
| `result_selector` | Select an already published date, preset, or result | No |
| `analysis` | Request a new authoritative calculation | Yes |
| `operation` | Backfill, refresh, republish, or another owner operation | Separate owner path |

Each project keeps a machine-readable registry containing the UI id, canonical key, schema version, type, unit, range, default source, serialization, authoritative engine parameter, expected result paths, legitimate no-op conditions, and binding test.

Platform identities are stable and do not require rewriting an existing public
`summary.json` identity:

| Dashboard | Platform project id | Existing public summary id |
| --- | --- | --- |
| Fear & Greed | `fear-greed` | `fearngreed` |
| Momentum Factor | `momentum` | `momentum` |
| DRAM Price | `dram` | `dram` |
| Best Factor | `best-factor` | `best` |
| ETF Tracking | `etf` | `etf` |
| SOX | `sox` | `sox` |

The boundary adapter owns this explicit mapping. It must validate both values
and must never change a generated public JSON field merely to match an API
route or navigation id.

## 5. Run and artifact identity

A run binds all of the following:

```json
{
  "projectId": "best-factor",
  "runId": "uuid",
  "inputSchemaVersion": "best-factor/v1",
  "requestedInputs": {},
  "normalizedInputs": {},
  "effectiveInputs": {},
  "ignoredInputs": [],
  "fallbacks": [],
  "configHash": "sha256",
  "effectiveConfigHash": "sha256",
  "dataSnapshot": {
    "asOf": "YYYY-MM-DD",
    "hash": "sha256"
  },
  "codeCommit": "git-sha",
  "engineVersion": "string",
  "artifact": {
    "url": "immutable-url",
    "sha256": "sha256",
    "byteSize": 0,
    "contractVersion": "string"
  }
}
```

Canonical JSON is hashed after schema validation and normalization. `configHash` binds the normalized requested configuration and stays stable for the run. `effectiveConfigHash` binds the settings the worker actually applied. They must be equal when there is no fallback; an explicitly allowed fallback may make them differ only when every difference has a structured fallback record.

The API and worker must use the project/version-specific algorithm named by the capability contract. The frontend treats both server hashes as authoritative and compares the exact values across create, status, and result responses; it does not guess a legacy Python number serialization with `JSON.stringify`.

`requestedInputs` and `effectiveInputs` may differ only when the request explicitly opted into a documented fallback. Otherwise the run fails closed.

## 6. API

```text
GET  /v1/projects/{projectId}/capabilities
POST /v1/projects/{projectId}/runs
GET  /v1/runs/{runId}
GET  /v1/runs/{runId}/result
```

`POST /runs` returns `202`, `runId`, `configHash`, and the initial status. Reusing
the same `Idempotency-Key` with the same normalized request replays the existing
run; reusing it with different inputs is a conflict. A new key may create a new
run because the worker's data snapshot and code identity are not known at
submission time. Result reuse is allowed only after exact
project/config/data/code/engine/artifact identity is known and verified.

Run states:

```text
queued → dispatched → running → validating → published
                                             ↘ failed
queued | dispatched | running                → cancelled
```

The first remote provider is the existing GitHub Actions workflow. A provider adapter may later dispatch Cloud Run Jobs or another worker without changing the public API.

The control API process never executes a 35–180 minute analysis itself.

## 7. Frontend state

Each analysis form keeps four distinct values:

```text
appliedConfig  settings bound to the visible published result
draftConfig    user edits not yet applied
pendingRun     queued/running request and its config hash
boundResult    successful artifact whose full binding was verified
```

The input summary remains visible while the form body is collapsed by default. Cards, charts, and tables switch only after the requested config hash, input schema, data snapshot, code version, and artifact hash have all been accepted.

Without a configured control API, a page stays in static mode. It may offer an accurately labelled command-copy or owner-workflow link, but it must not label that action `적용` or `재계산`.

## 8. Storage and publication

Supabase Postgres stores:

- `projects`
- `data_snapshots`
- `analysis_configs`
- `analysis_runs`
- `analysis_artifacts`

Large JSON/CSV artifacts use content-addressed Supabase Storage paths. PostgreSQL rows contain only the immutable object location, SHA-256, byte size, contract version, and a bounded summary.

Anonymous users may read only published project, snapshot, run, and artifact views. Authenticated owners may request runs. Only a worker or server secret role may update worker state or publish artifacts. A Supabase secret key (or legacy service-role key), provider credential, or GitHub token must never enter a browser bundle.

Publication is additive:

1. Existing Python job writes the current validated artifact.
2. A publisher verifies it and calculates hashes.
3. The publisher writes the immutable Storage object and metadata.
4. The existing Pages artifact is published unchanged.
5. Only a fully verified record becomes current.

During dual-write, a Supabase failure does not destroy or replace a valid Pages publication. The previous database current pointer remains and the mirror records a degraded state.

## 9. Preview and production

Vercel is initially a pull-request preview surface only:

- preview data origin points to the current read-only GitHub Pages data;
- a preview cannot update production records or current pointers;
- a successful preview proves UI behavior, not a successful analysis run;
- Pages remains the public production host until parity and operational checks are complete.

No deployment secret or provider account id is committed. Project linking is an explicit environment step after local tests pass.

## 10. Delivery order

1. Freeze `web-design.md` input/result rules and the six-project control inventory.
2. Build shared TypeScript packages, a reference app, and a new-dashboard template.
3. Add Vercel preview configuration without changing production hosting.
4. Add Supabase migrations, RLS, Storage policies, and a nonblocking publisher.
5. Connect Best Factor to the control API and its existing Actions/Python worker.
6. Adapt Momentum's existing local run contract to the common remote protocol.
7. Prove Fear & Greed JS/Python parity before changing its calculation boundary.
8. Migrate DRAM, ETF, and SOX presentation code to shared packages without adding analysis APIs.
9. Let the Hub read published metadata first with existing `summary.json` fallback.
10. Reconsider production hosting only after public parity, rollback, and cost evidence.

## 11. Local implementation status

The ordered implementation is complete in isolated, uncommitted worktrees.
External activation is intentionally separate from implementation:

| Delivery step | Local status | Production boundary |
| --- | --- | --- |
| Input/result rules and six-project inventory | Complete in `web-design.md` v2.2.1 and the control audit | Document is not yet merged |
| Shared TypeScript packages, reference app, template | Complete and build-tested | No existing Pages URL changed |
| Vercel Preview configuration | Complete | Project linking and deployment were not requested |
| Supabase schema, RLS, durable outbox, publisher contracts | Complete and API-tested | Migration was not applied without a target project |
| Best Factor remote worker | Complete in companion worktree | API URL, tokens, merge, and deployment remain gated |
| Momentum remote worker | Complete in companion worktree | API URL, tokens, merge, and deployment remain gated |
| Fear & Greed parity gate | Complete | Backend migration is intentionally blocked until the recorded semantic gaps are resolved |
| DRAM, ETF, and SOX shared-frontend seams | Complete and independently build-tested | Their existing production pages and static data contracts remain unchanged |
| Hub optional published-metadata read | Complete with static JSON fallback | Disabled unless explicit public Supabase configuration is supplied |
| Production hosting reconsideration | Not performed by design | Requires public parity, rollback, operations, and cost approval |

Docker image construction and applying the Supabase migration are CI/deployment
environment checks because this workstation has neither a Docker runtime nor a
configured Supabase target. CI contains a locked Docker build gate.

## 12. Required evidence

- Every control appears exactly once in its registry.
- Every `analysis` control reaches a real worker argument and a new config/run identity.
- Deterministic A/B fixtures prove the expected affected result path for each analysis input.
- Every `display` control leaves the config hash, run identity, worker command, and result unchanged.
- The same input/data/code/engine produces the same material result hash.
- Requested and effective inputs are equal with matching config hashes, or explicit fallback consent, a distinct effective hash, and complete fallback records are present.
- Queued, failed, stale, cancelled, and binding-mismatch states never adopt an unrelated result.
- Static Pages fallback continues to load when the API or database is unavailable.
- Desktop, tablet, and mobile light/dark previews preserve the project's original analytical content.

## 13. Primary references

- [Vercel monorepos](https://vercel.com/docs/monorepos)
- [Vercel deployment environments](https://vercel.com/docs/deployments/overview)
- [Supabase Data API security](https://supabase.com/docs/guides/api/securing-your-api)
- [Supabase Storage access control](https://supabase.com/docs/guides/storage/security/access-control)
- [Supabase publishable and secret API-key migration](https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys)
- [FastAPI background-task caveat](https://fastapi.tiangolo.com/tutorial/background-tasks/#caveat)
