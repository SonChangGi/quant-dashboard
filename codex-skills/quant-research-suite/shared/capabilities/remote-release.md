# Capability: remote release

Activate when the stated outcome includes commit/push, PR/merge, tag/release,
migration, deployment, schedule enablement, or another remote publication.
Selection adds gates; it does not grant authority.

- Reconfirm repository, account/project, base/head, remote, protected changes,
  and exact authorized actions immediately before release.
- Run authentication and cost/quota preflight without exposing credentials.
- Execute only the approved sequence; record each remote boundary separately.
- A commit, push, PR, merge, workflow success, deployment, and public readback
  are different checkpoints.
- On auth loss or interruption, re-verify state and resume from the last proven
  checkpoint. Never repeat a possibly completed mutation blindly.
- Verify rollback/fallback and the final remote/public identity.

Evidence gates: `release`, `cost`. Add `public-web` when public readback is part
of the outcome.
