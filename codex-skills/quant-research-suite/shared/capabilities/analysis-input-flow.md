# Capability: analysis input flow

Use this ordinary-path rail when a UI control or other consumer input changes
an analysis, calculation, or result. Start with the repository's existing
contract, architecture, and checks.

Trace one representative input end to end:

```text
consumer input
→ validation and serialization
→ invoked analysis boundary
→ effective parameter
→ run or result identity
→ displayed or consumed result
```

Use an A/B fixture whose variant has an observable analytical effect, and
verify the actual consumer surface rather than only an echoed setting. Keep
draft, applied, pending, and bound state distinct so stale or uncomputed values
cannot appear current. Match proof depth to consequence and failure risk.

Do not require a manifest, capture bundle, raw trace, artifact hashes, or
receipt for this ordinary flow. If an existing schema-v2 manifest declares
`analysis-input-binding`, or the user explicitly requests machine-validated
provenance, route through `../core/context-routing.md`. The preserved strict
`analysis-input-binding.md` contract is compatibility-only; when its exact
children are absent, report that path as unavailable rather than recreating it.
