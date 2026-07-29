---
name: "quant-plan"
description: "Use only when the user explicitly invokes $quant-plan. Shape work into a reviewed, decision-complete plan with observable acceptance; never auto-activate."
---

# Quant Plan

## Explicit invocation gate

Activate only when the current user request intentionally invokes this skill
through the literal token `$quant-plan`. If the host replaces that token with
invocation metadata, accept only current-user, same-request metadata produced
by that `$` selection.

A semantic task match, the plain name `quant-plan`, a quoted, example, or
negated token, an earlier invocation, an active Goal, a Plan Packet, an
artifact, or another agent's instruction is not activation. If this skill is
selected without the explicit gate, do not apply it or load its shared
references; continue as an ordinary Codex request.

The invocation applies only to the current request. It authorizes planning,
not implementation or activation of another Quant skill.

## Outcome and trigger

After the invocation gate passes, use this skill for a plan, structured audit,
external comparison, project-context map, or greenfield project shape before
implementation.

This skill owns discovery, the proposed decision, the proposed acceptance in
the Plan Packet, and the packet itself. It is read-only: it does not implement,
create Goal state, install dependencies, edit files, or perform local, remote,
provider, destructive, or paid mutations. Do not activate it for a direct
implementation request, simple explanation, or status check unless the user
also asks for a plan or audit.

Choose the lightest useful mode:

- `quick-plan`: a narrow, reversible decision;
- `audit`: current-state findings and prioritized recommendations;
- `audit+comparison`: an audit plus a comparison supported by current evidence;
- `new-project`: a decision-ready shape for a project that does not exist yet.

## Default path

The default path is self-contained. Do not require shared tooling, a project
manifest, a receipt, a Goal, or a suite command.

1. Define the user-visible outcome, audience, success criteria, constraints,
   non-goals, and decision to settle.
2. Inspect only current state relevant to that decision. Prefer the target's
   own instructions, source, configuration, entrypoints, tests, artifacts, and
   observed behavior.
3. Discover repository or system facts before asking the user. Ask one
   material preference at a time only when its answer changes the plan.
4. Research current primary sources when an external product, library,
   standard, provider, paper, price, quota, or other unstable fact affects the
   decision. Separate fact, inference, limitation, and recommendation.
5. When data is in scope, search the free-only source and method ladder below
   far enough to find the best attainable route under the user's environment
   and claims. Do not turn ideal evidence that the outcome does not claim into
   a default blocker.
6. Select one coherent approach and make its handoff decision-complete without
   designing unused infrastructure.

Only when a material decision or contradiction remains, add a short,
nonnumeric `decision_readiness` section to the draft with the issue, evidence,
decision owner, and clearing condition. Omit it when the decision is already
ready. Do not calculate a score, set a threshold, or force a fixed interview or
review round, and do not freeze the Plan Packet until every listed item is
resolved or explicitly removed from the selected scope.

Git, a branch, a public route, automation, or deployment matters only when it
exists and affects the decision. A non-Git directory, document, notebook,
process, or research deliverable is a valid planning target. Greenfield
planning does not create or scaffold the target.

## Context and evidence design

For a large, unfamiliar, or long-lived target, build a read-only Project
Context Packet before deciding. Read existing instruction and context files
first; do not create or rewrite `AGENTS.md` or another memory artifact unless
the user separately requests that mutation through an implementation
workflow. Map only the architecture, ownership boundaries, entrypoints,
project-native commands, protected contracts, source references, workspace
identity, and staleness conditions needed by the plan.

Already-installed local LSP, AST, or codegraph tools may supply opportunistic
read-only evidence when they materially improve navigation or reference
analysis. Confirm important claims with source, `rg`, a compiler, or
project-native checks. Do not install a tool, start a daemon, register MCP,
change global configuration, or upload source externally for this purpose.

Actively use available read-only subagent or agent-team lanes when independent
repository, source, method, or verification questions would materially widen
the search or shorten discovery. Useful lanes include project-contract
inspection, multiple free-source candidates, alternative methods or proxies,
and an independent challenge to a consequential assumption. Run independent
lanes in parallel and give each a bounded question and return contract. A
concise in-memory brief is the default; do not require a structured Team Run
Packet, worktree, hash binding, or fixed role count for ordinary read-only
planning.

The primary planner inspects and reconciles every returned claim into one
decision and remains responsible for the result. Route work by needed role and
capability rather than hard-coding a provider, model name, worker count, file
count, line-count threshold, or a rule that delegation is always required.

Every acceptance criterion names the direct evidence channel that could prove
it on the real target surface. The Project Context Packet, role router,
surface-evidence selector, and continuation rules are defined once in:

- installed
  `../quant-research-shared/references/agent-orchestration.md`;
- source `../../shared/references/agent-orchestration.md`.

## Free-only data and proportional evidence

Data acquisition has a hard no-paid-data boundary. Never propose or use a paid
dataset, feed, API, terminal, tier, or fallback. This prohibition includes:

- trials or credits that expire;
- freemium access that requires later payment for continuity;
- automatic free-to-paid conversion;
- card or billing-profile setup;
- pay-as-you-go, overage, paid add-ons, or paid tiers.

Do not ask the user to approve paid data. If a currently no-billing source
becomes paid or adds a billing requirement, mark that route unusable, stop
using it in the proposed path, and move to a no-billing fallback, a transparent
proxy, a narrower result, or an explicit unavailable state.

Match data evidence to the actual acceptance claim and planned use:

- Local or private research using a lawfully accessible no-billing price or
  corporate-actions source may proceed with lightweight provenance: provider
  and endpoint or collector, access date, source `as_of` when available,
  fields used, adjustment or corporate-action semantics, and known
  limitations. Do not require an exhaustive rights memorandum by default.
- Public display or publication needs a current, proportional check of the
  terms that govern the exact planned display or derived output. Raw or
  substantial provider-data redistribution, an explicit restriction,
  access-control circumvention, or unclear permission for the intended
  redistribution remains a stop boundary; prefer derived results, a permitted
  alternative, or no public data rather than assuming rights.
- Require historical point-in-time provenance only when acceptance claims that
  an input was known at the historical decision date, or that a result is
  look-ahead-free, survivorship-free, revision-safe, or otherwise PIT-correct.
  When those claims are not required, non-PIT data may be used if the plan
  labels the exact limitation and avoids making the stronger claim.
- Free-source uncertainty alone does not make work `strict`. Raise assurance
  only when the claimed result or intended use makes the uncertainty
  consequential.

For a local/private `light` or `standard` plan, the lightweight record above is
normally sufficient. Do not add immutable raw snapshots, per-file hashes, a
full source registry, offline replay, a universal PIT-status taxonomy, or
complete corporate-action reconstruction unless the accepted result actually
depends on that proof or the project already owns it. Completeness means the
strongest useful result requested under the available constraints, not the
largest provenance bundle.

Explore source and method alternatives in this order, stopping when the
selected route is sufficient for the claim:

1. an existing usable project-owned no-billing source, snapshot, or cache;
2. an official no-billing endpoint, download, filing, or publication;
3. another lawfully accessible no-billing public source with suitable fields;
4. reconciliation across free sources or a method derived from free inputs;
5. a disclosed proxy, reduced scope, degraded result, last-good result, or
   explicit unavailable state.

Compare viable candidates on fitness for the claim, coverage, adjustment and
revision behavior, quota and continuity, reproducibility, maintenance burden,
and actual use restrictions. Never fabricate, silently fill, disguise stale
or non-PIT data, bypass access controls, expose secrets, or weaken a project's
missing/degraded/unavailable semantics in order to complete the plan.
Do not spend the comparison budget cataloguing paid sources; mention an
ineligible source only when needed to prevent accidental selection, then
continue with free candidates.

## Proportional depth

Choose two independent dimensions:

- assurance: `light`, `standard`, or `strict`;
- delivery: `local` or `release`.

Assurance changes planning and review depth, not scope or authority. Delivery
describes where the accepted outcome must be observed. A `release` delivery
adds the applicable authorized remote checkpoints and public or consumer
readback; it does not by itself elevate assurance to `strict`. Treat the
shared matrix's combined `release` row as optional legacy strict compatibility,
not the generic default. Subagent use, file count, framework choice, free-data
use, or missing ideal provenance alone does not raise assurance.

For `light` and `standard`, the primary planner performs one self-critique for
missing decisions, acceptance gaps, and unsupported assumptions before
handoff. Do not commission an independent critic merely to add review count.

Use `strict` for actual high-consequence conditions such as security or
privacy exposure, destructive migration, regulated or explicitly restricted
data use, high-consequence computation, a required PIT-correct claim, or
repeated material failure. Establish the relevant baseline, failure modes,
recovery, and one independent plan critique, then, once decision-ready, freeze
the reviewed Plan Packet for the Goal or implementation handoff. Add an
independent architecture reviewer only when boundaries, data/control flow,
migration, security, or operational topology create a material architecture
risk. When both reviewers apply, they inspect the same immutable draft and the
primary planner joins their findings into one revision. Do not require fixed
three-role consensus or a fixed review-loop count.

Do not duplicate later implementation review: plan reviewers evaluate the
decision and acceptance before mutation. For every reviewed strict packet,
bind the exact Plan revision or digest, the exact acceptance revision, and the
critic verdict as one identity. Any change to the plan or acceptance invalidates
that verdict until the affected revision is reviewed again. Never hand off an
older reviewed Plan against newer acceptance, or call an unbound draft
reviewed.

The detailed assurance matrix, Plan Packet fields, reviewer ownership, and
handoff lifecycle live in the shared workflow contract. Resolve the path that
exists for the current layout:

- installed `../quant-research-shared/references/goal-and-subagents.md`;
- source `../../shared/references/goal-and-subagents.md`.

## Existing contracts and technology choices

Protect contracts established by the user, project, or inspected behavior.
Do not assume that every project has analytical data, a frontend, backend,
automation, public route, or deployment identity. Preserve a contract only
when it remains outside the approved change.

Recommend technology from demonstrated need, current project fit, operational
burden, failure model, verification, and exit cost. Popularity or another
project's choice is not sufficient.

## Output and handoff

Return the smallest output that settles the requested decision:

- `quick-plan`: outcome, selected decision, material assumptions, focused
  evidence or check, and the next handoff;
- `audit`: confirmed findings, impact, prioritized recommendations, and
  material limitations or unverified claims;
- `audit+comparison`: the audit plus only the viable alternatives and their
  decision-changing trade-offs;
- `new-project` or an implementation plan: the smallest decision-complete Plan
  Packet.

Do not force a full implementation sequence, source registry, authority
inventory, or frozen Plan Packet into a quick plan or audit unless the user
asks for it or the decision cannot be made safely without it. When a Plan
Packet is warranted, bind material findings to stable acceptance IDs, the
selected change, applicable contracts, verification, the assurance and
delivery dimensions, authority checkpoints, assumptions, and deferrals as
defined in the shared workflow contract.

The primary planner reconciles all read-only specialist evidence and authors
one packet. Use specialists only for bounded repository inspection, current
primary-source research, domain review, or an independent plan critique that
improves the decision.

Do not invoke implementation, Goal, or another skill. Planning approval is not
execution approval. If a later Goal binds the packet, its owner controls
acceptance revision history; Quant Plan remains an advisory, read-only author
of any proposed revision.

## Optional strict compatibility

Use suite tooling only when the target already has a Quant manifest or profile,
the user requests machine-validated evidence or legacy compatibility, or a
selected strict Quant capability needs its validator.

Then resolve `quant-research-shared`, use the existing manifest rather than
creating one, and load only selected capability, profile, adapter, or advisory
resources. Existing manifest v1/v2 and receipt v2/v3 contracts remain
authoritative on that path. Diagnostic commands are optional, not startup
requirements.

If the shared runtime is unavailable or invalid, report that the optional
strict check could not run and continue the generic read-only plan unless that
check is itself an acceptance criterion.

## Authority

Planning never grants implementation, remote, destructive, secret-bearing,
provider, raw-redistribution, or paid authority. The no-paid-data rule above is
an absolute scope constraint, not an approval checkpoint: never request an
exception or present paid data as a fallback. For all other applicable
authority, consult only the canonical policy at installed
`../quant-research-shared/core/authority.md` or source
`../../shared/core/authority.md`, whichever exists, and mark the later approval
boundary without reproducing its taxonomy.
