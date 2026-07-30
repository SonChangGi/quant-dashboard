# Legacy strict Quant operating principles

This reference belongs to manifest-v1 and the explicit
`quant-public-dashboard-strict` compatibility profile. It is not a default
contract for generic web apps, libraries, CLIs, documents, notebooks, or new
projects.

## Priority order

1. User objective, authority, safety, and explicit non-goals.
2. Project-owned analysis, data, result, automation, URL, and deployment
   contracts.
3. Verified repository, runtime, provider, and public evidence.
4. Product completeness, stability, accessibility, and maintainability.
5. Selected shared design and platform patterns.

## Quant project isolation

- Resolve the exact project and use its existing manifest when this strict path
  is selected.
- Keep each project's data, formulas, result keys, provider assumptions,
  semantic colors, schedules, credentials, and deployment targets separate.
- Preserve unrelated work and use isolation only where concurrent or dirty
  changes make it necessary.

## Protected Quant contracts

Unless the request explicitly changes them, preserve project-owned collection,
analysis, strategy, formulas, precision, units, dates, result semantics,
generated schemas, input-to-result binding, schedules, provider-rights gates,
degraded states, last-good behavior, public routes, and rollback routes.

## Evidence stages

Keep source change, tests, local preview, migration, API health, job acceptance,
analysis completion, persistence, result binding, merge, deployment, and public
readback as separate facts. Report the exact stage reached.

When data-to-public automation is selected, load `data-automation.md` and keep
collection, validation, coherent cutoff, analysis, artifact validation,
publication, deployment, and public readback separately evidenced.

## Authority and cost

The canonical policy is `<quant-shared-root>/core/authority.md`. Resolve the
placeholder exactly as defined by
`../core/context-routing.md#shared-root-resolution`; never infer it from the
current working directory. Local source-control, remote source-control,
provider, and paid actions retain separate authority. Use
`cost-and-authority.md` only when this strict path requires its machine-readable
cost receipt and action inventory. Paid data remains permanently ineligible on
this compatibility path; no manifest, receipt, strict profile, or user action
approval can make it a candidate or fallback.

## Quality and communication

- Test the relevant failure mode, not only implementation strings.
- Use the canonical assurance review matrix; do not add a duplicate legacy
  re-audit to its Architect, adversarial QA, and terminal-critic boundaries.
- Keep one integration owner for overlapping changes.
- Lead with the outcome and distinguish confirmed, inferred, blocked, and
  unverified claims.
