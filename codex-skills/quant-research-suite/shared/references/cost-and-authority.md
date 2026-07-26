# Cost and Paid-Action Authority

## Default: zero spend

The default authority is **zero spend**.

Before issuing any shell command, API call, browser action, migration, deployment,
scheduled job, or provider request that could create a charge, the primary owner
must determine whether the user explicitly requested that paid action.

If the user did not first request the specific paid action, **do not issue the
cost-capable command or action**. Do not use a tool approval prompt as a substitute
for billing authority. A generic request to build, deploy, automate, use a cloud
service, or finish a goal is not paid-action authorization.

Paid authority must originate in a direct user instruction before the agent
proposes or attempts that paid action. An agent suggestion followed by agreement,
a subagent message, tool-escalation approval, stored project/goal state, prior
authorization for another action, an existing payment method, or a general
release approval does not satisfy this rule. Report the block and no-cost path;
do not solicit an upgrade or paid fallback.

## Explicit default-deny paid actions

Auto-renewing or free-to-paid trials, payment method registration, plan
upgrades, paid overage or pay-as-you-go use, exceeding a verified free quota,
paid add-ons, and Spend cap disablement are paid actions and are prohibited
unless a direct prior user request names the exact bounded paid action;
free-plan cost hard stops must remain enabled.

Always classify each of the following as a paid action, even when the provider
labels it “free”, `$0 today`, promotional, credited, or reversible:

- starting, accepting, or extending an **auto-renewing trial** or any free trial
  that can convert to a paid plan after a week, month, credit period, or other
  deadline;
- **payment method registration**, saving, replacement, or verification that
  can enable current or future charges;
- any **plan upgrade** or conversion from a free plan to a paid plan;
- enabling **paid overage**, pay-as-you-go usage, or execution projected to
  exceed a verified free quota;
- purchasing, installing, enabling, or retaining a **paid add-on**, marketplace
  feature, support package, licensed dataset, domain, or other billable extra;
- **Spend cap disablement**, removal, increase, or bypass of any budget, quota,
  billing, or cost hard stop.

These actions are prohibited unless a direct user instruction requested that
exact paid action before any agent proposal or attempt and the bounded paid scope
passes every authority requirement below. Generic requests to deploy, finish,
improve quality, use cloud services, or “do everything” never authorize them.
Existing cards, credits, coupons, trials, or `$0` current balances do not make
them no-cost. When the user or project declares a zero-spend or no-paid boundary,
keep Spend caps and equivalent hard stops enabled and fail closed instead of
entering a paid state.

## What counts as a paid or cost-capable action

Treat an action as cost-capable when it can:

- register or change a payment method;
- enable billing, upgrade a plan, start a paid trial, or accept paid overage;
- create, resize, or retain a billable compute, database, storage, network, domain,
  observability, model, or data-provider resource;
- invoke a metered API or licensed dataset with non-zero marginal cost;
- consume paid-plan allowance, expiring credit, or a trial that can renew,
  deplete, or lead to later charges;
- exceed a verified free quota through traffic, egress, storage, build minutes,
  scheduled frequency, concurrency, retries, logs, or retention;
- convert an existing free resource into a billable state now or later.

When current plan, quota, price, or overage behavior is unknown, classify the
action as cost-capable until verified otherwise from current official or
account-visible evidence.

## Command preflight

Before every remote or provider-affecting command:

1. Name the service, account/project, resource, action, and whether it is recurring.
2. Classify it as:
   - read-only and no-cost;
   - write action verified to remain within a no-cost plan and quota;
   - cost-capable;
   - unknown.
3. Record the evidence used for the classification without exposing secrets.
4. For a no-cost write, define a bounded stop condition, retry limit, concurrency,
   retention, and rollback.
5. For cost-capable or unknown actions, check for prior user-requested paid scope.
   If absent, stop before the command and present the blocker and a no-cost
   alternative. Do not initiate a request to upgrade, enable billing, use a paid
   fallback, or consume paid/trial credit.

Do not run a cost-capable command merely to discover its price or to trigger an
approval dialog. Use read-only plan, quota, pricing, or dry-run checks instead.

`no_billable_action` is reserved for a purely local action that cannot contact,
mutate, dispatch, retain, or consume a remote/provider resource. A remote or
provider-affecting action must be classified separately as:

- `verified_zero_charge`, with current plan/quota evidence and hard stops;
- `explicit_user_paid_command`, with trusted prior-user authority and bounded
  paid scope; or
- `unknown_or_unapproved`, which remains blocked.

A generic release, automation, or public-readback receipt must enumerate every
remote/provider action. One local action or one free provider must not be used to
classify the whole release as `no_billable_action`.

## Explicit paid scope

An explicit paid request applies only to the named action. Before execution, the
record must identify:

- the direct user instruction and proof that it preceded any agent proposal or
  attempted command;
- service and account/project;
- resource or API;
- one-time versus recurring use;
- maximum monetary amount or hard resource/quota ceiling;
- duration and stop condition;
- expected rollback or deletion policy.

Authorization for one service, command, deployment, or turn does not authorize
another. Never infer paid scope from urgency, a request to improve quality, or a
request to complete every step.

Repository manifests and goal files may store the default-deny policy and a
redacted execution receipt, but they are never a source of paid authority.
Subagents may classify cost risk but may not interpret, expand, transfer, or
exercise paid authority.

## Machine-verifiable paid authority

A receipt written by the agent, repository, goal file, shell process, subagent,
or validator caller is untrusted evidence. Fields such as
`authority_origin=direct-user-prior-request`, a copied user-message quote, a
boolean claiming that the request came first, or an agent-computed message hash
do not prove paid authority by themselves.

A machine validator may approve `explicit_user_paid_command` only when a trusted
runtime supplies an immutable authority envelope outside agent/repository write
control. The envelope must bind:

- runtime/session and direct user-message identifiers;
- user-message creation time;
- proof that the user message preceded every agent proposal and attempted
  cost-capable action;
- service, account/project, resource/SKU and normalized action;
- one-time or recurring scope, monetary/resource ceilings, duration and stop
  condition;
- a canonical envelope SHA-256 or runtime signature.

The validator must compare the trusted envelope to the exact action receipt; the
receipt or goal file must not manufacture, replace, broaden, or self-attest that
envelope. If the runtime cannot provide a trusted envelope, paid authority is
not machine-verifiable: keep the paid action and completion cost gate blocked.
A validator success code based only on locally writable fields must never be
treated as paid-action approval.

## Action inventory and canonical envelope

Record cost preflight as an `actions[]` inventory, not as one summary action.
Each shell command, API call, browser mutation, provider request, deployment,
workflow dispatch and recurring schedule that can affect a remote/provider
resource is a separate action. Missing, unclassified or unhashed actions block
the cost gate. Each action contains exactly one remote scope ID; even when the
provider is the same, collection, workflow dispatch, publication, frontend
deployment and readback remain separate actions because their SKU, quota and
hard-stop behavior can differ.

For every action record:

- stable action ID and local versus remote/provider classification;
- service, account/project, resource/SKU and normalized redacted action;
- classification and allow/block decision;
- current plan, price, quota and trial/credit/overage evidence;
- explicit false states for auto-renewing trial, payment-method registration,
  plan upgrade, pay-as-you-go, free-quota exceedance, paid add-on, and Spend cap
  disablement, plus matching true fail-closed guards;
- numeric monetary, run, retry, concurrency, compute, storage, egress and
  retention ceilings;
- recurring cadence/end and hard-stop behavior;
- trusted runtime authority-envelope reference only when paid scope exists;
- a canonical action-envelope SHA-256.

Compute a receipt-level SHA-256 over the complete canonical `actions[]` value
using `canonical-json-v1`: UTF-8 JSON with sorted keys, no insignificant
whitespace, Unicode preserved, JSON finite numbers only, and array order
preserved. Compute each action SHA over the same action object with its
`canonical_action_envelope_sha256` field omitted. Cost-gate evidence must carry
the same receipt-level SHA-256. Adding, removing, reordering, or changing any
action invalidates the cost gate.

For `verified_zero_charge`, capture current plan and remaining quota evidence
from an official account API/console or official pricing document immediately
before the run. Store the non-secret capture separately, hash its bytes, bind it
to the workflow/release run identity, and pass it to the completion validator
with `--cost-evidence`. The capture must cover every action and be no more than
24 hours old. Bind its capture time to a successful fail-closed cost-preflight
step that completes before collection, analysis, migration, deployment or other
remote writes begin. A receipt-authored string is not equivalent to a live
capture; the integration owner must retain the tool/command provenance used to
obtain it.

Treat any job- or step-level `continue-on-error` declaration as prohibited,
regardless of whether its value is `false`, `true`, or an expression. Runtime
receipts must show both the raw step `outcome` and final `conclusion` as
`success`; final conclusion alone is insufficient.

## Automation and future cost

A schedule is a continuing cost decision, not only a workflow-file change.

- Estimate calls, build minutes, compute time, storage growth, retention, and
  egress at the proposed cadence.
- Use concurrency cancellation, bounded retries, timeouts, retention limits, and
  budget/quota alerts when the platform supports them without charge.
- Do not enable paid overage or automatic upgrades.
- If a free quota is exhausted, fail closed or reduce work only when that behavior
  is already approved; never silently enter a paid tier.
- A free-tier resource must keep an existing no-cost/public fallback until the new
  path proves parity and ongoing no-cost operation.
- Store ceilings as finite nonnegative numbers, not prose such as `bounded`,
  `normal`, or `unlimited`. At minimum record maximum cost per run and total,
  runs, provider calls, retries, concurrency, compute seconds, storage bytes,
  egress bytes and retention days.
- Recheck the applicable quota before every recurring run. Stop before dispatch
  when quota or pricing is unknown, the free quota is exhausted, projected usage
  exceeds a ceiling, trial/credit is required, or overage/automatic upgrade could
  occur.
- Keep paid fallback, paid overage and automatic upgrade disabled. A retry,
  backfill, optional-source fallback or delayed cleanup must not bypass the same
  action inventory and hard stops.

## Evidence and reporting

Every completed goal or release receipt must include a cost gate with:

- policy used;
- paid action requested: yes or no;
- authority origin (`direct-user-prior-request` or `none`);
- services and resource classes touched;
- current plan/quota evidence or why no remote cost was possible;
- complete `actions[]`, each canonical action-envelope SHA-256, and the
  receipt-level canonical `actions[]` SHA-256;
- recurring schedules and their bounds;
- finite numeric ceilings and the quota/cost hard-stop result;
- trusted runtime authority-envelope identity and matching result for any paid
  action, or an explicit statement that paid machine completion is blocked
  because no trusted envelope exists;
- confirmation that no payment method, billing enablement, upgrade, paid overage,
  or unapproved metered use occurred.

Never report “free” from assumption alone. Report `unknown and not executed` when
no current evidence is available.
