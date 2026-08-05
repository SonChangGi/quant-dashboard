# Adaptive workflow kernel

Use this kernel when a matching capability rail could materially change the
approach, authority, failure handling, or proof, or when the task has an
unfamiliar target, independent lanes, failed-route recovery, a one-off wait,
monitor, or host-lifecycle continuation after a time, event, thread, CI, or
external-status dependency, or proof across several stages. A small,
well-understood task should stay in its public skill.

The invoking public skill's role, read/write boundary, and the current user's
authority always win. An isolated root or worktree separates writes but is not
by itself a security sandbox and never expands that authority. This kernel
cannot activate a skill, turn planning into implementation, or grant
source-control, provider, destructive, remote, or paid authority.

Aim for the strongest complete result justified by the request, target
evidence, available capability, and current constraints. Proportionality means
least unrelated churn and ceremony, not least effort or the first technically
passing result. Include material correctness, resilience, usability,
operability, and proof that a reasonable user would need for the requested
outcome; do not add speculative features or adjacent redesign.

Set the proportional quality bar from the request and target evidence before
substantial action. Revise it only when user steering or material new evidence
changes what a dependable result requires; do not repeatedly raise it merely
to justify more work.

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
| project file edits or local branch, worktree, stage, commit, cherry-pick, or rebase | `capabilities/repo-mutation.md` |
| recurring or event-driven collection or refresh | `capabilities/scheduled-automation.md` |
| versioned artifact, candidate/current pointer, or last-good promotion | `capabilities/publication.md` |
| a public URL or hosted consumer outcome | `capabilities/public-web.md` |
| authorized push, PR, release, deployment, or remote checkpoint | `capabilities/remote-release.md` |
| an active Goal or unfinished Developer task must preserve accepted state across a real interruption, restart, handoff, or likely context compaction | `capabilities/long-running-recovery.md`; duration, complexity, and worker count alone do not select it |
| one-off wait for time, event, thread, CI, or external status | use the host lifecycle guidance below; do not select scheduled automation unless the user requested creation or enablement of a persistent recurring or provider-triggered operation on an identified target |

Several rails may compose. Do not infer a manifest, schema, receipt, ledger, or
legacy runtime merely because a rail is useful. Framework and provider adapters
are optional hints only when that exact technology is already selected.

For ordinary external-data automation, compose the external-data,
scheduled-automation, publication, and public-web rails only when each trigger
applies. A schedule, publication, raw redistribution, task duration, or
`strict` label does not select legacy data-automation machinery; only the
compatibility triggers in `core/context-routing.md` can do that.

## Coordinate by available capability

Inspect the collaboration and continuation surfaces the host actually exposes.
Derive the dependency shape without requiring a new artifact. Dispatch bounded
subagents for independent discovery or specialist-review lanes early enough to
influence the route when they materially improve coverage, quality, or elapsed
time, while the parent continues useful non-overlapping work. Use a native
coordinated team only when ongoing mutual coordination or a shared worker
lifecycle is useful; use an existing or explicitly user-authorized task or thread for
user-owned continuation; use host-native wait, monitor, or continuation for
one-off dependencies; otherwise serial work is the fallback. Do not assume a
surface exists, combine partial controls from incompatible surfaces, or
hard-code tool names, models, worker counts, or a fixed hierarchy.

For multi-lane work, keep the host-native plan or status concise and truthful
about ownership, dependencies, and the next integration gate. Do not create a
project file merely for coordination visibility. Synchronize before dependent
work, and bring all accepted lanes onto one integrated state before judging the
whole result.

Keep tightly coupled work with one owner. Give each delegated assignment a
bounded outcome or decision question, allowed scope, shared constraints,
relevant dependencies, and expected evidence or artifact. This is a concise
handoff, not a mandatory packet. For a writer in an existing isolated root,
also bind the assignment to the exact root, verified baseline, integration
target, and acceptance.

Prefer parallel readers and one canonical writer. Concurrent writers require
demonstrably disjoint roots or write sets and one integration owner. Treat a
timeout or silent worker as unknown state; inspect status and artifacts before
replacing it. The parent reconciles claims, re-inspects returned evidence and
artifacts, integrates results, and owns final verification. A worker completion
claim is not proof. When findings conflict, inspect the shared source and test
the competing claims; do not average them or silently choose the convenient
answer. An unresolved material conflict limits the conclusion.

Duplicate implementation only for an explicit comparison or material
uncertainty that justifies the extra work. Start alternatives from the same
verified baseline, integrate one coherent evidence-backed candidate without
blending unverified fragments, and rerun affected proof.

For a later slice in the same role and domain, reuse a retained worker only
when its context remains an asset, and send the changed scope, evidence, or
acceptance delta instead of the full history. Use a fresh worker after
cancellation, material drift, an off-track result, or unavailable context.

For a one-off time- or event-dependent wait, prefer the host's wait, monitor, or
continuation capability instead of busy polling. Creating or enabling a
persistent automation for recurring or provider-triggered operation is a
separate provider or production mutation; use the scheduled automation rail
only when the current user requested it on an identified target. Do not invent
a background lifecycle the host does not provide. If no wait surface exists,
use bounded serial status checks only while they can make progress; never busy
poll.

When a selected Goal or authorized Developer task has real interruption risk
after material progress, or the current user explicitly asks for resumability,
the long-running recovery rail may add one non-authoritative local checkpoint.
Use it only if native continuation does not preserve enough state. Duration,
complexity, worker count, and a short wait alone do not justify it. Plan remains
read-only. One integration owner writes only at meaningful scope, integration,
steering, or handoff boundaries; never on a timer or fixed command count. On
resume, reconcile native Goal, Git and workspace state, workers, external
systems, and consumer evidence before trusting or replaying anything.

Do not require fixed roles, models, worker counts, review counts, worktrees,
packets, ledgers, hashes, or receipts for ordinary host-native work.

## Adapt until acceptance, then stop

Use this completion loop:

```text
inspect → choose → act within scope → observe the real result
→ review against acceptance → repair or switch route → rerun affected proof
```

Continue while an acceptance condition is unmet or a material risk could
invalidate the result. Diagnose before retrying. Retry only when the failure is
plausibly transient and the action is safe to repeat; otherwise change the
source, method, tool, decomposition, or claim when evidence shows the route is
unsuitable.

Classify what remains:

- **blocker:** no safe in-scope path can meet a required condition without user
  input, external-state change, fabrication, destructive conflict, or missing
  authority;
- **adaptable constraint:** another source or method, narrower scope, disclosed
  proxy, last-good artifact, or explicit degraded/unavailable result can still
  produce an honest accepted outcome;
- **material gap against the established quality bar:** an in-scope
  correctness, resilience, usability, operability, or proof defect identified
  during Ground or Inspect, or material new evidence showing that the bar is
  not yet met; it is not permission to expand the bar;
- **quality debt:** cosmetic, speculative, adjacent, or otherwise low-value
  improvement that does not invalidate the requested quality bar or stated
  limits.

Exhaust safe useful alternatives before declaring a blocker. At the completion
decision, address material gaps against the established bar rather than
labeling them optional merely because a literal checklist omitted them. Stop
once acceptance and the proportional quality bar are verified and remaining
items are only quality debt.

## Route data policy only when data is in scope

When external data is required, read both `capabilities/external-data.md` and
`core/authority.md` before selecting a source. The data rail owns source
fitness, provenance, rights, fallback, and degraded behavior; authority owns
the permanent zero-billing, credential, and cost boundaries. Do not duplicate
those details here or load them for non-data work. The selected route remains
zero-billing, and paid data has no approval path.

## Prove the real outcome

Match proof to the consumer: native tests and representative output for code;
dates, coverage, and calculation checks for data; rendered and interactive
inspection for UI or documents; and distinct configuration, execution,
artifact, publication, and readback facts for automation or release.

A build, test, health check, workflow start, HTTP status, local artifact,
commit, or preview proves only its own stage. For a consequential or
multi-surface result, or when material uncertainty remains, use a fresh
independent reviewer when it can expose issues that the implementer may miss.
Review the same integrated state, treat the verdict as evidence rather than
authority, resolve material findings, and rerun affected proof. Ask for a
conclusion, supporting and counter-evidence, material limitations, and
actionable findings in the lightest useful form rather than a fixed schema. Do
not add a reviewer merely to satisfy a count.

For authority, cost, or credential decisions, read
`<quant-shared-root>/core/authority.md`; it owns those rules. Never expose
secret values to workers, commands, logs, artifacts, or reports.
