# Canonical Web Design Source

For the user's Quant Research projects, resolve the canonical design contract in this order:

1. `<current-project>/docs/web-design.md` when the project explicitly owns the canonical file.
2. `<quant-dashboard-source-root>/docs/web-design.md` when that repository checkout is explicitly supplied by the project manifest or current repository context.
3. In this source package, `<quant-research-suite>/shared/references/web-design-v2.4.0.md`.
4. In a local installation, `<installed-skills-root>/quant-research-shared/references/web-design-v2.4.0.md`.
5. Public fallback: `https://sonchanggi.github.io/quant-dashboard/docs/web-design.md`.

Read the selected file completely before UI work.
Do not guess a user home directory or scan unrelated worktrees to resolve it.

For the bundled baseline:

- version: `2.4.0`
- source date: `2026-07-24`
- SHA-256: `e7000c09db8250817e320a539a59b5482d325142ca8ba676a9f33c59ff3646d1`

If a local canonical file has a newer declared version, use it after confirming it is intentional. If content changes without a version update, report the drift before broad rollout.

The design contract does not authorize changes to analysis, data, result schema, automation, chart semantics, or table columns.

For non-Quant projects, use the same procedure with the project's own design system. Treat this bundled document as a quality and audit pattern, not a mandatory visual identity.
