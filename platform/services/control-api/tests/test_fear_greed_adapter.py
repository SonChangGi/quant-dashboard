from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from quant_control_api.adapters.fear_greed import (
    CANONICAL_JSON_VERSION,
    CONFIG_HASH_ALGORITHM,
    DEFAULT_INPUTS,
    INPUT_SCHEMA_HASH,
    INPUT_SCHEMA_VERSION,
    METHODOLOGY_VERSION,
    RESULT_CONTRACT_VERSION,
    RESULT_IDENTITY_VERSION,
    FearGreedAdapter,
    _bounded_result_payload,
    canonical_sha256,
    normalize_inputs,
)
from quant_control_api.app import create_app
from quant_control_api.artifacts import MappingArtifactFetcher
from quant_control_api.dual_write import NullDualWritePublisher
from quant_control_api.models import (
    ArtifactIdentity,
    DataIdentity,
    ResultBinding,
    WorkerResultManifest,
)
from quant_control_api.providers.fake import FakeWorkerProvider
from quant_control_api.settings import Settings
from quant_control_api.store import InMemoryRunStore


def _client() -> tuple[TestClient, FakeWorkerProvider, MappingArtifactFetcher]:
    provider = FakeWorkerProvider(auto_complete=False)
    fetcher = MappingArtifactFetcher()
    app = create_app(
        settings=Settings(worker_callback_token="worker-secret"),
        provider=provider,
        store=InMemoryRunStore(),
        publisher=NullDualWritePublisher(),
        artifact_fetcher=fetcher,
    )
    return TestClient(app), provider, fetcher


def _submission(**changes: object) -> dict[str, object]:
    return {
        "inputSchemaVersion": INPUT_SCHEMA_VERSION,
        "inputs": {**DEFAULT_INPUTS, **changes},
        "allowFallback": False,
    }


def _full_artifact(
    *,
    run: dict[str, object],
    calculated_at: datetime,
) -> dict[str, object]:
    data_identity = {
        "source": "fearngreed-python-control-inputs",
        "sourceHash": "a" * 64,
        "dataAsOf": "2026-07-23",
    }
    code_identity = {
        "repository": "SonChangGi/fearNgreed",
        "commitSha": "c" * 40,
        "methodologyVersion": METHODOLOGY_VERSION,
    }
    binding = {
        "projectId": "fear-greed",
        "runId": run["runId"],
        "inputSchemaVersion": INPUT_SCHEMA_VERSION,
        "inputSchemaHash": INPUT_SCHEMA_HASH,
        "configHashAlgorithm": CONFIG_HASH_ALGORITHM,
        "configHash": run["configHash"],
        "effectiveConfigHash": run["effectiveConfigHash"],
    }
    key_parts = {
        "identityVersion": RESULT_IDENTITY_VERSION,
        "canonicalJsonVersion": CANONICAL_JSON_VERSION,
        "binding": binding,
        "dataIdentity": data_identity,
        "codeIdentity": code_identity,
    }
    result_key = canonical_sha256(key_parts)
    return {
        "schemaVersion": 1,
        "contract": RESULT_CONTRACT_VERSION,
        "projectId": "fear-greed",
        "resultKey": result_key,
        "resultIdentity": {
            "identityVersion": RESULT_IDENTITY_VERSION,
            "resultKey": result_key,
            "keyParts": key_parts,
        },
        "requestedInputs": run["requestedInputs"],
        "normalizedInputs": run["normalizedInputs"],
        "effectiveInputs": run["effectiveInputs"],
        "data": data_identity,
        "calculatedAt": calculated_at.isoformat(),
        "signals": [
            {
                "date": "2026-07-23",
                "percentile": 52.4,
                "state": "neutral",
            }
        ],
        "event": {
            "asset": run["normalizedInputs"]["eventAsset"],  # type: ignore[index]
            "sample": run["normalizedInputs"]["eventSample"],  # type: ignore[index]
            "events": [],
        },
        "strategy": {
            "position": "cash",
            "status": "ok",
        },
        "summary": {
            "signalDate": "2026-07-23",
            "signalState": "neutral",
            "signalPercentile": 52.4,
            "eventAsset": run["normalizedInputs"]["eventAsset"],  # type: ignore[index]
            "eventSample": run["normalizedInputs"]["eventSample"],  # type: ignore[index]
            "eventCount": 0,
            "strategyPosition": "cash",
            "strategyStatus": "ok",
            "strategyTotalReturn": 0.12,
            "methodologyVersion": METHODOLOGY_VERSION,
            "notInCallback": "full artifact only",
        },
    }


def _manifest(
    *,
    run: dict[str, object],
    full_artifact: dict[str, object],
    artifact_bytes: bytes,
) -> WorkerResultManifest:
    data_identity = DataIdentity.model_validate(full_artifact["data"])
    result_key = full_artifact["resultKey"]
    return WorkerResultManifest(
        binding=ResultBinding(
            project_id="fear-greed",
            run_id=str(run["runId"]),
            input_schema_version=INPUT_SCHEMA_VERSION,
            input_schema_hash=INPUT_SCHEMA_HASH,
            config_hash_algorithm=CONFIG_HASH_ALGORITHM,
            config_hash=str(run["configHash"]),
        ),
        requested_inputs=run["requestedInputs"],  # type: ignore[arg-type]
        normalized_inputs=run["normalizedInputs"],  # type: ignore[arg-type]
        effective_inputs=run["effectiveInputs"],  # type: ignore[arg-type]
        effective_config_hash=str(run["effectiveConfigHash"]),
        ignored_inputs=[],
        fallbacks=[],
        fallback_used=False,
        data_as_of=date(2026, 7, 23),
        calculated_at=datetime.fromisoformat(str(full_artifact["calculatedAt"])),
        code_version=f"github:SonChangGi/fearNgreed@{'c' * 40}",
        data_identity=data_identity,
        artifact=ArtifactIdentity(
            url=(
                "https://sonchanggi.github.io/fearNgreed/data/control-runs/v1/"
                f"{run['runId']}/{result_key}.json"
            ),
            sha256=hashlib.sha256(artifact_bytes).hexdigest(),
            byte_size=len(artifact_bytes),
            contract_version=RESULT_CONTRACT_VERSION,
        ),
        payload=_bounded_result_payload(full_artifact),
    )


def _created_run(
    client: TestClient,
    *,
    key: str = "fear-greed-run-001",
    **changes: object,
) -> dict[str, object]:
    response = client.post(
        "/v1/projects/fear-greed/runs",
        headers={"Idempotency-Key": key},
        json=_submission(**changes),
    )
    assert response.status_code == 202
    return response.json()


def test_fear_greed_contract_matches_project_owned_hashes_and_defaults() -> None:
    assert len(DEFAULT_INPUTS) == 17
    assert INPUT_SCHEMA_HASH == (
        "70df5e68d4ecae4ad93fa410ccd74f2a12ee3d2ca0bfcba2ae2074de284c2e61"
    )
    normalized = normalize_inputs(DEFAULT_INPUTS)
    assert normalized.requested == DEFAULT_INPUTS
    assert normalized.normalized == DEFAULT_INPUTS
    assert normalized.effective == DEFAULT_INPUTS
    assert normalized.config_hash == (
        "cf8d60da8b6ad43c6849c553b953302721857cfccd1f0d49973f032bada922db"
    )


def test_fear_greed_capabilities_expose_all_wire_fields_and_fail_closed() -> None:
    client, _, _ = _client()
    with client:
        response = client.get("/v1/projects/fear-greed/capabilities")
    assert response.status_code == 200
    capability = response.json()
    assert capability["projectId"] == "fear-greed"
    assert capability["inputSchemaVersion"] == INPUT_SCHEMA_VERSION
    assert capability["inputSchemaHash"] == INPUT_SCHEMA_HASH
    assert capability["configHashAlgorithm"] == CONFIG_HASH_ALGORITHM
    assert capability["defaultConfigHash"] == (
        "cf8d60da8b6ad43c6849c553b953302721857cfccd1f0d49973f032bada922db"
    )
    assert [field["key"] for field in capability["inputs"]] == list(DEFAULT_INPUTS)
    assert len(capability["inputs"]) == 17
    assert capability["fallback"]["analysisRunAllowFallback"] is False
    assert capability["fallback"]["scheduledOwnerOperationMayFallback"] is False
    assert capability["staticFallbackUrl"].endswith("/fearNgreed/data/dashboard.json")


def test_fear_greed_normalization_matches_exact_date_and_numeric_rules() -> None:
    normalized = normalize_inputs(
        {
            **DEFAULT_INPUTS,
            "window": "custom",
            "historyStart": "2026-01-02",
            "historyEnd": "2026-07-23",
            "historyEndMode": "fixed",
            "backtestCost": 10.0,
            "signalMinimumR2": 0,
        }
    )
    assert normalized.normalized["backtestCost"] == 10
    assert normalized.normalized["signalMinimumR2"] == 0.0

    invalid_cases = []
    missing = dict(DEFAULT_INPUTS)
    missing.pop("model")
    invalid_cases.append(missing)
    invalid_cases.append({**DEFAULT_INPUTS, "unknown": 1})
    invalid_cases.append({**DEFAULT_INPUTS, "backtestCost": 7})
    invalid_cases.append({**DEFAULT_INPUTS, "signalMinimumR2": 0.41})
    invalid_cases.append(
        {
            **DEFAULT_INPUTS,
            "window": "custom",
            "historyStart": "2026-07-23",
            "historyEnd": "2026-01-02",
            "historyEndMode": "fixed",
        }
    )
    adapter = FearGreedAdapter()
    for index, inputs in enumerate(invalid_cases):
        try:
            adapter.normalize_inputs(inputs)
        except ValueError as exc:
            assert exc.args
        else:  # pragma: no cover
            raise AssertionError(f"invalid case {index} was accepted")


def test_fear_greed_dispatch_maps_exact_inputs_and_control_identity() -> None:
    client, provider, _ = _client()
    with client:
        run = _created_run(client, signalExtremeTail=3)
    envelope = provider.dispatched[run["providerRunId"]]
    values = FearGreedAdapter().workflow_inputs(envelope)
    assert json.loads(values["analysis_inputs_json"]) == run["effectiveInputs"]
    assert len(json.loads(values["analysis_inputs_json"])) == 17
    assert values["allow_fallback"] == "false"
    assert values["control_run_id"] == run["runId"]
    assert values["control_input_schema_version"] == INPUT_SCHEMA_VERSION
    assert values["control_input_schema_hash"] == INPUT_SCHEMA_HASH
    assert values["control_config_hash_algorithm"] == CONFIG_HASH_ALGORITHM
    assert values["control_config_hash"] == run["configHash"]
    assert len(values) == 7


def test_fear_greed_callback_binds_immutable_artifact_and_bounded_summary() -> None:
    client, _, fetcher = _client()
    calculated_at = datetime(2026, 7, 24, 1, 2, 3, tzinfo=UTC)
    with client:
        run = _created_run(client)
        full = _full_artifact(run=run, calculated_at=calculated_at)
        artifact_bytes = json.dumps(
            full,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        manifest = _manifest(
            run=run,
            full_artifact=full,
            artifact_bytes=artifact_bytes,
        )
        fetcher.artifacts[str(manifest.artifact.url)] = artifact_bytes
        callback = client.post(
            f"/v1/internal/runs/{run['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
        result = client.get(f"/v1/runs/{run['runId']}/result")
    assert callback.status_code == 200
    assert callback.json()["status"] == "published"
    assert result.status_code == 200
    payload = result.json()["payload"]
    assert payload == manifest.payload
    assert payload["resultKey"] == full["resultKey"]
    assert payload["summary"]["signalState"] == "neutral"
    assert "notInCallback" not in payload["summary"]
    assert "signals" not in payload
    assert result.json()["artifact"]["sha256"] == hashlib.sha256(
        artifact_bytes
    ).hexdigest()


def test_fear_greed_callback_rejects_identity_and_exact_byte_tampering() -> None:
    client, _, fetcher = _client()
    calculated_at = datetime(2026, 7, 24, 1, 2, 3, tzinfo=UTC)
    with client:
        run = _created_run(client, key="fear-greed-tamper-001")
        full = _full_artifact(run=run, calculated_at=calculated_at)
        full["resultIdentity"]["keyParts"]["binding"]["configHash"] = "f" * 64  # type: ignore[index]
        artifact_bytes = json.dumps(full, separators=(",", ":")).encode()
        manifest = _manifest(
            run=run,
            full_artifact=full,
            artifact_bytes=artifact_bytes,
        )
        fetcher.artifacts[str(manifest.artifact.url)] = artifact_bytes
        rejected = client.post(
            f"/v1/internal/runs/{run['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "result_binding_failed"
    assert "keyParts do not reproduce resultKey" in rejected.json()["error"]["message"]
    assert "identity binding does not match" in rejected.json()["error"]["message"]

    client, _, fetcher = _client()
    with client:
        run = _created_run(client, key="fear-greed-bytes-001")
        full = _full_artifact(run=run, calculated_at=calculated_at)
        artifact_bytes = json.dumps(full, separators=(",", ":")).encode()
        manifest = _manifest(
            run=run,
            full_artifact=full,
            artifact_bytes=artifact_bytes,
        )
        fetcher.artifacts[str(manifest.artifact.url)] = b'{"tampered":true}'
        rejected = client.post(
            f"/v1/internal/runs/{run['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "result_binding_failed"


def test_fear_greed_callback_rejects_noncommit_code_and_cross_run_url() -> None:
    calculated_at = datetime(2026, 7, 24, 1, 2, 3, tzinfo=UTC)
    client, _, fetcher = _client()
    with client:
        run = _created_run(client, key="fear-greed-code-001")
        full = _full_artifact(run=run, calculated_at=calculated_at)
        artifact_bytes = json.dumps(full, separators=(",", ":")).encode()
        manifest = _manifest(
            run=run,
            full_artifact=full,
            artifact_bytes=artifact_bytes,
        ).model_copy(update={"code_version": "main"})
        fetcher.artifacts[str(manifest.artifact.url)] = artifact_bytes
        rejected_code = client.post(
            f"/v1/internal/runs/{run['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
    assert rejected_code.status_code == 409
    assert "github:SonChangGi/fearNgreed" in rejected_code.json()["error"]["message"]

    client, _, fetcher = _client()
    with client:
        run = _created_run(client, key="fear-greed-cross-run-001")
        full = _full_artifact(run=run, calculated_at=calculated_at)
        artifact_bytes = json.dumps(full, separators=(",", ":")).encode()
        manifest = _manifest(
            run=run,
            full_artifact=full,
            artifact_bytes=artifact_bytes,
        )
        wrong_url = str(manifest.artifact.url).replace(
            str(run["runId"]),
            "11111111-1111-4111-8111-111111111111",
        )
        manifest = manifest.model_copy(
            update={
                "artifact": ArtifactIdentity(
                    url=wrong_url,
                    sha256=manifest.artifact.sha256,
                    byte_size=manifest.artifact.byte_size,
                    contract_version=manifest.artifact.contract_version,
                )
            }
        )
        fetcher.artifacts[wrong_url] = artifact_bytes
        rejected_url = client.post(
            f"/v1/internal/runs/{run['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
    assert rejected_url.status_code == 409
    assert "different control run" in rejected_url.json()["error"]["message"]


def test_fear_greed_rejects_partial_inputs_fallbacks_and_mutable_urls() -> None:
    client, _, fetcher = _client()
    partial = dict(DEFAULT_INPUTS)
    partial.pop("model")
    with client:
        invalid = client.post(
            "/v1/projects/fear-greed/runs",
            headers={"Idempotency-Key": "fear-greed-partial-001"},
            json={
                "inputSchemaVersion": INPUT_SCHEMA_VERSION,
                "inputs": partial,
                "allowFallback": False,
            },
        )
        fallback = client.post(
            "/v1/projects/fear-greed/runs",
            headers={"Idempotency-Key": "fear-greed-fallback-001"},
            json={**_submission(), "allowFallback": True},
        )
        run = _created_run(client, key="fear-greed-url-001")
        full = _full_artifact(
            run=run,
            calculated_at=datetime(2026, 7, 24, 1, 2, 3, tzinfo=UTC),
        )
        artifact_bytes = json.dumps(full, separators=(",", ":")).encode()
        manifest = _manifest(
            run=run,
            full_artifact=full,
            artifact_bytes=artifact_bytes,
        )
        mutable_url = str(manifest.artifact.url) + "?branch=main"
        manifest = manifest.model_copy(
            update={
                "artifact": ArtifactIdentity(
                    url=mutable_url,
                    sha256=manifest.artifact.sha256,
                    byte_size=manifest.artifact.byte_size,
                    contract_version=manifest.artifact.contract_version,
                )
            }
        )
        fetcher.artifacts[mutable_url] = artifact_bytes
        mutable = client.post(
            f"/v1/internal/runs/{run['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_analysis_inputs"
    assert fallback.status_code == 409
    assert (
        fallback.json()["error"]["code"]
        == "fallback_not_supported_for_controlled_runs"
    )
    assert mutable.status_code == 409
    assert "immutable Fear & Greed" in mutable.json()["error"]["message"]


def test_fear_greed_preflight_allows_only_configured_browser_origin() -> None:
    client, _, _ = _client()
    with client:
        allowed = client.options(
            "/v1/projects/fear-greed/runs",
            headers={
                "Origin": "https://sonchanggi.github.io",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "authorization,content-type,idempotency-key"
                ),
            },
        )
        denied = client.options(
            "/v1/projects/fear-greed/runs",
            headers={
                "Origin": "https://example.invalid",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert allowed.status_code == 200
    assert (
        allowed.headers["access-control-allow-origin"]
        == "https://sonchanggi.github.io"
    )
    assert "idempotency-key" in allowed.headers[
        "access-control-allow-headers"
    ].lower()
    assert "access-control-allow-origin" not in denied.headers
