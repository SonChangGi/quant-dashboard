# Capability: authoritative analysis

Apply this rail when a project computes or presents analytical results.

- Identify authoritative entrypoints and result identity before changing
  adapters or presentation.
- Preserve formulas, parameters, defaults, input data meaning, result schema,
  units, and date semantics unless explicitly authorized.
- Never replace project-owned Python or another authoritative worker with a
  frontend approximation.
- Bind results to the project, run or result, requested and effective inputs,
  data date, code or schema version, and artifact identity that the project
  actually uses. Do not invent missing identity fields or hashes for ordinary
  work.
- When a consumer input changes the analysis, use
  `analysis-input-flow.md` and prove an observable result change rather than an
  echoed setting. Preserve an existing strict schema contract only through
  `../core/context-routing.md`.
- When acceptance makes an empirical investment claim—such as backtest,
  ranking, performance, or signal validity—choose only the validity checks
  material to that claim. Consider timing or leakage and point-in-time
  availability, universe or survivorship, benchmark and portfolio construction,
  turnover, fees or slippage, out-of-sample stability, and selection,
  overfitting, or multiple-testing risk. State unsupported limits; do not run a
  universal checklist.
- Missing or failed required data must remain unavailable/degraded according to
  the project contract; never fabricate or silently weaken logic.
