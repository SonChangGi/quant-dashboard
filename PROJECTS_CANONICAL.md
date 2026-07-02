# PROJECTS_CANONICAL

Observed: 2026-07-02 13:19:41 KST

This is the Phase 0 operations map for the nine quant projects. It is documentation only: no feature implementation, UI/UX work, data collection changes, source rewrites, history rewrites, worktree deletion, or `.omx-worktrees` cleanup was performed.

Remote state was checked with `git ls-remote` instead of `git fetch`, so local remote-tracking refs were not mutated during this audit. Where `origin/main` below says "remote mismatch", it means the current GitHub remote head observed by `ls-remote` does not match the local `origin/main` object currently available in that repo.

## Canonical Working Paths

Use these paths when opening Codex CLI/App after Phase 0. The non-canonical base paths remain preserved as reference/archive paths and must not be deleted.

| Project | Canonical Codex working path | Branch at audit | Local upstream | Clean | Source-of-truth decision | Current risk |
|---|---|---:|---|---|---|---|
| quant-dashboard | `/Users/changgison/projects/quant-dashboard.omx-worktrees/launch-feat-quant-dashboard` | `feat/quant-dashboard` at `6da06a9660df` | `origin/main` | Yes | Product source is `SonChangGi/quant-dashboard` `origin/main`; `/Users/changgison/projects/quant-dashboard` is the Phase 0 docs/handoff branch. | Low for product path; keep docs branch separate. |
| momentum-factor-lab | `/Users/changgison/projects/momentum-factor-lab.omx-worktrees/launch-research-momentum-factor-lab` | `main` at `504b3d9f5cfd` | `origin/main` | Yes | Separate repo source; intended publication source is GitHub `origin/main`. | High until remote `main` mismatch is reconciled. |
| dram-price | `/Users/changgison/projects/dram-price.omx-worktrees/launch-feat-dram-price` | `feat/dram-price` at `2ab8b242af3e` | `origin/main` | Yes | Separate repo source; active branch currently equals GitHub `origin/main`. | Low; base path is detached reference only. |
| best-factor | `/Users/changgison/projects/best-factor.omx-worktrees/launch-feat-best-factor` | `main` at `1cfe83b92bfa` | `origin/main` | Yes | Separate repo source; intended publication source is GitHub `origin/main`. | High until remote `main` mismatch is reconciled. |
| etf-tracking | `/Users/changgison/projects/etf-tracking.omx-worktrees/launch-feat-etf-tracking` | `feat/etf-tracking` at `47edc70b7dd9` | `origin/main` | Yes | Separate repo source; intended publication source is GitHub `origin/main`. | High until remote `main` mismatch is reconciled. |
| port | `/Users/changgison/projects/port.omx-worktrees/launch-feat-port` | `feat/port` at `f5be28278bb2` | `origin/feat/port` | Yes | Separate repo source; active local source is `feat/port` pending remote-main reconciliation. | High: branch is ahead of local `origin/feat/port`, and current remote `main` differs. |
| valuation | `/Users/changgison/projects/valuation.omx-worktrees/launch-feat-valuation` | `feat/valuation` at `d8130c78ac3e` | `origin/main` | Yes | Separate repo source; intended publication source is GitHub `origin/main`. | High until remote `main` mismatch is reconciled. |
| risk-score | `/Users/changgison/projects/risk-score.omx-worktrees/launch-feat-risk-score` | `feat/risk-score` at `bf3339e116c8` | none configured | Yes | This launch worktree is the Risk Score source of truth and matches current GitHub `origin/main`; Quant Dashboard `risk-score/` is a deploy mirror. | Medium: upstream is not configured, and the base `risk-score` path is stale. |
| sox | `/Users/changgison/projects/sox.omx-worktrees/launch-feat-sox` | `feat/sox` at `63fffe737a91` | `origin/main` | Yes | Separate repo source; intended publication source is GitHub `origin/main`. | High until remote `main` mismatch is reconciled. |

## Branch, Status, And Remote Evidence

| Project | Base path state | Canonical path state | Current GitHub `HEAD` / `main` observed by `ls-remote` | Local remote-ref note |
|---|---|---|---|---|
| quant-dashboard | `/Users/changgison/projects/quant-dashboard`: `codex/post-omx-cleanup` at `21de5ab2c868`, clean, upstream `origin/codex/post-omx-cleanup` | `feat/quant-dashboard` at `6da06a9660df`, clean, upstream `origin/main` | `origin/main` = `6da06a9660df` | Aligned for product worktree. |
| momentum-factor-lab | Detached at `02bba8cf394d`, clean | `main` at `504b3d9f5cfd`, clean, upstream `origin/main` | `origin/main` = `7ed5b79387b3` | Current remote object is not present locally; fetch/reconcile required. |
| dram-price | Detached at `a6be583c92de`, clean | `feat/dram-price` at `2ab8b242af3e`, clean, upstream `origin/main` | `origin/main` = `2ab8b242af3e` | Aligned. |
| best-factor | Detached at `c5704a2230e4`, clean | `main` at `1cfe83b92bfa`, clean, upstream `origin/main` | `origin/main` = `e9241a8a7f0c` | Current remote object is not present locally; fetch/reconcile required. |
| etf-tracking | Detached at `889077274227`, clean | `feat/etf-tracking` at `47edc70b7dd9`, clean, upstream `origin/main` | `origin/main` = `30c35409abaf` | Current remote object is not present locally; fetch/reconcile required. |
| port | `main` at `597e8b65b782`, clean, no upstream | `feat/port` at `f5be28278bb2`, clean, upstream `origin/feat/port`; local status reported ahead 5 | `origin/main` = `01b8ecfc639c`; `origin/feat/port` = `60bf4f4d06b0` | Active branch is not safely publishable until branch policy is decided. |
| valuation | `main` at `1e4daf1d2a88`, clean, no upstream | `feat/valuation` at `d8130c78ac3e`, clean, upstream `origin/main` | `origin/main` = `e7d6693bfd5e` | Current remote object is not present locally; fetch/reconcile required. |
| risk-score | `main` at `db30b1dbe35f`, clean, no upstream | `feat/risk-score` at `bf3339e116c8`, clean, no upstream | `origin/main` = `bf3339e116c8` | Canonical worktree matches remote main, but upstream should be set only after an explicit Git plan. |
| sox | `main` at `d89a98628019`, clean, no upstream | `feat/sox` at `63fffe737a91`, clean, upstream `origin/main` | `origin/main` = `db0bdf21deb5` | Current remote object is not present locally; fetch/reconcile required. |

## Detached HEAD And Worktree Risk

| Project | Detached or stale path | Risk | Operating rule |
|---|---|---|---|
| momentum-factor-lab | `/Users/changgison/projects/momentum-factor-lab` detached at `02bba8cf394d` | High accidental-edit risk. | Reference/archive only; do not start Codex implementation here. |
| dram-price | `/Users/changgison/projects/dram-price` detached at `a6be583c92de` | High accidental-edit risk. | Reference/archive only. |
| best-factor | `/Users/changgison/projects/best-factor` detached at `c5704a2230e4` | High accidental-edit risk. | Reference/archive only. |
| etf-tracking | `/Users/changgison/projects/etf-tracking` detached at `889077274227` | High accidental-edit risk. | Reference/archive only. |
| risk-score | `/Users/changgison/projects/risk-score` on `main` at `db30b1dbe35f`, no upstream | Stale source risk; causes sync verifier failure against current deploy mirror. | Reference/archive until reconciled with `feat/risk-score` or current GitHub `main`. |
| port | `/Users/changgison/projects/port` on local `main` at `597e8b65b782`, no upstream | Stale branch and no upstream. | Reference/archive unless a separate plan makes it canonical. |
| valuation | `/Users/changgison/projects/valuation` on local `main` at `1e4daf1d2a88`, no upstream | Stale branch and no upstream. | Reference/archive unless a separate plan makes it canonical. |
| sox | `/Users/changgison/projects/sox` on local `main` at `d89a98628019`, no upstream | Initial commit path, not current product state. | Reference/archive only. |
| quant-dashboard | `/Users/changgison/projects/quant-dashboard` on `codex/post-omx-cleanup` | Useful for Phase 0 docs, not product UI/data work. | Use for handoff docs only until the docs branch is merged or retired. |

## Source-Of-Truth Decisions

| Project | Source of truth | Deploy/public route | Notes |
|---|---|---|---|
| quant-dashboard | GitHub `SonChangGi/quant-dashboard` `origin/main`; current product worktree is `launch-feat-quant-dashboard`. | `https://sonchanggi.github.io/quant-dashboard/` | Central hub reads public JSON from sibling Pages projects. It should not import sibling local source paths. |
| momentum-factor-lab | Separate repo `SonChangGi/momentum-factor-lab`, intended `origin/main` after reconciliation. | `https://sonchanggi.github.io/momentum-factor-lab/` | README documents `docs/` dashboard and workflow deployment. |
| dram-price | Separate repo `SonChangGi/dram-price`, current active commit equals GitHub `origin/main`. | `https://sonchanggi.github.io/dram-price/` | Active branch name is `feat/dram-price` but its upstream/source is `origin/main`. |
| best-factor | Separate repo `SonChangGi/best-factor`, intended `origin/main` after reconciliation. | `https://sonchanggi.github.io/best-factor/` | README explicitly says to deploy only this isolated repo. |
| etf-tracking | Separate repo `SonChangGi/etf-tracking`, intended `origin/main` after reconciliation. | `https://sonchanggi.github.io/etf-tracking/` | README says Pages serves the `main` branch root. |
| port | Separate repo `SonChangGi/port`; active local source is `feat/port` until remote policy is resolved. | `https://sonchanggi.github.io/port/` | Do not merge, push, or deploy until local `feat/port`, `origin/feat/port`, and remote `main` are compared. |
| valuation | Separate repo `SonChangGi/valuation`, intended `origin/main` after reconciliation. | `https://sonchanggi.github.io/valuation/` | README says it is independent and does not modify other repos. |
| risk-score | `risk-score.omx-worktrees/launch-feat-risk-score` at `bf3339e116c8`; this matches current GitHub `origin/main`. | `https://sonchanggi.github.io/quant-dashboard/risk-score/` | Quant Dashboard subtree is a deploy mirror only, not the source. |
| sox | Separate repo `SonChangGi/sox`, intended `origin/main` after reconciliation. | `https://sonchanggi.github.io/sox/` | README confirms SOX Pages/public summary route. |

## Risk-Score Drift Summary

The sync verifier was run read-only from both the base and launch Risk Score worktrees.

Failing case:

- Source: `/Users/changgison/projects/risk-score` (`main` at `db30b1dbe35f`)
- Targets checked:
  - `/Users/changgison/projects/quant-dashboard.omx-worktrees/launch-feat-quant-dashboard/risk-score`
  - `/Users/changgison/projects/quant-dashboard/risk-score`
- Problems in both targets:
  - `index.html` differs.
  - Target has extra `assets/common-ui.css`.
  - Target has extra `assets/common-ui.js`.
  - `data/` passes.

Passing case:

- Source: `/Users/changgison/projects/risk-score.omx-worktrees/launch-feat-risk-score` (`feat/risk-score` at `bf3339e116c8`)
- Same two Quant Dashboard targets both pass:
  - `index.html` matches.
  - `assets/` matches.
  - `data/` matches.

Conclusion:

- The drift is not a Quant Dashboard deploy-subtree problem when the canonical Risk Score source is used.
- The stale path is `/Users/changgison/projects/risk-score`, not the Quant Dashboard subtree.
- Source of truth is the Risk Score launch worktree matching current GitHub `origin/main`.
- No immediate file sync is required before implementation if future work opens the canonical launch worktree.
- If the base `risk-score` path must become usable again, use a separate Git plan to reconcile it with `bf3339e116c8` or create a new clean worktree. Do not hand-edit the Quant Dashboard subtree to fix this.

Safe verification commands:

```bash
cd /Users/changgison/projects/risk-score.omx-worktrees/launch-feat-risk-score
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/verify_quant_dashboard_sync.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/verify_quant_dashboard_sync.py --target /Users/changgison/projects/quant-dashboard/risk-score
```

Mutation command, only after an explicit plan:

```bash
python3 scripts/sync_to_quant_dashboard.py
```

That sync command removes and recopies `index.html`, `assets/`, and `data/` under the target mirror, so treat it as a deploy-mirror update, not as a read-only check.

## Recommended Codex CLI/App Structure

Use one Codex session per canonical worktree. Do not open one write session in a base/reference path while another session writes the canonical path for the same repo.

| Work type | Recommended path | Parallel-safe with | Do not combine with |
|---|---|---|---|
| Phase 0 docs and handoff | `/Users/changgison/projects/quant-dashboard` | Read-only audits of other repos | Product UI/data edits in this same root branch. |
| Quant Dashboard App UI/UX after Phase 0 | `/Users/changgison/projects/quant-dashboard.omx-worktrees/launch-feat-quant-dashboard` | Separate repo data work in other canonical paths | Direct edits to `/Users/changgison/projects/quant-dashboard/risk-score` while Risk Score source work is active. |
| Momentum data/research/dashboard | `/Users/changgison/projects/momentum-factor-lab.omx-worktrees/launch-research-momentum-factor-lab` | Other projects in their own canonical paths | Detached base path. |
| DRAM data/dashboard | `/Users/changgison/projects/dram-price.omx-worktrees/launch-feat-dram-price` | Other projects in their own canonical paths | Detached base path. |
| Best Factor data/research/dashboard | `/Users/changgison/projects/best-factor.omx-worktrees/launch-feat-best-factor` | Other projects in their own canonical paths | Detached base path. |
| ETF Tracking data/dashboard | `/Users/changgison/projects/etf-tracking.omx-worktrees/launch-feat-etf-tracking` | Other projects in their own canonical paths | Detached base path. |
| Port data/UI tool | `/Users/changgison/projects/port.omx-worktrees/launch-feat-port` | Other projects after branch reconciliation | Base `port/main` or remote push/deploy work without a branch plan. |
| Valuation data/UI tool | `/Users/changgison/projects/valuation.omx-worktrees/launch-feat-valuation` | Other projects after branch reconciliation | Base `valuation/main`. |
| Risk Score model/data/page source | `/Users/changgison/projects/risk-score.omx-worktrees/launch-feat-risk-score` | Quant Dashboard read-only verification | Direct manual edits to Quant Dashboard `risk-score/` mirror. |
| SOX data/dashboard | `/Users/changgison/projects/sox.omx-worktrees/launch-feat-sox` | Other projects after branch reconciliation | Base `sox/main`. |

Shared-file caution:

- `quant-dashboard/risk-score/index.html`, `quant-dashboard/risk-score/assets/**`, and `quant-dashboard/risk-score/data/**` are deploy mirrors from Risk Score. Do not edit them directly.
- `assets/common-ui.css`, `assets/common-ui.js`, `assets/styles.css`, `assets/app.js`, and `index.html` appear across several projects but are copied per repo, not a shared package. Do not make cross-project UI edits in parallel unless each repo has a separate explicit scope and verification pass.
- `data/**`, `docs/data/**`, generated JSON, and refresh outputs are project-local source artifacts. Do not run data refreshes in two terminals for the same repo.
- `.github/workflows/**`, `README.md`, `DESIGN.md`, `package.json`, `pyproject.toml`, and sync scripts are operational contracts. Treat cross-repo edits to these as separate planned changes.

## Must Resolve Before Implementation

Resolve these before feature, UI/UX, or data-logic work starts:

| Item | Why it blocks implementation | Safe next step |
|---|---|---|
| Remote `main` mismatch for momentum-factor-lab, best-factor, etf-tracking, port, valuation, and sox | Local `origin/main` refs are stale or inconsistent with current GitHub `main`; implementation could be based on the wrong history. | Present a Git reconciliation plan, then run a non-destructive fetch/compare sequence before any merge, rebase, reset, or push. |
| `port` branch policy | Canonical branch `feat/port` is ahead of local `origin/feat/port`, while remote `main` is a different unseen commit. | Compare `feat/port`, remote `feat/port`, and remote `main`; decide whether to push, merge, or create a new clean branch. |
| `risk-score` base path staleness | Base path fails sync verification; opening it for work would recreate drift. | Keep using the launch worktree, or explicitly reconcile/create a clean worktree. |
| `risk-score` upstream missing | Canonical branch matches current remote `main` but has no upstream configured. | Only after a Git plan, set the correct upstream or create a clean worktree from `origin/main`. |
| Quant Dashboard docs branch | `/Users/changgison/projects/quant-dashboard` is an operations-doc branch, while product work lives in the launch worktree. | Decide whether to merge/copy docs into product main or keep this branch as handoff-only. |

Work that is safe to start immediately:

| Work | Safe scope |
|---|---|
| Read-only audits | Any project path, including base/reference paths. |
| Phase 0 documentation | `/Users/changgison/projects/quant-dashboard` only. |
| Risk Score sync verification | From `risk-score.omx-worktrees/launch-feat-risk-score`, using verifier commands only. |
| Planning a Git reconciliation | Read-only commands such as `git status`, `git branch -vv`, `git log`, `git worktree list`, and `git ls-remote`. |

Do not start feature implementation, UI/UX changes, or data collection/analysis changes until the blocking reconciliation items above are resolved or explicitly scoped out by the user.
