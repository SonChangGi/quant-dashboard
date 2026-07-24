from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..models import (
    ArtifactIdentity,
    FallbackCapability,
    InputFieldCapability,
    WorkerResultManifest,
)
from ..providers.base import DispatchEnvelope, WorkerProvider
from ..store import RunRecord


@dataclass(frozen=True, slots=True)
class NormalizedAnalysisInputs:
    requested: dict[str, Any]
    normalized: dict[str, Any]
    effective: dict[str, Any]
    config_hash: str


class ProjectRequestError(ValueError):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class AnalysisProjectAdapter(Protocol):
    project_id: str
    project_name: str
    input_schema_version: str
    input_schema_hash: str
    config_hash_algorithm: str
    default_inputs: dict[str, Any]
    input_fields: list[InputFieldCapability]
    static_fallback_url: str

    def normalize_inputs(self, inputs: dict[str, Any]) -> NormalizedAnalysisInputs: ...

    def validate_run_request(
        self,
        *,
        allow_fallback: bool,
        normalized: NormalizedAnalysisInputs,
        provider: WorkerProvider,
    ) -> None: ...

    def fallback_capability(self, provider: WorkerProvider) -> FallbackCapability: ...

    def canonical_sha256(self, value: Any) -> str: ...

    def workflow_inputs(self, envelope: DispatchEnvelope) -> dict[str, str]: ...

    def validate_artifact_url(
        self,
        record: RunRecord,
        artifact: ArtifactIdentity,
    ) -> None: ...

    def validate_result_binding(
        self,
        record: RunRecord,
        manifest: WorkerResultManifest,
        artifact_bytes: bytes,
    ) -> None: ...

    def payload_from_artifact(
        self,
        record: RunRecord,
        artifact_payload: dict[str, Any],
    ) -> dict[str, Any]: ...
