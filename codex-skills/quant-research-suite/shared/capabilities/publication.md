# Capability: publication

Activate when generated artifacts or results become a current/shared version,
even if no website is involved.

- Stage a versioned candidate, validate identity and content, then update the
  current pointer atomically.
- Required failure, validation mismatch, or out-of-order completion must leave
  last-good current state intact.
- Record candidate identity, previous/current pointer, publication command or
  API, and verification.
- Publication authority is distinct from local implementation and from paid
  authority.

Evidence gate: `publication`.
