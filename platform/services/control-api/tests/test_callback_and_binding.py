from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient

from quant_control_api.app import create_app
from quant_control_api.artifacts import MappingArtifactFetcher
from quant_control_api.best_factor import canonical_json_bytes
from quant_control_api.dual_write import NullDualWritePublisher
from quant_control_api.models import FallbackEvent
from quant_control_api.providers.base import ProviderObservation
from quant_control_api.providers.fake import FakeWorkerProvider
from quant_control_api.settings import Settings
from quant_control_api.store import InMemoryRunStore


def callback_client() -> tuple[TestClient, FakeWorkerProvider, MappingArtifactFetcher]:
    worker = FakeWorkerProvider(auto_complete=False)
    fetcher = MappingArtifactFetcher()
    app = create_app(
        settings=Settings(worker_callback_token="worker-secret"),
        provider=worker,
        store=InMemoryRunStore(),
        publisher=NullDualWritePublisher(),
        artifact_fetcher=fetcher,
    )
    return TestClient(app), worker, fetcher


def create_manifest(
    client: TestClient,
    worker: FakeWorkerProvider,
    submission: dict[str, object],
) -> tuple[dict[str, object], object, str]:
    created = client.post(
        "/v1/projects/best-factor/runs",
        headers={"Idempotency-Key": "callback-test-001"},
        json=submission,
    ).json()
    provider_run_id = created["providerRunId"]
    envelope = worker.dispatched[provider_run_id]
    manifest = worker.make_manifest(envelope)
    return created, manifest, provider_run_id


def test_authenticated_callback_fetches_exact_bytes_and_publishes(
    submission: dict[str, object],
) -> None:
    client, worker, fetcher = callback_client()
    with client:
        created, manifest, _ = create_manifest(client, worker, submission)
        exact_bytes = json.dumps(
            manifest.payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        ).encode("utf-8")
        artifact = manifest.artifact.model_copy(
            update={
                "sha256": hashlib.sha256(exact_bytes).hexdigest(),
                "byte_size": len(exact_bytes),
            }
        )
        manifest = manifest.model_copy(update={"artifact": artifact})
        fetcher.artifacts[str(artifact.url)] = exact_bytes

        unauthorized = client.post(
            f"/v1/internal/runs/{created['runId']}/result-manifest",
            json=manifest.model_dump(mode="json", by_alias=True),
        )
        assert unauthorized.status_code == 401

        callback = client.post(
            f"/v1/internal/runs/{created['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
        assert callback.status_code == 200
        assert callback.json()["status"] == "published"

        replay = client.post(
            f"/v1/internal/runs/{created['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
        assert replay.status_code == 200
        assert replay.json()["replayed"] is True


def test_best_callback_keeps_only_bounded_summary_of_large_artifact(
    submission: dict[str, object],
) -> None:
    client, worker, fetcher = callback_client()
    with client:
        created, manifest, _ = create_manifest(client, worker, submission)
        full_payload = {
            **manifest.payload,
            "rankings": [
                {"rank": index, "factor": f"factor_{index}", "series": [0.1] * 200}
                for index in range(200)
            ],
        }
        full_payload["summary"] = {
            **manifest.payload["summary"],
            "not_in_control_summary": "must not be copied",
        }
        exact_bytes = json.dumps(
            full_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        artifact = manifest.artifact.model_copy(
            update={
                "sha256": hashlib.sha256(exact_bytes).hexdigest(),
                "byte_size": len(exact_bytes),
            }
        )
        manifest = manifest.model_copy(update={"artifact": artifact})
        fetcher.artifacts[str(artifact.url)] = exact_bytes
        callback = client.post(
            f"/v1/internal/runs/{created['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
        result = client.get(f"/v1/runs/{created['runId']}/result")
    assert callback.status_code == 200
    assert len(exact_bytes) > 64 * 1024
    assert result.json()["payload"] == manifest.payload
    assert "rankings" not in result.json()["payload"]
    assert "not_in_control_summary" not in result.json()["payload"]["summary"]


def test_result_callback_rejects_unbounded_inline_payload(
    submission: dict[str, object],
) -> None:
    client, worker, _ = callback_client()
    with client:
        created, manifest, _ = create_manifest(client, worker, submission)
        body = manifest.model_dump(mode="json", by_alias=True)
        body["payload"]["inlineFullResult"] = "x" * (65 * 1024)
        response = client.post(
            f"/v1/internal/runs/{created['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=body,
        )
    assert response.status_code == 422
    assert "64 KiB" in response.text


def test_authenticated_worker_failure_is_terminal_and_idempotent(
    submission: dict[str, object],
) -> None:
    client, worker, _ = callback_client()
    with client:
        created, manifest, provider_run_id = create_manifest(client, worker, submission)
        failure = {
            "binding": manifest.binding.model_dump(mode="json", by_alias=True),
            "errorCode": "worker_analysis_failed",
            "errorMessage": "controlled analysis exited before publication",
            "providerRunId": provider_run_id,
            "occurredAt": "2026-07-24T00:03:00Z",
        }
        response = client.post(
            f"/v1/internal/runs/{created['runId']}/failure",
            headers={"Authorization": "Bearer worker-secret"},
            json=failure,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert response.json()["errorCode"] == "worker_analysis_failed"

        replay = client.post(
            f"/v1/internal/runs/{created['runId']}/failure",
            headers={"Authorization": "Bearer worker-secret"},
            json=failure,
        )
        assert replay.status_code == 200
        assert replay.json()["replayed"] is True

        conflicting = client.post(
            f"/v1/internal/runs/{created['runId']}/failure",
            headers={"Authorization": "Bearer worker-secret"},
            json={**failure, "errorMessage": "different evidence"},
        )
        assert conflicting.status_code == 409
        assert conflicting.json()["error"]["code"] == "worker_failure_conflict"

        late_result = client.post(
            f"/v1/internal/runs/{created['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
        assert late_result.status_code == 409
        assert late_result.json()["error"]["code"] == "terminal_run"


def test_worker_failure_rejects_a_different_provider_run_correlation(
    submission: dict[str, object],
) -> None:
    client, worker, _ = callback_client()
    with client:
        created, manifest, _ = create_manifest(client, worker, submission)
        response = client.post(
            f"/v1/internal/runs/{created['runId']}/failure",
            headers={"Authorization": "Bearer worker-secret"},
            json={
                "binding": manifest.binding.model_dump(mode="json", by_alias=True),
                "errorCode": "worker_workflow_failed",
                "errorMessage": "wrong run correlation",
                "providerRunId": "fake:11111111-1111-4111-8111-111111111111",
                "occurredAt": "2026-07-24T00:03:00Z",
            },
        )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "worker_failure_provider_mismatch"


def test_callback_fails_closed_on_exact_byte_mismatch(
    submission: dict[str, object],
) -> None:
    client, worker, fetcher = callback_client()
    with client:
        created, manifest, _ = create_manifest(client, worker, submission)
        fetcher.artifacts[str(manifest.artifact.url)] = b'{"different":true}\n'
        response = client.post(
            f"/v1/internal/runs/{created['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "result_binding_failed"
        status = client.get(f"/v1/runs/{created['runId']}").json()
        assert status["status"] == "failed"
        assert status["errorCode"] == "result_binding_failed"


def test_callback_rejects_noncommit_code_version(
    submission: dict[str, object],
) -> None:
    client, worker, fetcher = callback_client()
    with client:
        created, manifest, _ = create_manifest(client, worker, submission)
        fetcher.artifacts[str(manifest.artifact.url)] = canonical_json_bytes(manifest.payload)
        invalid_manifest = manifest.model_copy(update={"code_version": "main"})
        response = client.post(
            f"/v1/internal/runs/{created['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=invalid_manifest.model_dump(mode="json", by_alias=True),
        )
        assert response.status_code == 409
        assert "40-character worker commit SHA" in response.json()["error"]["message"]


def test_provider_manifest_with_changed_input_requires_matching_fallback(
    submission: dict[str, object],
) -> None:
    client, worker, _ = callback_client()
    with client:
        created, manifest, provider_run_id = create_manifest(client, worker, submission)
        changed = {**manifest.effective_inputs, "min_market_cap": 0.0}
        invalid_manifest = manifest.model_copy(
            update={
                "effective_inputs": changed,
                "effective_config_hash": hashlib.sha256(canonical_json_bytes(changed)).hexdigest(),
            }
        )
        awaitable = worker.set_observation(
            provider_run_id,
            ProviderObservation(
                status="validating",  # type: ignore[arg-type]
                manifest=invalid_manifest,
                artifact_bytes=canonical_json_bytes(invalid_manifest.payload),
            ),
        )
        import asyncio

        asyncio.run(awaitable)
        response = client.get(f"/v1/runs/{created['runId']}")
        assert response.json()["status"] == "failed"
        assert "fallbacks must explain" in response.json()["errorMessage"]


def test_binding_rejects_fallback_without_request_consent(
    submission: dict[str, object],
) -> None:
    client, worker, _ = callback_client()
    with client:
        created, manifest, provider_run_id = create_manifest(client, worker, submission)
        changed = {**manifest.effective_inputs, "min_market_cap": 0.0}
        fallback = FallbackEvent(
            input="min_market_cap",
            code="market_cap_metadata_insufficient_preflight",
            requested=manifest.normalized_inputs["min_market_cap"],
            effective=0.0,
            reason="fixture fallback",
        )
        invalid_manifest = manifest.model_copy(
            update={
                "effective_inputs": changed,
                "effective_config_hash": hashlib.sha256(canonical_json_bytes(changed)).hexdigest(),
                "fallbacks": [fallback],
                "fallback_used": True,
                "fallback_reason": "fixture fallback",
            }
        )
        import asyncio

        asyncio.run(
            worker.set_observation(
                provider_run_id,
                ProviderObservation(
                    status="validating",  # type: ignore[arg-type]
                    manifest=invalid_manifest,
                    artifact_bytes=canonical_json_bytes(invalid_manifest.payload),
                ),
            )
        )
        response = client.get(f"/v1/runs/{created['runId']}")
        assert response.json()["status"] == "failed"
        assert "without explicit consent" in response.json()["errorMessage"]
