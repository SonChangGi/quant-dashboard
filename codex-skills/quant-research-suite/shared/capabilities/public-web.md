# Capability: public web

Apply this rail when the requested outcome includes a publicly reachable web
surface.

- Verify the intended production route, not only a preview or build artifact.
- Read back both HTML and the authoritative data/result identity the browser
  adopts.
- Check only affected or applicable cache/version behavior, navigation,
  interaction, supported layouts, and failure/last-good states.
- Preserve the stable fallback route until the authorized replacement is proven
  at the intended production route. This rail adds no duplicate approval
  boundary.
