# PROJECTS_CANONICAL

Observed: 2026-07-02 14:33:30 KST

This is the current Git-operations map for the nine quant projects after the
approved fast-forward cleanup. It is documentation only. During this cleanup no
feature implementation, UI/UX work, data collection logic change, analysis
logic change, rebase, reset, force push, branch deletion, worktree deletion,
`git clean`, Risk Score mirror sync, or `.omx-worktrees` cleanup was performed.

Approved Git operations completed:

- `git fetch origin --no-tags` in the canonical worktrees.
- `git merge --ff-only origin/main` for fast-forward-only projects.
- `git branch --set-upstream-to=origin/main` for `port` and `risk-score`.

All nine canonical worktrees are now clean, non-detached, have `origin/main` as
upstream, and have `HEAD == origin/main`.

## Canonical Paths And Current State

Use these paths when opening Codex CLI/App sessions. Base paths under
`/Users/changgison/projects/<project>` are reference/archive paths unless this
document explicitly says otherwise.

| Project | Canonical path | Current branch | HEAD | Upstream | `HEAD` vs `origin/main` | Clean | Detached | Remote mismatch type | Source of truth | Recommended action | Implementation start |
|---|---|---:|---:|---|---|---|---|---|---|---|---|
| quant-dashboard | `/Users/changgison/projects/quant-dashboard.omx-worktrees/launch-feat-quant-dashboard` | `feat/quant-dashboard` | `6da06a9` | `origin/main` | ahead 0 / behind 0 | Yes | No | none | GitHub `SonChangGi/quant-dashboard` `origin/main`; launch worktree is aligned product path. | No Git cleanup required. Keep `/Users/changgison/projects/quant-dashboard` for Phase 0 docs only. | Yes |
| momentum-factor-lab | `/Users/changgison/projects/momentum-factor-lab.omx-worktrees/launch-research-momentum-factor-lab` | `main` | `7ed5b79` | `origin/main` | ahead 0 / behind 0 | Yes | No | none | GitHub `SonChangGi/momentum-factor-lab` `origin/main`. | Fast-forward cleanup complete. | Yes |
| dram-price | `/Users/changgison/projects/dram-price.omx-worktrees/launch-feat-dram-price` | `feat/dram-price` | `324ed7a` | `origin/main` | ahead 0 / behind 0 | Yes | No | none | GitHub `SonChangGi/dram-price` `origin/main`. | Fast-forward cleanup complete. | Yes |
| best-factor | `/Users/changgison/projects/best-factor.omx-worktrees/launch-feat-best-factor` | `main` | `e9241a8` | `origin/main` | ahead 0 / behind 0 | Yes | No | none | GitHub `SonChangGi/best-factor` `origin/main`. | Fast-forward cleanup complete. | Yes |
| etf-tracking | `/Users/changgison/projects/etf-tracking.omx-worktrees/launch-feat-etf-tracking` | `feat/etf-tracking` | `b0dd9d2` | `origin/main` | ahead 0 / behind 0 | Yes | No | none | GitHub `SonChangGi/etf-tracking` `origin/main`. | Fast-forward cleanup complete. | Yes |
| port | `/Users/changgison/projects/port.omx-worktrees/launch-feat-port` | `feat/port` | `01b8ecf` | `origin/main` | ahead 0 / behind 0 | Yes | No | none | GitHub `SonChangGi/port` `origin/main`. `origin/feat/port` remains a stale remote feature ref and is not the current upstream. | Fast-forward cleanup and upstream reset complete. Do not push to `origin/feat/port` unless a separate branch-retirement plan requires it. | Yes |
| valuation | `/Users/changgison/projects/valuation.omx-worktrees/launch-feat-valuation` | `feat/valuation` | `e7d6693` | `origin/main` | ahead 0 / behind 0 | Yes | No | none | GitHub `SonChangGi/valuation` `origin/main`. | Fast-forward cleanup complete. | Yes |
| risk-score | `/Users/changgison/projects/risk-score.omx-worktrees/launch-feat-risk-score` | `feat/risk-score` | `bf3339e` | `origin/main` | ahead 0 / behind 0 | Yes | No | none | Launch worktree is the Risk Score source of truth and matches GitHub `origin/main`; Quant Dashboard `risk-score/` paths are deploy mirrors. | Upstream setup complete. Continue running verifier before any deploy-mirror sync. | Yes |
| sox | `/Users/changgison/projects/sox.omx-worktrees/launch-feat-sox` | `feat/sox` | `db0bdf2` | `origin/main` | ahead 0 / behind 0 | Yes | No | none | GitHub `SonChangGi/sox` `origin/main`. | Fast-forward cleanup complete. | Yes |

## Cleanup Evidence

Read-only checks and approved cleanup commands used during this pass:

```bash
git fetch origin --no-tags
git status -sb
git log --left-right --oneline HEAD...origin/main
git rev-list --left-right --count HEAD...origin/main
git merge-base --is-ancestor HEAD origin/main
git merge --ff-only origin/main
git branch --set-upstream-to=origin/main feat/port
git branch --set-upstream-to=origin/main feat/risk-score
```

Fast-forward results:

- `momentum-factor-lab`: `504b3d9..7ed5b79`
- `dram-price`: `2ab8b24..324ed7a`
- `best-factor`: `1cfe83b..e9241a8`
- `etf-tracking`: `47edc70..b0dd9d2`
- `port`: `f5be282..01b8ecf`
- `valuation`: `d8130c7..e7d6693`
- `sox`: `63fffe7..db0bdf2`

Upstream-only cleanup:

- `risk-score`: `feat/risk-score` now tracks `origin/main`.
- `port`: `feat/port` now tracks `origin/main`.

## Stale Base Paths

The non-canonical paths remain preserved. Do not delete them, do not open
write-mode Codex sessions there for implementation, and do not use them as the
starting point for feature, UI, or data work.

| Project | Base path | Base state | Difference from canonical | Operating rule |
|---|---|---|---|---|
| quant-dashboard | `/Users/changgison/projects/quant-dashboard` | `codex/post-omx-cleanup` at `c3bc54a`, clean, upstream `origin/codex/post-omx-cleanup` | Docs/handoff branch, not product branch. Product path is `feat/quant-dashboard` at `6da06a9`. | Use for Phase 0 docs only until docs are merged or retired by plan. |
| momentum-factor-lab | `/Users/changgison/projects/momentum-factor-lab` | detached at `02bba8c`, clean | Older detached reference; canonical `main` is now `7ed5b79`. | Reference/archive only. |
| dram-price | `/Users/changgison/projects/dram-price` | detached at `a6be583`, clean | Older detached reference; canonical branch is now `324ed7a`. | Reference/archive only. |
| best-factor | `/Users/changgison/projects/best-factor` | detached at `c5704a2`, clean | Older detached reference; canonical `main` is now `e9241a8`. | Reference/archive only. |
| etf-tracking | `/Users/changgison/projects/etf-tracking` | detached at `8890772`, clean | Older detached reference; canonical branch is now `b0dd9d2`. | Reference/archive only. |
| port | `/Users/changgison/projects/port` | local `main` at `597e8b6`, clean, no upstream | Initial local main; canonical branch is now `01b8ecf`. | Reference/archive unless a separate plan makes it canonical. |
| valuation | `/Users/changgison/projects/valuation` | local `main` at `1e4daf1`, clean, no upstream | Initial local main; canonical branch is now `e7d6693`. | Reference/archive unless a separate plan makes it canonical. |
| risk-score | `/Users/changgison/projects/risk-score` | local `main` at `db30b1d`, clean, no upstream | Stale source path. It fails mirror verification against both Quant Dashboard targets; canonical source is `bf3339e`. | Reference/archive only until reconciled or replaced by a clean worktree. |
| sox | `/Users/changgison/projects/sox` | local `main` at `d89a986`, clean, no upstream | Initial local main; canonical branch is now `db0bdf2`. | Reference/archive only. |

Recommended mistake-prevention rule:

- Put implementation Codex CLI/App sessions only in the canonical paths listed above.
- Treat base paths as read-only reference/archive unless a new Git plan explicitly promotes one.
- Do not run data refreshes, sync commands, or UI edits in stale base paths.
- Do not delete or move any `*.omx-worktrees` path.

## Risk Score Policy

Current decision:

- Source of truth: `/Users/changgison/projects/risk-score.omx-worktrees/launch-feat-risk-score`
- Source branch/commit: `feat/risk-score` at `bf3339e`
- Upstream: `origin/main`
- Deploy mirrors:
  - `/Users/changgison/projects/quant-dashboard.omx-worktrees/launch-feat-quant-dashboard/risk-score`
  - `/Users/changgison/projects/quant-dashboard/risk-score`
- Non-source path: `/Users/changgison/projects/risk-score` is stale and fails mirror verification.

Before any future Risk Score sync, run the canonical verifier commands:

```bash
cd /Users/changgison/projects/risk-score.omx-worktrees/launch-feat-risk-score
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/verify_quant_dashboard_sync.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/verify_quant_dashboard_sync.py --target /Users/changgison/projects/quant-dashboard/risk-score
```

Only after an explicit sync plan should this mutation command be used:

```bash
python3 scripts/sync_to_quant_dashboard.py
```

That sync command removes and recopies deploy mirror files under the target
mirror. Treat it as a deploy-mirror update, not as a read-only check.

## Immediate Implementation Split

Implementation can now start from all nine canonical paths, subject to normal
per-project scope and verification:

- `quant-dashboard`
- `momentum-factor-lab`
- `dram-price`
- `best-factor`
- `etf-tracking`
- `port`
- `valuation`
- `risk-score`
- `sox`

For parallel Codex CLI/App work, use one session per canonical worktree. Do not
open write sessions in stale base paths for the same project.

## Global Forbidden Commands

Do not run these as part of routine Git operations:

```bash
git reset --hard
git rebase
git push --force
git branch -D
git worktree remove
git clean -fdx
rm -rf *.omx-worktrees
python3 scripts/sync_to_quant_dashboard.py
```

Also do not run branch deletion, worktree deletion, history rewrite, force push,
or deploy sync without a separate user-approved plan.
