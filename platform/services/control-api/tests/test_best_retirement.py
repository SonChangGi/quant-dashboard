from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from quant_control_api.adapters import default_project_adapters
from quant_control_api.adapters.fear_greed import DEFAULT_INPUTS as FEAR_INPUTS
from quant_control_api.adapters.momentum import DEFAULT_INPUTS as FACTOR_INPUTS
from quant_control_api.app import _providers_from_settings, create_app
from quant_control_api.artifacts import ArtifactVerificationError, HttpArtifactFetcher, MappingArtifactFetcher
from quant_control_api.dual_write import NullDualWritePublisher
from quant_control_api.models import ArtifactIdentity, RunStatus
from quant_control_api.providers.fake import FakeWorkerProvider
from quant_control_api.service import ControlPlaneService
from quant_control_api.settings import Settings
from quant_control_api.store import InMemoryRunStore, RunRecord


class TrackedWorker(FakeWorkerProvider):
    def __init__(self):
        super().__init__(auto_complete=False)
        self.readiness_calls = 0

    async def check_ready(self):
        self.readiness_calls += 1


@pytest.mark.parametrize("integrated_url", ["", "http://127.0.0.1:8765"])
def test_retired_project_is_always_gone_and_never_changes_active_readiness_or_dispatch(integrated_url):
    factor, fear = TrackedWorker(), TrackedWorker()
    app = create_app(
        settings=Settings(integrated_engine_url=integrated_url, run_api_token="owner"),
        providers={"momentum": factor, "fear-greed": fear},
        store=InMemoryRunStore(),
        publisher=NullDualWritePublisher(),
        artifact_fetcher=MappingArtifactFetcher(),
    )
    with TestClient(app) as client:
        assert client.get("/readyz").status_code == 200
        assert factor.readiness_calls == fear.readiness_calls == 1
        assert client.get("/v1/projects/best-factor/capabilities").status_code == 410
        for body in (None, {}, {"inputSchemaVersion": "best-factor/v1", "inputs": {}}, {"unexpected": "legacy"}):
            response = client.post("/v1/projects/best-factor/runs", json=body)
            assert response.status_code == 410 and response.json()["error"]["code"] == "project_retired"
        assert factor.dispatched == fear.dispatched == {}
        for project, schema, inputs, worker in [
            ("momentum", "momentum/v3", FACTOR_INPUTS, factor),
            ("fear-greed", "fear-greed/control-inputs-v1", FEAR_INPUTS, fear),
        ]:
            assert client.get(f"/v1/projects/{project}/capabilities").status_code == 200
            response = client.post(
                f"/v1/projects/{project}/runs",
                headers={"Authorization": "Bearer owner", "Idempotency-Key": f"retirement-{project}"},
                json={"inputSchemaVersion": schema, "inputs": inputs, "allowFallback": False},
            )
            assert response.status_code == 202
            assert len(worker.dispatched) == 1


def test_removed_best_environment_does_not_create_a_provider_or_readiness_dependency(monkeypatch):
    monkeypatch.setenv("QUANT_CONTROL_GITHUB_REPO", "best-factor")
    monkeypatch.setenv("QUANT_CONTROL_GITHUB_WORKFLOW", "retired.yml")
    settings = Settings.from_env()
    assert not hasattr(settings, "github_repo")
    providers = _providers_from_settings(
        Settings(provider="github-actions", github_enabled=True, github_token="secret"), default_project_adapters()
    )
    assert set(providers) == {"momentum", "fear-greed"}
    assert {provider.repo for provider in providers.values()} == {"factor", "fearNgreed"}

    async def close():
        for provider in providers.values():
            await provider.close()

    asyncio.run(close())


def test_retired_artifact_is_rejected_before_network():
    calls = []

    async def scenario():
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(200))
        )
        fetcher = HttpArtifactFetcher(client=client)
        artifact = ArtifactIdentity(
            url=f"https://raw.githubusercontent.com/SonChangGi/best-factor/{'a' * 40}/docs/data/latest-results.json",
            sha256="a" * 64,
            byte_size=2,
            contract_version="best-factor/latest-results/v1",
        )
        with pytest.raises(ArtifactVerificationError, match="allowlisted"):
            await fetcher.fetch(artifact)
        await client.aclose()

    asyncio.run(scenario())
    assert calls == []


def test_pre_retirement_pending_outbox_cannot_dispatch_to_any_worker():
    async def scenario():
        now = datetime.now(UTC)
        record = RunRecord(
            project_id="best-factor",
            run_id="retired-pending-001",
            status=RunStatus.QUEUED,
            input_schema_version="best-factor/v1",
            input_schema_hash="a" * 64,
            config_hash_algorithm="legacy",
            config_hash="b" * 64,
            effective_config_hash="b" * 64,
            requested_inputs={},
            normalized_inputs={},
            effective_inputs={},
            ignored_inputs=[],
            allow_fallback=False,
            provider="fake",
            idempotency_key_digest="c" * 64,
            request_digest="d" * 64,
            created_at=now,
            updated_at=now,
        )
        store = InMemoryRunStore()
        await store.create_or_replay(record)
        worker = TrackedWorker()
        control = ControlPlaneService(
            provider=worker, store=store, publisher=NullDualWritePublisher(), artifact_fetcher=MappingArtifactFetcher()
        )
        result = await control.dispatch_pending_once()
        assert result.status == RunStatus.FAILED and result.error_code == "project_retired"
        assert worker.dispatched == {}
        assert await control.dispatch_pending_once() is None

    asyncio.run(scenario())


def test_retired_adapter_cannot_be_reintroduced_and_schema_exposes_only_active_projects():
    from types import SimpleNamespace

    from quant_control_api.adapters import ProjectAdapterRegistry
    from quant_control_api.models import RunCreateRequest

    with pytest.raises(ValueError, match="retired"):
        ProjectAdapterRegistry([SimpleNamespace(project_id="best-factor")])
    assert RunCreateRequest.model_json_schema()["properties"]["inputSchemaVersion"]["enum"] == [
        "momentum/v3",
        "fear-greed/control-inputs-v1",
    ]
