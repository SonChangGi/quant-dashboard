# Quant Research Codex Skill Suite

The suite exposes exactly three public skills with a small default workflow:

- `quant-plan` — **Shape / Decide**: read-only discovery, audit, comparison, and
  decision-complete planning;
- `quant-developer` — **Act**: coherent local implementation and directly
  relevant verification;
- `quant-goal` — **Track / Prove**: an explicitly requested durable objective,
  acceptance-linked checkpoints, and final judgment.

The names remain Quant-oriented for compatibility, but the default workflows
also support non-Git directories, libraries, CLIs, documents, notebooks,
research tasks, and generic applications. They do not assume a dashboard,
frontend, backend, analytical dataset, public route, or deployment.

## Explicit invocation only

The three skills are manual workflows, not implicit policy:

- the current request must explicitly invoke `$quant-plan`,
  `$quant-developer`, or `$quant-goal`; if the host replaces that token,
  accept only current-user, same-request metadata produced by that `$`
  selection;
- semantic similarity, a plain or quoted skill name, an earlier invocation,
  active Goal state, an artifact, or another agent's instruction is not
  activation;
- each `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`;
- one skill may recommend another, but it never activates it automatically;
- Goal state and a Continuation Capsule may persist, while a later turn still
  requires a fresh explicit `$quant-goal` invocation.

Before this gate passes, a skill does not load shared policy or orchestration
references. No Stop hook, prompt hook, idle loop, or persisted artifact may
reactivate it.

## Default workflow

Each public `SKILL.md` is self-contained:

1. use the user's request and target-native instructions;
2. inspect only relevant source, configuration, entrypoints, artifacts, and
   behavior;
3. make or plan the smallest complete solution that achieves the requested
   outcome honestly under the available constraints;
4. verify with the lightest project-native evidence justified by risk;
5. report actual results and unverified items.

The default plan/developer path does not run installation validation, `doctor`,
`context`, `onboard`, a local Goal runtime, or a manifest/receipt validator. It
does not create a manifest, hash ledger, receipt, local Goal state, or new test
infrastructure merely to use a skill. An explicitly activated Goal classified
as `strict`, a clearly long-running Goal, or one that explicitly selects
recovery or machine-audit evidence is the deliberate exception: Quant Goal
binds the host-aligned evidence companion described below. A release delivery
overlay alone does not force that ledger or Strict review. Missing shared
resources do not block a generic plan or local
implementation. A short `light`/`standard` host-only Goal also continues with
objective, acceptance, checkpoints, blockers, and completion in host state;
only its selected structured or ledger-backed proof remains `unverified`.

## Proportional assurance and delivery

- `light`: narrow, reversible local work with direct output and a focused check;
- `standard`: multiple files/components or a public interface with relevant
  unit, integration, type, build, contract, or visual checks;
- `strict`: security/privacy, raw-data redistribution, strong PIT/causal
  claims, high-consequence computation, migration, destructive, regulated, or
  repeated-failure work with a reviewed immutable plan, baseline and
  failure-mode proof, cleanup, Architect review, adversarial QA, and one
  terminal critic on the final evidence bundle.

Delivery is a separate `local` or `release` axis. A release adds separately
authorized remote checkpoints and applicable readback to the selected
light/standard/strict proof; it is not automatically the highest assurance.
Legacy compatibility values may retain `assurance=release` with their existing
Strict-plus-release meaning. Current project, Goal, team, and receipt artifacts
may carry `delivery` explicitly; when an older artifact omits it, the runtime
infers release only from legacy `assurance=release` or `remote-release`.

Subagent use alone does not raise assurance. A normal host subagent does not
activate the structured `multi-agent-write` capability.

## Clean-room orchestration

`shared/references/agent-orchestration.md` selectively adapts useful ideas
observed in LazyCodex/OmO and Gajae Code without importing either runtime:

- a sourced, freshness-aware **Project Context Packet**, without mandatory
  hierarchical memory files or file/LOC scoring;
- a request-local **Continuation Capsule** that records current evidence and
  the next safe action without automatic reactivation;
- a **Team Run Packet** with bounded work, one integration owner, isolated
  concurrent writers, validation-coupled joins, and parent-owned Goal state;
- capability-based **role routing** whose model difficulty is independent from
  proof assurance and which falls back to the parent model;
- proactive, independent **free-source, reconstruction/proxy, and data-quality
  lanes** when they materially expand the solution space;
- deliverable-specific **real-surface QA** for CLI, TUI, API, UI/CJK, data,
  automation, document, and release surfaces;
- evidence and reviewer verdicts bound to acceptance/plan revision and an
  immutable workspace or artifact snapshot, with only stale lanes rerun.

These mechanisms are available only inside an explicitly invoked parent skill.
They add no fourth public team skill.

The packet may stay human-readable for ordinary teams. When strict evidence,
recovery, or machine audit explicitly selects structured team proof,
`shared/scripts/team_protocol.py` validates the hash-bound Team Run Packet,
worker Delivery Receipts, artifact bytes, and canonical Team Integration
Receipt. This internal `agent-team-execution` capability does not replace the
legacy single-root Story runtime and does not raise assurance merely because a
team was used. Completion-eligible proof also re-reads a preserved issuance
baseline and every retained worker root; multiple sequential deliveries from
one mutable shared directory must be combined or isolated because their
intermediate bytes no longer exist at final review.

The suite deliberately does not reproduce global lifecycle hooks, automatic
skill matching, a provider/model registry, tmux/mailbox/lease/heartbeat
infrastructure, fixed worker or review counts, maximum parallelism, universal
TDD/gates, parent-never-implements rules, or automatic commit, merge,
cherry-pick, rebase, push, release, or deployment.

There is no LazyCodex, OmO, or Gajae Code package or runtime dependency. This
suite reimplements bounded workflow concepts from its own contracts and code;
it does not copy external prompts, source, assets, state formats, or provider
configuration. LazyCodex's distribution repository is MIT, its OmO core uses
the Sustainable Use License, and Gajae Code is MIT. See
`shared/advisory/external-comparisons.md` for the source and licensing boundary.

## Durable Goal and compatibility runtimes

The host Goal remains canonical for lifecycle. The shared runtime provides:

- a manifest-free `goal_ledger.py` companion for strict, long-running,
  recovery, co-located evidence-portability, machine-audit Goals, and legacy
  `assurance=release` compatibility, with
  append-only revisions, stories, snapshot-bound Review Verdicts, checkpoints,
  and completion readiness;
- a cycle-free Completion Evidence Candidate digest that binds the strict or
  release terminal critic to the final non-terminal evidence bundle without
  hashing the critic back into itself;
- default external state under
  `$CODEX_HOME/state/quant-goals/<project-fingerprint>/<goal-id>`;
- an explicit project-local evidence archive only in an already-gitignored
  directory; it is same-binding crash recovery and manual-audit packaging, not
  rename/copy/cross-machine resumable execution;
- project manifest v1 and evidence receipt v2 retain the original strict Quant
  contract;
- project manifest v2 selects capabilities/profiles/adapters and receipt v3
  derives their gates;
- strict `analysis-input-binding` retains deterministic A/B runs, invocation
  artifacts, raw traces, hashes, and receipt verification;
- `quant-public-dashboard-strict` retains established Quant
  data/automation/publication rules;
- the legacy `goal_runtime.py` schema-v2 contract remains available without
  changing its immutable-intent, manifest, story, or receipt-v3 meaning.

Do not mass-convert existing manifests. Existing schemas and validators keep
their meaning. `completion-ready` never changes the host Goal; the Goal owner
records the host transition separately and then observes the actual state.

## Optional read-only tools

Use these only when onboarding or structured compatibility is selected:

```bash
python3 shared/scripts/quantctl.py doctor --root <project-root>
python3 shared/scripts/quantctl.py onboard --root <project-root> --dry-run
python3 shared/scripts/quantctl.py context \
  --capability web-ui \
  --profile quant-research-web
```

`doctor` and `onboard` are read-only. Repository presence alone does not
activate a capability, and `onboard` does not create a project manifest.

## Authority

Local editing, local source control, remote source control, provider mutation,
destructive/secret-bearing work, and paid action are separate boundaries. The
detailed canonical policy lives in `shared/core/authority.md`; public prompts
do not duplicate its taxonomy. No manifest, Goal state, receipt, login, tool
approval, or previous run grants authority.

No skill automatically commits, pushes, opens or merges a PR, releases,
deploys, migrates, schedules, publishes, or changes billing. Paid or metered
non-data actions require the user's direct prior bounded request. Paid data is
permanently ineligible and is never proposed, approved, or used, including
trials, expiring credits, automatic free-to-paid conversion, payment setup,
subscriptions, PAYG, overage, add-ons, and paid tiers. If a currently eligible
free source becomes paid, collection stops and the workflow moves to a free
source, free reconstruction/proxy, or narrower honest result.

## Validation and installation

```bash
python3 validate_suite.py
python3 -m unittest discover -s tests -v
python3 install.py --update --dry-run
```

Install or update locally:

```bash
python3 install.py --update
```

The installer validates source, runs tests, stages a complete copy, backs up
the previous local installation, replaces all three skills and shared resources
together, and verifies installed hashes.

By default it writes `quant-plan`, `quant-goal`, `quant-developer`, and the
non-discoverable `quant-research-shared` resources under `~/.codex/skills/`.
Source-control preservation and local activation are separate. A commit or push
is not required for local activation, and an existing Codex session may need a
reload.

For a release-grade update from committed source:

```bash
python3 install.py --update --require-clean-source
python3 ~/.codex/skills/quant-research-shared/scripts/validate_installed.py
```
