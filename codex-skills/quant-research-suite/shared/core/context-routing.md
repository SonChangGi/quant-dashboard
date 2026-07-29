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
5. Load `references/agent-orchestration.md` only when the invoked workflow
   actually needs a Project Context Packet, role route, bounded team,
   real-surface evidence, or Continuation Capsule.

A missing or damaged shared runtime does not block an ordinary plan, local
implementation, or short `light`/`standard` host-only Goal. The short Goal may
still track objective, acceptance, checkpoints, blockers, and completion in
host state; report only selected ledger-backed or strict compatibility proof
as unavailable or unverified.

## Optional structured path

Use the shared routing tools when an applicable existing manifest or profile is
part of the project contract, the user explicitly requests onboarding or
machine-validated evidence, or a selected strict/legacy workflow requires them.
Do not infer capabilities merely from unrelated files elsewhere in a
multi-project workspace.

- Manifest schema v1 routes to the preserved legacy strict references and
  evidence receipt v2.
- Manifest schema v2 routes to its declared capabilities, profiles, adapters,
  and evidence receipt v3.
- Extra v2 modules supplied explicitly are supplemental; they do not reinterpret
  a v1 contract.
- `quantctl.py onboard --dry-run` is an optional read-only discovery aid. It
  never authorizes manifest creation or capability activation.

## Assurance and delivery

- `light`: small, reversible, low-risk work with direct deliverable proof.
- `standard`: work across multiple files/components or a public interface, with
  relevant project-native verification.
- `strict`: high-impact or repeated-failure work with the reviewed Plan Packet,
  baseline/failure-mode proof, cleanup, and layered independent review defined
  by the canonical assurance matrix. Selected capability gates extend that
  stack; they do not replace it or add a duplicate generic re-audit.

Represent risk assurance as `light`, `standard`, or `strict`, independently of
delivery `local` or `release`. A release delivery adds the release gate and the
consumer or public readback required by acceptance; it does not add a generic
independent re-audit or raise risk assurance. A declared public-web capability
specifically requires public-URL readback. Delivery never authorizes remote
action.

Legacy compatibility artifacts or values may retain `assurance=release` only
as the explicit Strict-plus-release meaning. Current structured artifacts use
the two dimensions, including `standard` risk assurance with `release`
delivery; older artifacts that omit `delivery` are interpreted without
rewriting their bytes.

Profiles are opt-in bundles. `quant-research-web` loads the Quant research
web-design contract; generic web tasks do not. Framework/provider adapters are
hints and checks for selected technology, never installation requirements.
