begin;
-- Lock only while checking references and deleting the retired project's rows.
lock table public.projects, public.analysis_configs, public.analysis_runs,
  public.analysis_dispatch_outbox, public.data_snapshots, public.analysis_artifacts
  in share row exclusive mode;

create temporary table retirement_other_projects on commit drop as
select 'projects'::text as name, md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text, '[]')) as digest
from public.projects t where id <> 'best-factor'
union all
select 'configs', md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text, '[]'))
from public.analysis_configs t where project_id <> 'best-factor'
union all
select 'runs', md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text, '[]'))
from public.analysis_runs t where project_id <> 'best-factor'
union all
select 'outbox', md5(coalesce(jsonb_agg(to_jsonb(t) order by run_id)::text, '[]'))
from public.analysis_dispatch_outbox t where project_id <> 'best-factor'
union all
select 'snapshots', md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text, '[]'))
from public.data_snapshots t where project_id <> 'best-factor'
union all
select 'artifacts', md5(coalesce(jsonb_agg(to_jsonb(t) order by t.id)::text, '[]'))
from public.analysis_artifacts t join public.analysis_runs r on r.id=t.run_id
where r.project_id <> 'best-factor';

do $$
begin
  if exists(select 1 from public.analysis_runs r join public.analysis_configs c on c.id=r.config_id where r.project_id<>c.project_id)
    or exists(select 1 from public.analysis_artifacts a join public.analysis_runs r on r.id=a.run_id join public.data_snapshots s on s.id=a.snapshot_id where r.project_id<>s.project_id)
    or exists(select 1 from public.data_snapshots s join public.analysis_runs r on r.id=s.run_id where r.project_id<>s.project_id)
    or exists(select 1 from public.analysis_dispatch_outbox o join public.analysis_runs r on r.id=o.run_id where r.project_id<>o.project_id)
  then raise exception 'Cross-project references prevent Best retirement'; end if;
end $$;

delete from public.analysis_artifacts where run_id in (select id from public.analysis_runs where project_id='best-factor');
delete from public.data_snapshots where project_id='best-factor';
delete from public.analysis_runs where project_id='best-factor';
-- Outbox rows cascade from the deleted runs.
delete from public.analysis_configs where project_id='best-factor';
delete from public.projects where id='best-factor';

-- Prevent old publishers or direct RPC clients from restoring the retired project.
alter table public.projects add constraint projects_best_factor_retired check (id <> 'best-factor');

do $$
declare after_digest text; row_record record;
begin
  for row_record in select * from retirement_other_projects loop
    case row_record.name
    when 'projects' then select md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text,'[]')) into after_digest from public.projects t where id<>'best-factor';
    when 'configs' then select md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text,'[]')) into after_digest from public.analysis_configs t where project_id<>'best-factor';
    when 'runs' then select md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text,'[]')) into after_digest from public.analysis_runs t where project_id<>'best-factor';
    when 'outbox' then select md5(coalesce(jsonb_agg(to_jsonb(t) order by run_id)::text,'[]')) into after_digest from public.analysis_dispatch_outbox t where project_id<>'best-factor';
    when 'snapshots' then select md5(coalesce(jsonb_agg(to_jsonb(t) order by id)::text,'[]')) into after_digest from public.data_snapshots t where project_id<>'best-factor';
    when 'artifacts' then select md5(coalesce(jsonb_agg(to_jsonb(t) order by t.id)::text,'[]')) into after_digest from public.analysis_artifacts t join public.analysis_runs r on r.id=t.run_id where r.project_id<>'best-factor';
    end case;
    if after_digest is distinct from row_record.digest then raise exception 'Other project changed during Best retirement: %',row_record.name; end if;
  end loop;
end $$;
commit;
