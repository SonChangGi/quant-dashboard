# Research and Planning Contract

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

When data automation is present, also inspect:

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
- risks, costs, provider rights, and open decisions.

If any remote/provider action is proposed, the plan must classify its cost risk
under `cost-and-authority.md`. If data-to-web automation is in scope, it must map
the full `data-automation.md` pipeline, failure policy, recurring bounds, and
public-readback evidence.

Do not use “improve”, “optimize”, “modernize”, or “make robust” without measurable evidence.
