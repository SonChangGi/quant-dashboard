# Shared project navigation

`v1/menu.json` is the public menu source. The Hub publishes it with `v1/nav.js` and `v1/nav.css`. Change the menu once, then run `node scripts/sync-navigation.mjs` to update the generated fallback used by the loader and the platform registry. `npm test` checks that those copies match. Consumer fallbacks can be generated or verified with `node scripts/sync-navigation.mjs [--check] --fallback /path/to/menu.generated.ts` (repeat `--fallback` for multiple consumers).

Static pages load the shared CSS and deferred script, with `data-quant-project` on the script or navigation element. The runtime replaces only `.quant-shared-nav__links` and preserves theme buttons. React pages use `useSharedNavigation` and `data-quant-navigation-managed="react"`; React retains ownership of its nodes. Their local `menu.generated.ts` is generated from the same JSON and is used if the shared runtime cannot load.

The runtime reads the menu on each page load with revalidation, omits credentials and referrers, rejects invalid or duplicate entries, and limits fetch plus body reading to three seconds. Failure retains the local menu. No result data, collection or calculation settings are changed.

Public paths:
- `https://sonchanggi.github.io/quant-dashboard/shared/navigation/v1/menu.json`
- `https://sonchanggi.github.io/quant-dashboard/shared/navigation/v1/nav.js`
- `https://sonchanggi.github.io/quant-dashboard/shared/navigation/v1/nav.css`

Navigation ids are separate from legacy calculation/API ids. `momentum` remains an explicit navigation alias for `factor`; the old public summary schema is not relabelled.

Current navigation contains the Hub brand and eight project links: Factor, DRAM, ETF, SOX, Fear & Greed, Regime, News, and 알파 하우스. Best and SPO are not navigation entries. Retired ids are rejected; they are never aliases for Factor. The central JSON remains the authority when this list changes.

Project links follow creation order. Factor inherits the original Momentum project and is first. For each new project, append its entry immediately before `observatory` in `menu.json` (after News today); preserve the existing project order. Alpha House stays at the trailing edge of the links, followed by the existing theme button. The navigation remains one 59px row at every viewport; narrow screens scroll only the project links.

Creation-order evidence: DRAM first published its Pages dashboard on 2026-06-10 ([commit 1bd8e31](https://github.com/SonChangGi/dram-price/commit/1bd8e31)); ETF first published on 2026-06-17 ([commit 4d01420](https://github.com/SonChangGi/etf-tracking/commit/4d01420)). DRAM therefore precedes ETF. Factor retains the original Momentum project's earlier creation order.
