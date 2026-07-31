# Adaptive workflow kernel

Use this kernel for a non-trivial Quant task: an unfamiliar target, multiple
independent lanes, external data, a specialized consumer surface, recovery
after a failed route, or proof across several stages. A small, well-understood
task should stay in its public skill.

The invoking public skill's role, read/write boundary, and the current user's
authority always win. This kernel cannot activate a skill, turn planning into
implementation, or grant source-control, provider, destructive, remote, or paid
authority.

## Ground in the actual environment

Inspect applicable instructions, current behavior, source, configuration,
entrypoints, tests, data paths, artifacts, dirty state, available tools, and the
surface where the outcome must work. Prefer target-native commands and existing
architecture. Preserve unrelated user changes and project-owned purpose, data
meaning, calculations, design, interfaces, and publication behavior.

Resolve discoverable facts through inspection or current primary sources. Ask
only when a user-owned choice materially changes product behavior, accepted
scope, authority, cost, or irreversible effects. Otherwise choose and disclose
the strongest supported default.

## Load only the needed capability rail

Resolve `<quant-shared-root>` as the `shared` directory beside source `skills`,
or the installed `quant-research-shared` sibling. Read only rows that match the
task:

| Trigger | Capability rail |
| --- | --- |
| calculation, ranking, backtest, or displayed analytical result | `capabilities/analysis.md` |
| provider, API, filing, feed, dataset, freshness, or rights | `capabilities/external-data.md` |
| a UI control changes an analysis input | `capabilities/analysis-input-flow.md`; check the repository-native path first |
| layout, interaction, responsive UI, or chart | `capabilities/web-ui.md` and, for chart interaction, `capabilities/interactive-chart.md` |
| API boundary, state, authentication, or secrets | `capabilities/backend.md` |
| recurring or event-driven collection or refresh | `capabilities/scheduled-automation.md` |
| versioned artifact, candidate/current pointer, or last-good promotion | `capabilities/publication.md` |
| a public URL or hosted consumer outcome | `capabilities/public-web.md` |
| authorized push, PR, release, deployment, or remote checkpoint | `capabilities/remote-release.md` |

Several rails may compose. Do not infer a manifest, schema, receipt, ledger, or
legacy runtime merely because a rail is useful. Framework and provider adapters
are optional hints only when that exact technology is already selected.

For ordinary external-data automation, compose the external-data,
scheduled-automation, publication, and public-web rails only when each trigger
applies. A schedule, publication, raw redistribution, task duration, or
`strict` label does not select legacy data-automation machinery; only the
compatibility triggers in `core/context-routing.md` can do that.

## Coordinate by capability

Keep tightly coupled work with one owner. Use subagents when at least two
bounded, independent questions or work units can progress in parallel. Use a
native agent team only when available and the lanes require ongoing
coordination, mutual discovery, or a shared worker lifecycle; otherwise use
ordinary subagents or sequential work.

Each delegated assignment states:

1. outcome or question;
2. allowed scope;
3. constraints and protected surfaces;
4. evidence or artifact to return.

Prefer parallel readers and one canonical writer. Concurrent writers require
demonstrably disjoint roots or write sets and one integration owner. Treat a
timeout or silent worker as unknown state; inspect status and artifacts before
replacing it. The parent reconciles claims, integrates results, and owns final
verification.

Do not require fixed roles, models, worker counts, review counts, worktrees,
packets, ledgers, hashes, or receipts for ordinary host-native work.

## Adapt until acceptance, then stop

Use this completion loop:

```text
inspect → choose → act within scope → observe the real result
→ review against acceptance → repair or switch route → rerun affected proof
```

Continue while an acceptance condition is unmet or a material risk could
invalidate the result. Diagnose before retrying, and change the source, method,
tool, decomposition, or claim when evidence shows the route is unsuitable.

Classify what remains:

- **blocker:** no safe in-scope path can meet a required condition without user
  input, external-state change, fabrication, destructive conflict, or missing
  authority;
- **adaptable constraint:** another source or method, narrower scope, disclosed
  proxy, last-good artifact, or explicit degraded/unavailable result can still
  produce an honest accepted outcome;
- **quality debt:** optional improvement that does not invalidate acceptance or
  the stated limits.

Exhaust safe useful alternatives before declaring a blocker. Stop once
acceptance is verified and remaining items are only quality debt.

## Discover broadly; select a zero-billing data route

Explore candidates in this order, but select on fitness rather than position:

1. usable project source, cache, snapshot, or last-good artifact;
2. official no-billing endpoint, filing, download, or publication;
3. another lawfully accessible no-billing public source;
4. defensible reconstruction or reconciliation from free inputs;
5. disclosed proxy, narrower universe or period, degraded/last-good result, or
   explicit unavailable state.

Compare claim fitness, freshness, coverage, field semantics, adjustment and
point-in-time behavior, rights, reliability, and reproducibility. The selected
route must be usable for the required scope at zero charge, require no payment
method, avoid trials or automatic conversion, have no PAYG or overage, and
hard-stop with no chargeable fallback. A provider may offer optional paid
tiers only when the selected route cannot enroll in or fall through to them.
Paid data has no approval path inside this suite.

Record origin, source and access dates when useful, fields, material
transformations, coverage and revision limits, and exact display or
redistribution rights in proportion to the claim. Require point-in-time proof
only when the claim depends on historical availability, survivorship control,
or look-ahead freedom. Never fabricate, silently fill gaps, bypass access
controls, hide staleness, or weaken degraded/unavailable semantics.

## Prove the real outcome

Match proof to the consumer: native tests and representative output for code;
dates, coverage, and calculation checks for data; rendered and interactive
inspection for UI or documents; and distinct configuration, execution,
artifact, publication, and readback facts for automation or release.

A build, test, health check, workflow start, HTTP status, local artifact,
commit, or preview proves only its own stage. Use an independent reviewer when
consequence, uncertainty, or specialized judgment warrants it—not to satisfy a
count.

For separate authority or cost decisions, read
`<quant-shared-root>/core/authority.md`. Existing hidden credential bridges may
support an already requested operation, but never expose secret values to
workers, commands, logs, artifacts, or reports.
