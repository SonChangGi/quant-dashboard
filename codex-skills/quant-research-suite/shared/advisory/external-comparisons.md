# Advisory: external comparisons

When comparing another workflow, framework, skill suite, design system, paper,
or product:

- inspect current primary sources when claims may have changed;
- separate observed facts from inference;
- compare against the user's objective and actual failure history;
- adopt bounded mechanisms, not branding or topology;
- state what was adopted, adapted, and rejected, with trade-offs.

For agent systems, durable intent, bounded story envelopes, evidence receipts,
and resumable checkpoints can be useful. Fixed team sizes, process managers,
heartbeats, or many always-on agents are not automatically useful. Keep one
integration owner and use specialists only where independent parallel work
improves quality or speed.

## LazyCodex and Gajae Code baseline

The current clean-room comparison was refreshed on 2026-07-27 from primary
sources. Recheck them before making version-specific claims:

- [LazyCodex documentation](https://lazycodex.ai/docs) and
  [Codex Light source](https://github.com/code-yeongyu/lazycodex);
- [OmO source and license](https://github.com/code-yeongyu/oh-my-openagent);
- [Gajae Code source](https://github.com/Yeachan-Heo/gajae-code),
  [skills](https://gajae-code.com/docs/skills.html), and
  [architecture](https://gajae-code.com/docs/architecture.html).

At that observation point, the LazyCodex install alias reported `0.2.2`, its
Codex payload release list reported `v4.19.2` at `8ec16c5`, and Gajae Code
reported `v0.11.11` at `0a18757`. These are comparison timestamps, not
compatibility pins or dependencies.

LazyCodex is a Codex distribution layer over OmO. Gajae Code is an external
agent runtime with its own CLI, state, providers, TUI, and optional tmux team
execution. Neither topology is part of this suite.

| Observed mechanism | Primary evidence | Independent adaptation here |
| --- | --- | --- |
| Project context before mutation | LazyCodex `$init-deep` in its documentation | Sourced, freshness-aware Project Context Packet without mandatory generated `AGENTS.md` files |
| Decision-complete reviewed planning | LazyCodex `$ulw-plan`; Gajae `deep-interview` and `ralplan` | Quant Plan interviews only for material ambiguity, then produces one immutable reviewed Plan Packet |
| Durable execution and evidence-first closure | LazyCodex `$start-work`/`$ulw-loop`; Gajae `ultragoal` and [receipts](https://gajae-code.com/docs/receipts.html) | Host Goal plus optional evidence ledger, snapshot freshness, repair, and one terminal critic |
| Bounded teams with an integration owner | LazyCodex parallel subagents/team mode; Gajae [`team`](https://gajae-code.com/docs/skills.html) | Host-native workers, Team Run Packet, isolated concurrent writers, serial canonical integration |
| Role-sensitive routing | LazyCodex role-based model profiles; Gajae role agents and provider boundary | Capability-based roles with host fallback and no provider/model registry |
| Repository code intelligence | External systems may bundle navigation or code-analysis services | Opportunistic read-only use of already-installed local LSP, AST, or codegraph tools with source and project-native fallback |
| Real-surface verification | LazyCodex manual-QA channels; Gajae evidence receipts | Deliverable-specific CLI/TUI/API/UI/data/document/release evidence with artifact and cleanup binding |

## Clean-room adaptations

The suite adapts these mechanisms in
`../references/agent-orchestration.md`:

- **Project Context Packet** — sourced entrypoints, ownership, native commands,
  protected contracts, workspace identity, and staleness conditions; no
  mandatory `AGENTS.md` tree or fixed complexity score.
- **Request-local continuation** — a Continuation Capsule records completed and
  open work, current and stale evidence, blockers, authority boundaries, and
  the next non-duplicating action. It persists information, not skill
  activation.
- **Decision readiness and steering** — material open decisions use a
  nonnumeric readiness list; optional typed steering preserves acceptance
  history and invalidation without creating a second Goal owner.
- **Local code intelligence** — an already-installed local LSP, AST, or
  codegraph may add read-only evidence, with `rg`, compiler or type-checker,
  direct source, and project-native checks as fallback and confirmation.
- **Team protocol** — bounded work packets, dependency and write scopes, one
  canonical integration owner, isolated concurrent writers, worker evidence,
  validation-coupled joins, and parent-owned Goal/checkpoint authority.
- **Role routing** — explorer, researcher, planner, implementer, integration,
  Architect, Surface QA, and terminal-critic roles are selected by needed
  capability. Model strength and assurance are separate decisions; provider
  and model names are not hard-coded.
- **Real-surface QA** — verification matches the actual CLI, TUI, API, UI/CJK,
  data, automation, document, or release surface and records exact invocation,
  observable result, artifact, redaction, and cleanup.
- **Evidence freshness** — evidence and Review Verdicts bind to acceptance and
  plan revision, exact snapshot, inspected scope, input/surface, artifact
  digest, and invalidation dependencies. Repairs rerun affected lanes only.

All of these operate only after a current explicit `$quant-plan`,
`$quant-developer`, or `$quant-goal` invocation. The public
`agents/openai.yaml` files set `allow_implicit_invocation: false`; no artifact,
active Goal, worker, or previous invocation bypasses that boundary.

## Deliberate non-adoptions

Do not copy or introduce:

- implicit skill matching, cross-skill chaining, or global prompt/edit/Stop
  hooks;
- LazyCodex's maximum-parallelism, parent-never-implements, universal TDD,
  fixed five-gate/five-lane review, fixed adversarial taxonomy, or
  merge-by-default behavior;
- Gajae Code's mathematical interview threshold, mandatory multi-role
  consensus loops, separate `.gjc` canonical Goal state, tmux panes, mailbox,
  lease, heartbeat, provider registry, TUI, or automatic
  checkpoint/merge/cherry-pick/rebase behavior;
- tool auto-installation, code-intelligence daemons, MCP or global
  configuration changes, telemetry, or external source/index upload;
- fixed file, LOC, duration, worker-count, review-round, or iteration
  thresholds;
- automatic provider authentication, dependency installation, commit, push,
  PR, release, deployment, or paid action.

Use host-native subagents and Host Goal lifecycle instead. A timeout is not
worker failure, a worker `done` message is not acceptance proof, and a team
never owns the parent Goal.

## Dependency and license boundary

This suite has no LazyCodex, OmO, or Gajae Code runtime dependency and does not
vendor their code, prompts, assets, schemas, state formats, hooks, or
configuration. The adaptations above are independently expressed concepts in
this suite's contracts and implementation.

At the comparison baseline:

- the LazyCodex distribution repository is MIT;
- the underlying OmO core uses the
  [Sustainable Use License](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/LICENSE.md);
- Gajae Code is MIT.

Do not infer that the wrapper's MIT license applies to OmO core content. If
future work proposes copying an implementation rather than independently
adapting a concept, stop and review the exact source file and its current
license first.
