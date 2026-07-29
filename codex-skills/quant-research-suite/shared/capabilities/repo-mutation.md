# Capability: repository mutation

Activate when files in a project will change.

- Record root, project instructions, protected paths, and current changed
  surfaces before editing. When Git exists, also record its common directory,
  worktree, branch, base/head, and dirty paths.
- Use an isolated worktree when Git exists and current state is stale,
  overlapping, or dirty in the target surface.
- Make the smallest coherent patch and preserve unrelated changes.
- Verify protected contracts and targeted tests after editing.
- Commit, push, PR, merge, tag, or release remain separate remote actions.

Evidence gates: `contract`, plus the assurance-level gates.
