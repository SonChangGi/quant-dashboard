# Context routing

Shared resources never activate a public skill. Enter this router only after
the current user selected the matching literal `$` skill, or the host supplied
trusted current-user, same-request selector metadata. Semantic, plain, quoted,
negated, prior-turn, Goal, artifact, or worker context is not activation.
`agents/openai.yaml` must keep `allow_implicit_invocation: false`.

## Ordinary path

Start from the selected public `SKILL.md`, the user's request, and the exact
target. Prefer target-native instructions, source, configuration, entrypoints,
fixtures, and checks.

When any listed capability trigger applies, or the work is otherwise
non-trivial, load `references/adaptive-workflow.md`. Its capability table is
the single ordinary-path router for analysis, external data, analysis-input
flow, UI and charts, backend boundaries, automation, publication, public
web, and remote release. Load only the rows that apply. A narrow task may skip
the kernel only when no capability rail could materially change its approach,
method, or proof.

Do not auto-load a manifest, schema, receipt, ledger, validator, durable
runtime, or the entire shared tree. Missing optional guidance does not block a
narrow public-skill workflow.

Resolve `<quant-shared-root>` from the active skill location, never the current
working directory:

- source: the `shared` directory beside source `skills`;
- installed: the `quant-research-shared` sibling of the installed public
  skills.

Do not search for another suite copy or silently switch roots.

## Role composition

When several public skills are explicitly selected in the same request, compose
only those roles: Quant Plan owns read-only planning, Quant Developer owns
authorized implementation, and Quant Goal owns lifecycle and overall
integration. A required plan-approval pause ends the request before mutation.
Composition never expands authority.

## Legacy compatibility path

Use structured resources only when an existing project depends on the exact
contract, or the user explicitly requests machine-audited output or
contract-specific high-risk recovery. Complexity, duration, release delivery,
failure, or a `strict` label alone does not select this path.

When selected, preserve existing schema and version semantics:

- manifest v1 uses its v1 validators and evidence receipt v2;
- manifest v2 uses declared capabilities, profiles, adapters, and receipt v3;
- existing Goal ledger, Story, team, and receipt objects keep their current
  identifiers, hashes, transitions, and validators.

Legacy resources may add proof requirements for that compatibility task, but
must not gate ordinary planning, native Goal progress, implementation, or
completion. Do not create, migrate, or repair legacy state merely because the
files are available.

The installed `base` profile intentionally omits the compatibility payload. If
an explicitly selected compatibility contract is absent, report that path as
unavailable; do not install or reconstruct it implicitly. The source installer
can add the preserved payload at the same relative paths only through its
explicit `--include-legacy` profile.

Before loading a compatibility child in an installed suite, verify that
`<quant-shared-root>/install-manifest.json` reports `install_profile: compat`
and that the exact child exists. In source, verify the exact child directly.
This includes `references/data-automation.md`,
`capabilities/analysis-input-binding.md`, and the strict analysis-input
schemas, templates, and validators. A `base` profile or missing child makes
only that compatibility path unavailable; do not search for another suite copy
or weaken the ordinary capability rails.
