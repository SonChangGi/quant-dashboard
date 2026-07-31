# Advisory: architecture options

Choose architecture from the demonstrated product need.

1. Static artifacts and static hosting: best when computation can run ahead of
   time and users only read/select stored results.
2. Static frontend plus orchestration API: useful when users submit validated
   jobs or need run state while authoritative workers remain elsewhere.
3. Frontend, API, persistence, and workers: justified by authorization,
   concurrency, durable run history, recovery, or long-running execution.

Compare options by user-visible completeness, failure recovery, contract
preservation, operational burden, provider rights, cost ceilings, fallback, and
testability—not by technology count. Prefer an incremental pilot while the
stable route remains available.
