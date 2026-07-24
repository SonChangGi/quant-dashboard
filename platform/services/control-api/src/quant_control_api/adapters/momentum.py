from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import rfc8785

from ..models import (
    ArtifactIdentity,
    FallbackCapability,
    InputFieldCapability,
    WorkerResultManifest,
)
from ..providers.base import DispatchEnvelope, WorkerProvider
from ..store import RunRecord
from .base import NormalizedAnalysisInputs, ProjectRequestError

PROJECT_ID = "momentum"
PROJECT_NAME = "Momentum Factor Lab"
INPUT_SCHEMA_VERSION = "momentum/v1"
INPUT_SCHEMA_HASH = "b80cf941ee1b66dcc64c360bdbabaf0e5ed8026d0ec25fc132c0731f11871766"
CONFIG_HASH_ALGORITHM = "momentum-research-inputs-rfc8785-v1"
RESULT_CONTRACT_VERSION = "momentum/schema-v5-control-result-v1"
STATIC_FALLBACK_URL = "https://sonchanggi.github.io/momentum-factor-lab/data/dashboard.json"
CODE_VERSION_PATTERN = re.compile(
    r"^github:SonChangGi/momentum-factor-lab@[0-9a-f]{40}$"
)
SAFE_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_PATH_PATTERN = re.compile(
    r"^/momentum-factor-lab/data/control-runs/v1/"
    r"(?P<run_id>[A-Za-z0-9][A-Za-z0-9._-]{7,127})/"
    r"(?P<result_key>[0-9a-f]{64})\.json$"
)

INPUT_KEYS = (
    "rebalanceFrequency",
    "evaluationYears",
    "topN",
    "maxWeight",
    "transactionCostBps",
    "slippageBps",
    "minHistoryDays",
    "minPrice",
    "minAvgDollarVolume",
    "minAvgVolume",
    "liquidityLookbackDays",
    "minLiquidityObservations",
    "maxPriceMissingRatio",
    "maxVolumeMissingRatio",
    "maxExtremeDailyReturn",
    "selectionMinSharpe",
    "selectionMaxDrawdown",
    "selectionMaxAnnualizedCostDrag",
    "selectionMinEffectiveNames",
    "selectionMaxTargetHhi",
    "selectionMaxTargetWeight",
    "selectionMaxAbsSecurityDayContribution",
    "selectionMaxSecurityAbsoluteContributionShare",
    "selectionMaxLeaveOneSecurityCagrDelta",
    "selectionExtremeEventAction",
    "selectionExtremeEventPenaltyPoints",
)

DEFAULT_INPUTS: dict[str, Any] = {
    "rebalanceFrequency": "ME",
    "evaluationYears": 3,
    "topN": 20,
    "maxWeight": 0.10,
    "transactionCostBps": 5.0,
    "slippageBps": 5.0,
    "minHistoryDays": 252,
    "minPrice": 5.0,
    "minAvgDollarVolume": 0.0,
    "minAvgVolume": 0.0,
    "liquidityLookbackDays": 63,
    "minLiquidityObservations": 42,
    "maxPriceMissingRatio": 0.05,
    "maxVolumeMissingRatio": 0.10,
    "maxExtremeDailyReturn": 0.80,
    "selectionMinSharpe": 0.0,
    "selectionMaxDrawdown": 0.60,
    "selectionMaxAnnualizedCostDrag": 0.02,
    "selectionMinEffectiveNames": 10.0,
    "selectionMaxTargetHhi": 0.15,
    "selectionMaxTargetWeight": 0.15,
    "selectionMaxAbsSecurityDayContribution": 0.10,
    "selectionMaxSecurityAbsoluteContributionShare": 0.35,
    "selectionMaxLeaveOneSecurityCagrDelta": 0.25,
    "selectionExtremeEventAction": "exclude",
    "selectionExtremeEventPenaltyPoints": 20.0,
}


def _field(
    key: str,
    field_type: str,
    *,
    choices: list[str] | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    exclusive_minimum: float | None = None,
    exclusive_maximum: float | None = None,
    unit: str | None = None,
) -> InputFieldCapability:
    return InputFieldCapability(
        key=key,
        label=key,
        type=field_type,  # type: ignore[arg-type]
        default=DEFAULT_INPUTS[key],
        choices=choices,
        minimum=minimum,
        maximum=maximum,
        exclusive_minimum=exclusive_minimum,
        exclusive_maximum=exclusive_maximum,
        unit=unit,
        cli_argument="--research-inputs-json",
        workflow_input="research_inputs_json",
    )


INPUT_FIELDS = [
    _field("rebalanceFrequency", "enum", choices=["W", "ME", "QE"]),
    _field("evaluationYears", "integer", minimum=1, maximum=10),
    _field("topN", "integer", minimum=1, maximum=50),
    _field("maxWeight", "number", exclusive_minimum=0, maximum=1),
    _field("transactionCostBps", "number", minimum=0, unit="bps"),
    _field("slippageBps", "number", minimum=0, unit="bps"),
    _field("minHistoryDays", "integer", minimum=21, unit="sessions"),
    _field("minPrice", "number", minimum=0, unit="USD"),
    _field("minAvgDollarVolume", "number", minimum=0, unit="USD"),
    _field("minAvgVolume", "number", minimum=0, unit="shares"),
    _field("liquidityLookbackDays", "integer", minimum=1, unit="sessions"),
    _field("minLiquidityObservations", "integer", minimum=1, unit="sessions"),
    _field("maxPriceMissingRatio", "number", minimum=0, exclusive_maximum=1, unit="ratio"),
    _field("maxVolumeMissingRatio", "number", minimum=0, exclusive_maximum=1, unit="ratio"),
    _field("maxExtremeDailyReturn", "number", exclusive_minimum=0, unit="ratio"),
    _field("selectionMinSharpe", "number", minimum=-10),
    _field("selectionMaxDrawdown", "number", exclusive_minimum=0, maximum=1, unit="ratio"),
    _field("selectionMaxAnnualizedCostDrag", "number", minimum=0, unit="ratio"),
    _field("selectionMinEffectiveNames", "number", exclusive_minimum=0),
    _field("selectionMaxTargetHhi", "number", exclusive_minimum=0, maximum=1, unit="ratio"),
    _field("selectionMaxTargetWeight", "number", exclusive_minimum=0, maximum=1, unit="ratio"),
    _field("selectionMaxAbsSecurityDayContribution", "number", minimum=0, unit="ratio"),
    _field(
        "selectionMaxSecurityAbsoluteContributionShare",
        "number",
        minimum=0,
        maximum=1,
        unit="ratio",
    ),
    _field("selectionMaxLeaveOneSecurityCagrDelta", "number", minimum=0, unit="ratio"),
    _field(
        "selectionExtremeEventAction",
        "enum",
        choices=["warn", "penalize", "exclude"],
    ),
    _field("selectionExtremeEventPenaltyPoints", "number", minimum=0, unit="points"),
]


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return rfc8785.dumps(value)
    except (rfc8785.CanonicalizationError, TypeError, ValueError) as exc:
        raise ValueError(f"value is not RFC 8785 canonicalizable: {exc}") from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def normalize_inputs(inputs: dict[str, Any]) -> NormalizedAnalysisInputs:
    if not isinstance(inputs, dict):
        raise TypeError("Momentum inputs must be a JSON object")
    expected = set(INPUT_KEYS)
    observed = set(inputs)
    if observed != expected:
        missing = sorted(expected - observed)
        unknown = sorted(observed - expected)
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unknown:
            details.append("unknown: " + ", ".join(unknown))
        raise ValueError(
            "inputs must contain exactly all 26 Momentum ResearchInputs "
            f"({'; '.join(details)})"
        )
    normalized = {key: inputs[key] for key in INPUT_KEYS}
    numeric_keys = set(INPUT_KEYS) - {
        "rebalanceFrequency",
        "selectionExtremeEventAction",
    }
    for key in numeric_keys:
        value = normalized[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"{key} must be a finite number")
    for key in (
        "evaluationYears",
        "topN",
        "minHistoryDays",
        "liquidityLookbackDays",
        "minLiquidityObservations",
    ):
        value = normalized[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{key} must be an integer")
    if normalized["rebalanceFrequency"] not in {"W", "ME", "QE"}:
        raise ValueError("rebalanceFrequency must be W, ME, or QE")
    if not 1 <= normalized["evaluationYears"] <= 10:
        raise ValueError("evaluationYears must be between 1 and 10")
    if not 1 <= normalized["topN"] <= 50:
        raise ValueError("topN must be between 1 and 50")
    if not 0 < normalized["maxWeight"] <= 1:
        raise ValueError("maxWeight must be in (0, 1]")
    for key in (
        "transactionCostBps",
        "slippageBps",
        "minPrice",
        "minAvgDollarVolume",
        "minAvgVolume",
    ):
        if normalized[key] < 0:
            raise ValueError(f"{key} must be non-negative")
    if normalized["minHistoryDays"] < 21:
        raise ValueError("minHistoryDays must be at least 21")
    if normalized["liquidityLookbackDays"] < 1:
        raise ValueError("liquidityLookbackDays must be positive")
    if not 1 <= normalized["minLiquidityObservations"] <= normalized["liquidityLookbackDays"]:
        raise ValueError("minLiquidityObservations must fit liquidityLookbackDays")
    for key in ("maxPriceMissingRatio", "maxVolumeMissingRatio"):
        if not 0 <= normalized[key] < 1:
            raise ValueError(f"{key} must be in [0, 1)")
    if normalized["maxExtremeDailyReturn"] <= 0:
        raise ValueError("maxExtremeDailyReturn must be positive")
    if normalized["selectionMinSharpe"] < -10:
        raise ValueError("selectionMinSharpe must be at least -10")
    if not 0 < normalized["selectionMaxDrawdown"] <= 1:
        raise ValueError("selectionMaxDrawdown must be in (0, 1]")
    if normalized["selectionMaxAnnualizedCostDrag"] < 0:
        raise ValueError("selectionMaxAnnualizedCostDrag must be non-negative")
    if not 0 < normalized["selectionMinEffectiveNames"] <= normalized["topN"]:
        raise ValueError("selectionMinEffectiveNames must be in (0, topN]")
    for key in ("selectionMaxTargetHhi", "selectionMaxTargetWeight"):
        if not 0 < normalized[key] <= 1:
            raise ValueError(f"{key} must be in (0, 1]")
    for key in (
        "selectionMaxAbsSecurityDayContribution",
        "selectionMaxLeaveOneSecurityCagrDelta",
        "selectionExtremeEventPenaltyPoints",
    ):
        if normalized[key] < 0:
            raise ValueError(f"{key} must be non-negative")
    share = normalized["selectionMaxSecurityAbsoluteContributionShare"]
    if not 0 <= share <= 1:
        raise ValueError(
            "selectionMaxSecurityAbsoluteContributionShare must be in [0, 1]"
        )
    if normalized["selectionExtremeEventAction"] not in {"warn", "penalize", "exclude"}:
        raise ValueError(
            "selectionExtremeEventAction must be warn, penalize, or exclude"
        )
    return NormalizedAnalysisInputs(
        requested=dict(normalized),
        normalized=dict(normalized),
        effective=dict(normalized),
        config_hash=canonical_sha256(normalized),
    )


def _research_inputs_with_derived(normalized: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": "research-inputs-v1",
        **normalized,
        "evaluationWindowDays": normalized["evaluationYears"] * 252,
    }


def _data_identity(payload: dict[str, Any]) -> dict[str, str]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise TypeError("Momentum artifact has no data identity")
    as_of = data.get("asOf")
    hashes = data.get("inputSha256")
    if not isinstance(as_of, str) or not as_of:
        raise ValueError("Momentum artifact has no data as-of date")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("Momentum artifact has no input hashes")
    if any(
        not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value)
        for value in hashes.values()
    ):
        raise ValueError("Momentum artifact contains an invalid input hash")
    return {
        "source": "momentum-live-market-input-hashes",
        "sourceHash": canonical_sha256(hashes),
        "dataAsOf": as_of,
    }


def _bounded_result_payload(
    payload: dict[str, Any],
    data_identity: dict[str, str],
) -> dict[str, Any]:
    portfolio = payload.get("bestFactorPortfolio")
    weights = portfolio.get("weights", []) if isinstance(portfolio, dict) else []
    return {
        "schemaVersion": payload.get("schemaVersion"),
        "resultKey": payload.get("resultKey"),
        "resultIdentity": payload.get("resultIdentity"),
        "researchInputs": payload.get("researchInputs"),
        "bestFactor": payload.get("bestFactor"),
        "weightingPolicy": payload.get("weightingPolicy"),
        "dataIdentity": dict(data_identity),
        "selectedSecurityCount": (
            portfolio.get("selectedSecurityCount")
            if isinstance(portfolio, dict)
            else None
        ),
        "holdings": list(weights[:50]) if isinstance(weights, list) else [],
    }


class MomentumAdapter:
    project_id = PROJECT_ID
    project_name = PROJECT_NAME
    input_schema_version = INPUT_SCHEMA_VERSION
    input_schema_hash = INPUT_SCHEMA_HASH
    config_hash_algorithm = CONFIG_HASH_ALGORITHM
    default_inputs = DEFAULT_INPUTS
    input_fields = INPUT_FIELDS
    static_fallback_url = STATIC_FALLBACK_URL

    def normalize_inputs(self, inputs: dict[str, Any]) -> NormalizedAnalysisInputs:
        try:
            return normalize_inputs(inputs)
        except (TypeError, ValueError) as exc:
            raise ProjectRequestError(
                status_code=422,
                code="invalid_analysis_inputs",
                message=str(exc),
            ) from exc

    def validate_run_request(
        self,
        *,
        allow_fallback: bool,
        normalized: NormalizedAnalysisInputs,
        provider: WorkerProvider,
    ) -> None:
        del normalized, provider
        if allow_fallback:
            raise ProjectRequestError(
                status_code=409,
                code="fallback_not_supported_for_controlled_runs",
                message="Momentum controlled runs require allowFallback=false",
            )

    def fallback_capability(self, provider: WorkerProvider) -> FallbackCapability:
        return FallbackCapability(
            default_allowed=False,
            analysis_run_allow_fallback=False,
            scheduled_owner_operation_may_fallback=False,
            possible_when="never",
            reason="momentum_controlled_runs_are_fail_closed",
            provider_can_enforce_rejection=provider.supports_fallback_rejection,
        )

    @staticmethod
    def canonical_sha256(value: Any) -> str:
        return canonical_sha256(value)

    @staticmethod
    def workflow_inputs(envelope: DispatchEnvelope) -> dict[str, str]:
        return {
            "research_inputs_json": canonical_json_bytes(
                envelope.effective_inputs
            ).decode("utf-8"),
            "allow_fallback": "true" if envelope.allow_fallback else "false",
            "control_run_id": envelope.run_id,
            "control_input_schema_version": envelope.input_schema_version,
            "control_input_schema_hash": envelope.input_schema_hash,
            "control_config_hash_algorithm": envelope.config_hash_algorithm,
            "control_config_hash": envelope.config_hash,
        }

    def validate_artifact_url(
        self,
        record: RunRecord,
        artifact: ArtifactIdentity,
    ) -> None:
        parsed = urlparse(str(artifact.url))
        match = ARTIFACT_PATH_PATTERN.fullmatch(parsed.path)
        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
            or parsed.query
            or parsed.fragment
            or parsed.hostname != "sonchanggi.github.io"
            or match is None
        ):
            raise ValueError("artifact URL is not an immutable Momentum control result")
        if match.group("run_id") != record.run_id:
            raise ValueError("Momentum artifact URL belongs to a different control run")
        payload_result_key = (
            record.result_manifest.payload.get("resultKey")
            if record.result_manifest is not None
            else None
        )
        if payload_result_key is not None and match.group("result_key") != payload_result_key:
            raise ValueError("Momentum artifact URL result key does not match the result manifest")

    def validate_result_binding(
        self,
        record: RunRecord,
        manifest: WorkerResultManifest,
        artifact_bytes: bytes,
    ) -> None:
        errors: list[str] = []
        expected_binding = {
            "projectId": record.project_id,
            "runId": record.run_id,
            "inputSchemaVersion": record.input_schema_version,
            "inputSchemaHash": record.input_schema_hash,
            "configHashAlgorithm": record.config_hash_algorithm,
            "configHash": record.config_hash,
        }
        if manifest.binding.model_dump(mode="json", by_alias=True) != expected_binding:
            errors.append("binding identity does not match the requested run")
        for label, observed, expected in (
            ("requestedInputs", manifest.requested_inputs, record.requested_inputs),
            ("normalizedInputs", manifest.normalized_inputs, record.normalized_inputs),
            ("effectiveInputs", manifest.effective_inputs, record.effective_inputs),
        ):
            if observed != expected:
                errors.append(f"worker {label} do not exactly match the requested 26 inputs")
        try:
            if canonical_sha256(manifest.normalized_inputs) != record.config_hash:
                errors.append("worker normalizedInputs do not reproduce configHash")
            if canonical_sha256(manifest.effective_inputs) != manifest.effective_config_hash:
                errors.append("worker effectiveInputs do not reproduce effectiveConfigHash")
        except ValueError as exc:
            errors.append(str(exc))
        if manifest.effective_config_hash != record.config_hash:
            errors.append("effectiveConfigHash must equal configHash")
        if manifest.ignored_inputs:
            errors.append("worker ignored one or more Momentum inputs")
        if manifest.fallbacks or manifest.fallback_used or manifest.fallback_reason:
            errors.append("Momentum controlled results must not contain fallbacks")
        if manifest.data_identity.data_as_of != manifest.data_as_of:
            errors.append("dataIdentity.dataAsOf does not match dataAsOf")
        if not CODE_VERSION_PATTERN.fullmatch(manifest.code_version):
            errors.append(
                "codeVersion must be github:SonChangGi/momentum-factor-lab@<40hex>"
            )
        if manifest.artifact.contract_version != RESULT_CONTRACT_VERSION:
            errors.append("artifact contractVersion is not the Momentum control contract")
        if hashlib.sha256(artifact_bytes).hexdigest() != manifest.artifact.sha256:
            errors.append("artifact sha256 does not bind the exact fetched bytes")
        if len(artifact_bytes) != manifest.artifact.byte_size:
            errors.append("artifact byteSize does not bind the exact fetched bytes")
        try:
            fetched = json.loads(
                artifact_bytes,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-standard JSON number: {value}")
                ),
            )
            if not isinstance(fetched, dict):
                raise TypeError("artifact JSON root must be an object")
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            errors.append(f"artifact bytes are not valid UTF-8 JSON: {exc}")
            fetched = None
        if fetched is not None:
            if fetched.get("schemaVersion") != 5:
                errors.append("Momentum artifact schemaVersion must be 5")
            result_key = fetched.get("resultKey")
            if not isinstance(result_key, str) or not SHA256_PATTERN.fullmatch(result_key):
                errors.append("Momentum artifact resultKey must be a lowercase SHA-256 digest")
            identity = fetched.get("resultIdentity")
            if not isinstance(identity, dict) or identity.get("resultKey") != result_key:
                errors.append("Momentum resultIdentity does not bind resultKey")
            elif identity.get("identityVersion") != "momentum-result-identity-v1":
                errors.append("Momentum resultIdentity has an unsupported identityVersion")
            else:
                key_parts = identity.get("keyParts")
                if not isinstance(key_parts, dict):
                    errors.append("Momentum resultIdentity keyParts are missing")
                else:
                    try:
                        reproduced_result_key = canonical_sha256(key_parts)
                    except ValueError as exc:
                        errors.append(str(exc))
                    else:
                        if reproduced_result_key != result_key:
                            errors.append(
                                "Momentum resultIdentity keyParts do not reproduce resultKey"
                            )
                    if key_parts.get("identityVersion") != "momentum-result-identity-v1":
                        errors.append("Momentum keyParts identityVersion is invalid")
                    if key_parts.get("canonicalJsonVersion") != "rfc8785-jcs-v1":
                        errors.append("Momentum keyParts canonicalJsonVersion is invalid")
                    for digest_field in (
                        "engineSha256",
                        "factorDefinitionSha256",
                        "policyDefinitionSha256",
                        "selectionSpecSha256",
                    ):
                        digest = key_parts.get(digest_field)
                        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(
                            digest
                        ):
                            errors.append(
                                f"Momentum keyParts {digest_field} is not a SHA-256 digest"
                            )
                    normalized_engine_inputs = key_parts.get("normalizedInputs")
                    expected_engine_inputs = {
                        "rebalance_frequency": record.normalized_inputs[
                            "rebalanceFrequency"
                        ],
                        "evaluation_window_days": record.normalized_inputs[
                            "evaluationYears"
                        ]
                        * 252,
                        "top_n": record.normalized_inputs["topN"],
                        "max_weight": record.normalized_inputs["maxWeight"],
                        "transaction_cost_bps": record.normalized_inputs[
                            "transactionCostBps"
                        ],
                        "slippage_bps": record.normalized_inputs["slippageBps"],
                        "min_history_days": record.normalized_inputs["minHistoryDays"],
                        "min_price": record.normalized_inputs["minPrice"],
                        "min_avg_dollar_volume": record.normalized_inputs[
                            "minAvgDollarVolume"
                        ],
                        "min_avg_volume": record.normalized_inputs["minAvgVolume"],
                        "liquidity_lookback_days": record.normalized_inputs[
                            "liquidityLookbackDays"
                        ],
                        "min_liquidity_observations": record.normalized_inputs[
                            "minLiquidityObservations"
                        ],
                        "max_price_missing_ratio": record.normalized_inputs[
                            "maxPriceMissingRatio"
                        ],
                        "max_volume_missing_ratio": record.normalized_inputs[
                            "maxVolumeMissingRatio"
                        ],
                        "max_extreme_daily_return": record.normalized_inputs[
                            "maxExtremeDailyReturn"
                        ],
                        "selection_min_sharpe": record.normalized_inputs[
                            "selectionMinSharpe"
                        ],
                        "selection_max_drawdown": record.normalized_inputs[
                            "selectionMaxDrawdown"
                        ],
                        "selection_max_annualized_cost_drag": record.normalized_inputs[
                            "selectionMaxAnnualizedCostDrag"
                        ],
                        "selection_min_effective_names": record.normalized_inputs[
                            "selectionMinEffectiveNames"
                        ],
                        "selection_max_target_hhi": record.normalized_inputs[
                            "selectionMaxTargetHhi"
                        ],
                        "selection_max_target_weight": record.normalized_inputs[
                            "selectionMaxTargetWeight"
                        ],
                        "selection_max_abs_security_day_contribution": (
                            record.normalized_inputs[
                                "selectionMaxAbsSecurityDayContribution"
                            ]
                        ),
                        "selection_max_security_absolute_contribution_share": (
                            record.normalized_inputs[
                                "selectionMaxSecurityAbsoluteContributionShare"
                            ]
                        ),
                        "selection_max_leave_one_security_cagr_delta": (
                            record.normalized_inputs[
                                "selectionMaxLeaveOneSecurityCagrDelta"
                            ]
                        ),
                        "selection_extreme_event_action": record.normalized_inputs[
                            "selectionExtremeEventAction"
                        ],
                        "selection_extreme_event_penalty_points": (
                            record.normalized_inputs[
                                "selectionExtremeEventPenaltyPoints"
                            ]
                        ),
                    }
                    if not isinstance(normalized_engine_inputs, dict):
                        errors.append("Momentum keyParts normalizedInputs are missing")
                    else:
                        for key, expected_value in expected_engine_inputs.items():
                            if normalized_engine_inputs.get(key) != expected_value:
                                errors.append(
                                    f"Momentum engine input {key} does not match the request"
                                )
                    data = fetched.get("data")
                    market_snapshot = key_parts.get("marketSnapshot")
                    if not isinstance(data, dict) or not isinstance(
                        market_snapshot,
                        dict,
                    ):
                        errors.append("Momentum result identity market snapshot is missing")
                    else:
                        if market_snapshot.get("dataAsOf") != data.get("asOf"):
                            errors.append(
                                "Momentum marketSnapshot.dataAsOf does not match artifact data"
                            )
                        if market_snapshot.get("inputSha256") != data.get(
                            "inputSha256"
                        ):
                            errors.append(
                                "Momentum marketSnapshot input hashes do not match artifact data"
                            )
                        if market_snapshot.get("sourceMode") != "live_market":
                            errors.append(
                                "Momentum controlled result must bind live_market sourceMode"
                            )
            expected_research_inputs = _research_inputs_with_derived(
                record.normalized_inputs
            )
            if fetched.get("researchInputs") != expected_research_inputs:
                errors.append("Momentum artifact researchInputs do not match the request")
            try:
                data_identity = _data_identity(fetched)
            except (TypeError, ValueError) as exc:
                errors.append(str(exc))
            else:
                if data_identity != manifest.data_identity.model_dump(
                    mode="json",
                    by_alias=True,
                ):
                    errors.append("Momentum artifact data identity does not match the manifest")
                if data_identity["dataAsOf"] != manifest.data_as_of.isoformat():
                    errors.append("Momentum artifact dataAsOf does not match the manifest")
                expected_summary = _bounded_result_payload(fetched, data_identity)
                if manifest.payload != expected_summary:
                    errors.append(
                        "Momentum callback payload is not the bounded summary of the fetched artifact"
                    )
            generated_at = fetched.get("generatedAtUtc")
            try:
                parsed_generated_at = datetime.fromisoformat(str(generated_at))
            except ValueError:
                errors.append("Momentum generatedAtUtc is not an ISO-8601 timestamp")
            else:
                if (
                    parsed_generated_at.tzinfo is None
                    or parsed_generated_at.utcoffset() is None
                    or parsed_generated_at != manifest.calculated_at
                ):
                    errors.append("Momentum generatedAtUtc does not match calculatedAt")
            parsed_url = urlparse(str(manifest.artifact.url))
            match = ARTIFACT_PATH_PATTERN.fullmatch(parsed_url.path)
            if match is None or match.group("result_key") != result_key:
                errors.append("Momentum artifact URL does not bind resultKey")
        if errors:
            from ..binding import ResultBindingError

            raise ResultBindingError("; ".join(errors))

    @staticmethod
    def payload_from_artifact(
        record: RunRecord,
        artifact_payload: dict[str, Any],
    ) -> dict[str, Any]:
        del record
        return _bounded_result_payload(artifact_payload, _data_identity(artifact_payload))
