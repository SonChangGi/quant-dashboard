# Quant Research Codex Skill Suite

This package exposes exactly three public skills:

- `quant-plan` inspects a target read-only and returns an audit or a
  decision-complete plan.
- `quant-goal` explicitly initializes, resumes, or steers one native Goal.
- `quant-developer` implements and verifies the complete accepted outcome
  while minimizing unrelated churn.

Their names are retained for compatibility, but the workflows also apply to
non-Git directories, applications, libraries, CLIs, research, notebooks, data,
and documents. There is no fourth team skill.

## Explicit invocation

Each skill is manual. Its `agents/openai.yaml` sets
`policy.allow_implicit_invocation: false`.

Activation requires the current user's literal `$quant-plan`, `$quant-goal`,
or `$quant-developer` selection, or same-request metadata produced by that `$`
selection. A plain-text name, semantic match, prior invocation, persisted
artifact, active Goal, or another agent's request does not activate a skill.
One Quant skill never activates another.

When the current user explicitly selects more than one, the selected roles
compose in stages without cross-activation: `quant-plan` owns read-only planning,
`quant-developer` owns later implementation, and `quant-goal` owns Goal
lifecycle and overall integration. If plan approval is required before
mutation, the turn stops after planning and implementation requires a fresh
explicit selection. Composition never expands authority.

After `$quant-goal` explicitly initializes a native Goal, the host may
auto-continue that Goal in follow-up turns without reactivating the skill.
This is native Goal lifecycle behavior, not implicit skill invocation. The
Goal and conversation remain the ordinary source of truth; follow-up turns do
not create a local state system.

## Adaptive default workflow

The suite starts from the user's outcome and the capabilities that are
available in the actual environment:

1. inspect applicable instructions, current behavior, inputs, entrypoints,
   tests, artifacts, dirty state, and the intended consumer surface;
2. choose a supported route and split only genuinely independent work;
3. plan or implement a coherent result with project-native tools;
4. observe the result on the surface where it must work;
5. review it against the accepted outcome, repair or switch routes, and rerun
   affected checks while a safe useful action remains.

Discoverable facts are resolved through inspection or current research.
Questions are reserved for choices that materially alter product behavior,
scope, authority, cost, or irreversible effects. Otherwise the skill chooses
the strongest supported default and discloses its assumptions.

The ordinary path is host-native and lightweight. It does not load or create
a project manifest, local Goal ledger, Story Envelope, receipt, hash-bound
packet, or assurance label. It also does not install a workflow harness or add
process artifacts merely to run a skill. The concise conditional guidance in
`shared/references/adaptive-workflow.md` covers multi-lane work, free-data
fallbacks, recovery after a failed route, and proof across real surfaces.

## Selective delegation

Use native subagents for independent discovery, method comparison, source
research, bounded implementation, review, or QA when doing so improves speed
or quality. Use a coordinated team only when at least two lanes can make real
progress independently. Roles, worker counts, models, and review counts are
not fixed.

Every delegated assignment states four things:

1. objective;
2. scope;
3. constraints and protected surfaces;
4. expected evidence or artifact.

Prefer parallel readers and one writer. Concurrent writers are appropriate
only with demonstrably isolated roots or write scopes. One integration owner
reconciles evidence, combines outputs, and verifies the integrated result.

## Zero-billing data

Paid and free-to-paid data are outside the solution space. This includes
trials, expiring credits, card-required access, subscriptions, PAYG or
overage, and paid add-ons or tiers.

When external data is needed, use the first route that can support the actual
claim:

1. a usable project-owned source, cache, snapshot, or last-good artifact;
2. an official no-billing endpoint, filing, download, or publication;
3. another lawfully accessible no-billing public source;
4. a defensible method reconstructed from free inputs;
5. a disclosed proxy, narrower universe or period, degraded or last-good
   result, or explicit unavailable state.

Evidence should identify the origin and relevant source date, fields,
transformations, adjustment or point-in-time limits, gaps, and display rights
in proportion to the claim. Values are never fabricated, access controls are
never bypassed, and stale, degraded, or unavailable conditions remain visible.

## Proof and authority

Proof follows the real consumer: project-native tests and representative
output for code, dates and calculation checks for data, rendered and
interactive inspection for UI or documents, and distinct execution, artifact,
publication, and readback checks for automation or release. A build, commit,
workflow start, health response, or HTTP status proves only that stage.

Local inspection, edits, tests, generated artifacts, and reversible non-Git
task-scoped temporary isolation are normal when the invoked skill permits
mutation. Local source-control mutation (branch, worktree, stage, commit,
cherry-pick, or rebase); remote source-control mutation (push, PR, merge, tag,
or release); destructive work; new authentication or secret handling; external
production or provider mutation; publication, deployment, migration,
scheduling; and paid actions are separate authority boundaries. The canonical
details remain in `shared/core/authority.md`; a Goal, plan, worker result,
login, or evidence record never broadens authority.

## Opt-in legacy compatibility

Existing structured contracts remain installed and retain their current
paths, schemas, versions, validators, and semantics. They are used only when
an existing project already depends on the exact contract, the user explicitly
requests machine-audited output, or the user explicitly requests high-risk
recovery that needs that exact contract:

- project manifest v1/v2 resources under `shared/templates/` and
  `shared/schemas/`, with `shared/scripts/validate_project.py` and
  `shared/scripts/validate_project_v2.py`;
- Goal ledger and durable Story runtime in
  `shared/scripts/goal_ledger.py`, `shared/scripts/goal_runtime.py`, and
  `shared/references/durable-runtime.md`;
- evidence receipt v2/v3 schemas, templates, and validators in
  `shared/templates/`, `shared/schemas/`,
  `shared/scripts/validate_evidence.py`, and
  `shared/scripts/validate_evidence_v3.py`;
- Story Envelope and Story Receipt schemas/templates, and the hash-bound team
  runtime in `shared/scripts/team_protocol.py` with its existing Team Run,
  Worker Delivery, and Team Integration schemas/templates;
- established capability and profile contracts, including analysis input
  binding and `shared/profiles/quant-public-dashboard-strict.md`.

Legacy assurance and delivery labels apply only inside those existing
contracts. Do not mass-convert legacy artifacts, change their interpretation,
or require this compatibility layer for ordinary planning, Goal progress,
implementation, or completion. A `strict` label, long duration, release
delivery, task complexity, or repeated failure alone does not select a ledger
or structured runtime.

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

The installer validates the source, runs tests, stages a complete copy, backs
up the previous installation, transactionally replaces each of the three skills
and the shared resources with rollback on a caught failure, and verifies
installed hashes. A single directory rename is atomic, but the four-directory
suite update is not crash-atomic across process termination or power loss. It
installs `quant-plan`, `quant-goal`, `quant-developer`, and the non-discoverable
`quant-research-shared` resources under `~/.codex/skills/`.

For a release-grade update from committed source:

```bash
python3 install.py --update --require-clean-source
python3 ~/.codex/skills/quant-research-shared/scripts/validate_installed.py
```

## Design provenance

The suite has no LazyCodex or Gajae Code package, runtime, provider, state, or
installation dependency. It adapts only general principles such as
outcome-oriented persistence, useful parallelism, evidence over status, and
small workflow surfaces. It does not copy their prompts, source, assets,
protocols, or fixed orchestration machinery. Source and licensing notes remain
in `shared/advisory/external-comparisons.md`.
