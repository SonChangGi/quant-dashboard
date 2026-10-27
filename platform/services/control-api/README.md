# Quant Research Control API

This FastAPI service is a durable control plane, not a second analysis
implementation. It validates project-owned input contracts and dispatches the
existing GitHub Actions/Python workers. Heavy analysis never runs in the API
process.

The adapter registry currently contains:

| projectId | input contract | hash contract | worker |
| --- | --- | --- | --- |
| `momentum` | exactly 26 `ResearchInputs`, `momentum/v3` | `momentum-research-inputs-rfc8785-v1` | `SonChangGi/factor`, `controlled-analysis.yml` |
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

Factor uses the stable `momentum` API ID and requires all 26 public
`ResearchInputs`; `evaluationWindowDays` is an authoritative integer from 21
through 2520 sessions, while derived `version` is rejected as a duplicate
source of truth. Fear & Greed's 16 visible controls serialize to 17
wire fields because the composite evaluation-window control binds `window`,
`historyStart`, `historyEnd`, and `historyEndMode` independently. Both
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

Best Factor is permanently retired. Its capabilities and run creation return
HTTP 410, independently of the optional integrated engine. It has no adapter,
worker provider, readiness dependency, accepted input schema, or artifact URL
allowlist. Legacy generic `QUANT_CONTROL_GITHUB_OWNER/REPO/WORKFLOW/REF`
settings are ignored; only the explicit Factor and Fear & Greed targets are used.

Factor uses the existing `momentum` API ID and accepts only these immutable paths:

- `https://sonchanggi.github.io/factor/data/control-runs/v1/<safeRunId>/<64hexResultKey>.json`
- Historical `https://sonchanggi.github.io/momentum-factor-lab/data/control-runs/v1/<safeRunId>/<64hexResultKey>.json`

Its artifact contract is `momentum/schema-v5-control-result-v1`, and
`codeVersion` must be
`github:SonChangGi/factor@<40hex>`; the historical
`github:SonChangGi/momentum-factor-lab@<40hex>` remains valid. The callback payload is the
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
    "inputSchemaVersion": "momentum/v3",
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

Build the non-root Python 3.11.18 container with:

```bash
docker build --pull --no-cache -t quant-control-api .
docker run --env-file .env -p 8000:8000 quant-control-api
```

The image installs production dependencies from `uv.lock` with
`uv sync --locked --no-dev`; dependency resolution cannot drift during a
container build.

### Certificate security updates

The [Render eMudhra advisory](https://render.com/docs/advisory-emudhra)
requires refreshing every trust store and rebuilding the image. This service
requires `certifi>=2026.10.19`, locked to `2026.10.23`. HTTPX remains at `0.28.1`.
Both Docker stages update Debian's `ca-certificates` and refuse versions below
`20250419~deb12u2`, the Bookworm fix in
[DLA-4845-1](https://security-tracker.debian.org/tracker/DLA-4845-1).
Keep `--pull --no-cache` for security rebuilds so old layers cannot skip updates.

Python `3.11.18`, pip `26.2.2`, and uv `0.13.4` address the same incident,
including build tools' separate bundled roots; see the
[Python security announcement](https://discuss.python.org/t/109576).
The hash-pinned pip bootstrap comes from that announcement. Do not replace it
with an unverified installer or disable certificate verification.

GitHub, Supabase, and artifact clients use HTTPX's verified defaults. HTTPX
normally loads certifi, but `SSL_CERT_FILE` or `SSL_CERT_DIR` can override it.
Before deployment, inspect whether those overrides or additional mounted CA
stores exist and update them separately. Do not print secret values or assume
that a local test proves the deployed store is safe.

After an independently approved deployment, confirm the deployed image/revision,
Python, pip, certifi and Debian CA versions. From the running service, use HTTPX
with its effective trust configuration and a fresh credential-free request to
both endpoints in the Render advisory. Each must fail specifically with
`CERTIFICATE_VERIFY_FAILED`; DNS errors and timeouts are inconclusive. Never
reuse authenticated GitHub/Supabase request headers for these probes. A normal
HTTPS control request should succeed. Then verify `/healthz` and `/readyz`
without dispatching an analysis run. Keep the deployment unverified until these
checks succeed; publishing source or a Pages build alone does not deploy this API.

The API CI job builds with fresh base layers, checks the non-root image's exact
Python/pip/certifi versions and Debian CA security floor, and runs
`scripts/verify_image_tls.py` via standard input. The script sends only a Host
header and exercises the actual service clients, system CA and pip's vendored CA.
It treats network failures other than certificate rejection as failures, then
CI starts the image and checks `/healthz`. No production environment or secrets
are passed to these containers. uv's pinned version is verified in the builder.

Deploy this long-running API on a container service that supports background
work and graceful shutdown. Vercel is for the frontend and preview deployments
only; do not deploy this dispatch pump as a Vercel serverless function.

The current `sb_secret_` key is sent only in Supabase's `apikey` header because
it is not a JWT. Existing projects may temporarily use the legacy
`QUANT_CONTROL_SUPABASE_SERVICE_ROLE_KEY`; only that JWT form receives a
bearer header.

Never expose GitHub tokens, owner/worker tokens, or either Supabase server key
through `VITE_*`, `NEXT_PUBLIC_*`, static JSON, or browser JavaScript.

## Optional local integrated research bridge

In development or test only, `QUANT_CONTROL_INTEGRATED_ENGINE_URL=http://127.0.0.1:50073` enables `/v2/momentum-integrated/capabilities` and `/v2/momentum-integrated/runs`. This route accepts the explicit integrated request contract and rejects legacy Best inputs. It does not change the existing Momentum adapter or enable a production provider. Without this environment variable the routes are absent.

### Factor repository transition

The current worker repository is `SonChangGi/factor`, its exact run title is
`Controlled Factor · <runId>`, and its static fallback is `/factor/data/dashboard.json`.
`QUANT_CONTROL_MOMENTUM_GITHUB_REPO` keeps its existing environment variable name;
set its value to `factor` in an existing deployment. The API project ID, all
`momentum/*` schemas, canonical input hashes, and historical artifact identities
remain unchanged. An explicitly configured previous worker repository is not silently
rewritten by the server. For stored immutable artifacts only, an unavailable old
Pages URL (404/410), or its exact Factor redirect, can be fetched from the identical
`/factor/` path. The stored identity stays unchanged and byte/SHA verification
remains mandatory; unrelated redirects and server errors fail closed.

Deploy this API code and apply `20261020071642_allow_factor_repository.sql` before
accepting callbacks with the new repository code version. The additive migration
preserves the old repository and other projects. These are separate operator
steps; a static Pages deployment does not deploy the API or apply SQL.

Operational application on 2026-10-20 used the official Management API migration
endpoint with name `allow_factor_repository`; Supabase registered version
`20261020071642`. The source draft was `202610200001` in commit `580d415`;
only its filename changed to match the registered version, preventing a later CLI
run from treating it as pending. The registered SQL and repository file share
SHA-256 `72445af79da9bde8bbfb0a804dcc28fcd6386bd7f2f8b2d2b3c54cfb2256f46d`.
Read-only checks confirmed the migration history, both repository prefixes,
rejection of unrelated identities, and unchanged fingerprints for all seven
existing analysis runs. No new analysis run was created for this verification.
