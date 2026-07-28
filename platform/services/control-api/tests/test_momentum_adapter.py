from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from quant_control_api.adapters.momentum import (
    CONFIG_HASH_ALGORITHM,
    DEFAULT_INPUTS,
    INPUT_SCHEMA_HASH,
    INPUT_SCHEMA_VERSION,
    RESULT_CONTRACT_VERSION,
    MomentumAdapter,
    _evaluation_window_days,
    _research_inputs_for_schema,
    canonical_sha256,
)
from quant_control_api.app import create_app
from quant_control_api.artifacts import MappingArtifactFetcher
from quant_control_api.best_factor import DEFAULT_CONFIG
from quant_control_api.dual_write import NullDualWritePublisher
from quant_control_api.models import (
    ArtifactIdentity,
    DataIdentity,
    ResultBinding,
    RunStatus,
    WorkerResultManifest,
)
from quant_control_api.providers.fake import FakeWorkerProvider
from quant_control_api.settings import Settings
from quant_control_api.store import InMemoryRunStore, RunRecord


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
    inputs: dict[str, object],
    calculated_at: datetime,
) -> dict[str, object]:
    if "evaluationWindowDays" in inputs:
        evaluation_window_days = int(inputs["evaluationWindowDays"])
        research_inputs = {
            "version": "research-inputs-v2",
            **inputs,
        }
    else:
        evaluation_window_days = int(inputs["evaluationYears"]) * 252
        research_inputs = {
            "version": "research-inputs-v1",
            **inputs,
            "evaluationWindowDays": evaluation_window_days,
        }
    minimum_evaluation_observations = max(252, evaluation_window_days - 252)
    input_hashes = {
        "prices": "a" * 64,
        "volumes": "b" * 64,
    }
    engine_inputs = {
        "rebalance_frequency": inputs["rebalanceFrequency"],
        "evaluation_window_days": evaluation_window_days,
        "min_evaluation_observations": minimum_evaluation_observations,
        "min_daily_risk_observations": minimum_evaluation_observations,
        "top_n": inputs["topN"],
        "max_weight": inputs["maxWeight"],
        "transaction_cost_bps": inputs["transactionCostBps"],
        "slippage_bps": inputs["slippageBps"],
        "min_history_days": inputs["minHistoryDays"],
        "min_price": inputs["minPrice"],
        "min_avg_dollar_volume": inputs["minAvgDollarVolume"],
        "min_avg_volume": inputs["minAvgVolume"],
        "liquidity_lookback_days": inputs["liquidityLookbackDays"],
        "min_liquidity_observations": inputs["minLiquidityObservations"],
        "max_price_missing_ratio": inputs["maxPriceMissingRatio"],
        "max_volume_missing_ratio": inputs["maxVolumeMissingRatio"],
        "max_extreme_daily_return": inputs["maxExtremeDailyReturn"],
        "selection_min_sharpe": inputs["selectionMinSharpe"],
        "selection_max_drawdown": inputs["selectionMaxDrawdown"],
        "selection_max_annualized_cost_drag": inputs[
            "selectionMaxAnnualizedCostDrag"
        ],
        "selection_min_effective_names": inputs["selectionMinEffectiveNames"],
        "selection_max_target_hhi": inputs["selectionMaxTargetHhi"],
        "selection_max_target_weight": inputs["selectionMaxTargetWeight"],
        "selection_max_abs_security_day_contribution": inputs[
            "selectionMaxAbsSecurityDayContribution"
        ],
        "selection_max_security_absolute_contribution_share": inputs[
            "selectionMaxSecurityAbsoluteContributionShare"
        ],
        "selection_max_leave_one_security_cagr_delta": inputs[
            "selectionMaxLeaveOneSecurityCagrDelta"
        ],
        "selection_extreme_event_action": inputs["selectionExtremeEventAction"],
        "selection_extreme_event_penalty_points": inputs[
            "selectionExtremeEventPenaltyPoints"
        ],
    }
    key_parts = {
        "identityVersion": "momentum-result-identity-v1",
        "canonicalJsonVersion": "rfc8785-jcs-v1",
        "analysisCacheVersion": "analysis-cache-v2",
        "normalizedInputs": engine_inputs,
        "marketSnapshot": {
            "dataAsOf": "2026-07-23",
            "inputSha256": input_hashes,
            "sourceMode": "live_market",
        },
        "factorDefinitionSha256": "1" * 64,
        "policyDefinitionSha256": "2" * 64,
        "selectionSpecSha256": "3" * 64,
        "engineSha256": "4" * 64,
    }
    result_key = canonical_sha256(key_parts)
    return {
        "schemaVersion": 5,
        "generatedAtUtc": calculated_at.isoformat(),
        "resultKey": result_key,
        "resultIdentity": {
            "identityVersion": "momentum-result-identity-v1",
            "resultKey": result_key,
            "keyParts": key_parts,
        },
        "researchInputs": research_inputs,
        "bestFactor": "downside_adjusted_12m",
        "weightingPolicy": "score_liquidity_rank",
        "data": {
            "asOf": "2026-07-23",
            "mode": "live_market",
            "inputSha256": input_hashes,
        },
        "bestFactorPortfolio": {
            "selectedSecurityCount": 2,
            "weights": [
                {"rank": 1, "symbol": "AAA", "weight": 0.6},
                {"rank": 2, "symbol": "BBB", "weight": 0.4},
            ],
        },
    }


def _manifest(
    *,
    run: dict[str, object],
    full_artifact: dict[str, object],
    artifact_bytes: bytes,
) -> WorkerResultManifest:
    data_identity = {
        "source": "momentum-live-market-input-hashes",
        "sourceHash": canonical_sha256(full_artifact["data"]["inputSha256"]),  # type: ignore[index]
        "dataAsOf": "2026-07-23",
    }
    portfolio = full_artifact["bestFactorPortfolio"]
    bounded_payload = {
        "schemaVersion": full_artifact["schemaVersion"],
        "resultKey": full_artifact["resultKey"],
        "resultIdentity": full_artifact["resultIdentity"],
        "researchInputs": full_artifact["researchInputs"],
        "bestFactor": full_artifact["bestFactor"],
        "weightingPolicy": full_artifact["weightingPolicy"],
        "dataIdentity": data_identity,
        "selectedSecurityCount": portfolio["selectedSecurityCount"],  # type: ignore[index]
        "holdings": portfolio["weights"][:50],  # type: ignore[index]
    }
    return WorkerResultManifest(
        binding=ResultBinding(
            project_id="momentum",
            run_id=str(run["runId"]),
            input_schema_version=str(run["inputSchemaVersion"]),
            input_schema_hash=str(run["inputSchemaHash"]),
            config_hash_algorithm=str(run["configHashAlgorithm"]),
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
        calculated_at=datetime.fromisoformat(str(full_artifact["generatedAtUtc"])),
        code_version=f"github:SonChangGi/momentum-factor-lab@{'c' * 40}",
        data_identity=DataIdentity.model_validate(data_identity),
        artifact=ArtifactIdentity(
            url=(
                "https://sonchanggi.github.io/momentum-factor-lab/data/"
                f"control-runs/v1/{run['runId']}/{full_artifact['resultKey']}.json"
            ),
            sha256=hashlib.sha256(artifact_bytes).hexdigest(),
            byte_size=len(artifact_bytes),
            contract_version=RESULT_CONTRACT_VERSION,
        ),
        payload=bounded_payload,
    )


def test_momentum_capabilities_are_worker_authoritative() -> None:
    client, _, _ = _client()
    with client:
        response = client.get("/v1/projects/momentum/capabilities")
    assert response.status_code == 200
    capability = response.json()
    assert capability["projectId"] == "momentum"
    assert capability["inputSchemaVersion"] == INPUT_SCHEMA_VERSION
    assert capability["inputSchemaHash"] == INPUT_SCHEMA_HASH
    assert INPUT_SCHEMA_HASH == (
        "a2240581098f496fc555edac9d4b0e342eee6221a87e046a47f51ee7f6a4e81e"
    )
    assert capability["configHashAlgorithm"] == CONFIG_HASH_ALGORITHM
    assert capability["defaultConfigHash"] == (
        "a0a776fc7ce1227c4a39c14fbea19eb4fe667e0539cb081d5e60e562b709751d"
    )
    evaluation_window = next(
        field
        for field in capability["inputs"]
        if field["key"] == "evaluationWindowDays"
    )
    assert evaluation_window["type"] == "integer"
    assert evaluation_window["minimum"] == 252
    assert evaluation_window["maximum"] == 2520
    assert evaluation_window["unit"] == "sessions"
    assert len(capability["inputs"]) == 26
    assert capability["fallback"]["analysisRunAllowFallback"] is False
    assert capability["fallback"]["scheduledOwnerOperationMayFallback"] is False


def test_momentum_dispatch_maps_exact_26_inputs_and_control_identity() -> None:
    client, provider, _ = _client()
    with client:
        created = client.post(
            "/v1/projects/momentum/runs",
            headers={"Idempotency-Key": "momentum-dispatch-001"},
            json=_submission(topN=25, evaluationWindowDays=300),
        )
    assert created.status_code == 202
    run = created.json()
    assert run["projectId"] == "momentum"
    assert run["configHash"] == canonical_sha256(run["normalizedInputs"])
    envelope = provider.dispatched[run["providerRunId"]]
    workflow_inputs = MomentumAdapter().workflow_inputs(envelope)
    assert json.loads(workflow_inputs["research_inputs_json"]) == run["normalizedInputs"]
    assert workflow_inputs["allow_fallback"] == "false"
    assert workflow_inputs["control_run_id"] == run["runId"]
    assert workflow_inputs["control_input_schema_hash"] == INPUT_SCHEMA_HASH
    assert workflow_inputs["control_config_hash"] == run["configHash"]
    assert len(run["normalizedInputs"]) == 26
    assert run["normalizedInputs"]["evaluationWindowDays"] == 300
    assert "evaluationYears" not in run["normalizedInputs"]


def test_momentum_v1_research_inputs_remain_readable_for_stored_results() -> None:
    legacy = {
        **DEFAULT_INPUTS,
        "evaluationYears": 3,
    }
    legacy.pop("evaluationWindowDays")
    assert _evaluation_window_days(
        legacy,
        input_schema_version="momentum/v1",
    ) == 756
    assert _research_inputs_for_schema(
        legacy,
        input_schema_version="momentum/v1",
    ) == {
        "version": "research-inputs-v1",
        **legacy,
        "evaluationWindowDays": 756,
    }


def test_momentum_v1_stored_artifact_still_passes_semantic_restore_validation() -> None:
    calculated_at = datetime(2026, 7, 24, 1, 2, 3, tzinfo=UTC)
    legacy_inputs = {
        **DEFAULT_INPUTS,
        "evaluationYears": 3,
    }
    legacy_inputs.pop("evaluationWindowDays")
    legacy_config_hash = canonical_sha256(legacy_inputs)
    legacy_run = {
        "runId": "legacy-run-001",
        "inputSchemaVersion": "momentum/v1",
        "inputSchemaHash": (
            "b80cf941ee1b66dcc64c360bdbabaf0e5ed8026d0ec25fc132c0731f11871766"
        ),
        "configHashAlgorithm": CONFIG_HASH_ALGORITHM,
        "configHash": legacy_config_hash,
        "effectiveConfigHash": legacy_config_hash,
        "requestedInputs": legacy_inputs,
        "normalizedInputs": legacy_inputs,
        "effectiveInputs": legacy_inputs,
    }
    full = _full_artifact(
        inputs=legacy_inputs,
        calculated_at=calculated_at,
    )
    artifact_bytes = json.dumps(full, separators=(",", ":")).encode()
    manifest = _manifest(
        run=legacy_run,
        full_artifact=full,
        artifact_bytes=artifact_bytes,
    )
    record = RunRecord(
        project_id="momentum",
        run_id=str(legacy_run["runId"]),
        status=RunStatus.PUBLISHED,
        input_schema_version=str(legacy_run["inputSchemaVersion"]),
        input_schema_hash=str(legacy_run["inputSchemaHash"]),
        config_hash_algorithm=str(legacy_run["configHashAlgorithm"]),
        config_hash=legacy_config_hash,
        effective_config_hash=legacy_config_hash,
        requested_inputs=legacy_inputs,
        normalized_inputs=legacy_inputs,
        effective_inputs=legacy_inputs,
        ignored_inputs=[],
        allow_fallback=False,
        provider="github-actions",
        idempotency_key_digest="legacy-idempotency",
        request_digest="legacy-request",
        created_at=calculated_at,
        updated_at=calculated_at,
    )

    MomentumAdapter().validate_result_binding(record, manifest, artifact_bytes)


def test_momentum_callback_binds_full_artifact_to_bounded_summary() -> None:
    client, _, fetcher = _client()
    calculated_at = datetime(2026, 7, 24, 1, 2, 3, tzinfo=UTC)
    with client:
        created = client.post(
            "/v1/projects/momentum/runs",
            headers={"Idempotency-Key": "momentum-callback-001"},
            json=_submission(),
        ).json()
        full = _full_artifact(
            inputs=created["normalizedInputs"],
            calculated_at=calculated_at,
        )
        result_key = full["resultKey"]
        artifact_bytes = json.dumps(
            full,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        manifest = _manifest(
            run=created,
            full_artifact=full,
            artifact_bytes=artifact_bytes,
        )
        fetcher.artifacts[str(manifest.artifact.url)] = artifact_bytes
        callback = client.post(
            f"/v1/internal/runs/{created['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
        assert callback.status_code == 200
        result = client.get(f"/v1/runs/{created['runId']}/result")
    assert result.status_code == 200
    payload = result.json()["payload"]
    assert payload == manifest.payload
    assert payload != full
    assert payload["resultKey"] == result_key
    assert payload["holdings"] == full["bestFactorPortfolio"]["weights"]  # type: ignore[index]


def test_momentum_callback_rejects_tampered_result_identity_key_parts() -> None:
    client, _, fetcher = _client()
    calculated_at = datetime(2026, 7, 24, 1, 2, 3, tzinfo=UTC)
    with client:
        created = client.post(
            "/v1/projects/momentum/runs",
            headers={"Idempotency-Key": "momentum-identity-tamper-001"},
            json=_submission(),
        ).json()
        full = _full_artifact(
            inputs=created["normalizedInputs"],
            calculated_at=calculated_at,
        )
        identity = full["resultIdentity"]
        identity["keyParts"]["engineSha256"] = "5" * 64  # type: ignore[index]
        artifact_bytes = json.dumps(full, separators=(",", ":")).encode()
        manifest = _manifest(
            run=created,
            full_artifact=full,
            artifact_bytes=artifact_bytes,
        )
        fetcher.artifacts[str(manifest.artifact.url)] = artifact_bytes
        callback = client.post(
            f"/v1/internal/runs/{created['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
    assert callback.status_code == 409
    assert "do not reproduce resultKey" in callback.json()["error"]["message"]


@pytest.mark.parametrize(
    "derived_field",
    [
        "min_evaluation_observations",
        "min_daily_risk_observations",
    ],
)
def test_momentum_callback_rejects_tampered_derived_evaluation_gate(
    derived_field: str,
) -> None:
    client, _, fetcher = _client()
    calculated_at = datetime(2026, 7, 24, 1, 2, 3, tzinfo=UTC)
    with client:
        created = client.post(
            "/v1/projects/momentum/runs",
            headers={"Idempotency-Key": f"momentum-{derived_field}-tamper-001"},
            json=_submission(evaluationWindowDays=1_000),
        ).json()
        full = _full_artifact(
            inputs=created["normalizedInputs"],
            calculated_at=calculated_at,
        )
        identity = full["resultIdentity"]
        key_parts = identity["keyParts"]  # type: ignore[index]
        normalized_inputs = key_parts["normalizedInputs"]  # type: ignore[index]
        normalized_inputs[derived_field] += 1  # type: ignore[index]
        tampered_result_key = canonical_sha256(key_parts)
        full["resultKey"] = tampered_result_key
        identity["resultKey"] = tampered_result_key  # type: ignore[index]
        artifact_bytes = json.dumps(full, separators=(",", ":")).encode()
        manifest = _manifest(
            run=created,
            full_artifact=full,
            artifact_bytes=artifact_bytes,
        )
        fetcher.artifacts[str(manifest.artifact.url)] = artifact_bytes
        callback = client.post(
            f"/v1/internal/runs/{created['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=manifest.model_dump(mode="json", by_alias=True),
        )
    assert callback.status_code == 409
    assert (
        f"Momentum engine input {derived_field} does not match the request"
        in callback.json()["error"]["message"]
    )


def test_project_idempotency_and_artifact_allowlists_are_isolated() -> None:
    client, provider, fetcher = _client()
    with client:
        best = client.post(
            "/v1/projects/best-factor/runs",
            headers={"Idempotency-Key": "shared-project-key-001"},
            json={
                "inputSchemaVersion": "best-factor/v1",
                "inputs": DEFAULT_CONFIG,
                "allowFallback": False,
            },
        ).json()
        momentum = client.post(
            "/v1/projects/momentum/runs",
            headers={"Idempotency-Key": "shared-project-key-001"},
            json=_submission(),
        ).json()
        assert best["runId"] != momentum["runId"]

        best_envelope = provider.dispatched[best["providerRunId"]]
        best_manifest = provider.make_manifest(best_envelope)
        cross_project_url = (
            "https://sonchanggi.github.io/momentum-factor-lab/data/"
            f"control-runs/v1/{best['runId']}/{'f' * 64}.json"
        )
        cross_project_artifact = ArtifactIdentity(
            url=cross_project_url,
            sha256=best_manifest.artifact.sha256,
            byte_size=best_manifest.artifact.byte_size,
            contract_version=best_manifest.artifact.contract_version,
        )
        best_manifest = best_manifest.model_copy(
            update={"artifact": cross_project_artifact}
        )
        fetcher.artifacts[cross_project_url] = json.dumps(
            best_manifest.payload,
            separators=(",", ":"),
        ).encode()
        rejected = client.post(
            f"/v1/internal/runs/{best['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=best_manifest.model_dump(mode="json", by_alias=True),
        )
        calculated_at = datetime(2026, 7, 24, 1, 2, 3, tzinfo=UTC)
        full = _full_artifact(
            inputs=momentum["normalizedInputs"],
            calculated_at=calculated_at,
        )
        momentum_bytes = json.dumps(full, separators=(",", ":")).encode()
        momentum_manifest = _manifest(
            run=momentum,
            full_artifact=full,
            artifact_bytes=momentum_bytes,
        )
        best_url = (
            "https://raw.githubusercontent.com/SonChangGi/best-factor/"
            f"{'d' * 40}/docs/data/latest-results.json"
        )
        momentum_manifest = momentum_manifest.model_copy(
            update={
                "artifact": ArtifactIdentity(
                    url=best_url,
                    sha256=hashlib.sha256(momentum_bytes).hexdigest(),
                    byte_size=len(momentum_bytes),
                    contract_version=RESULT_CONTRACT_VERSION,
                )
            }
        )
        fetcher.artifacts[best_url] = momentum_bytes
        reverse_rejected = client.post(
            f"/v1/internal/runs/{momentum['runId']}/result-manifest",
            headers={"Authorization": "Bearer worker-secret"},
            json=momentum_manifest.model_dump(mode="json", by_alias=True),
        )
    assert rejected.status_code == 409
    assert "Best Factor" in rejected.json()["error"]["message"]
    assert reverse_rejected.status_code == 409
    assert "Momentum" in reverse_rejected.json()["error"]["message"]


def test_momentum_fails_closed_on_partial_inputs_and_fallback_request() -> None:
    client, _, _ = _client()
    partial = dict(DEFAULT_INPUTS)
    partial.pop("topN")
    with client:
        invalid = client.post(
            "/v1/projects/momentum/runs",
            headers={"Idempotency-Key": "momentum-partial-001"},
            json={
                "inputSchemaVersion": INPUT_SCHEMA_VERSION,
                "inputs": partial,
                "allowFallback": False,
            },
        )
        fallback = client.post(
            "/v1/projects/momentum/runs",
            headers={"Idempotency-Key": "momentum-fallback-001"},
            json={**_submission(), "allowFallback": True},
        )
        legacy_years = client.post(
            "/v1/projects/momentum/runs",
            headers={"Idempotency-Key": "momentum-legacy-years-001"},
            json={
                **_submission(),
                "inputs": {
                    **DEFAULT_INPUTS,
                    "evaluationYears": 3,
                },
            },
        )
        too_short = client.post(
            "/v1/projects/momentum/runs",
            headers={"Idempotency-Key": "momentum-window-short-001"},
            json=_submission(evaluationWindowDays=251),
        )
        too_long = client.post(
            "/v1/projects/momentum/runs",
            headers={"Idempotency-Key": "momentum-window-long-001"},
            json=_submission(evaluationWindowDays=2521),
        )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_analysis_inputs"
    assert fallback.status_code == 409
    assert fallback.json()["error"]["code"] == "fallback_not_supported_for_controlled_runs"
    assert legacy_years.status_code == 422
    assert "evaluationYears" in legacy_years.json()["error"]["message"]
    assert too_short.status_code == 422
    assert "between 252 and 2520" in too_short.json()["error"]["message"]
    assert too_long.status_code == 422
    assert "between 252 and 2520" in too_long.json()["error"]["message"]
