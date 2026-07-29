# Capability: authoritative analysis

Activate when a project computes or presents analytical results.

- Identify authoritative entrypoints and result identity before changing
  adapters or presentation.
- Preserve formulas, parameters, defaults, input data meaning, result schema,
  units, and date semantics unless explicitly authorized.
- Never replace project-owned Python or another authoritative worker with a
  frontend approximation.
- Bind results to project, run/result identity, requested/effective config, data
  date, code/schema version, and artifact hash when those identities exist.
- Keep human-readable identity names in `result_identity_fields`. When
  `analysis-input-binding` is active, also declare their exact result JSON
  locations, in the same order, in `result_identity_pointers`. The arrays must
  have equal length; identity/config metadata cannot be used as evidence that
  an analytical outcome changed.
- Missing or failed required data must remain unavailable/degraded according to
  the project contract; never fabricate or silently weaken logic.

Evidence gate: `analysis_result`.
