# Adapter: GitHub

Use only when the selected project actually uses GitHub.

- Verify `gh auth status`, intended host/account, repository remote, base branch,
  and `git ls-remote` before a remote mutation.
- Treat commit, push, PR, review, merge, tag/release, and workflow dispatch as
  distinct authorized actions and evidence checkpoints.
- Never retain device codes or tokens in logs, receipts, prompts, or files.
- After authentication loss, re-check remote state before retrying so a
  completed action is not duplicated.
