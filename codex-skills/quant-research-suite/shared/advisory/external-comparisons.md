# Advisory: external workflow comparisons

When comparing another workflow, framework, skill suite, or agent runtime:

- inspect current primary sources before making version-specific claims;
- separate observed behavior from inference;
- compare mechanisms against the user's objective and available environment;
- adopt independently expressed principles, not branding or topology;
- record what was adopted, adapted, and deliberately rejected.

## LazyCodex and Gajae Code

The vNext comparison was refreshed on 2026-08-24. The latest tagged releases
observed then were LazyCodex v4.19.4 and Gajae Code v0.15.0. Package or
installer aliases may use separate version lines. Version-specific claims use
tagged source where overview documentation lags:

- [LazyCodex v4.19.4](https://github.com/code-yeongyu/lazycodex/releases/tag/v4.19.4);
- [LazyCodex planning](https://github.com/code-yeongyu/lazycodex/blob/v4.19.4/plugins/omo/components/ultrawork/skills/ulw-plan/SKILL.md);
- [LazyCodex discipline agents](https://github.com/code-yeongyu/lazycodex/blob/v4.19.4/packages/web/content/docs/discipline-agents.md);
- [Gajae Code v0.15.0](https://github.com/Yeachan-Heo/gajae-code/releases/tag/v0.15.0);
- [Gajae Code skills](https://gajae-code.com/docs/skills.html);
- [Gajae Code receipts](https://gajae-code.com/docs/receipts.html);
- [Gajae Code harness](https://gajae-code.com/docs/harness.html);
- [Gajae Code delegation update](https://github.com/Yeachan-Heo/gajae-code/pull/3355);
- [Gajae Code same-domain worker reuse](https://github.com/Yeachan-Heo/gajae-code/pull/3359).

The suite does not install either project and does not depend on their CLI,
runtime, state, provider, team, tmux, hook, or configuration systems.

| External principle | Independent vNext adaptation |
| --- | --- |
| Goal-oriented persistence | Continue while acceptance is unmet or material risk remains; repair or switch routes after failure, then stop at verified acceptance |
| Explore before acting | Inspect the target, environment, capabilities, data, and real consumer surface before choosing a route |
| Useful parallel exploration | Use native subagents for independent lanes and a team only when ongoing cross-lane coordination or a shared lifecycle makes it useful |
| Tool-surface negotiation | Inspect what the host actually exposes, choose a complete supported coordination surface, and degrade to serial work instead of assuming product-specific tools |
| Context-efficient follow-up | Reuse a retained worker only for the same role/domain while its context remains useful; send a delta and use a fresh worker after cancellation, drift, or unavailable context |
| Waiting and persistence | Use host-native wait, monitor, or continuation for one-off waits; create persistent automation only with authority for the recurring target |
| Plan, implement, verify, and QA | Use role-appropriate loops with verification on the actual consumption surface |
| Small workflow surface | Keep ordinary work in the selected public `SKILL.md`; load one lean kernel and only matching capability rails for non-trivial work |
| Evidence over status | Treat tests, artifacts, rendered behavior, execution, publication, and readback as distinct observable facts |

These principles are expressed in
`../references/adaptive-workflow.md` and the three public skills. Ordinary work
does not require a Project Context Packet, Plan Packet, Goal ledger, Story
Envelope, Team Run Packet, receipt, hash protocol, or assurance label.

## ORCA and LobeHub

The 2026-08-04 comparison used [ORCA
v1.4.168](https://github.com/stablyai/orca/releases/tag/v1.4.168) and [LobeHub
v2.2.13](https://github.com/lobehub/lobehub/releases/tag/v2.2.13), plus their
current official documentation:

- [ORCA orchestration](https://www.onorca.dev/docs/cli/orchestration),
  [worktrees](https://www.onorca.dev/docs/model/worktrees),
  [checkpoints](https://www.onorca.dev/docs/cli/worktree-checkpoints), and
  [diff review](https://www.onorca.dev/docs/review/diff-viewer);
- [LobeHub Agent Groups](https://github.com/lobehub/lobehub/blob/canary/docs/usage/agent/agent-team.mdx),
  [Tasks](https://github.com/lobehub/lobehub/blob/canary/docs/usage/getting-started/task.mdx),
  [Memory](https://github.com/lobehub/lobehub/blob/canary/docs/usage/getting-started/memory.mdx),
  and [Codex integration](https://github.com/lobehub/lobehub/blob/canary/docs/usage/agent/codex.mdx).

ORCA is a coding-agent control plane with run/task/dispatch state, worktree and
terminal management, combined diffs, and user-selected candidate integration;
its documented orchestration is experimental and is not an automatic semantic
decomposer or evaluator. LobeHub is a broader operator platform with Agent
Groups, task review states, editable memory, scheduling, and a Codex bridge; it
is not documented as a repository-native Git integration engine.

Portable adaptations are deliberately smaller than either product:

| External principle | Independent Quant adaptation |
| --- | --- |
| Dependency-aware dispatch | Derive dependencies, run independent lanes early, synchronize before dependent work, and keep one integration owner |
| Visible ownership and progress | Use concise host-native plan or status state; do not create a project artifact solely for coordination |
| Evidence-bearing review | When independent review is warranted, return a conclusion, supporting and counter-evidence, limitations, and actionable findings against the integrated state |
| State is not proof | Treat idle, heartbeat, task completion, checkpoint comments, and worker consensus as status until the parent verifies the real outcome |
| Safe recovery | Inspect current state, distinguish transient replay-safe failure from a permanent or unsafe route, and reject stale or conflicting results |
| User-owned authority | Keep review, local writes, source control, remote actions, provider mutations, memory, and schedules as separate permissions |

ORCA's SQLite state, run/task/dispatch IDs, PTYs, mailbox, heartbeat, worktree UI,
and permissive agent launch flags remain host features. LobeHub's Task, Topic,
Agent Group, Memory, scheduler, RBAC, marketplace, and Codex-process bridge also
remain product features. Neither is a reason to require a fixed DAG, fixed team
size, universal reviewer, persistent memory, background worker, or automatic
Git/provider action in the Quant skills.

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
- Stop-hook reinjection, telemetry, daemon processes, automatic session state,
  or product-specific tool and model routing;
- automatic checkpoint, commit, merge, cherry-pick, rebase, push, PR, release,
  deployment, authentication, dependency installation, or paid action;
- permission-bypass or sandbox-bypass launch flags, or the assumption that a
  worktree is an operating-system security sandbox;
- automatic personal memory extraction, background scheduling, connector
  execution, or product RBAC as if it were current-request authority;
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
worded and implemented against Codex host capabilities. The LazyCodex wrapper
is [MIT-licensed](https://github.com/code-yeongyu/lazycodex/blob/v4.19.4/LICENSE)
while its synchronized OmO engine uses
[SUL-1.0](https://github.com/code-yeongyu/oh-my-openagent/blob/v4.19.4/LICENSE.md);
do not assume the wrapper license covers engine material.

If future work proposes copying an implementation instead of adapting a
principle, stop and inspect the exact current source and license first. Do not
infer that one repository's license covers a dependency or separately
distributed runtime.
