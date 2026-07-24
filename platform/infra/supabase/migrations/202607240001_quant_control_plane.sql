begin;

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table public.projects (
  id text primary key,
  display_name text not null,
  input_schema_version text not null,
  capability jsonb not null default '{}'::jsonb,
  active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint projects_id_format check (id ~ '^[a-z0-9][a-z0-9-]{1,62}$'),
  constraint projects_capability_object check (jsonb_typeof(capability) = 'object'),
  constraint projects_capability_bounded check (pg_column_size(capability) <= 262144)
);

create table public.analysis_configs (
  id uuid primary key default gen_random_uuid(),
  project_id text not null references public.projects(id) on delete restrict,
  input_schema_version text not null,
  input_schema_hash text not null,
  config_hash_algorithm text not null,
  config_hash text not null,
  normalized_inputs jsonb not null,
  created_at timestamptz not null default timezone('utc', now()),
  constraint analysis_configs_hash_format check (config_hash ~ '^[0-9a-f]{64}$'),
  constraint analysis_configs_schema_hash_format check (input_schema_hash ~ '^[0-9a-f]{64}$'),
  constraint analysis_configs_inputs_object check (jsonb_typeof(normalized_inputs) = 'object'),
  constraint analysis_configs_inputs_bounded check (pg_column_size(normalized_inputs) <= 131072),
  unique (project_id, input_schema_version, config_hash)
);

create table public.analysis_runs (
  id uuid primary key,
  project_id text not null references public.projects(id) on delete restrict,
  config_id uuid not null references public.analysis_configs(id) on delete restrict,
  status text not null,
  idempotency_key_digest text not null,
  request_digest text not null,
  input_schema_version text not null,
  input_schema_hash text not null,
  config_hash_algorithm text not null,
  config_hash text not null,
  effective_config_hash text not null,
  requested_inputs jsonb not null,
  normalized_inputs jsonb not null,
  effective_inputs jsonb not null,
  ignored_inputs jsonb not null default '[]'::jsonb,
  allow_fallback boolean not null default false,
  fallbacks jsonb not null default '[]'::jsonb,
  fallback_used boolean not null default false,
  fallback_reason text,
  provider text not null,
  provider_run_id text,
  data_as_of date,
  calculated_at timestamptz,
  code_version text,
  error_code text,
  error_message text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint analysis_runs_status check (
    status in ('queued', 'dispatched', 'running', 'validating', 'published', 'failed', 'cancelled')
  ),
  constraint analysis_runs_hash_format check (
    idempotency_key_digest ~ '^[0-9a-f]{64}$'
    and request_digest ~ '^[0-9a-f]{64}$'
    and input_schema_hash ~ '^[0-9a-f]{64}$'
    and config_hash ~ '^[0-9a-f]{64}$'
    and effective_config_hash ~ '^[0-9a-f]{64}$'
  ),
  constraint analysis_runs_code_version_format check (
    code_version is null
    or (
      project_id = 'best-factor'
      and code_version ~ '^[0-9a-f]{40}$'
    )
    or (
      project_id = 'momentum'
      and code_version ~ '^github:SonChangGi/momentum-factor-lab@[0-9a-f]{40}$'
    )
  ),
  constraint analysis_runs_input_objects check (
    jsonb_typeof(requested_inputs) = 'object'
    and jsonb_typeof(normalized_inputs) = 'object'
    and jsonb_typeof(effective_inputs) = 'object'
  ),
  constraint analysis_runs_audit_arrays check (
    jsonb_typeof(ignored_inputs) = 'array'
    and jsonb_typeof(fallbacks) = 'array'
  ),
  constraint analysis_runs_inputs_bounded check (
    pg_column_size(requested_inputs) <= 131072
    and pg_column_size(normalized_inputs) <= 131072
    and pg_column_size(effective_inputs) <= 131072
    and pg_column_size(ignored_inputs) <= 32768
    and pg_column_size(fallbacks) <= 32768
  ),
  constraint analysis_runs_fallback_consistency check (
    (fallback_used is true and jsonb_array_length(fallbacks) > 0)
    or (fallback_used is false and jsonb_array_length(fallbacks) = 0)
  ),
  unique (project_id, idempotency_key_digest)
);

create table public.analysis_dispatch_outbox (
  run_id uuid primary key references public.analysis_runs(id) on delete cascade,
  project_id text not null references public.projects(id) on delete restrict,
  provider text not null,
  status text not null default 'pending',
  attempt_count integer not null default 0,
  max_attempts integer not null default 5,
  available_at timestamptz not null default timezone('utc', now()),
  lease_owner text,
  lease_token uuid,
  lease_expires_at timestamptz,
  last_attempt_started_at timestamptz,
  acknowledged_at timestamptz,
  provider_run_id text,
  last_error_code text,
  last_error_message text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint analysis_dispatch_outbox_status check (
    status in ('pending', 'leased', 'acknowledged', 'dead_letter')
  ),
  constraint analysis_dispatch_outbox_attempts check (
    max_attempts between 1 and 20
    and attempt_count between 0 and max_attempts
  ),
  constraint analysis_dispatch_outbox_lengths check (
    length(provider) between 1 and 120
    and (lease_owner is null or length(lease_owner) between 1 and 200)
    and (provider_run_id is null or length(provider_run_id) between 1 and 200)
    and (last_error_code is null or length(last_error_code) between 1 and 120)
    and (last_error_message is null or length(last_error_message) between 1 and 1000)
  ),
  constraint analysis_dispatch_outbox_state_consistency check (
    (
      status = 'pending'
      and lease_owner is null
      and lease_token is null
      and lease_expires_at is null
      and acknowledged_at is null
      and provider_run_id is null
    )
    or (
      status = 'leased'
      and lease_owner is not null
      and lease_token is not null
      and lease_expires_at is not null
      and acknowledged_at is null
      and provider_run_id is null
    )
    or (
      status = 'acknowledged'
      and lease_owner is null
      and lease_token is null
      and lease_expires_at is null
      and acknowledged_at is not null
      and provider_run_id is not null
    )
    or (
      status = 'dead_letter'
      and lease_owner is null
      and lease_token is null
      and lease_expires_at is null
      and acknowledged_at is null
      and provider_run_id is null
    )
  )
);

create table public.data_snapshots (
  id uuid primary key default gen_random_uuid(),
  project_id text not null references public.projects(id) on delete restrict,
  run_id uuid unique references public.analysis_runs(id) on delete set null,
  data_as_of date not null,
  source text not null,
  source_hash text not null,
  artifact_url text not null,
  artifact_sha256 text not null,
  byte_size bigint not null,
  contract_version text not null,
  summary jsonb not null default '{}'::jsonb,
  published boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  constraint data_snapshots_source_hash check (source_hash ~ '^[0-9a-f]{8,128}$'),
  constraint data_snapshots_artifact_hash check (artifact_sha256 ~ '^[0-9a-f]{64}$'),
  constraint data_snapshots_byte_size check (byte_size between 0 and 15728640),
  constraint data_snapshots_https check (artifact_url ~ '^https://'),
  constraint data_snapshots_summary_object check (jsonb_typeof(summary) = 'object'),
  constraint data_snapshots_summary_bounded check (pg_column_size(summary) <= 65536)
);

create table public.analysis_artifacts (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null unique references public.analysis_runs(id) on delete cascade,
  snapshot_id uuid references public.data_snapshots(id) on delete set null,
  url text not null,
  sha256 text not null,
  byte_size bigint not null,
  contract_version text not null,
  published boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  constraint analysis_artifacts_sha check (sha256 ~ '^[0-9a-f]{64}$'),
  constraint analysis_artifacts_byte_size check (byte_size between 0 and 15728640),
  constraint analysis_artifacts_https check (url ~ '^https://')
);

create index analysis_runs_project_created_idx
  on public.analysis_runs (project_id, created_at desc);
create index analysis_runs_status_updated_idx
  on public.analysis_runs (status, updated_at desc);
create index analysis_runs_config_hash_idx
  on public.analysis_runs (project_id, config_hash, created_at desc);
create index analysis_dispatch_outbox_claim_idx
  on public.analysis_dispatch_outbox (available_at, created_at)
  where status in ('pending', 'leased');
create index data_snapshots_project_asof_idx
  on public.data_snapshots (project_id, data_as_of desc)
  where published;
create index analysis_artifacts_sha_idx
  on public.analysis_artifacts (sha256);

create trigger projects_set_updated_at
before update on public.projects
for each row execute function public.set_updated_at();

create trigger analysis_runs_set_updated_at
before update on public.analysis_runs
for each row execute function public.set_updated_at();

create trigger analysis_dispatch_outbox_set_updated_at
before update on public.analysis_dispatch_outbox
for each row execute function public.set_updated_at();

create or replace function public.control_create_or_replay_analysis_run(p_run jsonb)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_project_id text := p_run ->> 'project_id';
  v_idempotency_digest text := p_run ->> 'idempotency_key_digest';
  v_config_id uuid;
  v_config public.analysis_configs%rowtype;
  v_max_attempts integer := coalesce((p_run ->> 'dispatch_max_attempts')::integer, 5);
  v_existing public.analysis_runs%rowtype;
  v_created public.analysis_runs%rowtype;
  v_outbox public.analysis_dispatch_outbox%rowtype;
begin
  if v_project_id is null or v_idempotency_digest is null then
    raise exception 'project_id and idempotency_key_digest are required';
  end if;
  if p_run ->> 'status' <> 'queued' then
    raise exception 'new analysis runs must start in queued state';
  end if;
  if v_max_attempts not between 1 and 20 then
    raise exception 'dispatch_max_attempts must be between 1 and 20';
  end if;

  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(v_project_id || ':' || v_idempotency_digest, 0)
  );

  select *
  into v_existing
  from public.analysis_runs
  where project_id = v_project_id
    and idempotency_key_digest = v_idempotency_digest;

  if found then
    if v_existing.request_digest = p_run ->> 'request_digest' then
      if v_existing.status = 'queued' then
        insert into public.analysis_dispatch_outbox (
          run_id,
          project_id,
          provider,
          max_attempts,
          available_at
        )
        values (
          v_existing.id,
          v_existing.project_id,
          v_existing.provider,
          v_max_attempts,
          v_existing.created_at
        )
        on conflict (run_id) do nothing;
      end if;
      select *
      into v_outbox
      from public.analysis_dispatch_outbox
      where run_id = v_existing.id;
      return jsonb_build_object(
        'outcome', 'replayed',
        'run', to_jsonb(v_existing),
        'outbox', case when found then to_jsonb(v_outbox) else null end
      );
    end if;
    return jsonb_build_object('outcome', 'conflict');
  end if;

  insert into public.projects (
    id,
    display_name,
    input_schema_version,
    capability,
    active
  )
  values (
    v_project_id,
    coalesce(nullif(p_run ->> 'project_display_name', ''), v_project_id),
    p_run ->> 'input_schema_version',
    '{}'::jsonb,
    true
  )
  on conflict (id) do nothing;

  insert into public.analysis_configs (
    project_id,
    input_schema_version,
    input_schema_hash,
    config_hash_algorithm,
    config_hash,
    normalized_inputs
  )
  values (
    v_project_id,
    p_run ->> 'input_schema_version',
    p_run ->> 'input_schema_hash',
    p_run ->> 'config_hash_algorithm',
    p_run ->> 'config_hash',
    p_run -> 'normalized_inputs'
  )
  on conflict (project_id, input_schema_version, config_hash)
  do nothing
  returning id into v_config_id;

  if v_config_id is null then
    select *
    into v_config
    from public.analysis_configs
    where project_id = v_project_id
      and input_schema_version = p_run ->> 'input_schema_version'
      and config_hash = p_run ->> 'config_hash'
    for update;

    if not found then
      raise exception 'analysis config disappeared during identity reuse';
    end if;
    if (
      v_config.input_schema_hash <> p_run ->> 'input_schema_hash'
      or v_config.config_hash_algorithm <> p_run ->> 'config_hash_algorithm'
      or v_config.normalized_inputs <> p_run -> 'normalized_inputs'
    ) then
      raise exception 'analysis config identity conflict';
    end if;
    v_config_id := v_config.id;
  end if;

  insert into public.analysis_runs (
    id,
    project_id,
    config_id,
    status,
    idempotency_key_digest,
    request_digest,
    input_schema_version,
    input_schema_hash,
    config_hash_algorithm,
    config_hash,
    effective_config_hash,
    requested_inputs,
    normalized_inputs,
    effective_inputs,
    ignored_inputs,
    allow_fallback,
    fallbacks,
    fallback_used,
    fallback_reason,
    provider,
    provider_run_id,
    data_as_of,
    calculated_at,
    code_version,
    error_code,
    error_message
  )
  values (
    (p_run ->> 'id')::uuid,
    v_project_id,
    v_config_id,
    p_run ->> 'status',
    v_idempotency_digest,
    p_run ->> 'request_digest',
    p_run ->> 'input_schema_version',
    p_run ->> 'input_schema_hash',
    p_run ->> 'config_hash_algorithm',
    p_run ->> 'config_hash',
    p_run ->> 'effective_config_hash',
    p_run -> 'requested_inputs',
    p_run -> 'normalized_inputs',
    p_run -> 'effective_inputs',
    coalesce(p_run -> 'ignored_inputs', '[]'::jsonb),
    coalesce((p_run ->> 'allow_fallback')::boolean, false),
    coalesce(p_run -> 'fallbacks', '[]'::jsonb),
    coalesce((p_run ->> 'fallback_used')::boolean, false),
    nullif(p_run ->> 'fallback_reason', ''),
    p_run ->> 'provider',
    nullif(p_run ->> 'provider_run_id', ''),
    nullif(p_run ->> 'data_as_of', '')::date,
    nullif(p_run ->> 'calculated_at', '')::timestamptz,
    nullif(p_run ->> 'code_version', ''),
    nullif(p_run ->> 'error_code', ''),
    nullif(p_run ->> 'error_message', '')
  )
  returning * into v_created;

  insert into public.analysis_dispatch_outbox (
    run_id,
    project_id,
    provider,
    max_attempts,
    available_at
  )
  values (
    v_created.id,
    v_created.project_id,
    v_created.provider,
    v_max_attempts,
    v_created.created_at
  )
  returning * into v_outbox;

  return jsonb_build_object(
    'outcome', 'created',
    'run', to_jsonb(v_created),
    'outbox', to_jsonb(v_outbox)
  );
end;
$$;

create or replace function public.control_claim_analysis_dispatch(
  p_run_id uuid,
  p_lease_owner text,
  p_lease_seconds integer,
  p_now timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_now timestamptz := coalesce(p_now, timezone('utc', now()));
  v_candidate_id uuid;
  v_outbox public.analysis_dispatch_outbox%rowtype;
  v_run public.analysis_runs%rowtype;
  v_token uuid;
begin
  if length(p_lease_owner) not between 1 and 200 then
    raise exception 'lease_owner must contain 1-200 characters';
  end if;
  if p_lease_seconds not between 5 and 300 then
    raise exception 'lease_seconds must be between 5 and 300';
  end if;

  if p_run_id is not null then
    select *
    into v_outbox
    from public.analysis_dispatch_outbox
    where run_id = p_run_id
    for update skip locked;

    if not found then
      return jsonb_build_object('outcome', 'busy');
    end if;
  else
    select o.run_id
    into v_candidate_id
    from public.analysis_dispatch_outbox o
    join public.analysis_runs r on r.id = o.run_id
    where r.status = 'queued'
      and (
        (o.status = 'pending' and o.available_at <= v_now)
        or (
          o.status = 'leased'
          and o.lease_expires_at is not null
          and o.lease_expires_at <= v_now
        )
    )
    order by o.available_at, o.created_at, o.run_id
    limit 1
    for update of o skip locked;

    if not found then
      return jsonb_build_object('outcome', 'none');
    end if;

    select *
    into strict v_outbox
    from public.analysis_dispatch_outbox
    where run_id = v_candidate_id;
  end if;

  select *
  into v_run
  from public.analysis_runs
  where id = v_outbox.run_id
  for update;

  if not found then
    return jsonb_build_object('outcome', 'none');
  end if;
  if v_run.status <> 'queued' then
    return jsonb_build_object('outcome', 'none');
  end if;
  if v_outbox.status = 'acknowledged' then
    return jsonb_build_object('outcome', 'acknowledged');
  end if;
  if v_outbox.status = 'dead_letter' then
    return jsonb_build_object('outcome', 'dead_letter');
  end if;
  if v_outbox.status = 'pending' and v_outbox.available_at > v_now then
    return jsonb_build_object('outcome', 'not_ready');
  end if;
  if (
    v_outbox.status = 'leased'
    and v_outbox.lease_expires_at is not null
    and v_outbox.lease_expires_at > v_now
  ) then
    return jsonb_build_object('outcome', 'busy');
  end if;

  if v_outbox.attempt_count >= v_outbox.max_attempts then
    update public.analysis_dispatch_outbox
    set
      status = 'dead_letter',
      lease_owner = null,
      lease_token = null,
      lease_expires_at = null,
      last_error_code = 'dispatch_retry_exhausted',
      last_error_message = 'Dispatch lease expired before acknowledgment'
    where run_id = v_outbox.run_id
    returning * into v_outbox;

    update public.analysis_runs
    set
      status = 'failed',
      error_code = 'worker_dispatch_retry_exhausted',
      error_message = 'Dispatch lease expired before acknowledgment'
    where id = v_outbox.run_id
      and status = 'queued'
    returning * into v_run;

    return jsonb_build_object(
      'outcome', 'dead_letter',
      'run', to_jsonb(v_run),
      'outbox', to_jsonb(v_outbox)
    );
  end if;

  v_token := gen_random_uuid();
  update public.analysis_dispatch_outbox
  set
    status = 'leased',
    attempt_count = attempt_count + 1,
    lease_owner = p_lease_owner,
    lease_token = v_token,
    lease_expires_at = v_now + make_interval(secs => p_lease_seconds),
    last_attempt_started_at = v_now
  where run_id = v_outbox.run_id
  returning * into v_outbox;

  return jsonb_build_object(
    'outcome', 'claimed',
    'run', to_jsonb(v_run),
    'outbox', to_jsonb(v_outbox)
  );
end;
$$;

create or replace function public.control_ack_analysis_dispatch(
  p_run_id uuid,
  p_lease_token uuid,
  p_provider_run_id text,
  p_now timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_now timestamptz := coalesce(p_now, timezone('utc', now()));
  v_outbox public.analysis_dispatch_outbox%rowtype;
  v_run public.analysis_runs%rowtype;
begin
  if length(p_provider_run_id) not between 1 and 200 then
    raise exception 'provider_run_id must contain 1-200 characters';
  end if;

  select *
  into v_outbox
  from public.analysis_dispatch_outbox
  where run_id = p_run_id
  for update;

  if not found then
    return jsonb_build_object('outcome', 'not_found');
  end if;
  if v_outbox.status = 'acknowledged' then
    select * into v_run from public.analysis_runs where id = p_run_id;
    if v_outbox.provider_run_id = p_provider_run_id then
      return jsonb_build_object(
        'outcome', 'replayed',
        'run', to_jsonb(v_run),
        'outbox', to_jsonb(v_outbox)
      );
    end if;
    return jsonb_build_object('outcome', 'lease_lost');
  end if;
  if v_outbox.status <> 'leased' or v_outbox.lease_token <> p_lease_token then
    return jsonb_build_object('outcome', 'lease_lost');
  end if;

  select *
  into v_run
  from public.analysis_runs
  where id = p_run_id
  for update;

  if not found then
    return jsonb_build_object('outcome', 'not_found');
  end if;
  if v_run.status <> 'queued' then
    return jsonb_build_object(
      'outcome', 'invalid_transition',
      'message', 'only queued runs can acknowledge dispatch'
    );
  end if;

  update public.analysis_runs
  set
    status = 'dispatched',
    provider_run_id = p_provider_run_id,
    error_code = null,
    error_message = null
  where id = p_run_id
  returning * into v_run;

  update public.analysis_dispatch_outbox
  set
    status = 'acknowledged',
    acknowledged_at = v_now,
    provider_run_id = p_provider_run_id,
    lease_owner = null,
    lease_token = null,
    lease_expires_at = null,
    last_error_code = null,
    last_error_message = null
  where run_id = p_run_id
  returning * into v_outbox;

  return jsonb_build_object(
    'outcome', 'acknowledged',
    'run', to_jsonb(v_run),
    'outbox', to_jsonb(v_outbox)
  );
end;
$$;

create or replace function public.control_confirm_dispatch_from_callback(
  p_run_id uuid,
  p_provider_run_id text,
  p_now timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_now timestamptz := coalesce(p_now, timezone('utc', now()));
  v_outbox public.analysis_dispatch_outbox%rowtype;
  v_run public.analysis_runs%rowtype;
begin
  if length(p_provider_run_id) not between 1 and 200 then
    raise exception 'provider_run_id must contain 1-200 characters';
  end if;

  select *
  into v_outbox
  from public.analysis_dispatch_outbox
  where run_id = p_run_id
  for update;

  if not found then
    return jsonb_build_object('outcome', 'not_found');
  end if;

  select *
  into v_run
  from public.analysis_runs
  where id = p_run_id
  for update;

  if not found then
    return jsonb_build_object('outcome', 'not_found');
  end if;

  if v_run.status = 'queued' then
    update public.analysis_runs
    set
      status = 'dispatched',
      provider_run_id = p_provider_run_id,
      error_code = null,
      error_message = null
    where id = p_run_id
    returning * into v_run;

    update public.analysis_dispatch_outbox
    set
      status = 'acknowledged',
      acknowledged_at = v_now,
      provider_run_id = p_provider_run_id,
      lease_owner = null,
      lease_token = null,
      lease_expires_at = null,
      last_error_code = null,
      last_error_message = null
    where run_id = p_run_id
    returning * into v_outbox;

    return jsonb_build_object(
      'outcome', 'acknowledged',
      'run', to_jsonb(v_run),
      'outbox', to_jsonb(v_outbox)
    );
  end if;

  if v_run.status in ('dispatched', 'running', 'validating') then
    if (
      v_run.provider_run_id = p_provider_run_id
      and v_outbox.status = 'acknowledged'
      and v_outbox.provider_run_id = p_provider_run_id
    ) then
      return jsonb_build_object(
        'outcome', 'replayed',
        'run', to_jsonb(v_run),
        'outbox', to_jsonb(v_outbox)
      );
    end if;
    return jsonb_build_object('outcome', 'provider_conflict');
  end if;

  return jsonb_build_object(
    'outcome', 'invalid_transition',
    'message', 'terminal runs cannot confirm callback dispatch'
  );
end;
$$;

create or replace function public.control_reschedule_analysis_dispatch(
  p_run_id uuid,
  p_lease_token uuid,
  p_error_code text,
  p_error_message text,
  p_base_delay_seconds integer,
  p_max_delay_seconds integer,
  p_now timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_now timestamptz := coalesce(p_now, timezone('utc', now()));
  v_delay_seconds integer;
  v_outbox public.analysis_dispatch_outbox%rowtype;
  v_run public.analysis_runs%rowtype;
begin
  if not (
    p_base_delay_seconds between 1 and 3600
    and p_max_delay_seconds between p_base_delay_seconds and 3600
  ) then
    raise exception 'dispatch retry delay bounds are invalid';
  end if;

  select *
  into v_outbox
  from public.analysis_dispatch_outbox
  where run_id = p_run_id
  for update;

  if not found then
    return jsonb_build_object('outcome', 'not_found');
  end if;
  if v_outbox.status <> 'leased' or v_outbox.lease_token <> p_lease_token then
    return jsonb_build_object('outcome', 'lease_lost');
  end if;

  select *
  into v_run
  from public.analysis_runs
  where id = p_run_id
  for update;

  if not found then
    return jsonb_build_object('outcome', 'not_found');
  end if;

  if v_outbox.attempt_count >= v_outbox.max_attempts then
    update public.analysis_dispatch_outbox
    set
      status = 'dead_letter',
      lease_owner = null,
      lease_token = null,
      lease_expires_at = null,
      last_error_code = left(p_error_code, 120),
      last_error_message = left(p_error_message, 1000)
    where run_id = p_run_id
    returning * into v_outbox;

    update public.analysis_runs
    set
      status = 'failed',
      error_code = 'worker_dispatch_retry_exhausted',
      error_message = left(p_error_message, 1000)
    where id = p_run_id
      and status = 'queued'
    returning * into v_run;

    return jsonb_build_object(
      'outcome', 'dead_letter',
      'run', to_jsonb(v_run),
      'outbox', to_jsonb(v_outbox)
    );
  end if;

  v_delay_seconds := least(
    p_max_delay_seconds,
    (p_base_delay_seconds * power(2::numeric, greatest(v_outbox.attempt_count - 1, 0)))::integer
  );

  update public.analysis_dispatch_outbox
  set
    status = 'pending',
    available_at = v_now + make_interval(secs => v_delay_seconds),
    lease_owner = null,
    lease_token = null,
    lease_expires_at = null,
    last_error_code = left(p_error_code, 120),
    last_error_message = left(p_error_message, 1000)
  where run_id = p_run_id
  returning * into v_outbox;

  return jsonb_build_object(
    'outcome', 'retry_scheduled',
    'run', to_jsonb(v_run),
    'outbox', to_jsonb(v_outbox)
  );
end;
$$;

create or replace function public.control_fail_analysis_run(
  p_run_id uuid,
  p_provider_run_id text,
  p_error_code text,
  p_error_message text,
  p_now timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_now timestamptz := coalesce(p_now, timezone('utc', now()));
  v_run public.analysis_runs%rowtype;
  v_outbox public.analysis_dispatch_outbox%rowtype;
begin
  if length(p_provider_run_id) not between 1 and 200 then
    raise exception 'provider_run_id must contain 1-200 characters';
  end if;
  if length(p_error_code) not between 1 and 120 then
    raise exception 'error_code must contain 1-120 characters';
  end if;
  if length(p_error_message) not between 1 and 1000 then
    raise exception 'error_message must contain 1-1000 characters';
  end if;

  select *
  into v_run
  from public.analysis_runs
  where id = p_run_id
  for update;

  if not found then
    return jsonb_build_object('outcome', 'not_found');
  end if;
  if v_run.status = 'failed' then
    if v_run.error_code = p_error_code and v_run.error_message = p_error_message then
      return jsonb_build_object('outcome', 'replayed', 'run', to_jsonb(v_run));
    end if;
    return jsonb_build_object(
      'outcome', 'invalid_transition',
      'message', 'failed run already has different terminal evidence'
    );
  end if;
  if v_run.status in ('published', 'cancelled') then
    return jsonb_build_object(
      'outcome', 'invalid_transition',
      'message', 'terminal analysis runs are immutable'
    );
  end if;

  update public.analysis_runs
  set
    status = 'failed',
    provider_run_id = coalesce(provider_run_id, p_provider_run_id),
    error_code = p_error_code,
    error_message = p_error_message
  where id = p_run_id
  returning * into v_run;

  select *
  into v_outbox
  from public.analysis_dispatch_outbox
  where run_id = p_run_id
  for update;

  if found and v_outbox.status in ('pending', 'leased') then
    update public.analysis_dispatch_outbox
    set
      status = 'acknowledged',
      acknowledged_at = v_now,
      provider_run_id = p_provider_run_id,
      lease_owner = null,
      lease_token = null,
      lease_expires_at = null,
      last_error_code = null,
      last_error_message = null
    where run_id = p_run_id;
  end if;

  return jsonb_build_object('outcome', 'failed', 'run', to_jsonb(v_run));
end;
$$;

create or replace function public.control_expire_stuck_analysis_runs(
  p_timeout_seconds integer,
  p_limit integer,
  p_now timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_now timestamptz := coalesce(p_now, timezone('utc', now()));
  v_run_id uuid;
  v_run public.analysis_runs%rowtype;
  v_expired jsonb := '[]'::jsonb;
begin
  if p_timeout_seconds not between 300 and 86400 then
    raise exception 'timeout_seconds must be between 300 and 86400';
  end if;
  if p_limit not between 1 and 100 then
    raise exception 'expiry limit must be between 1 and 100';
  end if;

  for v_run_id in
    select r.id
    from public.analysis_runs r
    join public.analysis_dispatch_outbox o on o.run_id = r.id
    where r.status in ('dispatched', 'running', 'validating')
      and o.status = 'acknowledged'
      and o.acknowledged_at <= v_now - make_interval(secs => p_timeout_seconds)
    order by o.acknowledged_at, r.id
    limit p_limit
    for update of r skip locked
  loop
    update public.analysis_runs
    set
      status = 'failed',
      error_code = 'worker_result_timeout',
      error_message = 'Worker did not publish a result or failure callback before the deadline'
    where id = v_run_id
      and status in ('dispatched', 'running', 'validating')
    returning * into v_run;

    if found then
      v_expired := v_expired || jsonb_build_array(to_jsonb(v_run));
    end if;
  end loop;

  return jsonb_build_object('outcome', 'expired', 'runs', v_expired);
end;
$$;

create or replace function public.control_update_analysis_run(
  p_run jsonb,
  p_expected_updated_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_id uuid := (p_run ->> 'id')::uuid;
  v_next_status text := p_run ->> 'status';
  v_current public.analysis_runs%rowtype;
  v_updated public.analysis_runs%rowtype;
  v_snapshot public.data_snapshots%rowtype;
  v_artifact public.analysis_artifacts%rowtype;
begin
  select *
  into v_current
  from public.analysis_runs
  where id = v_id
  for update;

  if not found then
    return jsonb_build_object('outcome', 'not_found');
  end if;
  if v_current.updated_at <> p_expected_updated_at then
    return jsonb_build_object('outcome', 'conflict', 'run', to_jsonb(v_current));
  end if;

  if (
    v_current.project_id <> p_run ->> 'project_id'
    or v_current.input_schema_version <> p_run ->> 'input_schema_version'
    or v_current.input_schema_hash <> p_run ->> 'input_schema_hash'
    or v_current.config_hash_algorithm <> p_run ->> 'config_hash_algorithm'
    or v_current.config_hash <> p_run ->> 'config_hash'
    or v_current.request_digest <> p_run ->> 'request_digest'
    or v_current.idempotency_key_digest <> p_run ->> 'idempotency_key_digest'
    or v_current.requested_inputs <> p_run -> 'requested_inputs'
    or v_current.normalized_inputs <> p_run -> 'normalized_inputs'
    or v_current.allow_fallback <> (p_run ->> 'allow_fallback')::boolean
    or v_current.provider <> p_run ->> 'provider'
  ) then
    return jsonb_build_object(
      'outcome', 'invalid_transition',
      'message', 'immutable run identity cannot change'
    );
  end if;

  if v_current.status in ('published', 'failed', 'cancelled') then
    return jsonb_build_object(
      'outcome', 'invalid_transition',
      'message', 'terminal analysis runs are immutable'
    );
  end if;

  if v_next_status <> v_current.status and not (
    (v_current.status = 'queued' and v_next_status in ('dispatched', 'failed', 'cancelled'))
    or (v_current.status = 'dispatched' and v_next_status in ('running', 'validating', 'failed', 'cancelled'))
    or (v_current.status = 'running' and v_next_status in ('validating', 'failed', 'cancelled'))
    or (v_current.status = 'validating' and v_next_status in ('published', 'failed', 'cancelled'))
  ) then
    return jsonb_build_object(
      'outcome', 'invalid_transition',
      'message', 'invalid analysis run state transition'
    );
  end if;

  update public.analysis_runs
  set
    status = v_next_status,
    effective_config_hash = p_run ->> 'effective_config_hash',
    effective_inputs = p_run -> 'effective_inputs',
    ignored_inputs = coalesce(p_run -> 'ignored_inputs', '[]'::jsonb),
    fallbacks = coalesce(p_run -> 'fallbacks', '[]'::jsonb),
    fallback_used = coalesce((p_run ->> 'fallback_used')::boolean, false),
    fallback_reason = nullif(p_run ->> 'fallback_reason', ''),
    provider_run_id = nullif(p_run ->> 'provider_run_id', ''),
    data_as_of = nullif(p_run ->> 'data_as_of', '')::date,
    calculated_at = nullif(p_run ->> 'calculated_at', '')::timestamptz,
    code_version = nullif(p_run ->> 'code_version', ''),
    error_code = nullif(p_run ->> 'error_code', ''),
    error_message = nullif(p_run ->> 'error_message', '')
  where id = v_id
  returning * into v_updated;

  if v_next_status = 'published' then
    if (
      jsonb_typeof(p_run -> 'artifact') is distinct from 'object'
      or jsonb_typeof(p_run -> 'snapshot') is distinct from 'object'
    ) then
      raise exception 'published run requires artifact and snapshot identities';
    end if;

    insert into public.data_snapshots (
      project_id,
      run_id,
      data_as_of,
      source,
      source_hash,
      artifact_url,
      artifact_sha256,
      byte_size,
      contract_version,
      summary,
      published
    )
    values (
      v_updated.project_id,
      v_updated.id,
      (p_run #>> '{snapshot,data_as_of}')::date,
      p_run #>> '{snapshot,source}',
      p_run #>> '{snapshot,source_hash}',
      p_run #>> '{artifact,url}',
      p_run #>> '{artifact,sha256}',
      (p_run #>> '{artifact,byte_size}')::bigint,
      p_run #>> '{artifact,contract_version}',
      coalesce(p_run #> '{snapshot,summary}', '{}'::jsonb),
      true
    )
    on conflict (run_id)
    do update set
      data_as_of = excluded.data_as_of,
      source = excluded.source,
      source_hash = excluded.source_hash,
      artifact_url = excluded.artifact_url,
      artifact_sha256 = excluded.artifact_sha256,
      byte_size = excluded.byte_size,
      contract_version = excluded.contract_version,
      summary = excluded.summary,
      published = true
    returning * into v_snapshot;

    insert into public.analysis_artifacts (
      run_id,
      snapshot_id,
      url,
      sha256,
      byte_size,
      contract_version,
      published
    )
    values (
      v_updated.id,
      v_snapshot.id,
      p_run #>> '{artifact,url}',
      p_run #>> '{artifact,sha256}',
      (p_run #>> '{artifact,byte_size}')::bigint,
      p_run #>> '{artifact,contract_version}',
      true
    )
    on conflict (run_id)
    do update set
      snapshot_id = excluded.snapshot_id,
      url = excluded.url,
      sha256 = excluded.sha256,
      byte_size = excluded.byte_size,
      contract_version = excluded.contract_version,
      published = true
    returning * into v_artifact;
  end if;

  return jsonb_build_object(
    'outcome', 'updated',
    'run', to_jsonb(v_updated),
    'snapshot', case when v_next_status = 'published' then to_jsonb(v_snapshot) else null end,
    'artifact', case when v_next_status = 'published' then to_jsonb(v_artifact) else null end
  );
end;
$$;

revoke all on function public.control_create_or_replay_analysis_run(jsonb) from public;
revoke all on function public.control_create_or_replay_analysis_run(jsonb) from anon, authenticated;
grant execute on function public.control_create_or_replay_analysis_run(jsonb) to service_role;

revoke all on function public.control_claim_analysis_dispatch(uuid, text, integer, timestamptz) from public;
revoke all on function public.control_claim_analysis_dispatch(uuid, text, integer, timestamptz)
  from anon, authenticated;
grant execute on function public.control_claim_analysis_dispatch(uuid, text, integer, timestamptz)
  to service_role;

revoke all on function public.control_ack_analysis_dispatch(uuid, uuid, text, timestamptz) from public;
revoke all on function public.control_ack_analysis_dispatch(uuid, uuid, text, timestamptz)
  from anon, authenticated;
grant execute on function public.control_ack_analysis_dispatch(uuid, uuid, text, timestamptz)
  to service_role;

revoke all on function public.control_confirm_dispatch_from_callback(uuid, text, timestamptz)
  from public;
revoke all on function public.control_confirm_dispatch_from_callback(uuid, text, timestamptz)
  from anon, authenticated;
grant execute on function public.control_confirm_dispatch_from_callback(uuid, text, timestamptz)
  to service_role;

revoke all on function public.control_reschedule_analysis_dispatch(
  uuid, uuid, text, text, integer, integer, timestamptz
) from public;
revoke all on function public.control_reschedule_analysis_dispatch(
  uuid, uuid, text, text, integer, integer, timestamptz
) from anon, authenticated;
grant execute on function public.control_reschedule_analysis_dispatch(
  uuid, uuid, text, text, integer, integer, timestamptz
) to service_role;

revoke all on function public.control_fail_analysis_run(uuid, text, text, text, timestamptz)
  from public;
revoke all on function public.control_fail_analysis_run(uuid, text, text, text, timestamptz)
  from anon, authenticated;
grant execute on function public.control_fail_analysis_run(uuid, text, text, text, timestamptz)
  to service_role;

revoke all on function public.control_expire_stuck_analysis_runs(integer, integer, timestamptz)
  from public;
revoke all on function public.control_expire_stuck_analysis_runs(integer, integer, timestamptz)
  from anon, authenticated;
grant execute on function public.control_expire_stuck_analysis_runs(integer, integer, timestamptz)
  to service_role;

revoke all on function public.control_update_analysis_run(jsonb, timestamptz) from public;
revoke all on function public.control_update_analysis_run(jsonb, timestamptz) from anon, authenticated;
grant execute on function public.control_update_analysis_run(jsonb, timestamptz) to service_role;

alter table public.projects enable row level security;
alter table public.projects force row level security;
alter table public.analysis_configs enable row level security;
alter table public.analysis_configs force row level security;
alter table public.analysis_runs enable row level security;
alter table public.analysis_runs force row level security;
alter table public.analysis_dispatch_outbox enable row level security;
alter table public.analysis_dispatch_outbox force row level security;
alter table public.data_snapshots enable row level security;
alter table public.data_snapshots force row level security;
alter table public.analysis_artifacts enable row level security;
alter table public.analysis_artifacts force row level security;

create policy projects_public_read_active
on public.projects for select
to anon, authenticated
using (active);

create policy data_snapshots_public_read_published
on public.data_snapshots for select
to anon, authenticated
using (published);

create policy analysis_artifacts_public_read_published
on public.analysis_artifacts for select
to anon, authenticated
using (published);

-- No client write policy exists. The server-only service role performs
-- bounded control-plane operations and Supabase never receives provider
-- credentials.
revoke all on public.analysis_configs from anon, authenticated;
revoke all on public.analysis_runs from anon, authenticated;
revoke all on public.analysis_dispatch_outbox from anon, authenticated;
grant usage on schema public to service_role;
grant select on public.analysis_runs to service_role;
grant select on public.analysis_dispatch_outbox to service_role;
grant select on public.data_snapshots to service_role;
grant select on public.analysis_artifacts to service_role;
grant select on public.projects to anon, authenticated;
grant select on public.data_snapshots to anon, authenticated;
grant select on public.analysis_artifacts to anon, authenticated;

create or replace view public.public_project_capabilities
with (security_barrier = true)
as
select id as project_id, display_name, input_schema_version, capability, updated_at
from public.projects
where active;

create or replace view public.published_project_snapshots
with (security_barrier = true)
as
select
  id,
  project_id,
  run_id,
  data_as_of,
  source,
  source_hash,
  artifact_url,
  artifact_sha256,
  byte_size,
  contract_version,
  summary,
  created_at
from public.data_snapshots
where published;

create or replace view public.published_analysis_results
with (security_barrier = true)
as
select
  r.id as run_id,
  r.project_id,
  r.input_schema_version,
  r.input_schema_hash,
  r.config_hash_algorithm,
  r.config_hash,
  r.effective_config_hash,
  r.effective_inputs,
  r.fallbacks,
  r.data_as_of,
  r.calculated_at,
  r.code_version,
  a.url as artifact_url,
  a.sha256 as artifact_sha256,
  a.byte_size,
  a.contract_version,
  r.updated_at as published_at
from public.analysis_runs r
join public.analysis_artifacts a on a.run_id = r.id
where r.status = 'published' and a.published;

-- These deliberately narrow, owner-defined views are the only public surface
-- over the private analysis_runs/configs tables.
revoke all on public.public_project_capabilities from public;
revoke all on public.published_project_snapshots from public;
revoke all on public.published_analysis_results from public;
grant select on public.public_project_capabilities to anon, authenticated;
grant select on public.published_project_snapshots to anon, authenticated;
grant select on public.published_analysis_results to anon, authenticated;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  (
    'quant-public-snapshots',
    'quant-public-snapshots',
    true,
    15728640,
    array['application/json']
  ),
  (
    'quant-run-artifacts',
    'quant-run-artifacts',
    false,
    52428800,
    array['application/json', 'text/csv', 'text/markdown', 'text/html', 'application/zip']
  )
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create policy quant_public_snapshots_read
on storage.objects for select
to anon, authenticated
using (bucket_id = 'quant-public-snapshots');

commit;
