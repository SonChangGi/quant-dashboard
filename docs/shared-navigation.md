# Shared project navigation

`v1/menu.json` is the public menu source. The Hub publishes it with `v1/nav.js` and `v1/nav.css`. Change the menu once, then run `node scripts/sync-navigation.mjs` to update the generated fallback used by the loader and the platform registry. `npm test` checks that those copies match. Consumer fallbacks can be generated or verified with `node scripts/sync-navigation.mjs [--check] --fallback /path/to/menu.generated.ts` (repeat `--fallback` for multiple consumers).

Static pages load the shared CSS and deferred script, with `data-quant-project` on the script or navigation element. The runtime replaces only `.quant-shared-nav__links` and preserves theme buttons. React pages use `useSharedNavigation` and `data-quant-navigation-managed="react"`; React retains ownership of its nodes. Their local `menu.generated.ts` is generated from the same JSON and is used if the shared runtime cannot load.

The runtime reads the menu on each page load with revalidation, omits credentials and referrers, rejects invalid or duplicate entries, and limits fetch plus body reading to three seconds. Failure retains the local menu. No result data, collection or calculation settings are changed.

Public paths:
- `https://sonchanggi.github.io/quant-dashboard/shared/navigation/v1/menu.json`
- `https://sonchanggi.github.io/quant-dashboard/shared/navigation/v1/nav.js`
- `https://sonchanggi.github.io/quant-dashboard/shared/navigation/v1/nav.css`

Navigation ids are separate from legacy calculation/API ids. `momentum` remains an explicit navigation alias for `factor`; the old public summary schema is not relabelled.

Current navigation contains the Hub brand and eight project links: Fear & Greed, Factor, DRAM, ETF, SOX, Regime, News, and 알파 하우스. Best and SPO are not navigation entries. Retired ids are rejected; they are never aliases for Factor. The central JSON remains the authority when this list changes.
