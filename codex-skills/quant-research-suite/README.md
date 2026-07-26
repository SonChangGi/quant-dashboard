# Quant Research Codex Skill Suite

This source package installs three project-oriented Codex skills:

- `quant-plan`
- `quant-goal`
- `quant-developer`

They share contract, data-automation, release, and zero-spend safeguards from
`shared/`. Auto-renewing or free-to-paid trials, payment method registration,
plan upgrades, paid overage or pay-as-you-go use, exceeding a verified free
quota, paid add-ons, and Spend cap disablement are paid actions and are
prohibited unless a direct prior user request names the exact bounded paid
action; free-plan cost hard stops must remain enabled.

## Validate

```bash
python3 validate_suite.py
python3 -m unittest discover -s tests -v
python3 install.py --update --dry-run
```

## Install or update locally

```bash
python3 install.py --update
```

The installer validates the source, runs the tests, stages a complete copy,
backs up the previous local installation, replaces all three skills and shared
resources together, and verifies installed hashes.

By default, the installer writes `quant-plan`, `quant-goal`,
`quant-developer`, and `quant-research-shared` under `~/.codex/skills/`.
Codex discovers the three skill directories from that local skills root; the
shared directory supplies their references and validators but is not itself a
discoverable skill. Use `--target` only when the active Codex installation has
an explicitly configured alternative skills root.

Source control and local discovery are separate. Committing or pushing this
directory only versions and transports the source package; it neither installs
nor activates the skills and does not require web or cloud deployment. Run
`python3 install.py --update` in the checked-out source package to validate and
activate that exact revision on the current local Codex installation.

For a release-grade local update after committing the suite, require a clean,
traceable Git source and verify the installed manifest:

```bash
python3 install.py --update --require-clean-source
python3 ~/.codex/skills/quant-research-shared/scripts/validate_installed.py
```

The install affects only this Codex installation. Another machine or Codex
skills root must install separately, and an already-open session may need to be
reloaded before newly installed skill metadata appears.
