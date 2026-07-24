from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from quant_control_api.app import create_app
from quant_control_api.artifacts import (
    ArtifactIdentity,
    ArtifactVerificationError,
    HttpArtifactFetcher,
    MappingArtifactFetcher,
)
from quant_control_api.best_factor import DEFAULT_CONFIG
from quant_control_api.dual_write import (
    SupabaseDualWritePublisher,
    SupabaseProjectMetadataPublisher,
)
from quant_control_api.models import RunCreateRequest
from quant_control_api.providers.fake import FakeWorkerProvider
from quant_control_api.service import ControlPlaneService
from quant_control_api.settings import Settings
from quant_control_api.store import InMemoryRunStore
from quant_control_api.supabase_auth import supabase_admin_headers
from quant_control_api.supabase_store import SupabaseRunStore


def test_production_rejects_volatile_run_store() -> None:
    settings = Settings(
        environment="production",
        store_backend="supabase",
        supabase_url="https://project.supabase.co",
        supabase_service_role_key="service-role",
    )
    with pytest.raises(ValueError, match="development-only InMemoryRunStore"):
        create_app(
            settings=settings,
            provider=FakeWorkerProvider(),
            store=InMemoryRunStore(),
        )


def test_production_requires_supabase_store_configuration() -> None:
    with pytest.raises(ValueError, match="QUANT_CONTROL_STORE=supabase"):
        Settings(environment="production").validate()
    with pytest.raises(ValueError, match="SUPABASE_URL"):
        Settings(environment="production", store_backend="supabase").validate()


def test_environment_and_live_provider_configuration_fail_closed() -> None:
    with pytest.raises(ValueError, match="QUANT_CONTROL_ENV"):
        Settings(environment="prodution").validate()

    live_provider = {
        "provider": "github-actions",
        "github_enabled": True,
        "github_token": "github",
        "run_api_token": "owner",
        "worker_callback_token": "worker",
    }
    with pytest.raises(ValueError, match="durable"):
        Settings(**live_provider).validate()
    with pytest.raises(ValueError, match="DISPATCH_PUMP_ENABLED"):
        Settings(
            **live_provider,
            store_backend="supabase",
            supabase_url="https://project.supabase.co",
            supabase_service_role_key="service-role",
        ).validate()


def test_default_result_timeout_covers_momentum_worker_window() -> None:
    assert Settings().worker_result_timeout_seconds == 4 * 60 * 60


def test_supabase_headers_support_new_secret_and_legacy_service_role_keys() -> None:
    secret_headers = supabase_admin_headers("sb_secret_server-only")
    assert secret_headers["apikey"] == "sb_secret_server-only"
    assert "Authorization" not in secret_headers

    legacy_headers = supabase_admin_headers("legacy-service-role-jwt")
    assert legacy_headers["apikey"] == "legacy-service-role-jwt"
    assert legacy_headers["Authorization"] == "Bearer legacy-service-role-jwt"

    with pytest.raises(ValueError, match="publishable"):
        supabase_admin_headers("sb_publishable_public")


def test_supabase_env_prefers_one_server_key_without_ambiguity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUANT_CONTROL_SUPABASE_SECRET_KEY", "sb_secret_new")
    monkeypatch.delenv(
        "QUANT_CONTROL_SUPABASE_SERVICE_ROLE_KEY",
        raising=False,
    )
    assert Settings.from_env().supabase_service_role_key == "sb_secret_new"

    monkeypatch.setenv(
        "QUANT_CONTROL_SUPABASE_SERVICE_ROLE_KEY",
        "different-legacy-key",
    )
    with pytest.raises(ValueError, match="Set only"):
        Settings.from_env()


def test_github_settings_require_both_owner_and_worker_tokens() -> None:
    settings = Settings(
        provider="github-actions",
        github_enabled=True,
        github_token="github",
    )
    with pytest.raises(ValueError, match="RUN_API_TOKEN"):
        settings.validate()
    settings = Settings(
        provider="github-actions",
        github_enabled=True,
        github_token="github",
        run_api_token="owner",
    )
    with pytest.raises(ValueError, match="WORKER_CALLBACK_TOKEN"):
        settings.validate()


def test_artifact_fetcher_rejects_non_allowlisted_url_before_network() -> None:
    async def scenario() -> None:
        fetcher = HttpArtifactFetcher(
            client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
        )
        artifact = ArtifactIdentity(
            url="https://attacker.example/result.json",
            sha256="0" * 64,
            byte_size=2,
            contract_version="best-factor/latest-results/v1",
        )
        with pytest.raises(ArtifactVerificationError, match="host"):
            await fetcher.fetch(artifact)
        await fetcher._client.aclose()  # injected client ownership remains with the test

    asyncio.run(scenario())


def test_artifact_fetcher_rejects_malformed_content_length() -> None:
    async def scenario() -> None:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    headers={"Content-Length": "not-a-number"},
                    content=b"{}",
                )
            )
        )
        fetcher = HttpArtifactFetcher(client=client)
        artifact = ArtifactIdentity(
            url=(
                "https://raw.githubusercontent.com/SonChangGi/best-factor/"
                "0123456789abcdef0123456789abcdef01234567/docs/data/latest-results.json"
            ),
            sha256="0" * 64,
            byte_size=2,
            contract_version="best-factor/latest-results/v1",
        )
        with pytest.raises(ArtifactVerificationError, match="malformed"):
            await fetcher.fetch(artifact)
        await client.aclose()

    asyncio.run(scenario())


def test_mutable_pages_latest_url_is_never_a_control_artifact() -> None:
    async def scenario() -> None:
        fetcher = HttpArtifactFetcher(
            client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
        )
        artifact = ArtifactIdentity(
            url="https://sonchanggi.github.io/best-factor/data/latest-results.json",
            sha256="0" * 64,
            byte_size=2,
            contract_version="best-factor/latest-results/v1",
        )
        with pytest.raises(ArtifactVerificationError, match="host"):
            await fetcher.fetch(artifact)
        await fetcher._client.aclose()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("url", "message"),
    [
        (
            (
                "https://raw.githubusercontent.com/SonChangGi/best-factor/"
                "0123456789abcdef0123456789abcdef01234567/docs/data/latest-results.json?raw=1"
            ),
            "query or fragment",
        ),
        (
            (
                "https://user@raw.githubusercontent.com/SonChangGi/best-factor/"
                "0123456789abcdef0123456789abcdef01234567/docs/data/latest-results.json"
            ),
            "user information",
        ),
    ],
)
def test_artifact_fetcher_rejects_ambiguous_immutable_urls(url: str, message: str) -> None:
    async def scenario() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
        fetcher = HttpArtifactFetcher(client=client)
        artifact = ArtifactIdentity(
            url=url,
            sha256="0" * 64,
            byte_size=2,
            contract_version="best-factor/latest-results/v1",
        )
        with pytest.raises(ArtifactVerificationError, match=message):
            await fetcher.fetch(artifact)
        await client.aclose()

    asyncio.run(scenario())


def test_supabase_dual_write_is_queued_and_stores_bounded_identity_only() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, request=request)

    async def scenario() -> None:
        client = httpx.AsyncClient(
            base_url="https://project.supabase.co/rest/v1",
            transport=httpx.MockTransport(handler),
        )
        publisher = SupabaseDualWritePublisher(
            url="https://unused.supabase.co",
            service_role_key="server-only",
            client=client,
        )
        service = ControlPlaneService(
            provider=FakeWorkerProvider(),
            store=InMemoryRunStore(),
            publisher=publisher,
            artifact_fetcher=MappingArtifactFetcher(),
        )
        service.capabilities("best-factor")
        created = await service.create_run(
            "best-factor",
            RunCreateRequest(
                input_schema_version="best-factor/v1",
                inputs=DEFAULT_CONFIG,
                allow_fallback=False,
            ),
            "dual-write-test-001",
        )
        await service.get_status(created.run_id)
        await publisher.close()
        await client.aclose()

    asyncio.run(scenario())
    paths = [request.url.path for request in requests]
    assert any(path.endswith("/projects") for path in paths)
    assert any(path.endswith("/analysis_configs") for path in paths)
    assert any(path.endswith("/analysis_runs") for path in paths)
    assert any(path.endswith("/data_snapshots") for path in paths)
    assert any(path.endswith("/analysis_artifacts") for path in paths)
    snapshot_requests = [request for request in requests if request.url.path.endswith("/data_snapshots")]
    assert snapshot_requests
    snapshot_body = json.loads(snapshot_requests[-1].content)
    assert "payload" not in snapshot_body
    assert set(snapshot_body["summary"]) == {
        "schema_version",
        "generated_at",
        "summary",
    }
    assert set(snapshot_body["summary"]["summary"]) >= {
        "data_end_date",
        "source_hash",
    }


def test_authoritative_store_project_publisher_never_writes_run_state() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, request=request)

    async def scenario() -> None:
        client = httpx.AsyncClient(
            base_url="https://project.supabase.co/rest/v1",
            transport=httpx.MockTransport(handler),
        )
        publisher = SupabaseProjectMetadataPublisher(
            url="https://unused.supabase.co",
            service_role_key="server-only",
            client=client,
        )
        service = ControlPlaneService(
            provider=FakeWorkerProvider(auto_complete=False),
            store=InMemoryRunStore(),
            publisher=publisher,
            artifact_fetcher=MappingArtifactFetcher(),
        )
        capability = service.capabilities("momentum")
        assert capability.project_name == "Momentum Factor Lab"
        await service.create_run(
            "best-factor",
            RunCreateRequest(
                input_schema_version="best-factor/v1",
                inputs=DEFAULT_CONFIG,
                allow_fallback=False,
            ),
            "project-only-writer-001",
        )
        await publisher.close()
        await client.aclose()

    asyncio.run(scenario())
    assert requests
    assert {request.url.path.rsplit("/", 1)[-1] for request in requests} == {
        "projects"
    }
    project_payloads = [json.loads(request.content) for request in requests]
    momentum = next(payload for payload in project_payloads if payload["id"] == "momentum")
    assert momentum["display_name"] == "Momentum Factor Lab"
    assert momentum["capability"]["projectId"] == "momentum"


def test_supabase_migration_has_private_bounded_control_tables() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "infra"
        / "supabase"
        / "migrations"
        / "202607240001_quant_control_plane.sql"
    ).read_text(encoding="utf-8")
    for table in (
        "projects",
        "analysis_configs",
        "analysis_runs",
        "analysis_dispatch_outbox",
        "data_snapshots",
        "analysis_artifacts",
    ):
        assert f"create table public.{table}" in migration
        assert f"alter table public.{table} enable row level security" in migration
    assert "published_analysis_results" in migration
    assert "quant-public-snapshots" in migration
    assert "quant-run-artifacts" in migration
    assert "byte_size between 0 and 15728640" in migration
    assert "payload jsonb" not in migration
    assert "No client write policy exists" in migration
    assert "terminal analysis runs are immutable" in migration
    assert "control_confirm_dispatch_from_callback" in migration
    assert "r.status in ('dispatched', 'running', 'validating')" in migration
    assert "project_id = 'best-factor'" in migration
    assert "code_version ~ '^[0-9a-f]{40}$'" in migration
    assert "project_id = 'momentum'" in migration
    assert (
        "code_version ~ '^github:SonChangGi/momentum-factor-lab@[0-9a-f]{40}$'"
        in migration
    )
    assert "coalesce(nullif(p_run ->> 'project_display_name', ''), v_project_id)" in migration
    assert "analysis config identity conflict" in migration
    assert "on conflict (project_id, input_schema_version, config_hash)\n  do nothing" in migration
    assert "do update set\n    input_schema_hash = excluded.input_schema_hash" not in migration
    assert "new analysis runs must start in queued state" in migration
    assert "grant select on public.analysis_runs to service_role" in migration


def test_health_readiness_and_container_operability_contract() -> None:
    development = create_app(
        settings=Settings(),
        provider=FakeWorkerProvider(auto_complete=False),
        store=InMemoryRunStore(),
        artifact_fetcher=MappingArtifactFetcher(),
    )
    with TestClient(development) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/readyz").json() == {"status": "ready"}

    dependency_client = httpx.AsyncClient(
        base_url="https://project.supabase.co/rest/v1",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                503,
                json={"message": "unavailable"},
                request=request,
            )
        ),
    )
    durable_store = SupabaseRunStore(
        url="https://project.supabase.co",
        service_role_key="service-role",
        client=dependency_client,
    )
    production_settings = Settings(
        environment="production",
        provider="github-actions",
        store_backend="supabase",
        github_enabled=True,
        github_token="github",
        run_api_token="owner",
        worker_callback_token="worker",
        supabase_url="https://project.supabase.co",
        supabase_service_role_key="service-role",
        dispatch_pump_enabled=True,
    )
    production = create_app(
        settings=production_settings,
        provider=FakeWorkerProvider(auto_complete=False),
        store=durable_store,
        artifact_fetcher=MappingArtifactFetcher(),
    )
    with TestClient(production) as client:
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json()["reason"] == "dependency_unavailable"
    asyncio.run(dependency_client.aclose())

    dockerfile = Path(__file__).resolve().parents[1] / "Dockerfile"
    contents = dockerfile.read_text(encoding="utf-8")
    assert contents.startswith("FROM python:3.11.15-slim-bookworm")
    assert "COPY pyproject.toml uv.lock README.md ./" in contents
    assert "uv sync --locked --no-dev --no-editable --no-cache" in contents
    assert "USER quant-control" in contents
    assert "0.0.0.0" in contents
