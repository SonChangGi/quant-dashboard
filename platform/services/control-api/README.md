# Quant Research Control API

This FastAPI service is a durable control plane, not a second analysis
implementation. It validates project-owned input contracts and dispatches the
existing GitHub Actions/Python workers. Heavy analysis never runs in the API
process.

The adapter registry currently contains:

| projectId | input contract | hash contract | worker |
| --- | --- | --- | --- |
| `best-factor` | exactly 11 fields, `best-factor/v1` | `best-factor-python-json-v1` | `SonChangGi/best-factor`, `update-dashboard.yml` |
| `momentum` | exactly 26 `ResearchInputs`, `momentum/v2` | `momentum-research-inputs-rfc8785-v1` | `SonChangGi/momentum-factor-lab`, `controlled-analysis.yml` |
| `fear-greed` | 16 visible inputs serialized as exactly 17 fields, `fear-greed/control-inputs-v1` | `fear-greed-json-sort-keys-sha256-v1` | `SonChangGi/fearNgreed`, `controlled-analysis.yml` |

Project adapters own normalization, hashing, fallback policy, workflow input
mapping, artifact URL allowlists, code-version syntax, and result binding.
Adding a project must add an adapter and provider target rather than weakening a
shared generic validator.

## HTTP protocol

- `GET /healthz`: process liveness only.
- `GET /readyz`: verifies the authoritative store and every enabled provider.
  Production also requires Supabase, GitHub Actions, and the dispatch pump.
- `GET /v1/projects/{projectId}/capabilities`
- `POST /v1/projects/{projectId}/runs`
- `GET /v1/runs/{runId}`
- `GET /v1/runs/{runId}/result`
- `POST /v1/internal/runs/{runId}/result-manifest`
- `POST /v1/internal/runs/{runId}/failure`

Run creation requires a client-generated 8-128 character `Idempotency-Key` and,
when configured, `Authorization: Bearer <owner token>`. Idempotency is isolated
by project and covers the complete normalized request.

Best Factor requires all 11 inputs. Momentum requires all 26 public
`ResearchInputs`; `evaluationWindowDays` is an authoritative integer from 252
through 2520 sessions, while derived `version` is rejected as a duplicate
source of truth. Fear & Greed's 16 visible controls serialize to 17
wire fields because the composite evaluation-window control binds `window`,
`historyStart`, `historyEnd`, and `historyEndMode` independently. All three
controlled-run adapters require `allowFallback=false`.

## Dispatch durability

Supabase creates the run and dispatch-outbox row in one transaction. Dispatchers
claim a short lease, call the project-specific GitHub workflow, and atomically
persist the acknowledgment. Failed calls use bounded exponential backoff and
become a dead-lettered failed run after retry exhaustion.

If the process dies after GitHub accepted a dispatch but before acknowledgment,
the next lease owner reconciles by the exact control run ID in that project's
workflow title. It never selects a "latest" workflow run. An authenticated
result callback can also atomically acknowledge a still-queued run, closing the
same crash window without causing a second dispatch.

Acknowledged runs that produce neither a result nor a failure callback are
failed by the reaper. The default result timeout is four hours because the
Momentum workflow itself permits 180 minutes plus publication/readback time.
`validating` runs are also reaped, and lagging provider observations cannot
regress `validating` back to `running` or `dispatched`.

## Worker callbacks

Both internal endpoints require
`Authorization: Bearer <worker callback token>`.

A result manifest contains:

- exact run/schema/config binding;
- requested, normalized, and effective inputs;
- ignored-input and fallback evidence;
- data date and source identity;
- immutable code and artifact identity;
- a maximum 64 KiB bounded result summary.

The API fetches the full immutable artifact without redirects, query strings,
userinfo, or non-standard ports, then verifies SHA-256 and byte size before
project-specific semantic binding.

Best Factor accepts only:

`https://raw.githubusercontent.com/SonChangGi/best-factor/<40hex>/docs/data/latest-results.json`

Its `codeVersion` is a bare 40-character worker commit SHA. The callback
`payload` is not the 5+ MiB artifact. It must exactly equal:

```json
{
  "schema_version": 1,
  "generated_at": "<artifact generated_at>",
  "summary": {
    "...": "only allowlisted scalar fields copied from artifact.summary"
  }
}
```

The allowlisted summary fields are:
`best_composite_score`, `best_factor`, `best_factor_holdout_cagr`,
`best_factor_holdout_rank`, `best_factor_holdout_sharpe`, `data_end_date`,
`effective_factor_count`, `factor_library_size`, `factor_preset`, `fetched_at`,
`holding_count`, `interpretation_label`, `provider`, `ranking_count`,
`selected_factor_count`, `source_hash`, `tested_factor_count`, and
`universe_as_of_date`. Missing optional fields are omitted; extra artifact
summary fields are not copied. The API reconstructs this object from the fetched
artifact and requires exact equality.

Momentum accepts only:

`https://sonchanggi.github.io/momentum-factor-lab/data/control-runs/v1/<safeRunId>/<64hexResultKey>.json`

Its artifact contract is `momentum/schema-v5-control-result-v1`, and
`codeVersion` must be
`github:SonChangGi/momentum-factor-lab@<40hex>`. The callback payload is the
worker's bounded schema-v5 summary: schema/version identity, `resultKey`,
`resultIdentity`, complete derived `researchInputs`, selected factor and
weighting policy, data identity, selected-security count, and at most 50
holdings. The fetched artifact remains the full schema-v5 result. The adapter
binds the summary fields to the full artifact; it does not require the bounded
summary to equal the entire artifact.

Fear & Greed accepts only:

`https://sonchanggi.github.io/fearNgreed/data/control-runs/v1/<safeRunId>/<64hexResultKey>.json`

Its artifact contract is `fear-greed/control-result-v1`, and `codeVersion` must
be `github:SonChangGi/fearNgreed@<40hex>`. The result key is reproduced from
the exact run/schema/config binding, data identity, and immutable worker code
identity. The fetched artifact atomically contains `signals`, `event`, and
`strategy`; the callback keeps only the allowlisted bounded summary plus the
result, data, and code identity needed to retrieve and verify that artifact.
The summary allowlist is `signalDate`, `signalState`, `signalPercentile`,
`eventAsset`, `eventSample`, `eventCount`, `strategyPosition`,
`strategyStatus`, `strategyTotalReturn`, and `methodologyVersion`.

A worker failure callback has this exact shape:

```json
{
  "binding": {
    "projectId": "momentum",
    "runId": "<control UUID>",
    "inputSchemaVersion": "momentum/v2",
    "inputSchemaHash": "<64hex>",
    "configHashAlgorithm": "momentum-research-inputs-rfc8785-v1",
    "configHash": "<64hex>"
  },
  "errorCode": "worker_analysis_failed",
  "errorMessage": "bounded non-secret diagnostic",
  "providerRunId": "github-actions:<control UUID>",
  "occurredAt": "2026-07-24T00:03:00Z"
}
```

`errorCode` is one of `worker_workflow_failed`, `worker_analysis_failed`, or
`worker_publication_failed`. Terminal results are immutable. An exact failure
replay is idempotent; conflicting or late terminal evidence returns `409`.

## Local development

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run quant-control-api
```

Development defaults to the disabled provider and in-memory store. Tests inject
deterministic providers. Copy `.env.example` to configure a real service.

## Production configuration

Apply every file in `platform/infra/supabase/migrations/` in chronological
order, then set at least:

```dotenv
QUANT_CONTROL_ENV=production
QUANT_CONTROL_STORE=supabase
QUANT_CONTROL_PROVIDER=github-actions
QUANT_CONTROL_GITHUB_ENABLED=true
QUANT_CONTROL_DISPATCH_PUMP_ENABLED=true
QUANT_CONTROL_WORKER_RESULT_TIMEOUT_SECONDS=14400
QUANT_CONTROL_SUPABASE_URL=https://<project>.supabase.co
QUANT_CONTROL_SUPABASE_SECRET_KEY=<server-only sb_secret key>
QUANT_CONTROL_GITHUB_TOKEN=<server-only>
QUANT_CONTROL_FEAR_GITHUB_REPO=fearNgreed
QUANT_CONTROL_FEAR_GITHUB_WORKFLOW=controlled-analysis.yml
QUANT_CONTROL_RUN_API_TOKEN=<owner-only>
QUANT_CONTROL_WORKER_CALLBACK_TOKEN=<worker-only>
```

The remaining lease, retry, polling, batching, project target, and CORS
variables are documented in `.env.example`.

`QUANT_CONTROL_ENV` accepts only `development`, `test`, `staging`, or
`production`. Enabling the GitHub Actions provider in any environment requires
the durable Supabase store and dispatch pump; a live worker can never be paired
with the volatile in-memory queue.

Build the non-root Python 3.11.15 container with:

```bash
docker build -t quant-control-api .
docker run --env-file .env -p 8000:8000 quant-control-api
```

The image installs production dependencies from `uv.lock` with
`uv sync --locked --no-dev`; dependency resolution cannot drift during a
container build.

Deploy this long-running API on a container service that supports background
work and graceful shutdown. Vercel is for the frontend and preview deployments
only; do not deploy this dispatch pump as a Vercel serverless function.

The current `sb_secret_` key is sent only in Supabase's `apikey` header because
it is not a JWT. Existing projects may temporarily use the legacy
`QUANT_CONTROL_SUPABASE_SERVICE_ROLE_KEY`; only that JWT form receives a
bearer header.

Never expose GitHub tokens, owner/worker tokens, or either Supabase server key
through `VITE_*`, `NEXT_PUBLIC_*`, static JSON, or browser JavaScript.
