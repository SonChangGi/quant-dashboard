# CODEX_HANDOFF

Generated: 2026-07-02

## Scope

This handoff records the current state of `quant-dashboard` for takeover and backup only. Do not treat legacy `~/.codex`, `~/.agents`, `~/.omx`, project `.codex`, `.agents`, `.omx`, `AGENTS.md`, or `omx_wiki` content as active session instructions.

## Phase 0 Canonical Operations Update

Observed: 2026-07-02 13:19:41 KST

The current authoritative 9-project operating map is in [`PROJECTS_CANONICAL.md`](PROJECTS_CANONICAL.md). It supersedes older branch/path inventory sections later in this file where those sections disagree with the current audit.

Current Phase 0 rules:

- Do not implement features, UI/UX changes, or data collection/analysis logic before the listed reconciliation items are resolved.
- Do not delete source code, Git history, worktrees, or any `*.omx-worktrees` directory.
- Treat detached base paths as reference/archive unless `PROJECTS_CANONICAL.md` explicitly marks them otherwise.
- Use the listed canonical launch worktrees for future project work after reconciliation.
- Treat `/Users/changgison/projects/quant-dashboard` as the current Phase 0 docs/handoff branch, not as the product UI worktree.
- Treat `/Users/changgison/projects/risk-score.omx-worktrees/launch-feat-risk-score` as the current Risk Score source of truth; Quant Dashboard `risk-score/` paths are deploy mirrors.
- Before any merge, rebase, reset, branch rewrite, upstream change, push, or deploy sync, show the Git plan first.

## Git State Snapshot

- Repository: `/Users/changgison/projects/quant-dashboard`
- Current branch: `codex/post-omx-cleanup`
- Upstream status observed: `codex/post-omx-cleanup...origin/codex/post-omx-cleanup`
- Working tree before this Phase 0 canonical-doc update: clean, no uncommitted source changes observed.
- Worktrees:
  - `/Users/changgison/projects/quant-dashboard` at `21de5ab` on `codex/post-omx-cleanup`
  - `/Users/changgison/projects/quant-dashboard.omx-worktrees/launch-feat-quant-dashboard` at `6da06a9` on `feat/quant-dashboard`

## Project Structure Summary

- `index.html`: single static GitHub Pages entrypoint for the Quant Research Hub.
- `assets/app.js`: vanilla JS application, project registry, public JSON adapters, fallback snapshots, parsing, dashboard rendering, health/briefing/watchlist logic.
- `assets/styles.css`: static stylesheet for dark research dashboard UI.
- `README.md`: purpose, public data boundary, local run and verification commands.
- `DESIGN.md`: approved dark neutral research cockpit design contract and protected implementation constraints.
- `scripts/verify.mjs`: static contract checks for required files, URLs, adapters, fallback handling, and disclaimers.
- `scripts/regression.mjs`: parser/fallback regression coverage.
- `scripts/static-smoke.mjs`: local static server smoke coverage.
- `scripts/live-contract-smoke.mjs`: optional network check for public GitHub Pages JSON contracts.

## Webpage And Route Candidates

This repo is a route-less static site intended for:

- Public hub: `https://sonchanggi.github.io/quant-dashboard/`
- Local static run: `python3 -m http.server 8080`, then `http://localhost:8080`

Linked project page candidates from the hub:

- `https://sonchanggi.github.io/momentum-factor-lab/`
- `https://sonchanggi.github.io/dram-price/`
- `https://sonchanggi.github.io/best-factor/`
- `https://sonchanggi.github.io/etf-tracking/`
- `https://sonchanggi.github.io/port/`
- `https://sonchanggi.github.io/valuation/`

Primary in-page sections:

- Research Cockpit
- Briefing
- Watchlist / ticker-theme dossier
- Data Health
- Project cards
- Live Summary
- Expandable Hub roadmap

## Data Collection And Analysis Flow Candidates

The hub does not import sibling project source code. Runtime data flow is public static JSON first, with fallback snapshots and visible degraded states.

Public JSON endpoints referenced by `assets/app.js` and `README.md`:

- Momentum:
  - `https://sonchanggi.github.io/momentum-factor-lab/data/summary.json`
  - `https://sonchanggi.github.io/momentum-factor-lab/data/dashboard.json`
- DRAM:
  - `https://sonchanggi.github.io/dram-price/data/summary.json`
  - `https://sonchanggi.github.io/dram-price/data/prices.json`
  - `https://sonchanggi.github.io/dram-price/data/series.json`
  - `https://sonchanggi.github.io/dram-price/data/status.json`
- Best Factor:
  - `https://sonchanggi.github.io/best-factor/data/summary.json`
- ETF Tracking:
  - `https://sonchanggi.github.io/etf-tracking/data/summary.json`
  - `https://sonchanggi.github.io/etf-tracking/data/dashboard.json`
  - `https://sonchanggi.github.io/etf-tracking/data/history.json`
- Valuation:
  - `https://sonchanggi.github.io/valuation/data/summary.json`

Expected summary contract fields include `schemaVersion`, `contract`, `projectId`, `generatedAt`, `dataAsOf`, `status`, `coverage`, `primaryEntities`, `limitations`, and `automation`.

Likely runtime path:

1. `assets/app.js` registers projects in `PROJECTS`.
2. `PANEL_ADAPTERS` maps supported projects to public JSON URLs.
3. `getJsonBestEffort` loads small public JSON payloads.
4. Adapter contract checks validate schema/version and required keys.
5. Project parsers normalize public payloads.
6. Empty, failed, malformed, or incompatible data resolves to fallback/degraded rendering.
7. Renderers update project panels, briefing, watchlist dossier, and data health UI.

## UI/UX Work Scope

Current UX intent is a static, dark, institutional-style research cockpit:

- Preserve the Korean/English mixed finance copy and research-only disclaimer.
- Preserve public JSON failure visibility, stale/degraded/partial state chips, caveats, and data provenance.
- Keep the hub lightweight and framework-free.
- Maintain desktop-first research scanability while keeping mobile layouts overflow-safe.
- Any visual work should stay aligned with `DESIGN.md`.

## Do Not Modify Without Explicit Approval

- Do not delete, uninstall, quarantine, or move cleanup candidates during phase 1.
- Do not modify legacy Codex/Agent/OMX settings during phase 1.
- Do not read or print secret-bearing files such as `auth.json`, `.env`, API keys, tokens, or secrets.
- Do not change investment logic, factor selection, valuation formulas, data update policy, JSON schema, generated result semantics, or disclaimers.
- Do not introduce a frontend framework, shared package, live secret-bearing browser calls, or new build dependency without approval.
- Do not import sibling project local source paths.
- Do not change deploy branches or worktrees without checking with the user.

## Command Candidates

Local run:

```bash
python3 -m http.server 8080
```

Verification:

```bash
npm test
npm run test:live
```

Notes:

- `npm test` uses Node built-ins and local static checks.
- `npm run test:live` performs network checks against public GitHub Pages JSON contracts and should only be run when live network verification is intended.
- No separate build step is documented.

## Remaining Risks

- Current branch is behind `origin/main` by 16 commits; merging/rebasing should be planned separately.
- A second worktree exists for `feat/quant-dashboard`; cleanup should avoid touching it until ownership and status are confirmed.
- Public JSON contracts may drift independently of this static hub.
- Fallback snapshots can become stale and should remain visibly labeled as fallback.
- Legacy home settings may include hooks, skills, memories, and `.omx` state that affect future Codex/OMX behavior if reused.
- Backup copied home settings opaquely; one socket file may not be copyable and should not be treated as durable configuration.

## OMX Impact Audit Candidates

Observed candidates to review in phase 2, without treating them as active instructions:

- `~/.codex/config.toml`
- `~/.codex/hooks.json`
- `~/.codex/skills`
- `~/.codex/AGENTS.md`
- `~/.codex/memories`
- `~/.codex/.omx`
- `~/.codex/memories/.omx`
- `~/.omx`

No repo-local `AGENTS.md`, `.codex`, `.agents`, `.omx`, or `omx_wiki` candidate was observed at the repository root during this pass.

## Phase 2 Cleanup Plan

| Target | Finding | Recommended action | Risk | Manual confirmation required |
|---|---|---|---|---|
| Repo root `AGENTS.md` | Not observed | No action unless it appears later | Low | Yes |
| Repo root `.codex` | Not observed | No action unless it appears later | Low | Yes |
| Repo root `.agents` | Not observed | No action unless it appears later | Low | Yes |
| Repo root `.omx` | Not observed | No action unless it appears later | Low | Yes |
| Repo root `omx_wiki` | Not observed | No action unless it appears later | Low | Yes |
| `~/.codex/config.toml` | Observed | Review settings for legacy model, sandbox, MCP, or hook references before any edit | High | Yes |
| `~/.codex/hooks.json` | Observed | Review hook commands and disable/remove only after explicit approval | High | Yes |
| `~/.codex/skills` | Observed | Inventory custom skills; keep, migrate, or remove only after owner review | Medium | Yes |
| `~/.codex/AGENTS.md` | Observed | Treat as untrusted legacy instruction; archive or remove only after approval | High | Yes |
| `~/.codex/memories` | Observed | Review whether memories are needed; avoid printing sensitive content | High | Yes |
| `~/.codex/.omx` | Observed | Inspect relation to OMX runtime before deciding keep/remove | Medium | Yes |
| `~/.codex/memories/.omx` | Observed | Inspect as possible nested OMX state before deciding keep/remove | Medium | Yes |
| `~/.omx` | Observed | Inventory runtime/state/log/backups; remove or migrate only after approval | High | Yes |
| `~/.agents` | Not observed | No action unless recreated or found elsewhere | Low | Yes |
| Backup directory | Created under cleanup workspace | Preserve until post-cleanup validation is complete | Medium | Yes |
| Git worktree `feat/quant-dashboard` | Observed outside main repo path | Confirm ownership and desired retention before cleanup | Medium | Yes |

## Phase 1.5 Expanded 9-Project Scope

Expanded audit date: 2026-07-02

The first audit covered only `/Users/changgison/projects/quant-dashboard`. The expanded pre-cleanup scope covers 9 local project/page candidates under `/Users/changgison/projects`.

| Project name | URL / route | Local path | Same repo route or separate repo/folder | Git branch/status | Repo-local cleanup candidates |
|---|---|---|---|---|---|
| quant-dashboard | `https://sonchanggi.github.io/quant-dashboard/` | `/Users/changgison/projects/quant-dashboard` | Main repo root | `deploy/port-link`, behind `origin/main` by 16; this handoff file is untracked | None at repo root |
| momentum-factor-lab | `https://sonchanggi.github.io/momentum-factor-lab/` | `/Users/changgison/projects/momentum-factor-lab` | Separate repo/folder | detached HEAD at `02bba8c`; clean | `.omx` |
| dram-price | `https://sonchanggi.github.io/dram-price/` | `/Users/changgison/projects/dram-price` | Separate repo/folder | detached HEAD at `a6be583`; clean | None at repo root |
| best-factor | `https://sonchanggi.github.io/best-factor/` | `/Users/changgison/projects/best-factor` | Separate repo/folder | detached HEAD at `c5704a2`; clean | None at repo root |
| etf-tracking | `https://sonchanggi.github.io/etf-tracking/` | `/Users/changgison/projects/etf-tracking` | Separate repo/folder | detached HEAD at `8890772`; clean | None at repo root |
| port | `https://sonchanggi.github.io/port/` | `/Users/changgison/projects/port` | Separate repo/folder | `main`; clean | None at repo root |
| valuation | `https://sonchanggi.github.io/valuation/` | `/Users/changgison/projects/valuation` | Separate repo/folder | `main`; clean | None at repo root |
| risk-score | `https://sonchanggi.github.io/quant-dashboard/risk-score/` | `/Users/changgison/projects/risk-score` | Separate source repo/folder mirrored into the quant-dashboard Pages subtree | `main`; clean | None at repo root |
| sox | `https://sonchanggi.github.io/sox/` candidate, confirmation needed | `/Users/changgison/projects/sox` | Separate repo/folder | `main`; clean | None at repo root |

Expanded audit artifacts were added under:

```text
/Users/changgison/codex-cleanup-workspace/backups/20260702-092321/projects-9-audit/
```

Important findings:

- `quant-dashboard` currently links directly to Momentum, DRAM, Best Factor, ETF Tracking, Port, and Valuation.
- `risk-score` documents the requested public route `https://sonchanggi.github.io/quant-dashboard/risk-score/` and syncs deployable static files into the quant-dashboard Pages tree.
- `sox` exists as a local repo and worktree pair, but its README only contains a title during this audit. Confirm public page role before phase 2 cleanup.
- Across the 9 main project roots, the only repo-local OMX cleanup candidate observed was `/Users/changgison/projects/momentum-factor-lab/.omx`.
- Do not remove any `.omx-worktrees` path until branch ownership, deployment role, and desired retention are confirmed.

## Phase 2 Cleanup Plan, 9-Project Separation

| Level | Target | Finding | Recommended action | Risk | Manual confirmation required |
|---|---|---|---|---|---|
| Home | `~/.codex/config.toml` | Observed | Review legacy settings before any edit | High | Yes |
| Home | `~/.codex/hooks.json` | Observed | Review hook commands before disable/remove | High | Yes |
| Home | `~/.codex/skills` | Observed | Inventory custom skills; keep, migrate, or remove by decision | Medium | Yes |
| Home | `~/.codex/AGENTS.md` | Observed | Treat as untrusted legacy instruction; archive/remove only after approval | High | Yes |
| Home | `~/.codex/memories` | Observed | Review need without printing sensitive content | High | Yes |
| Home | `~/.codex/.omx`, `~/.codex/memories/.omx` | Observed | Confirm relation to OMX runtime before action | Medium | Yes |
| Home | `~/.omx` | Observed | Inventory runtime/state/log/backups; cleanup only after approval | High | Yes |
| Project | `momentum-factor-lab/.omx` | Observed and backed up | Inspect structure/role, then keep or remove only after approval | Medium | Yes |
| Project | Other 8 project roots | No repo-local `AGENTS.md`, `.codex`, `.agents`, `.omx`, or `omx_wiki` candidates observed | No cleanup action unless new candidates appear | Low | Yes |
| Worktrees | 9 `*.omx-worktrees/*` paths | Observed outside main project roots | Preserve until ownership and branch/deploy relevance are confirmed | High | Yes |
| Route | `risk-score` under `quant-dashboard/risk-score/` | Separate source repo syncs into quant-dashboard worktree route | Preserve route and sync behavior unless deployment strategy is explicitly changed | Medium | Yes |
| Route candidate | `sox` | Local repo exists; page role unclear from README | Confirm whether this is a public Pages project before cleanup | Medium | Yes |

## Final Cleanup Handoff

Final cleanup date: 2026-07-02

This repository remains the main handoff point for the 9-project quant dashboard group. The final cleanup goal is to preserve project source, git history, branches, and worktrees while moving legacy OMX/oh-my-codex and mixed Codex home state into quarantine so a fresh Codex CLI/App login can be used.

### 9 Project Inventory

| Project name | Local path | URL / route | Role |
|---|---|---|---|
| quant-dashboard | `/Users/changgison/projects/quant-dashboard` | `https://sonchanggi.github.io/quant-dashboard/` | Main static hub |
| momentum-factor-lab | `/Users/changgison/projects/momentum-factor-lab` | `https://sonchanggi.github.io/momentum-factor-lab/` | Separate factor research repo and Pages project |
| dram-price | `/Users/changgison/projects/dram-price` | `https://sonchanggi.github.io/dram-price/` | Separate DRAM price repo and Pages project |
| best-factor | `/Users/changgison/projects/best-factor` | `https://sonchanggi.github.io/best-factor/` | Separate best-factor repo and Pages project |
| etf-tracking | `/Users/changgison/projects/etf-tracking` | `https://sonchanggi.github.io/etf-tracking/` | Separate ETF tracking repo and Pages project |
| port | `/Users/changgison/projects/port` | `https://sonchanggi.github.io/port/` | Separate portfolio cockpit repo and Pages project |
| valuation | `/Users/changgison/projects/valuation` | `https://sonchanggi.github.io/valuation/` | Separate valuation repo and Pages project |
| risk-score | `/Users/changgison/projects/risk-score` | `https://sonchanggi.github.io/quant-dashboard/risk-score/` | Separate source repo synced into quant-dashboard Pages route |
| sox | `/Users/changgison/projects/sox` | `https://sonchanggi.github.io/sox/` candidate | Separate local repo; public page role still needs confirmation |

### Data, Analysis, And Deployment Flow

- `quant-dashboard` reads public static JSON from linked Pages projects and renders a route-less static hub.
- Momentum, DRAM, Best Factor, ETF Tracking, and Valuation expose small summary/detail JSON files consumed by the hub.
- `risk-score` is source-owned by `/Users/changgison/projects/risk-score` and documents a sync step into the quant-dashboard Pages subtree route `/quant-dashboard/risk-score/`.
- `port` is linked as a standalone Pages tool and is not currently parsed by the central summary adapter.
- `sox` exists locally but needs manual confirmation before treating it as an active public route.
- Deployments should preserve static GitHub Pages behavior and project-local workflows. Do not point one project at another project's deployment target unless its README explicitly documents that sync.

### UI/UX Work Scope

- Preserve the dark, data-first research cockpit style described in `DESIGN.md`.
- Keep status, freshness, fallback, caveat, source, and research-only disclaimer states visible.
- Keep static HTML/CSS/JS patterns and avoid introducing a frontend framework without approval.
- For `risk-score`, preserve nested route safety under `/quant-dashboard/risk-score/`.

### Protected Areas

- Do not delete or rewrite source code, git history, branches, or worktrees as part of cleanup.
- Do not delete any `*.omx-worktrees` path without separate manual confirmation.
- Do not read or print `auth.json`, `.env`, API keys, tokens, or secrets.
- Do not change investment logic, data collection formulas, JSON contracts, generated-result semantics, or disclaimers during cleanup.
- Do not modify deploy workflows or sync targets unless explicitly requested.

### Command Candidates

Quant dashboard:

```bash
cd /Users/changgison/projects/quant-dashboard
python3 -m http.server 8080
npm test
npm run test:live
```

Risk score:

```bash
cd /Users/changgison/projects/risk-score
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/update_risk_score_data.py
npm test
python3 scripts/sync_to_quant_dashboard.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/verify_quant_dashboard_sync.py
```

Other projects should use their local README, `package.json`, `pyproject.toml`, and workflow docs as source of truth.

### Remaining Risks

- `quant-dashboard` is behind `origin/main` and `CODEX_HANDOFF.md` is intentionally uncommitted unless the user decides to commit it.
- Several project main folders are detached HEAD checkouts; verify intended branch before making future edits there.
- 9 `*.omx-worktrees` paths remain preserved and need manual ownership review before any future cleanup.
- `momentum-factor-lab` had the only repo-local `.omx` candidate observed in the 9 project roots.
- Home-level Codex state is quarantined during final cleanup; future CLI use requires `codex login`.
- `sox` public page role remains unclear from local README and should be confirmed manually.

### Final Cleanup Result

Quarantine root:

```text
/Users/changgison/codex-cleanup-workspace/backups/20260702-092321/final-cleanup-quarantine/
```

Cleanup actions completed:

- Ran `omx uninstall`; it reported no active OMX entries remaining in config, then completed.
- Removed global npm package `oh-my-codex`.
- Moved legacy `~/.omx` to quarantine.
- Moved legacy nested `~/.codex/.omx` and `~/.codex/memories/.omx` to quarantine.
- Moved legacy `~/.codex` to quarantine, including `auth.json` without reading or printing its contents.
- Recreated only an empty `~/.codex` directory.
- Moved auto-created `~/.codex/models_cache.json` to quarantine so the new `~/.codex` remains empty.
- Moved `/Users/changgison/projects/momentum-factor-lab/.omx` to quarantine.

Cleanup verification:

- `command -v omx` returned no command.
- npm global list showed no `oh-my-codex` or `omx` package match after cleanup.
- `pnpm` and `bun` were not found in PATH, so no global package cleanup was performed for them.
- No repo-local `.omx` path remained in the 9 main project roots.
- `*.omx-worktrees` paths were preserved.
- New `~/.codex` contains only the directory itself.

Fresh Codex CLI/App restart:

```bash
unset CODEX_HOME
codex login
cd /Users/changgison/projects/quant-dashboard
codex
```
