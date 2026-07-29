# Runtime capability: multi-agent write

This is an opt-in structured task-runtime capability, not a persistent project
property. Normal host subagents do not activate it merely by being used, and
the capability itself does not raise assurance. Select it when a strict/legacy
Goal runtime needs machine-checked write handoffs.

For host-native concurrent teams, use `agent-team-execution` instead. Do not
run both handoff protocols for the same worker result merely to duplicate
evidence; this capability preserves the legacy single-root Story contract.

- Use specialists only for concrete bounded work that can proceed independently.
- One integration owner remains responsible for the project.
- Only one open write story may own an overlapping surface. Prefer read-only
  research and independent audit specialists.
- Issue a story envelope with project binding, objective, mode, allowed and
  protected paths, dependencies, acceptance criteria, baseline identity, and
  external-effect/cost class.
- A worker returns a receipt marked ready for review. The integration owner
  recomputes changed paths, verifies evidence and dependencies, runs integration
  checks, and alone accepts it.
- Envelopes and receipts cannot grant remote, deploy, merge, destructive, or paid
  authority.

Evidence gate: `handoff_review`.
