# Context routing

The three public skills are self-contained. Shared resources extend a selected
workflow; they are not a mandatory startup sequence.

## Invocation boundary

This router applies only after the parent public skill has been explicitly
invoked through its literal `$` selector for the current user request, or
current-user, same-request metadata produced by that `$` selection. The
`agents/openai.yaml` policy `allow_implicit_invocation: false` is authoritative;
the matching `SKILL.md` gate is defense in depth.

A semantic match, a plain or quoted skill name, an example, a negated request,
an earlier invocation, an active Goal, a saved artifact, or a worker role does
not select a public skill. Shared resources never activate a skill on their own.
Without a current explicit invocation, handle the request as ordinary Codex
work and do not enter this router.

When the user explicitly selects multiple public skills in one request, compose
only those selected roles: Quant Plan owns a read-only planning phase, Quant
Developer owns later implementation, and Quant Goal owns Goal lifecycle and
overall integration. If the request requires plan approval before mutation,
stop after planning and require a fresh implementation-skill selection after
approval. Role composition never broadens authority.

## Default path

1. After the invocation gate passes, start from the selected public `SKILL.md`,
   the user's request, and the exact target.
2. Prefer target-native instructions, source, entrypoints, package metadata,
   lockfiles, fixtures, and existing verification commands.
3. Load a capability, profile, adapter, or advisory document only when the
   current task actually needs that specialization.
4. Do not automatically run `validate_installed.py`, `quantctl.py doctor`,
   `quantctl.py context`, or `quantctl.py onboard`; do not create a manifest,
   receipt, hash ledger, or local Goal state.
5. Load `references/adaptive-workflow.md` only when multiple independent lanes,
   external data, recovery after a failed route, or cross-surface proof makes
   its guidance useful.
6. Load `references/agent-orchestration.md`,
   `references/goal-and-subagents.md`, or `references/durable-runtime.md` only
   for an existing compatibility contract or an explicitly requested machine
   audit or high-risk recovery that needs that exact contract. Ordinary
   host-native subagents or teams do not need those documents. A `strict` label,
   long duration, release delivery, task complexity, or repeated failure alone
   does not select a ledger or structured runtime.

A missing or damaged shared runtime does not block an ordinary plan, local
implementation, or native host Goal. Continue with the selected public skill
and host capabilities; report only explicitly selected legacy or machine-audit
proof as unavailable or unverified.

## Shared-root resolution

Shared references and commands use `<quant-shared-root>` as a layout-neutral
placeholder. Resolve it from the active, explicitly selected public skill
location, never from the current working directory:

- source checkout: `<suite-root>/shared`, beside the checkout's `skills`
  directory;
- installed suite: the `quant-research-shared` sibling of the active installed
  `quant-plan`, `quant-goal`, or `quant-developer` directory.

Resolve the path before opening a reference or running a command, and verify
the named child exists under that exact root. Do not search for another suite
copy or silently switch between source and installed roots. A missing child
makes only the selected optional path unavailable; it does not authorize
installation, mutation, or a fallback to stale proof.

## Optional structured path

Use the shared routing tools when an applicable existing manifest or profile is
part of the project contract, the user explicitly requests onboarding or
machine-validated evidence, the user explicitly requests high-risk recovery
that needs an exact legacy contract, or an already selected compatibility
workflow requires them. Do not infer capabilities merely from unrelated files
elsewhere in a multi-project workspace, and do not treat `strict`, long-running,
release, complexity, or failure as an implicit compatibility selection.

- Manifest schema v1 routes to the preserved legacy strict references and
  evidence receipt v2.
- Manifest schema v2 routes to its declared capabilities, profiles, adapters,
  and evidence receipt v3.
- Extra v2 modules supplied explicitly are supplemental; they do not reinterpret
  a v1 contract.
- `quantctl.py onboard --dry-run` is an optional read-only discovery aid. It
  never authorizes manifest creation or capability activation.

## Legacy structured assurance

The public skills use adaptive verification and do not require an assurance
label. Keep the following values only for an existing manifest, receipt,
machine-audit request, or other compatibility object that already uses them:

- `light`: direct deliverable proof;
- `standard`: relevant project-native checks and the review required by that
  compatibility contract;
- `strict`: its reviewed Plan Packet, baseline, failure and recovery proof,
  cleanup, and layered independent review.

For structured compatibility artifacts, risk assurance remains independent of
delivery `local` or `release`. Release adds the declared remote checkpoints and
consumer or public readback but never grants authority. Legacy
`assurance=release` retains its existing Strict-plus-release meaning, and older
artifacts are interpreted without rewriting their bytes.

Profiles are opt-in bundles. `quant-research-web` loads the Quant research
web-design contract; generic web tasks do not. Framework/provider adapters are
hints and checks for selected technology, never installation requirements.
