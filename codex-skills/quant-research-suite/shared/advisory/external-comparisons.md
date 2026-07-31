# Advisory: external workflow comparisons

When comparing another workflow, framework, skill suite, or agent runtime:

- inspect current primary sources before making version-specific claims;
- separate observed behavior from inference;
- compare mechanisms against the user's objective and available environment;
- adopt independently expressed principles, not branding or topology;
- record what was adopted, adapted, and deliberately rejected.

## LazyCodex and Gajae Code

The vNext comparison was refreshed on 2026-07-30 from these primary sources:

- [LazyCodex documentation](https://lazycodex.ai/docs);
- [Gajae Code skills](https://gajae-code.com/docs/skills.html);
- [Gajae Code receipts](https://gajae-code.com/docs/receipts.html).

The suite does not install either project and does not depend on their CLI,
runtime, state, provider, team, tmux, hook, or configuration systems.

| External principle | Independent vNext adaptation |
| --- | --- |
| Goal-oriented persistence | Continue while acceptance is unmet or material risk remains; repair or switch routes after failure, then stop at verified acceptance |
| Explore before acting | Inspect the target, environment, capabilities, data, and real consumer surface before choosing a route |
| Useful parallel exploration | Use native subagents for independent lanes and a team only when ongoing cross-lane coordination or a shared lifecycle makes it useful |
| Plan, implement, verify, and QA | Use role-appropriate loops with verification on the actual consumption surface |
| Small workflow surface | Keep ordinary work in the selected public `SKILL.md`; load one lean kernel and only matching capability rails for non-trivial work |
| Evidence over status | Treat tests, artifacts, rendered behavior, execution, publication, and readback as distinct observable facts |

These principles are expressed in
`../references/adaptive-workflow.md` and the three public skills. Ordinary work
does not require a Project Context Packet, Plan Packet, Goal ledger, Story
Envelope, Team Run Packet, receipt, hash protocol, or assurance label.

## Deliberate non-adoptions

Do not copy or introduce as default behavior:

- implicit skill matching, cross-skill chaining, or global hooks;
- mandatory `AGENTS.md` generation;
- universal strict TDD, fixed gate counts, fixed reviewer counts, or a fixed
  adversarial taxonomy;
- maximum parallelism, parent-never-implements rules, fixed roles, fixed worker
  counts, or mandatory team execution;
- a separate canonical Goal state, tmux panes, mailbox, lease, heartbeat,
  provider registry, or TUI;
- automatic checkpoint, commit, merge, cherry-pick, rebase, push, PR, release,
  deployment, authentication, dependency installation, or paid action;
- fixed file, line, duration, review-round, or iteration thresholds.

A timeout is unknown worker state, not proof of failure. A worker status is not
acceptance. A local test is not remote or public proof. Unavailable preferred
tooling is normally a reason to adapt the route, not stop useful work.

## Legacy compatibility boundary

The source preserves the existing manifest, ledger, receipt v2/v3, Story,
durable runtime, and hash-bound team resources at their established relative
paths. The default installation excludes that compatibility payload; an
explicit compatibility install overlays it at the same paths. It is used only
for an existing project contract, an explicit machine-audit request, or
explicitly requested high-risk recovery that needs the exact legacy contract.

References such as `../references/agent-orchestration.md`,
`../references/goal-and-subagents.md`, and
`../references/durable-runtime.md` describe that compatibility layer. Their
packets, roles, assurance labels, and receipts must not leak back into the
ordinary host-native path.

## Clean-room and license boundary

This suite does not vendor external code, prompts, assets, schemas, state
formats, hooks, or configuration. General workflow ideas are independently
worded and implemented against Codex host capabilities.

If future work proposes copying an implementation instead of adapting a
principle, stop and inspect the exact current source and license first. Do not
infer that one repository's license covers a dependency or separately
distributed runtime.
