# Canonical Web Design Source

For the user's Quant Research projects, resolve the canonical design contract in this order:

1. `<current-project>/docs/web-design.md` when the project explicitly owns the canonical file.
2. `<quant-dashboard-source-root>/docs/web-design.md` when that repository checkout is explicitly supplied by the project manifest or current repository context.
3. In this source package, `<quant-research-suite>/shared/references/web-design-v2.4.2.md`.
4. In a local installation, `<installed-skills-root>/quant-research-shared/references/web-design-v2.4.2.md`.
5. Public fallback: `https://sonchanggi.github.io/quant-dashboard/docs/web-design.md`.

A candidate is usable only when its declared navigation count, repeated
menu/link count statements, and registry label, order, and URL agree. If a
candidate contradicts itself, report the drift and continue to the next
candidate; locality alone does not make an inconsistent contract canonical.

Read the selected usable file completely before UI work.
Do not guess a user home directory or scan unrelated worktrees to resolve it.

For the bundled baseline:

- version: `2.4.2`
- source date: `2026-08-25`
- SHA-256: `88b2f130f354b1232ffbcb4a48d0807bbb78ce81aaf74c8a41ddbc4f88f7e996`

If a local canonical file has a newer declared version, use it after confirming it is intentional. If content changes without a version update, report the drift before broad rollout.

The design contract does not authorize changes to analysis, data, result schema, automation, chart semantics, or table columns.

For non-Quant projects, use the same procedure with the project's own design system. Treat this bundled document as a quality and audit pattern, not a mandatory visual identity.
