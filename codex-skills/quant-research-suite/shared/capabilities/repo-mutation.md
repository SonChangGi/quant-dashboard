# Capability: repository mutation

Activate when files in a project will change.

- Record root, project instructions, protected paths, and current changed
  surfaces before editing. When Git exists, also record its common directory,
  worktree, branch, base/head, and dirty paths.
- Branch, worktree, stage, commit, cherry-pick, and rebase are local
  source-control mutations. Use any of them only when the current user request
  separately authorizes that exact local source-control action; permission to
  edit files is not enough.
- Use an isolated worktree when Git exists and current state is stale,
  overlapping, or dirty in the target surface only when worktree creation is
  separately authorized. Otherwise preserve one writer and sequence the edits
  in the existing workspace.
- Make the smallest coherent patch and preserve unrelated changes.
- Verify protected contracts and targeted tests after editing.
- Commit remains a separate local source-control action. Push, PR, merge, tag,
  and release are separate remote source-control actions.

Evidence gates: `contract`, plus the assurance-level gates.
