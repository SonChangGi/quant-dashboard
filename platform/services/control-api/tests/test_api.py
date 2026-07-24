from __future__ import annotations

from fastapi.testclient import TestClient

from quant_control_api.app import create_app
from quant_control_api.artifacts import MappingArtifactFetcher
from quant_control_api.dual_write import NullDualWritePublisher
from quant_control_api.providers.fake import FakeWorkerProvider
from quant_control_api.settings import Settings
from quant_control_api.store import InMemoryRunStore


def make_client(
    provider: FakeWorkerProvider | None = None,
    *,
    settings: Settings | None = None,
    fetcher: MappingArtifactFetcher | None = None,
) -> tuple[TestClient, FakeWorkerProvider]:
    worker = provider or FakeWorkerProvider()
    application = create_app(
        settings=settings or Settings(),
        provider=worker,
        store=InMemoryRunStore(),
        publisher=NullDualWritePublisher(),
        artifact_fetcher=fetcher or MappingArtifactFetcher(),
    )
    return TestClient(application), worker


def test_capabilities_expose_server_authority_and_static_fallback() -> None:
    client, _ = make_client()
    with client:
        response = client.get("/v1/projects/best-factor/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["projectId"] == "best-factor"
    assert payload["inputSchemaVersion"] == "best-factor/v1"
    assert len(payload["inputSchemaHash"]) == 64
    assert payload["configHashAlgorithm"] == "best-factor-python-json-v1"
    assert payload["defaultConfigHash"] == "082b5dbbe2c6cdf08d669733f9eacbc1518b0c88693d091f27574c8bc2f50750"
    assert payload["acceptsRuns"] is True
    assert payload["provider"]["executesHeavyAnalysisInApi"] is False
    assert payload["fallback"]["analysisRunAllowFallback"] is False
    assert payload["fallback"]["scheduledOwnerOperationMayFallback"] is True
    assert payload["staticFallbackUrl"].endswith("/best-factor/data/latest-results.json")
    assert len(payload["inputs"]) == 11
    assert all(field["required"] is True for field in payload["inputs"])


def test_create_status_and_result_are_fully_bound(
    submission: dict[str, object],
    idempotency_headers: dict[str, str],
) -> None:
    client, _ = make_client()
    with client:
        created = client.post(
            "/v1/projects/best-factor/runs",
            headers=idempotency_headers,
            json=submission,
        )
        assert created.status_code == 202
        queued = created.json()
        assert queued["status"] == "dispatched"
        assert queued["fallbackUsed"] is False
        assert queued["fallbacks"] == []
        assert queued["ignoredInputs"] == []
        assert queued["configHash"] == queued["effectiveConfigHash"]
        assert queued["requestedInputs"] == queued["normalizedInputs"] == queued["effectiveInputs"]
        assert "errorCode" not in queued
        assert "dataAsOf" not in queued

        status = client.get(f"/v1/runs/{queued['runId']}")
        assert status.status_code == 200
        published = status.json()
        assert published["status"] == "published"
        assert published["dataAsOf"] == "2026-07-23"
        assert published["codeVersion"] == "d" * 40
        assert len(published["artifact"]["sha256"]) == 64

        result = client.get(f"/v1/runs/{queued['runId']}/result")
        assert result.status_code == 200
        envelope = result.json()
        assert envelope["status"] == "published"
        for field in (
            "projectId",
            "runId",
            "inputSchemaVersion",
            "inputSchemaHash",
            "configHashAlgorithm",
            "configHash",
            "effectiveConfigHash",
            "requestedInputs",
            "normalizedInputs",
            "effectiveInputs",
            "artifact",
        ):
            assert envelope[field] == published[field]


def test_idempotency_replays_same_request_and_rejects_collision(
    submission: dict[str, object],
    idempotency_headers: dict[str, str],
) -> None:
    client, _ = make_client(FakeWorkerProvider(auto_complete=False))
    with client:
        first = client.post(
            "/v1/projects/best-factor/runs",
            headers=idempotency_headers,
            json=submission,
        )
        second = client.post(
            "/v1/projects/best-factor/runs",
            headers=idempotency_headers,
            json=submission,
        )
        assert first.status_code == second.status_code == 202
        assert first.json()["runId"] == second.json()["runId"]
        assert second.json()["replayed"] is True

        changed = dict(submission)
        changed["inputs"] = {**submission["inputs"], "top_n": 21}  # type: ignore[dict-item]
        conflict = client.post(
            "/v1/projects/best-factor/runs",
            headers=idempotency_headers,
            json=changed,
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "idempotency_conflict"


def test_request_validation_and_owner_auth(
    submission: dict[str, object],
    idempotency_headers: dict[str, str],
) -> None:
    settings = Settings(run_api_token="owner-secret")
    client, _ = make_client(settings=settings)
    with client:
        unauthorized = client.post(
            "/v1/projects/best-factor/runs",
            headers=idempotency_headers,
            json=submission,
        )
        assert unauthorized.status_code == 401
        accepted = client.post(
            "/v1/projects/best-factor/runs",
            headers={**idempotency_headers, "Authorization": "Bearer owner-secret"},
            json=submission,
        )
        assert accepted.status_code == 202

    public_client, _ = make_client()
    with public_client:
        assert (
            public_client.post(
                "/v1/projects/best-factor/runs",
                json=submission,
            ).status_code
            == 422
        )


def test_schema_unknown_input_and_fallback_rejections(
    submission: dict[str, object],
    idempotency_headers: dict[str, str],
) -> None:
    client, _ = make_client()
    with client:
        mismatched = {**submission, "inputSchemaVersion": "best-factor/v2"}
        assert (
            client.post(
                "/v1/projects/best-factor/runs",
                headers=idempotency_headers,
                json=mismatched,
            ).status_code
            == 422
        )

        invalid = {
            **submission,
            "inputs": {**submission["inputs"], "mystery": 1},  # type: ignore[dict-item]
        }
        response = client.post(
            "/v1/projects/best-factor/runs",
            headers={**idempotency_headers, "Idempotency-Key": "test-request-0002"},
            json=invalid,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_analysis_inputs"

        fallback = {**submission, "allowFallback": True}
        response = client.post(
            "/v1/projects/best-factor/runs",
            headers={**idempotency_headers, "Idempotency-Key": "test-request-0003"},
            json=fallback,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "fallback_not_supported_for_controlled_runs"


def test_result_is_unavailable_before_publication(
    submission: dict[str, object],
    idempotency_headers: dict[str, str],
) -> None:
    client, _ = make_client(FakeWorkerProvider(auto_complete=False))
    with client:
        created = client.post(
            "/v1/projects/best-factor/runs",
            headers=idempotency_headers,
            json=submission,
        ).json()
        response = client.get(f"/v1/runs/{created['runId']}/result")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "result_not_published"


def test_unknown_project_and_run_are_404() -> None:
    client, _ = make_client()
    with client:
        project = client.get("/v1/projects/not-real/capabilities")
        run = client.get("/v1/runs/00000000-0000-0000-0000-000000000000")
    assert project.status_code == 404
    assert run.status_code == 404
