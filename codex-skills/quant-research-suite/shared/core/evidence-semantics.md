# Evidence semantics

Evidence records what was actually checked. It does not grant scope, release, or
payment authority.

## Default evidence

Ordinary planning and local implementation use the smallest direct evidence
that supports the claim: an inspected artifact, a focused test, a project-native
build, or an observed behavior. They do not require a manifest, receipt, hash,
cost gate, or machine-readable bundle.

Use structured receipts and derived gates only when an existing strict/legacy
contract or an explicit request selects that compatibility path. Local,
non-billable work does not create cost evidence merely because the structured
runtime supports it.

## Status vocabulary

- `passed`: a deterministic check completed successfully.
- `verified`: an inspection confirmed the claimed state.
- `failed`: the check ran and disproved the claim.
- `blocked`: the check could not safely run because authority, prerequisites, or
  trusted state were missing.
- `not_applicable`: allowed only for a gate that is not required by the resolved
  capability context.

Do not translate `blocked`, skipped, queued, started, expected, or inferred into
`passed`.

## Structured evidence item

When a structured receipt is selected, each item identifies its kind, source,
timestamp, concise claim, and result.
Command evidence includes the normalized command and exit code. Artifact
evidence includes a project-relative path or stable identifier and, when
identity matters, its SHA-256. Inspection evidence states what surface was
inspected and how.

## Gate derivation

Within the structured manifest/receipt runtime, required gates are derived from
assurance and effective capabilities, not copied from a receipt. Custom gates
may add rigor but cannot remove derived gates. Structured completion requires a
passing item for every derived gate and every bound acceptance criterion.

## Evidence boundaries

- Local tests do not prove remote deployment.
- Deployment does not prove public readback.
- Public HTML does not prove current result data.
- Data collection does not prove coherent freshness, analysis, publication, or
  frontend adoption.
- Health/readiness does not prove a job result.
- A subagent receipt is a review input, not accepted completion.
- A locally authored capture proves validated bundle consistency, not an
  external identity. Cryptographic origin claims require a trusted CI/runtime
  attestation in addition to the local receipt.
