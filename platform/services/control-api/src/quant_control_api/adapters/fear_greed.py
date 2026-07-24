from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse

from ..models import (
    ArtifactIdentity,
    FallbackCapability,
    InputFieldCapability,
    WorkerResultManifest,
)
from ..providers.base import DispatchEnvelope, WorkerProvider
from ..store import RunRecord
from .base import NormalizedAnalysisInputs, ProjectRequestError

PROJECT_ID = "fear-greed"
PROJECT_NAME = "Fear & Greed"
INPUT_SCHEMA_VERSION = "fear-greed/control-inputs-v1"
INPUT_SCHEMA_HASH = "70df5e68d4ecae4ad93fa410ccd74f2a12ee3d2ca0bfcba2ae2074de284c2e61"
CONFIG_HASH_ALGORITHM = "fear-greed-json-sort-keys-sha256-v1"
RESULT_CONTRACT_VERSION = "fear-greed/control-result-v1"
RESULT_IDENTITY_VERSION = "fear-greed-result-identity-v1"
CANONICAL_JSON_VERSION = CONFIG_HASH_ALGORITHM
METHODOLOGY_VERSION = "fear-flow-v5"
STATIC_FALLBACK_URL = "https://sonchanggi.github.io/fearNgreed/data/dashboard.json"

CODE_VERSION_PATTERN = re.compile(r"^github:SonChangGi/fearNgreed@[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SAFE_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$")
ARTIFACT_PATH_PATTERN = re.compile(
    r"^/fearNgreed/data/control-runs/v1/"
    r"(?P<run_id>[A-Za-z0-9][A-Za-z0-9._-]{7,127})/"
    r"(?P<result_key>[0-9a-f]{64})\.json$"
)

# The page describes these as 16 user-facing inputs because the evaluation
# window is one composite control. Its wire representation deliberately has
# 17 exact keys: window, start, end, and end mode are independently bound.
DEFAULT_INPUTS: dict[str, Any] = {
    "window": "ytd",
    "historyStart": "",
    "historyEnd": "",
    "historyEndMode": "latest",
    "model": "raw",
    "eventAsset": "KOSPI",
    "eventSample": "all",
    "backtestProxy": "1x",
    "backtestPolicy": "compare",
    "backtestVariant": "raw_ols",
    "backtestCost": 10,
    "backtestPeriod": "common",
    "longExitPercentile": 80,
    "signalLookback": 196,
    "signalMinimumR2": 0.4,
    "signalExtremeTail": 2,
    "signalMaxHolding": 20,
}
INPUT_KEYS = tuple(DEFAULT_INPUTS)

ENUM_CHOICES: dict[str, tuple[str, ...]] = {
    "window": ("1m", "3m", "6m", "ytd", "1y", "3y", "all", "custom"),
    "historyEndMode": ("latest", "fixed"),
    "model": ("robust", "scaled", "raw"),
    "eventAsset": ("KOSPI", "226490", "069500"),
    "eventSample": ("all", "nonOverlapping20d"),
    "backtestProxy": ("1x", "2x"),
    "backtestPolicy": ("compare", "long_cash", "long_inverse_cash"),
    "backtestVariant": ("scaled_huber", "scaled_ols", "raw_ols", "disparity"),
    "backtestPeriod": ("common", "full"),
}

FEAR_CONTROL_SUMMARY_FIELDS = (
    "signalDate",
    "signalState",
    "signalPercentile",
    "eventAsset",
    "eventSample",
    "eventCount",
    "strategyPosition",
    "strategyStatus",
    "strategyTotalReturn",
    "methodologyVersion",
)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


if canonical_sha256(
    {
        "schemaVersion": INPUT_SCHEMA_VERSION,
        "fields": INPUT_KEYS,
        "defaults": DEFAULT_INPUTS,
    }
) != INPUT_SCHEMA_HASH:
    raise RuntimeError("Fear & Greed input schema hash does not match its fields")


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


def _integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return value


def _iso_date_or_empty(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be an ISO date or an empty string")
    if value:
        date.fromisoformat(value)
    return value


def normalize_inputs(inputs: dict[str, Any]) -> NormalizedAnalysisInputs:
    if not isinstance(inputs, dict):
        raise TypeError("Fear & Greed inputs must be a JSON object")
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
            "inputs must contain every declared field "
            f"({'; '.join(details)})"
        )

    normalized = {key: inputs[key] for key in INPUT_KEYS}
    for field, choices in ENUM_CHOICES.items():
        if normalized[field] not in choices:
            raise ValueError(f"{field} is not an allowed value")

    normalized["historyStart"] = _iso_date_or_empty(
        normalized["historyStart"],
        "historyStart",
    )
    normalized["historyEnd"] = _iso_date_or_empty(
        normalized["historyEnd"],
        "historyEnd",
    )
    if normalized["window"] == "custom":
        if not normalized["historyStart"] or not normalized["historyEnd"]:
            raise ValueError("custom windows require historyStart and historyEnd")
        if normalized["historyStart"] > normalized["historyEnd"]:
            raise ValueError("historyStart must not be after historyEnd")
    if normalized["historyEndMode"] == "fixed" and not normalized["historyEnd"]:
        raise ValueError("fixed historyEndMode requires historyEnd")

    cost = _finite_number(normalized["backtestCost"], "backtestCost")
    if cost not in {0.0, 5.0, 10.0, 20.0}:
        raise ValueError("backtestCost must be 0, 5, 10, or 20")
    normalized["backtestCost"] = int(cost)
    normalized["longExitPercentile"] = _integer(
        normalized["longExitPercentile"],
        "longExitPercentile",
        50,
        94,
    )
    normalized["signalLookback"] = _integer(
        normalized["signalLookback"],
        "signalLookback",
        60,
        756,
    )
    minimum_r2 = _finite_number(
        normalized["signalMinimumR2"],
        "signalMinimumR2",
    )
    if (
        not 0 <= minimum_r2 <= 0.8
        or abs(minimum_r2 * 20 - round(minimum_r2 * 20)) > 1e-9
    ):
        raise ValueError(
            "signalMinimumR2 must be between 0 and 0.8 in 0.05 steps"
        )
    normalized["signalMinimumR2"] = minimum_r2
    normalized["signalExtremeTail"] = _integer(
        normalized["signalExtremeTail"],
        "signalExtremeTail",
        1,
        20,
    )
    normalized["signalMaxHolding"] = _integer(
        normalized["signalMaxHolding"],
        "signalMaxHolding",
        1,
        60,
    )

    requested = dict(inputs)
    effective = dict(normalized)
    return NormalizedAnalysisInputs(
        requested=requested,
        normalized=normalized,
        effective=effective,
        config_hash=canonical_sha256(effective),
    )


def _field(
    key: str,
    label: str,
    field_type: str,
    *,
    choices: tuple[str, ...] | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    unit: str | None = None,
) -> InputFieldCapability:
    return InputFieldCapability(
        key=key,
        label=label,
        type=field_type,  # type: ignore[arg-type]
        default=DEFAULT_INPUTS[key],
        choices=list(choices) if choices else None,
        minimum=minimum,
        maximum=maximum,
        unit=unit,
        cli_argument="--analysis-inputs-json",
        workflow_input="analysis_inputs_json",
    )


INPUT_FIELDS = [
    _field("window", "평가 기간", "enum", choices=ENUM_CHOICES["window"]),
    _field("historyStart", "시작일", "string", unit="ISO date"),
    _field("historyEnd", "종료일", "string", unit="ISO date"),
    _field(
        "historyEndMode",
        "종료일 방식",
        "enum",
        choices=ENUM_CHOICES["historyEndMode"],
    ),
    _field("model", "연구 트랙", "enum", choices=ENUM_CHOICES["model"]),
    _field("eventAsset", "사건 자산", "enum", choices=ENUM_CHOICES["eventAsset"]),
    _field("eventSample", "사건 표본", "enum", choices=ENUM_CHOICES["eventSample"]),
    _field(
        "backtestProxy",
        "ETF 페어",
        "enum",
        choices=ENUM_CHOICES["backtestProxy"],
    ),
    _field(
        "backtestPolicy",
        "전략 정책",
        "enum",
        choices=ENUM_CHOICES["backtestPolicy"],
    ),
    _field(
        "backtestVariant",
        "전략 변형",
        "enum",
        choices=ENUM_CHOICES["backtestVariant"],
    ),
    _field("backtestCost", "거래비용", "number", minimum=0, maximum=20, unit="bps"),
    _field(
        "backtestPeriod",
        "백테스트 기간",
        "enum",
        choices=ENUM_CHOICES["backtestPeriod"],
    ),
    _field(
        "longExitPercentile",
        "롱 청산 백분위",
        "integer",
        minimum=50,
        maximum=94,
        unit="percentile",
    ),
    _field(
        "signalLookback",
        "신호 학습창",
        "integer",
        minimum=60,
        maximum=756,
        unit="sessions",
    ),
    _field(
        "signalMinimumR2",
        "최소 R²",
        "number",
        minimum=0,
        maximum=0.8,
    ),
    _field(
        "signalExtremeTail",
        "극단 꼬리",
        "integer",
        minimum=1,
        maximum=20,
        unit="percent",
    ),
    _field(
        "signalMaxHolding",
        "최대 보유기간",
        "integer",
        minimum=1,
        maximum=60,
        unit="sessions",
    ),
]


def _strict_json_object(artifact_bytes: bytes) -> dict[str, Any]:
    fetched = json.loads(
        artifact_bytes,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-standard JSON number: {value}")
        ),
    )
    if not isinstance(fetched, dict):
        raise TypeError("artifact JSON root must be an object")
    return fetched


def _artifact_data_identity(payload: dict[str, Any]) -> dict[str, str]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise TypeError("Fear & Greed artifact data identity is missing")
    expected_keys = {"source", "sourceHash", "dataAsOf"}
    if set(data) != expected_keys:
        raise ValueError("Fear & Greed artifact data identity has unexpected fields")
    source = data.get("source")
    source_hash = data.get("sourceHash")
    data_as_of = data.get("dataAsOf")
    if not isinstance(source, str) or not source:
        raise ValueError("Fear & Greed artifact data source is missing")
    if (
        not isinstance(source_hash, str)
        or not 8 <= len(source_hash) <= 128
        or any(character not in "0123456789abcdef" for character in source_hash)
    ):
        raise ValueError("Fear & Greed artifact sourceHash is invalid")
    if not isinstance(data_as_of, str):
        raise TypeError("Fear & Greed artifact dataAsOf is missing")
    date.fromisoformat(data_as_of)
    return {
        "source": source,
        "sourceHash": source_hash,
        "dataAsOf": data_as_of,
    }


def _bounded_result_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise TypeError("Fear & Greed artifact summary is missing")
    bounded_summary: dict[str, Any] = {}
    for key in FEAR_CONTROL_SUMMARY_FIELDS:
        if key not in summary:
            continue
        value = summary[key]
        if isinstance(value, (dict, list)):
            raise TypeError(
                f"Fear & Greed summary.{key} must be a scalar JSON value"
            )
        bounded_summary[key] = value
    bounded = {
        "schemaVersion": payload.get("schemaVersion"),
        "contract": payload.get("contract"),
        "resultKey": payload.get("resultKey"),
        "resultIdentity": payload.get("resultIdentity"),
        "data": payload.get("data"),
        "calculatedAt": payload.get("calculatedAt"),
        "summary": bounded_summary,
    }
    if len(canonical_json_bytes(bounded)) > 64 * 1024:
        raise ValueError("Fear & Greed bounded callback payload exceeds 64 KiB")
    return bounded


class FearGreedAdapter:
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
                message="Fear & Greed controlled runs require allowFallback=false",
            )

    def fallback_capability(self, provider: WorkerProvider) -> FallbackCapability:
        return FallbackCapability(
            default_allowed=False,
            analysis_run_allow_fallback=False,
            scheduled_owner_operation_may_fallback=False,
            possible_when="never",
            reason="fear_greed_controlled_runs_are_fail_closed",
            provider_can_enforce_rejection=provider.supports_fallback_rejection,
        )

    @staticmethod
    def canonical_sha256(value: Any) -> str:
        return canonical_sha256(value)

    @staticmethod
    def workflow_inputs(envelope: DispatchEnvelope) -> dict[str, str]:
        return {
            "analysis_inputs_json": canonical_json_bytes(
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
            raise ValueError(
                "artifact URL is not an immutable Fear & Greed control result"
            )
        if match.group("run_id") != record.run_id:
            raise ValueError(
                "Fear & Greed artifact URL belongs to a different control run"
            )
        payload_result_key = (
            record.result_manifest.payload.get("resultKey")
            if record.result_manifest is not None
            else None
        )
        if (
            payload_result_key is not None
            and match.group("result_key") != payload_result_key
        ):
            raise ValueError(
                "Fear & Greed artifact URL result key does not match the manifest"
            )

    def validate_result_binding(
        self,
        record: RunRecord,
        manifest: WorkerResultManifest,
        artifact_bytes: bytes,
    ) -> None:
        from ..binding import ResultBindingError

        errors: list[str] = []
        expected_binding = {
            "projectId": record.project_id,
            "runId": record.run_id,
            "inputSchemaVersion": record.input_schema_version,
            "inputSchemaHash": record.input_schema_hash,
            "configHashAlgorithm": record.config_hash_algorithm,
            "configHash": record.config_hash,
        }
        if (
            manifest.binding.model_dump(mode="json", by_alias=True)
            != expected_binding
        ):
            errors.append("binding identity does not match the requested run")
        for label, observed, expected in (
            ("requestedInputs", manifest.requested_inputs, record.requested_inputs),
            ("normalizedInputs", manifest.normalized_inputs, record.normalized_inputs),
            ("effectiveInputs", manifest.effective_inputs, record.effective_inputs),
        ):
            if observed != expected:
                errors.append(
                    f"worker {label} do not exactly match the requested 17 fields"
                )
        try:
            if canonical_sha256(manifest.normalized_inputs) != record.config_hash:
                errors.append("worker normalizedInputs do not reproduce configHash")
            if (
                canonical_sha256(manifest.effective_inputs)
                != manifest.effective_config_hash
            ):
                errors.append(
                    "worker effectiveInputs do not reproduce effectiveConfigHash"
                )
        except (TypeError, ValueError) as exc:
            errors.append(str(exc))
        if manifest.effective_config_hash != record.config_hash:
            errors.append("effectiveConfigHash must equal configHash")
        if manifest.ignored_inputs:
            errors.append("worker ignored one or more Fear & Greed inputs")
        if manifest.fallbacks or manifest.fallback_used or manifest.fallback_reason:
            errors.append(
                "Fear & Greed controlled results must not contain fallbacks"
            )
        if manifest.data_identity.data_as_of != manifest.data_as_of:
            errors.append("dataIdentity.dataAsOf does not match dataAsOf")
        if not CODE_VERSION_PATTERN.fullmatch(manifest.code_version):
            errors.append(
                "codeVersion must be github:SonChangGi/fearNgreed@<40hex>"
            )
        if manifest.artifact.contract_version != RESULT_CONTRACT_VERSION:
            errors.append(
                "artifact contractVersion is not the Fear & Greed control contract"
            )
        if hashlib.sha256(artifact_bytes).hexdigest() != manifest.artifact.sha256:
            errors.append("artifact sha256 does not bind the exact fetched bytes")
        if len(artifact_bytes) != manifest.artifact.byte_size:
            errors.append("artifact byteSize does not bind the exact fetched bytes")

        try:
            fetched = _strict_json_object(artifact_bytes)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as exc:
            errors.append(f"artifact bytes are not valid UTF-8 JSON: {exc}")
            fetched = None

        if fetched is not None:
            self._validate_fetched_artifact(
                record,
                manifest,
                fetched,
                errors,
            )
        if errors:
            raise ResultBindingError("; ".join(errors))

    @staticmethod
    def _validate_fetched_artifact(
        record: RunRecord,
        manifest: WorkerResultManifest,
        fetched: dict[str, Any],
        errors: list[str],
    ) -> None:
        if fetched.get("schemaVersion") != 1:
            errors.append("Fear & Greed artifact schemaVersion must be 1")
        if fetched.get("contract") != RESULT_CONTRACT_VERSION:
            errors.append("Fear & Greed artifact contract is invalid")
        if fetched.get("projectId") != PROJECT_ID:
            errors.append("Fear & Greed artifact projectId is invalid")
        for key, expected in (
            ("requestedInputs", record.requested_inputs),
            ("normalizedInputs", record.normalized_inputs),
            ("effectiveInputs", record.effective_inputs),
        ):
            if fetched.get(key) != expected:
                errors.append(f"Fear & Greed artifact {key} do not match the run")
        for section, section_type in (
            ("signals", list),
            ("event", dict),
            ("strategy", dict),
            ("summary", dict),
        ):
            if not isinstance(fetched.get(section), section_type):
                errors.append(f"Fear & Greed artifact {section} is missing")
        event = fetched.get("event")
        if isinstance(event, dict):
            if event.get("asset") != record.effective_inputs["eventAsset"]:
                errors.append(
                    "Fear & Greed event asset does not match effectiveInputs"
                )
            if event.get("sample") != record.effective_inputs["eventSample"]:
                errors.append(
                    "Fear & Greed event sample does not match effectiveInputs"
                )
        summary = fetched.get("summary")
        if isinstance(summary, dict):
            if summary.get("methodologyVersion") != METHODOLOGY_VERSION:
                errors.append(
                    "Fear & Greed summary methodologyVersion is invalid"
                )
            if summary.get("eventAsset") != record.effective_inputs["eventAsset"]:
                errors.append(
                    "Fear & Greed summary eventAsset does not match effectiveInputs"
                )
            if summary.get("eventSample") != record.effective_inputs["eventSample"]:
                errors.append(
                    "Fear & Greed summary eventSample does not match effectiveInputs"
                )

        result_key = fetched.get("resultKey")
        if not isinstance(result_key, str) or not SHA256_PATTERN.fullmatch(
            result_key
        ):
            errors.append(
                "Fear & Greed artifact resultKey must be a lowercase SHA-256 digest"
            )
        identity = fetched.get("resultIdentity")
        if not isinstance(identity, dict):
            errors.append("Fear & Greed resultIdentity is missing")
        elif identity.get("identityVersion") != RESULT_IDENTITY_VERSION:
            errors.append("Fear & Greed resultIdentity version is invalid")
        elif identity.get("resultKey") != result_key:
            errors.append("Fear & Greed resultIdentity does not bind resultKey")
        else:
            key_parts = identity.get("keyParts")
            expected_key_part_fields = {
                "identityVersion",
                "canonicalJsonVersion",
                "binding",
                "dataIdentity",
                "codeIdentity",
            }
            if (
                not isinstance(key_parts, dict)
                or set(key_parts) != expected_key_part_fields
            ):
                errors.append("Fear & Greed resultIdentity keyParts are invalid")
            else:
                if canonical_sha256(key_parts) != result_key:
                    errors.append(
                        "Fear & Greed resultIdentity keyParts do not reproduce resultKey"
                    )
                if key_parts.get("identityVersion") != RESULT_IDENTITY_VERSION:
                    errors.append(
                        "Fear & Greed keyParts identityVersion is invalid"
                    )
                if key_parts.get("canonicalJsonVersion") != CANONICAL_JSON_VERSION:
                    errors.append(
                        "Fear & Greed keyParts canonicalJsonVersion is invalid"
                    )
                expected_identity_binding = {
                    "projectId": record.project_id,
                    "runId": record.run_id,
                    "inputSchemaVersion": record.input_schema_version,
                    "inputSchemaHash": record.input_schema_hash,
                    "configHashAlgorithm": record.config_hash_algorithm,
                    "configHash": record.config_hash,
                    "effectiveConfigHash": manifest.effective_config_hash,
                }
                if key_parts.get("binding") != expected_identity_binding:
                    errors.append(
                        "Fear & Greed result identity binding does not match the run"
                    )

        try:
            data_identity = _artifact_data_identity(fetched)
        except (TypeError, ValueError) as exc:
            errors.append(str(exc))
            data_identity = None
        if data_identity is not None:
            expected_data_identity = manifest.data_identity.model_dump(
                mode="json",
                by_alias=True,
            )
            if data_identity != expected_data_identity:
                errors.append(
                    "Fear & Greed artifact data identity does not match the manifest"
                )
            if data_identity["dataAsOf"] != manifest.data_as_of.isoformat():
                errors.append(
                    "Fear & Greed artifact dataAsOf does not match the manifest"
                )
            if isinstance(identity, dict):
                key_parts = identity.get("keyParts")
                if (
                    isinstance(key_parts, dict)
                    and key_parts.get("dataIdentity") != data_identity
                ):
                    errors.append(
                        "Fear & Greed result identity does not bind artifact data"
                    )

        if isinstance(identity, dict):
            key_parts = identity.get("keyParts")
            if isinstance(key_parts, dict):
                commit_sha = manifest.code_version.rsplit("@", 1)[-1]
                expected_code_identity = {
                    "repository": "SonChangGi/fearNgreed",
                    "commitSha": commit_sha,
                    "methodologyVersion": METHODOLOGY_VERSION,
                }
                if key_parts.get("codeIdentity") != expected_code_identity:
                    errors.append(
                        "Fear & Greed result identity does not bind code identity"
                    )

        calculated_at = fetched.get("calculatedAt")
        try:
            parsed_calculated_at = datetime.fromisoformat(str(calculated_at))
        except ValueError:
            errors.append("Fear & Greed calculatedAt is not an ISO-8601 timestamp")
        else:
            if (
                parsed_calculated_at.tzinfo is None
                or parsed_calculated_at.utcoffset() is None
                or parsed_calculated_at != manifest.calculated_at
            ):
                errors.append(
                    "Fear & Greed calculatedAt does not match the manifest"
                )

        try:
            expected_payload = _bounded_result_payload(fetched)
        except (TypeError, ValueError) as exc:
            errors.append(str(exc))
        else:
            if manifest.payload != expected_payload:
                errors.append(
                    "Fear & Greed callback payload is not the bounded artifact summary"
                )

        parsed_url = urlparse(str(manifest.artifact.url))
        match = ARTIFACT_PATH_PATTERN.fullmatch(parsed_url.path)
        if match is None or match.group("result_key") != result_key:
            errors.append("Fear & Greed artifact URL does not bind resultKey")

    @staticmethod
    def payload_from_artifact(
        record: RunRecord,
        artifact_payload: dict[str, Any],
    ) -> dict[str, Any]:
        del record
        return _bounded_result_payload(artifact_payload)
