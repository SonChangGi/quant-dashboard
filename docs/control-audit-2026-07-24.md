# Six-dashboard control audit

> Read-only source audit completed 2026-07-24.
>
> Local implementation status updated 2026-07-24. Nothing in this document
> implies that the uncommitted worktrees are deployed.

This audit answers one question for every visible control: does it only change presentation, select an existing result, request a new authoritative analysis, or perform an owner operation?

## Summary

| Project | Analysis controls | Audited calculation boundary | Local implementation |
| --- | ---: | --- | --- |
| DRAM Price | 0 | Python collector, static JSON | Same-origin, GET-only static adapter; 8 controls are `display` and chart observation date is `result_selector`. |
| ETF Tracking | 0 | Python collector/analyzer, static JSON | Static adapter; visible controls are `display` or `result_selector`, backfill is `operation`. |
| SOX | 0 | Python analyzer, static JSON | Static adapter; visible controls are `display` or `result_selector`. |
| Momentum Factor | 26 | Static preset or local Python job API | Common API + durable dispatch + controlled Python worker + immutable result binding implemented locally. |
| Best Factor | 11 | GitHub Actions → Python CLI | Common API + durable dispatch + existing CLI worker + immutable result binding implemented locally. |
| Fear & Greed | 13 browser scenarios | JavaScript signal/strategy engines | 5 display controls and 3 operations stay separate; cross-runtime parity gate blocks backend migration on recorded semantic gaps. |

## DRAM Price

Product, source, metric, and visible-series/limit controls filter saved
observations. The chart observation date selects an already saved result
identity. None creates a new observation or calls Python. This is the correct
boundary; adding an analysis API would not improve the current product.

Evidence:

- `frontend/src/components/filter-controls.tsx`
- `frontend/src/App.tsx`
- `frontend/src/lib/market.ts`
- `frontend/src/lib/market.test.ts`

## ETF Tracking

ETF, period, chart observation date, ticker emphasis, search, and sorting operate on saved Python output. `backfill_all` and `refresh_existing` are owner operations in the data workflow, not public analysis inputs.

Evidence:

- `index.html`
- `assets/app.js`
- `scripts/update_data.py`
- `.github/workflows/update-data.yml`

## SOX

Snapshot date, ticker selection, search, and sorting choose or present saved output. Selecting a snapshot date must never be labelled as recalculation.

Evidence:

- `index.html`
- `assets/app.js`
- `scripts/fetch_sox_data.py`

## Momentum Factor

The following 26 independent `ResearchInputs` map into `RunConfig` and change the canonical input state:

```text
rebalanceFrequency
evaluationYears
topN
maxWeight
transactionCostBps
slippageBps
minHistoryDays
minPrice
minAvgDollarVolume
minAvgVolume
liquidityLookbackDays
minLiquidityObservations
maxPriceMissingRatio
maxVolumeMissingRatio
maxExtremeDailyReturn
selectionMinSharpe
selectionMaxDrawdown
selectionMaxAnnualizedCostDrag
selectionMinEffectiveNames
selectionMaxTargetHhi
selectionMaxTargetWeight
selectionMaxAbsSecurityDayContribution
selectionMaxSecurityAbsoluteContributionShare
selectionMaxLeaveOneSecurityCagrDelta
selectionExtremeEventAction
selectionExtremeEventPenaltyPoints
```

The audited local flow is:

```text
draft inputs
→ exact static preset lookup
→ otherwise local POST /api/runs
→ queued/running
→ existing Python run_analysis()
→ resultKey and market-snapshot validation
→ bound result
```

The local API is process-memory state and loopback-only. The calculation can take much longer than a serverless request, so the implemented remote control plane dispatches an external worker rather than running it in a Vercel or FastAPI request process:

```text
browser draft
→ common control API and durable outbox
→ controlled GitHub Actions workflow
→ control_run adapter
→ existing Python run_analysis()
→ immutable schema-v5 artifact
→ authenticated result callback
→ server and browser identity/hash verification
→ bound result
```

The 26-control parameterized contract test proves that changing each public
input changes the canonical server hash and the corresponding existing
`RunConfig` field.

Evidence:

- `momentum_factor_lab/research_inputs.py`
- `momentum_factor_lab/local_api.py`
- `tests/test_local_api.py`
- `tests/test_identity.py`
- `tests/test_control_run.py`
- `.github/workflows/controlled-analysis.yml`
- `docs/assets/dashboard.js`

## Best Factor

The 11 analysis controls are:

```text
period
rebalance
top_n
weighting
factor_preset
factor_allowlist
min_market_cap
min_dollar_volume
eligibility_adv_window
transaction_cost_bps
transaction_cost_model
```

All 11 reach the workflow resolver and existing Python CLI. In the audited
baseline the browser form generated a `gh workflow run` command, so editing the
form alone did not start Python or change the visible result.

The local pilot now submits to the common API when an HTTPS API endpoint is
configured. The API dispatches the existing workflow and accepts the result
only after the requested/effective inputs, code commit, data identity, bounded
callback, and full immutable artifact bytes match. Without that configuration,
the fallback remains accurately labelled as command generation rather than
`적용` or `재계산`.

The current published result also records:

```text
requested min_market_cap = 10,000,000,000 USD
market_cap_filter_effective = false
filter_fallback_reason = market_cap_metadata_insufficient_preflight
```

This is the published baseline, not a controlled-run success example. The
local controlled-run contract now requires `allowFallback=false` and rejects a
worker result whose requested/effective inputs differ, so this mismatch cannot
be adopted as the requested interactive result.

Evidence:

- `docs/index.html`
- `docs/app.js`
- `docs/data/dashboard-config.json`
- `.github/workflows/update-dashboard.yml`
- `.github/scripts/dashboard_config.py`
- `src/best_factor/cli.py`
- `tests/test_dashboard_config.py`
- `tests/control_api.test.mjs`

## Fear & Greed

Research track, training window, minimum R², extreme tail, maximum holding period, ETF pair, transaction cost, price sample, liquidation threshold, evaluation period, event asset/sample, and position policy change signal, event, or strategy results.

The calculation currently runs in browser JavaScript against server-published history and adjusted prices. The public contract explicitly treats it as a user scenario, not a canonical server result. The page default scenario also differs from the stored Python model default.

Before moving this boundary, preserve a matrix of JS/Python parity fixtures. Until parity is demonstrated, keep the calculation location visible in result metadata and do not call a browser scenario a Python result.

Evidence:

- `index.html`
- `assets/app.js`
- `assets/signal-engine.js`
- `assets/strategy-engine.js`
- `tests-js/signal-engine.test.mjs`
- `tests-js/app-dom.test.mjs`

## Required regression matrix

1. Every visible control appears exactly once in a control registry.
2. Every `analysis` value reaches its worker argument after canonical validation.
3. Changing one analysis value changes the config hash and run identity.
4. A deterministic fixture crosses the relevant threshold and changes the expected result path.
5. A `display` change does not send a run, alter a config hash, or modify a result.
6. A `result_selector` selects an existing identity without creating a run.
7. Failed, stale, timed-out, and mismatched runs never adopt the prior result as if it were new.
8. Requested and effective inputs are identical unless explicit fallback consent is bound to the run.
9. A result is accepted only when project, run, input schema, config, data snapshot, code version, and artifact hash all match.
