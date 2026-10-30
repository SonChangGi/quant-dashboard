# Canonical Web Design Source

For the user's Quant Research projects, resolve the canonical design contract in this order:

1. `<current-project>/docs/web-design.md` when the project explicitly owns the canonical file.
2. `<quant-dashboard-source-root>/docs/web-design.md` when that repository checkout is explicitly supplied by the project manifest or current repository context.
3. Public current fallback: `https://raw.githubusercontent.com/SonChangGi/quant-dashboard/main/docs/web-design.md`, with its companion `https://raw.githubusercontent.com/SonChangGi/quant-dashboard/main/docs/design-v3.md`.
4. When no current source is available, the historical package baseline `<quant-research-suite>/shared/references/web-design-v2.4.2.md`.
5. Historical installed baseline: `<installed-skills-root>/quant-research-shared/references/web-design-v2.4.2.md`.

A candidate is usable only when its declared navigation count, repeated
menu/link count statements, and registry label, order, and URL agree. If a
candidate contradicts itself, report the drift and continue to the next
candidate; locality alone does not make an inconsistent contract canonical.

The current intentional contract is document `2.5.0` (2026-10-30), production UI `0.4.0`. Read the selected usable file completely before UI work and read `docs/design-v3.md` for loader, scope and production-delivery details. The `v3` filename and asset directory are compatibility paths, not the UI version. Do not require the historical baseline menu count from a newer current contract.
Do not guess a user home directory or scan unrelated worktrees to resolve it.

For the immutable historical bundled baseline (retain its bytes and validation identity):

- version: `2.4.2`
- source date: `2026-08-25`
- SHA-256: `88b2f130f354b1232ffbcb4a48d0807bbb78ce81aaf74c8a41ddbc4f88f7e996`

The v0.4 contract covers 10 registered sites (Hub plus 9 projects), Pretendard and the existing three-bar Quant mark, default dark, native functionality, and the added project picker, favorites, density, collapsible rail and page outline. Changes are scoped to `body.qd-v04`; the original navigation entrypoint and `shared/design/v3/` remain. Production must not contain local-preview URL adapters, compare mode or `QuantPreview`. Display preferences use `quant-ui-v04-favorites`, `quant-ui-v04-density`, and `quant-ui-v04-rail`, independently per origin. Theme keeps `quant-research-theme`.

The bundled 2.4.2 file is an archived domain/audit reference, not a replacement for the current registry, default theme or v0.4 visual system. If only that baseline is available, explicitly record that current visual/navigation guidance is unavailable instead of claiming v0.4 compliance. Preserve its still-valid data, analysis, chart and table protections.

If a current canonical file has a newer declared version, use it after confirming it is intentional. If content changes without a version update, report the drift before broad rollout.

The design contract does not authorize changes to analysis, data, result schema, automation, chart semantics, or table columns.

For non-Quant projects, use the same procedure with the project's own design system. Treat this bundled document as a quality and audit pattern, not a mandatory visual identity.
