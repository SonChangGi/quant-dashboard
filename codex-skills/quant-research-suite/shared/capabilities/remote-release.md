# Capability: remote release

Apply this rail when the stated outcome includes push, PR/merge, tag/release,
migration, deployment, schedule enablement, or another remote publication.
A local commit alone does not activate this capability. Loading this rail
identifies relevant preflight and proof; it does not grant authority.

- Reconfirm relevant target identities and exact authorized actions immediately
  before release: repository and base/head/remote, account/project, or provider
  target only when applicable.
- Run applicable authentication and cost/quota preflight without exposing
  credentials.
- Execute only the approved sequence; record each remote boundary separately.
- A local commit, remote push, PR, merge, workflow success, deployment, and
  public readback are different checkpoints. Commit authority does not grant
  any remote checkpoint.
- On auth loss or interruption, re-verify state and resume from the last proven
  checkpoint. Never repeat a possibly completed mutation blindly.
- Verify rollback/fallback and the final remote/public identity.
- Add `public-web.md` when public readback is part of the outcome.
