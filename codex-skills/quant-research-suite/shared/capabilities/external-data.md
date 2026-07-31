# Capability: external data

Activate when the project reads a provider, file feed, API, database, or other
source outside its authoritative codebase.

## Free-only eligibility

Use only a selected access path that supplies the required data at zero charge
without a trial, expiring credit, automatic paid conversion, card or billing
setup, subscription, PAYG, overage, paid add-on, or paid tier for the required
scope. A provider may offer separate optional paid tiers only when the selected
path cannot enroll in, depend on, or fall through to them and hard-stops before
any charge. Do not present paid data as an alternative or ask for approval to
use it. If an eligible path later becomes paid for the required use, stop new
collection and move to an eligible free source, a free reconstruction or
proxy, or a narrower honest claim. Follow `../core/authority.md`.

Only after the legacy router selects an existing schema-v2 `external-data`
contract, record `access_eligibility: permanently-free-no-billing`. This is a
closed execution eligibility assertion: the selected access path has zero
price, no payment method or billing setup, no trial or expiring credit, no
subscription, and no automatic paid conversion. It does not replace the
separate `rights_policy` or claim-specific rights check. Recheck it when
provider terms or the access path change; an ineligible source must be
replaced, reconstructed, proxied, or removed from the claim. Ordinary work
does not create schema state merely because it uses external data.

## Match evidence to use and claim

Classify the proposed use before selecting evidence:

- `private_analysis`: local or private exploration that does not redistribute
  source rows;
- `derived_output`: a result, chart, statistic, or model output that exposes
  only what the selected source permits;
- `raw_redistribution`: public or third-party delivery of source fields or
  substantially equivalent records.

For `private_analysis`, record the source ID, provider and endpoint or collector,
collection time, source `as_of`, relevant fields, adjusted/raw price meaning,
transformations, and known limitations. Unclear redistribution language is not
by itself a blocker for private analysis, but known access restrictions,
authentication bypass, or prohibited use still fail closed.

For `derived_output`, check the terms that apply to the fields and output
actually exposed. If the intended display is not supported, keep the work
private, change to a permitted aggregation or derivation, narrow the output, or
select another eligible free source. For `raw_redistribution`, affirmative
display or redistribution permission is a hard gate.

Historical point-in-time provenance is required only when acceptance claims
that the result is point-in-time, as-known-then, look-ahead-free,
survivorship-free, or historically investable. Otherwise a non-PIT or currently
reconstructed analysis may proceed when it is labeled with the applicable
restatement, look-ahead, and survivorship limitations.

For price analysis, verify the provider's adjusted/raw semantics. Require a
separate corporate-actions feed and event-adjustment rules only when acceptance
depends on dividends, reinvestment, splits, total return, or an event study.

## Best-attainable path

When a source is missing, incomplete, stale, ineligible, or unsuitable, search
before declaring a blocker:

1. official, regulator, exchange, or public-sector zero-charge sources;
2. another eligible free provider or a multi-source cross-check;
3. free public filings, bulk files, project caches, or reproducible derivation;
4. a defensible free proxy, forward-only collection, or narrower
   period/universe/method;
5. an explicit degraded or unavailable result with the claim reduced to what
   the evidence supports.

Never fabricate a value, conceal a gap, bypass access controls, silently weaken
a filter, or describe a proxy or non-PIT result as stronger evidence.

## Automation and compatibility

Separate collection, normalization, coherent cutoff, analysis, result
validation, and publication whenever those stages exist. Preserve source
revisions and last-good state; do not rewrite historical values to zero, empty,
stale, or unrelated substitutes.

For ordinary scheduled collection, combine this rail with
`scheduled-automation.md`; add `publication.md` and `public-web.md` only when
their triggers apply. Scheduling, publication, raw redistribution, complexity,
or a `strict` label alone does not select a legacy registry, immutable snapshot,
hash, or receipt contract.

When an existing exact data-automation contract, explicit machine audit, or
contract-specific recovery actually requires that legacy payload, enter it
through `../core/context-routing.md`. If the installed profile or exact child
is absent, report that compatibility path as unavailable; do not search for,
reconstruct, or install another suite copy.

Evidence gates when acceptance selects them: `collection`, `freshness`.
