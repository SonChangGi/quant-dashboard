from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from ..best_factor import (
    CONFIG_HASH_ALGORITHM,
    DEFAULT_CONFIG,
    INPUT_FIELDS,
    INPUT_SCHEMA_HASH,
    INPUT_SCHEMA_VERSION,
    PROJECT_ID,
    PROJECT_NAME,
    STATIC_FALLBACK_URL,
    canonical_sha256,
    normalize_inputs,
)
from ..binding import bounded_best_result_payload, validate_result_binding
from ..models import (
    ArtifactIdentity,
    FallbackCapability,
    WorkerResultManifest,
)
from ..providers.base import DispatchEnvelope, WorkerProvider
from ..providers.github_actions import workflow_inputs as best_workflow_inputs
from ..store import RunRecord
from .base import NormalizedAnalysisInputs, ProjectRequestError

_BEST_FACTOR_IMMUTABLE_PATH = re.compile(
    r"^/SonChangGi/best-factor/[0-9a-f]{40}/docs/data/latest-results\.json$"
)


class BestFactorAdapter:
    project_id = PROJECT_ID
    project_name = PROJECT_NAME
    input_schema_version = INPUT_SCHEMA_VERSION
    input_schema_hash = INPUT_SCHEMA_HASH
    config_hash_algorithm = CONFIG_HASH_ALGORITHM
    default_inputs = DEFAULT_CONFIG
    input_fields = INPUT_FIELDS
    static_fallback_url = STATIC_FALLBACK_URL

    def normalize_inputs(self, inputs: dict[str, Any]) -> NormalizedAnalysisInputs:
        try:
            normalized = normalize_inputs(inputs)
        except (ValidationError, ValueError, TypeError) as exc:
            raise ProjectRequestError(
                status_code=422,
                code="invalid_analysis_inputs",
                message=str(exc),
            ) from exc
        return NormalizedAnalysisInputs(
            requested=normalized.requested,
            normalized=normalized.normalized,
            effective=normalized.effective,
            config_hash=normalized.config_hash,
        )

    def validate_run_request(
        self,
        *,
        allow_fallback: bool,
        normalized: NormalizedAnalysisInputs,
        provider: WorkerProvider,
    ) -> None:
        if allow_fallback:
            raise ProjectRequestError(
                status_code=409,
                code="fallback_not_supported_for_controlled_runs",
                message=(
                    "Best Factor controlled runs currently require allowFallback=false. "
                    "Scheduled owner refreshes retain their separately audited fallback path."
                ),
            )
        fallback_possible = float(normalized.effective["min_market_cap"]) > 0
        if fallback_possible and not provider.supports_fallback_rejection:
            raise ProjectRequestError(
                status_code=409,
                code="fallback_rejection_not_enforceable",
                message=(
                    "The selected worker can automatically remove the market-cap filter. "
                    "Set min_market_cap=0 or use a worker that can enforce fail-closed execution."
                ),
            )

    def fallback_capability(self, provider: WorkerProvider) -> FallbackCapability:
        return FallbackCapability(
            default_allowed=False,
            analysis_run_allow_fallback=False,
            scheduled_owner_operation_may_fallback=True,
            possible_when="min_market_cap > 0 and market-cap metadata preflight is insufficient",
            reason="market_cap_metadata_insufficient_preflight",
            provider_can_enforce_rejection=provider.supports_fallback_rejection,
        )

    @staticmethod
    def canonical_sha256(value: Any) -> str:
        return canonical_sha256(value)

    @staticmethod
    def workflow_inputs(envelope: DispatchEnvelope) -> dict[str, str]:
        return best_workflow_inputs(envelope)

    def validate_artifact_url(
        self,
        record: RunRecord,
        artifact: ArtifactIdentity,
    ) -> None:
        del record
        parsed = urlparse(str(artifact.url))
        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
            or parsed.query
            or parsed.fragment
            or parsed.hostname != "raw.githubusercontent.com"
            or not _BEST_FACTOR_IMMUTABLE_PATH.fullmatch(parsed.path)
        ):
            raise ValueError("artifact URL is not an immutable Best Factor commit result")

    @staticmethod
    def validate_result_binding(
        record: RunRecord,
        manifest: WorkerResultManifest,
        artifact_bytes: bytes,
    ) -> None:
        validate_result_binding(record, manifest, artifact_bytes)

    @staticmethod
    def payload_from_artifact(
        record: RunRecord,
        artifact_payload: dict[str, Any],
    ) -> dict[str, Any]:
        del record
        return bounded_best_result_payload(artifact_payload)
