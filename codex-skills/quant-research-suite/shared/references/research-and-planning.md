# Research and Planning Contract

## Contents

- [Research routing](#research-routing)
- [Evidence record](#evidence-record)
- [Repository audit](#repository-audit)
- [External-data decision rule](#external-data-decision-rule)
- [Architecture decision](#architecture-decision)
- [Plan quality gate](#plan-quality-gate)

## Research routing

Research must answer a decision in the plan.

| Question | Preferred evidence |
| --- | --- |
| Current repository behavior | Source, tests, generated artifacts, workflows, runtime |
| Current public behavior | Public page, assets, data endpoint, CI/deploy record |
| Technical API or library | Official documentation, specification, source repository |
| Academic method | Original paper, proceedings, publisher, author materials |
| Provider rights or data limits | Provider terms and official documentation |
| Security guidance | Platform/vendor security documentation and standards |
| Product/design benchmark | Actual product plus its official design guidance |
| Community tool | Official repository and release documentation; treat reputation as weak evidence |

## Evidence record

For each material source, capture:

- title;
- URL or local path;
- publisher/owner;
- publication or release date when available;
- access date;
- exact decision supported;
- applicability and limitation;
- evidence type: confirmed, inference, or recommendation.

Do not paste large copyrighted passages. Summarize and link.

## Repository audit

Inspect:

- purpose and intended users;
- entrypoints and runtime;
- analysis/data/result lifecycle;
- input taxonomy and actual propagation;
- generated artifacts and freshness;
- frontend hierarchy and visible controls;
- chart/table interaction contracts;
- tests and gaps;
- worktrees and uncommitted changes;
- workflows, secrets names, schedules, deploy targets, and public state.

Do not read secret values. Record only required secret names and whether the path is configured.

When scheduled or publicly published data automation is in scope, also inspect:

- every source and its role, rights, collector, timezone/calendar, availability
  lag, cache, schema, raw/normalized artifact, and stale/fallback behavior;
- the coherent cutoff rule across required sources;
- collection, validation, analysis, staging, publication, deployment, and public
  readback as distinct current facts;
- cron timezone, default-branch enablement, concurrency, idempotency, retry,
  timeout, retention, manual backfill, last-good, and recovery behavior;
- per-source `as_of`, `data_as_of`, calculation, publication and public
  verification timestamps.

Workflow presence is not schedule proof. A recently fetched source is not proof
of a coherent latest analysis, and a successful deployment is not proof of fresh
public data.

## External-data decision rule

Separate source eligibility, analytical fitness, and publication rights:

- eligibility: the required data is zero-charge without a trial, expiring
  credit, automatic paid conversion, payment method, subscription, PAYG,
  overage, paid add-on, or paid tier;
- analytical fitness: the fields, dates, adjustments, coverage, and known
  limitations support the intended calculation and claim;
- publication rights: the selected display, derived output, or raw
  redistribution is supported for the intended audience.

Exclude ineligible paid data from alternatives instead of presenting it for
approval. If a currently eligible source becomes paid, plan a free replacement,
free reconstruction or proxy, or a narrower honest claim.

Require historical PIT provenance only for a PIT, as-known-then,
look-ahead-free, survivorship-free, or historically investable claim. A
non-PIT retrospective or current-universe exploration may proceed when its
limitations are explicit. For price work, treat adjusted-price semantics as
separate from a corporate-actions feed; require the latter only when dividends,
reinvestment, splits, total return, or event timing are part of acceptance.

When material source or method uncertainty remains, consider independent
read-only lanes for free-source discovery, reconstruction or proxy methods,
bias/quality review, and operational feasibility. The primary planner compares
their evidence and selects the strongest zero-charge path; agent output is not
authority or proof by itself.

## Architecture decision

Reject technology-first planning.

### Keep static when

- the page displays stored, validated results;
- user controls select or format existing data;
- scheduled workers already generate authoritative artifacts;
- server-side state, authorization, or long-running on-demand execution is unnecessary.

### Add a control backend when

- user inputs must trigger authoritative computation;
- execution is long-running or asynchronous;
- validation, authorization, idempotency, run tracking, or result persistence is required;
- browser-only computation would diverge from the authoritative engine;
- a server is needed for provider-secret isolation.

### Separate frontend and backend in code when

- they have different trust, scaling, deployment, or lifecycle requirements;
- the frontend must remain replaceable without changing analysis;
- the worker must remain runnable independently of the website.

One developer skill may own integration while the code and deployment boundaries remain separate.

## Plan quality gate

A plan is actionable only when it includes:

- objective and observable outcome;
- scope and non-goals;
- protected contracts;
- current-state evidence;
- decision and alternatives;
- exact components/files or discovery step;
- ordered steps with dependencies;
- tests and acceptance criteria;
- local-preview gate;
- release authority gate;
- rollback/fallback;
- material risks, free-only data eligibility, use-specific provider rights,
  and open decisions.

If any remote/provider action is proposed, the plan must classify its cost risk
under `cost-and-authority.md`. If data-to-web automation is in scope, it must map
the full `data-automation.md` pipeline, failure policy, recurring bounds, and
public-readback evidence.

For a local/private or exploratory data task, keep the Plan Packet lighter:
record the provider/endpoint, source and collection dates, relevant fields,
adjusted/raw semantics, transformations, and known limitations. Do not require
the full automation registry, publication-rights packet, or PIT history unless
the selected delivery or claim needs it.

Do not use “improve”, “optimize”, “modernize”, or “make robust” without measurable evidence.
