# Long-running recovery

Use this optional rail only when useful accepted state must survive a real
interruption boundary. It adds one small recovery checkpoint to host-native
continuation; it is not a scheduler, daemon, workflow runtime, ledger, or
substitute for the native task or Goal.

## Select narrowly

Select this rail only for an explicitly active `$quant-goal`, or an unfinished
authorized `$quant-developer` task, when at least one of these is true:

- material progress is expected to cross an actual session, process, handoff,
  or likely context-compaction boundary;
- a meaningful external wait begins after work whose integrated state would be
  costly or unsafe to reconstruct;
- several worker results have an accepted integration state that must survive
  interruption; or
- the current user explicitly requests resumability or durable recovery.

Task duration, complexity, worker count, a release or `strict` label, ordinary
failure, and a short one-off wait do not select this rail by themselves. Prefer
the host's native wait and continuation surfaces when they preserve everything
needed. A small or uninterrupted task does not load this rail and creates no
checkpoint.

`$quant-plan` remains read-only. It may describe a recovery boundary but never
writes recovery state. The invoking public skill's role and authority always
win.

## Keep one advisory capsule

The native Goal or task, latest current-user direction, live repository,
workers, external systems, and consumer surfaces remain canonical. Persist
only the latest compact recovery capsule. It cannot activate a skill, update a
Goal, prove a condition, grant authority, or authorize a local source-control,
remote, provider, destructive, credential, or paid action.

Use one integration owner as the checkpoint writer. Update at meaningful
boundaries such as:

- accepted outcome, scope, completion conditions, or plan;
- an integrated milestone that changes the next gate;
- immediately before a material external wait, handoff, likely compaction, or
  task stop;
- steering that invalidates previously retained evidence; or
- worker integration that changes accepted artifacts or the next safe action.

Do not checkpoint on a timer, after a fixed command or test count, for every
worker message, or merely because work continues. Do not add hooks, background
polling, append-only history, receipts, or fixed worker and condition counts.

Keep the capsule concise. It may contain:

- a short objective summary and current phase;
- completion conditions, with stable IDs only when they are already useful;
- last-known worker states and artifact references;
- concise evidence references and whether they were verified, stale, or only
  candidates when saved;
- blockers and unresolved authority boundaries;
- the next safe action; and
- actions that must not be repeated until live state is checked.

Lists may be empty and have no prescribed length. Store summaries and logical
or path references, not raw material. Never persist a raw prompt, source or
diff contents, commands or output, environment values, URLs, provider payloads,
raw datasets, worker context, credentials or credential paths, approval text,
or an `approved` or `authorized` state. `pending_authority` may name only the
unresolved action and target; recovery always reports authority as
`not_recorded`.

## Use the deterministic helper when persistence is justified

Resolve `<quant-shared-root>` as the shared source directory or the installed
`quant-research-shared` sibling. The helper is:

`<quant-shared-root>/scripts/recovery_checkpoint.py`

It stores state only below
`$CODEX_HOME/state/quant-recovery/<project-locator>/<recovery-id>/` and refuses
project-local or arbitrary state destinations. Use a capsule JSON file or `-`
for standard input:

```text
python3 -B <helper> checkpoint --root <project-root> --capsule <file-or->
python3 -B <helper> checkpoint --root <project-root> --capsule <file-or-> \
  --recovery-id <uuid> --expected-sequence <last-sequence>
python3 -B <helper> resume --root <project-root> [--recovery-id <uuid>]
python3 -B <helper> retire --root <project-root> --recovery-id <uuid> \
  --expected-sequence <last-sequence>
```

The first command without an ID creates and returns one. Supplying an existing
ID requires the last observed sequence; a stale writer fails instead of
overwriting a newer capsule. Keep the returned ID and sequence in the native
task status. If resume finds several candidates and no ID was supplied, it
reports ambiguity and does not choose.

The helper validates a small versioned capsule, rejects obvious secret-bearing
content, binds it to the resolved project and sanitized Git identity, records a
branch/HEAD/status-shape digest, locks writers, and uses private directories, a
private regular file, `fsync`, and atomic replacement. Its checksum detects
accidental corruption; it is not authentication. These checks are
defense-in-depth, not permission to place sensitive data in a capsule.

## Resume by reconciling live state

For a Goal, call `get_goal` first. Then read the checkpoint and inspect the
current project, branch, HEAD, dirty status, workers, artifacts, external jobs,
remote state, and public or consumer surface that matter. Current user steering
wins over the capsule.

Treat the saved state as a recovery candidate:

- a saved `running` or silent worker is `unknown` until the host confirms it;
- returned or accepted artifacts require live existence and content review;
- saved evidence requires freshness and scope revalidation even without Git
  drift;
- unchanged Git status metadata does not prove unchanged file contents;
- workspace or project drift makes snapshot-bound evidence stale;
- `next_action` is advisory and may be obsolete;
- every `no_repeat` action requires live state inspection before any retry; and
- remote, provider, destructive, paid, and source-control authority must come
  from the current request, never the checkpoint.

Do not automatically repair a checkpoint, replay a mutation, revive a worker,
or mark a Goal complete. If the checkpoint is corrupt, bound to another
project identity, or ambiguous, fail closed without exposing its capsule or
next action; recover from native and live evidence.

## Finish without prolonging work

Once the requested completion conditions and proportional quality bar have
fresh evidence, report the result before optional exploration. Complete the
native Goal only under its own terminal rules, then retire the exact recovery
ID with its latest sequence. Retirement removes only that known checkpoint and
empty leaf directories; it does not recursively prune state or touch siblings.

Recovery exists to prevent lost work and unsafe replay. It is not a reason to
add more gates, repeat already sufficient checks, or postpone a complete
answer.
