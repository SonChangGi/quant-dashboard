begin;

alter table public.analysis_runs
  drop constraint analysis_runs_code_version_format;

alter table public.analysis_runs
  add constraint analysis_runs_code_version_format check (
    code_version is null
    or (
      project_id = 'best-factor'
      and code_version ~ '^[0-9a-f]{40}$'
    )
    or (
      project_id = 'momentum'
      and code_version ~ '^github:SonChangGi/momentum-factor-lab@[0-9a-f]{40}$'
    )
    or (
      project_id = 'fear-greed'
      and code_version ~ '^github:SonChangGi/fearNgreed@[0-9a-f]{40}$'
    )
  );

commit;
