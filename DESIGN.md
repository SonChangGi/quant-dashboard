# Design

## Source of truth
- Status: Approved Visual Ralph reference implemented
- Last refreshed: 2026-06-24
- Primary product surfaces:
  - `quant-dashboard` hub: `index.html`, `assets/styles.css`, `assets/app.js`
  - `momentum-factor-lab`: `docs/index.html`, `docs/assets/styles.css`, `docs/assets/dashboard.js`, source template `momentum_factor_lab/dashboard.py`
  - `best-factor`: `docs/index.html`, `docs/styles.css`, `docs/app.js`
  - `etf-tracking`: `index.html`, `assets/styles.css`, `assets/app.js`
  - `dram-price`: `web/index.html`, `web/styles.css`, `web/app.js`
  - `valuation`: `docs/index.html`, `docs/assets/styles.css`, `docs/assets/app.js`
- Evidence reviewed:
  - Current UI files and CSS tokens across all six surfaces.
  - Root/package verification entrypoints: `quant-dashboard/package.json`, sibling `package.json`/`pyproject.toml`/README files where present.
  - Existing deployment posture: static GitHub Pages sites with generated or committed JSON payloads.
  - Existing product constraints from sibling READMEs: research-only disclaimers, static-data-first behavior, freshness/status surfacing, and no browser-side secret/API dependence.

## Brand
- Personality:
  - High-end institutional research cockpit: calm, precise, understated, data-first.
  - Dark neutral, graphite, charcoal, slate, ink, warm off-white text; accent colors are restrained signal lights, not brand decoration.
- Trust signals:
  - Clear data freshness/status chips, caveats, source provenance, and failure states.
  - Tables and charts should feel auditable: visible axes, legible labels, consistent spacing, and no decorative chart noise.
  - Avoid hiding uncertainty; stale/degraded/partial data must remain prominent.
- Avoid:
  - Bright blue SaaS gradients, saturated rainbow cards, neon glow, gamified colors, excessive glassmorphism, dense shadow stacks, and low-contrast gray-on-black text.
  - Changing calculation logic, generated JSON contracts, disclaimers, or data-fetch behavior during a design-only pass.

## Product goals
- Goals:
  - Convert the quant hub and five linked project pages into one cohesive dark-mode family.
  - Make every page feel like the same premium research suite while preserving each project's information architecture.
  - Improve scanability of summaries, cards, tables, and charts in Korean/English mixed finance content.
  - Preserve static GitHub Pages reliability and existing automation/deploy flows.
- Non-goals:
  - No investment logic changes, factor-selection changes, valuation formula changes, data update policy changes, or JSON schema rewrites.
  - No new frontend framework, build system, or runtime dependency unless unavoidable and explicitly approved.
  - No new live-data browser calls or secret-bearing client behavior.
- Success signals:
  - All six sites share recognizable tokens: background, panels, border, typography, focus, status, and chart palette.
  - Existing tests/static smoke checks pass per repo.
  - Visual Ralph final verdict after approval scores `>= 90` against the approved reference.
  - Live GitHub Pages readback shows the deployed dark neutral design assets.

## Personas and jobs
- Primary personas:
  - Individual quant/research operator reviewing daily signals and data freshness.
  - Portfolio/research reader comparing factor, ETF, DRAM, and valuation evidence quickly.
  - Future maintainer needing a clear token/component contract to keep independent repos aligned.
- User jobs:
  - Open the hub, understand which project data is fresh/degraded, and navigate to the relevant detail page.
  - Read the key result and caveats without mistaking research output for advice.
  - Compare charts/tables under dim-light or dense-workflow conditions without eye strain.
- Key contexts of use:
  - Desktop research sessions first; mobile/tablet must remain readable and overflow-safe.
  - Static pages loaded from GitHub Pages, sometimes with stale or partial JSON payloads.

## Information architecture
- Primary navigation:
  - Quant hub remains the entry surface with cards/deep links to each project.
  - Sibling pages retain existing route-less static-page navigation and local controls.
- Core routes/screens:
  - `quant-dashboard`: research briefing, project summaries, freshness/status, linked cards.
  - `momentum-factor-lab`: best/selected factor dashboard, factor catalog, portfolio/freshness states.
  - `best-factor`: factor ranking summary, holdings, diagnostics, caveats.
  - `etf-tracking`: ETF selector, holdings weight charts, residual/price-aligned explanations, status files.
  - `dram-price`: product/category/source controls, DRAM series charts/tables/status.
  - `valuation`: ticker search, decision cockpit, DCF/relative valuation, diagnostics, assumptions, print/copy.
- Content hierarchy:
  - 1. Page identity and latest state/freshness.
  - 2. Primary conclusion or decision cockpit.
  - 3. Comparison charts/cards.
  - 4. Detail tables, assumptions, caveats, methodology.

## Design principles
- Principle 1: Quiet confidence over decoration.
  - Use depth, spacing, and contrast to signal hierarchy; use color only for meaning.
- Principle 2: Research integrity stays visible.
  - Data freshness, partial failures, caveats, and confidence limits remain first-class UI, not footnotes.
- Principle 3: One family, native repos.
  - Align visual tokens and component treatment without forcing a shared package or framework.
- Principle 4: Charts must be legible before beautiful.
  - Axes, labels, gridlines, active series, and empty/degraded states need stronger contrast than decorative backgrounds.
- Tradeoffs:
  - Slightly larger spacing and stronger borders are acceptable to improve dark-mode readability.
  - Accent palette may vary by semantic status/series but must stay muted and consistent.

## Visual language
- Color:
  - Base: near-black graphite `#080a0f`, page gradient `#0b0d12 -> #11141b`.
  - Panels: `#12161d`, elevated panels `#171b23`, soft panels `#1c212b`.
  - Borders: `rgba(226, 232, 240, 0.10-0.16)`.
  - Text: primary `#f4f4f5`, secondary `#c4c7cc`, muted `#8b919c`.
  - Accent: restrained platinum/steel `#d7dde8`, cyan-slate `#7dd3fc`, green `#86efac`, amber `#fbbf24`, red `#f87171`, violet `#c4b5fd` only when semantically useful.
  - Avoid large saturated blue gradients; gradients should be subtle graphite light falloff.
- Typography:
  - System sans stack. Prefer existing repo-native typography.
  - Financial numerals use tabular figures where possible.
  - Headings: clear weight, modest letter-spacing; avoid oversized marketing hero copy on data pages.
- Spacing/layout rhythm:
  - 8px base rhythm; dashboard cards use 20-28px padding on desktop and 16-20px on mobile.
  - Max widths remain similar to current sites; avoid breaking existing table/chart layouts.
- Shape/radius/elevation:
  - Radius: 16-24px for major panels, 10-14px for chips/buttons, 8px for dense table controls.
  - Elevation: subtle inset/highlight borders and low-opacity shadows; no bright glow-heavy neon.
- Motion:
  - Minimal. Use short hover/focus transitions only; respect reduced motion.
- Imagery/iconography:
  - No new logos or decorative illustrations required. Existing text-first research identity is preferred.

## Components
- Existing components to reuse:
  - Static hero/header sections, summary cards, metric cards, status/freshness badges, project cards, filter controls, chart containers, tables, caveat sections, buttons/links.
- New/changed components:
  - Shared dark token layer per repo using repo-native CSS variables.
  - Premium dark panels with consistent border/elevation.
  - Status chips with semantic dark-mode variants: ok/success, warning/stale, error/degraded, neutral/unknown.
  - Chart containers with stronger axis/grid/legend contrast and readable empty/loading states.
- Variants and states:
  - Loading: skeleton/shimmer or subdued placeholder panel; no white flash.
  - Empty: explicit neutral state with next action or data condition.
  - Error/degraded/stale: high-contrast warning/error chip plus plain-language explanation.
  - Active/selected controls: clear filled/inset state, keyboard focus ring.
  - Disabled: visibly unavailable but readable.
- Token/component ownership:
  - No shared package in this pass. Each repo owns its CSS file/template but follows this contract.
  - `momentum-factor-lab` must update the Python HTML/CSS source template as well as generated `docs` assets when applicable.

## Accessibility
- Target standard:
  - WCAG 2.1 AA contrast for body text, controls, and chart labels where practical.
- Keyboard/focus behavior:
  - Preserve native focusability and add visible dark-mode focus rings for links/buttons/inputs/selects.
- Contrast/readability:
  - Avoid pure black panels with low-contrast gray labels. Tables and dense numerics must remain readable.
  - Chart series cannot rely on color alone; legends/labels/tooltips remain textual.
- Screen-reader semantics:
  - Preserve existing headings, table structure, ARIA labels, and status text.
- Reduced motion and sensory considerations:
  - Keep hover/transition effects subtle and disable nonessential motion under `prefers-reduced-motion`.

## Readability remediation audit — 2026-06-24
- Shared findings across all six pages:
  - Dense tables need consistent tabular numerals, darker sticky/clear headers, stronger row separation, and visible horizontal-scroll affordance on mobile.
  - Residual light cards from the former light theme reduce contrast on dark pages; all info/status/source/method cards must use dark or tinted surfaces with readable secondary text.
  - Charts need brighter axes, gridlines, legends, and series labels; labels should never stack into unreadable piles.
  - The dark system should not look like pure black only: use restrained cyan, teal, violet, amber, and rose surface accents for hierarchy and semantics.
- `quant-dashboard`:
  - Baseline is mostly coherent, but summary/detail tables and mini chart cards need stronger numeric alignment, row contrast, and accent variety.
  - Project cards, briefing items, health items, and ETF mini detail cards should use subtle alternating surface tints while preserving the hub's data/status hierarchy.
- `momentum-factor-lab`:
  - Forward Rank-IC notice/diagnostic strips and selected/best bar rows can fall back to light surfaces with pale labels.
  - Trend bars and line charts need darker containers, stronger label contrast, and mobile overflow protection.
  - The generated `docs` CSS and the `momentum_factor_lab/dashboard.py` source template must stay synchronized.
- `best-factor`:
  - Factor-scope/taxonomy cards, mini items, empty states, and performance cards are the lowest-contrast surfaces.
  - Factor pills, ranking cards, and performance tables need dark tinted cards, readable muted text, and tabular numeric alignment.
- `etf-tracking`:
  - The holdings-weight chart end labels are crowded, and the chart summary/source cards below the graph are too low-contrast.
  - End labels should be shortened, vertically staggered with label pills, and backed by readable summary cards/legend text.
- `dram-price`:
  - DRAM chart Y-axis labels can render dirty decimals such as `252.92`/`4.4543`; axis tick generation should use clean, rounded ticks without changing the underlying price series.
  - Chart/table/source support panels need stronger axis/grid/text contrast and readable tinted surfaces.
- `valuation`:
  - Decision cockpit, method comparison, assumptions, diagnostic, workflow, and methodology cards still contain light-surface remnants that wash out in dark mode.
  - Mobile hero/nav must remain overflow-safe, and the final print stylesheet must stay light/white for report output.

## Responsive behavior
- Supported breakpoints/devices:
  - Mobile narrow widths, tablet, desktop research monitor.
- Layout adaptations:
  - Cards stack before overflow. Charts allow horizontal scrolling only when data density demands it.
  - Tables keep sticky/clear headers where already present; do not make data inaccessible on mobile.
- Touch/hover differences:
  - Hover polish is additive; controls must be obvious on touch devices without hover.

## Interaction states
- Loading:
  - Dark panels with muted placeholders and clear “loading data” text.
- Empty:
  - Neutral panel explaining which dataset/filter produced no rows.
- Error:
  - Red/amber semantic treatment with source/status detail and no silent failure.
- Success:
  - Low-saturation green/cyan status, paired with timestamp/provenance.
- Disabled:
  - Muted but readable; explain unavailable actions when current pages already do so.
- Offline/slow network, if applicable:
  - JSON fetch failures must remain explicit; stale cached/public JSON must not look fresh.

## Content voice
- Tone:
  - Precise, restrained, research-first Korean/English mixed finance copy.
- Terminology:
  - Keep existing domain terms: freshness, stale, degraded, factor, holdings, DCF, relative valuation, residual, source caveat.
- Microcopy rules:
  - Do not overpromise. Use “가능성”, “관찰”, “research only”, “not investment advice” language where existing pages do.
  - Dark-mode redesign should not rewrite disclaimers except for readability/layout.

## Implementation constraints
- Framework/styling system:
  - Static HTML/CSS/JS and Python-generated static assets; no framework migration.
  - Use each repo's existing CSS variable and vanilla JS/SVG patterns.
- Design-token constraints:
  - Add/rename tokens conservatively. Prefer mapping existing variables (`--bg`, `--panel`, `--surface`, `--ink`, `--muted`, `--line`, `--accent`) to the dark system.
  - Avoid introducing a cross-repo dependency; duplicate the token contract intentionally where needed.
- Performance constraints:
  - Keep static assets lightweight. No webfont dependency or large image dependency for the actual sites unless explicitly approved.
- Compatibility constraints:
  - Preserve GitHub Pages static loading and generated-data paths.
  - Preserve JSON contracts and existing automation schedules/deploy workflows.
- Test/screenshot expectations:
  - Before implementation: create approved Visual Ralph reference artifact.
  - During implementation: capture screenshots at desktop and mobile widths when feasible.
  - Verify with each repo's local tests/static smoke commands; if a repo has known environment caveats, record them explicitly.
  - Final deployment: push to the appropriate remote branches and verify public Pages assets or pages.

## Resolved decisions
- Visual reference approval: user approved the dark neutral luxury Visual Ralph reference on 2026-06-24.
- Connected surfaces: quant-dashboard plus momentum-factor-lab, best-factor, etf-tracking, dram-price, and valuation share the same dark neutral design language.
- Delivery scope: design-only implementation. Analysis methodology, calculation logic, generated results, JSON contracts, data automation, and research disclaimers are protected boundaries.

## Readability remediation audit — 2026-06-29
- Protected boundary: this pass is UI-only. Static HTML/CSS and browser-rendered explanatory JS may change; calculation code, generated result/data JSON, analysis methodology, automation schedules, and existing disclaimer intent remain unchanged.
- Connected surfaces now treated as one Pages family for readability: `quant-dashboard`, `momentum-factor-lab`, `dram-price`, `best-factor`, `etf-tracking`, `sox`, `port`, and `valuation`.
- Shared page structure decisions:
  - Every site gets fixed “↑ 위 / ↓ 아래” jump controls with real `#top` and `#page-bottom` anchors.
  - Operational notices, manual-update panels, data-contract warnings, and caveats belong near the bottom when they are not required to interpret the first result view.
  - Primary result/analysis cards must appear before warnings where safe, while all warnings remain present and readable.
- `momentum-factor-lab` decisions:
  - “원자료” means the stored original/backtest output, not KRW. Avoid the one-character “원” label; use `원자료(저장값)` plus a glossary note.
  - Selected-factor method cards should show exact factor formulas from the factor spec catalog, observation/skip windows, weighting scenario assumptions, and the distinction between original output and browser scenario proxy.
  - Daily investment-weight rows should be pivoted by symbol columns so saved/current scenario weights can be compared horizontally without a source column.
- `best-factor` decisions:
  - Factor family cards should expose expandable formula/method examples derived from the existing factor catalog metadata.
  - Ranking cards should surface the selected factor's formula and plain-language scoring method inline, without changing ranking metrics or portfolio outputs.
- Source/provenance decisions:
  - Source labels that already have URLs in deployed JSON/status payloads should be clickable hyperlinks.
  - Do not add browser-side live crawling or provider calls; links are provenance/navigation only.
- Visual verification expectation: compare before/after screenshots at desktop and mobile widths, then run local syntax/regression gates. Public Pages readback is required only after explicit deployment/push approval because pushing multiple sibling repos is an external-production action.
