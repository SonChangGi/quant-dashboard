# Adapter: GitHub

Use only when the selected project actually uses GitHub.

- Verify `gh auth status`, intended host/account, repository remote, base branch,
  and `git ls-remote` before a remote mutation.
- Treat commit as a local source-control action. Treat push, PR, review,
  merge, tag/release, and workflow dispatch as remote source-control or
  provider actions. Every selected action remains a distinct authority and
  evidence checkpoint.
- Never retain device codes or tokens in logs, receipts, prompts, or files.
- After authentication loss, re-check remote state before retrying so a
  completed action is not duplicated.
