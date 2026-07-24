from __future__ import annotations

import json
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class RunStatus(StrEnum):
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    VALIDATING = "validating"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = {RunStatus.PUBLISHED, RunStatus.FAILED, RunStatus.CANCELLED}


class RunCreateRequest(APIModel):
    input_schema_version: Literal[
        "best-factor/v1",
        "momentum/v1",
        "fear-greed/control-inputs-v1",
    ]
    inputs: dict[str, Any] = Field(default_factory=dict)
    allow_fallback: bool = False


class InputFieldCapability(APIModel):
    key: str
    label: str
    type: Literal["enum", "integer", "number", "string", "string-list"]
    required: bool = True
    default: Any
    choices: list[str] | None = None
    minimum: float | None = None
    maximum: float | None = None
    exclusive_minimum: float | None = None
    exclusive_maximum: float | None = None
    unit: str | None = None
    cli_argument: str
    workflow_input: str


class FallbackCapability(APIModel):
    default_allowed: bool = False
    analysis_run_allow_fallback: bool = False
    scheduled_owner_operation_may_fallback: bool = True
    possible_when: str
    reason: str
    provider_can_enforce_rejection: bool


class ProviderCapability(APIModel):
    name: str
    run_creation_enabled: bool
    executes_heavy_analysis_in_api: bool = False
    status_tracking: Literal["native", "adapter-required", "disabled"]
    result_binding: Literal["manifest-required", "disabled"]
    owner: str | None = None
    repository: str | None = None
    workflow: str | None = None
    ref: str | None = None


class ProjectCapabilities(APIModel):
    project_id: str
    project_name: str
    input_schema_version: str
    input_schema_hash: str
    config_hash_algorithm: str
    accepts_runs: bool
    default_inputs: dict[str, Any]
    default_config_hash: str
    inputs: list[InputFieldCapability]
    fallback: FallbackCapability
    provider: ProviderCapability
    endpoints: dict[str, str]
    static_fallback_url: HttpUrl


class DataIdentity(APIModel):
    source: str = Field(min_length=1, max_length=500)
    source_hash: str
    data_as_of: date

    @field_validator("source_hash")
    @classmethod
    def validate_source_hash(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) < 8 or len(normalized) > 128 or any(ch not in "0123456789abcdef" for ch in normalized):
            raise ValueError("sourceHash must be an 8-128 character hexadecimal digest")
        return normalized


class ArtifactIdentity(APIModel):
    url: HttpUrl
    sha256: str
    byte_size: int = Field(ge=0)
    contract_version: str = Field(min_length=1, max_length=120)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
            raise ValueError("artifact sha256 must be a 64-character hexadecimal digest")
        return normalized


class FallbackEvent(APIModel):
    input: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=120)
    requested: Any
    effective: Any
    reason: str = Field(min_length=1, max_length=500)


class RunStatusResponse(APIModel):
    project_id: str
    run_id: str
    status: RunStatus
    input_schema_version: str
    input_schema_hash: str
    config_hash_algorithm: str
    config_hash: str
    effective_config_hash: str
    requested_inputs: dict[str, Any]
    normalized_inputs: dict[str, Any]
    effective_inputs: dict[str, Any]
    ignored_inputs: list[str] = Field(default_factory=list)
    allow_fallback: bool
    fallbacks: list[FallbackEvent] = Field(default_factory=list)
    fallback_used: bool = False
    fallback_reason: str | None = None
    provider: str
    provider_run_id: str | None = None
    replayed: bool = False
    created_at: datetime
    updated_at: datetime
    data_as_of: date | None = None
    calculated_at: datetime | None = None
    code_version: str | None = None
    data_identity: DataIdentity | None = None
    artifact: ArtifactIdentity | None = None
    error_code: str | None = None
    error_message: str | None = None


class ResultBinding(APIModel):
    project_id: str
    run_id: str
    input_schema_version: str
    input_schema_hash: str
    config_hash_algorithm: str
    config_hash: str


class WorkerResultManifest(APIModel):
    binding: ResultBinding
    requested_inputs: dict[str, Any]
    normalized_inputs: dict[str, Any]
    effective_inputs: dict[str, Any]
    effective_config_hash: str
    ignored_inputs: list[str] = Field(default_factory=list)
    fallbacks: list[FallbackEvent] = Field(default_factory=list)
    fallback_used: bool
    fallback_reason: str | None = None
    data_as_of: date
    calculated_at: datetime
    code_version: str = Field(min_length=1, max_length=200)
    data_identity: DataIdentity
    artifact: ArtifactIdentity
    payload: dict[str, Any]

    @field_validator("calculated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("calculatedAt must include a timezone")
        return value

    @field_validator("payload")
    @classmethod
    def require_bounded_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("payload must be strict JSON") from exc
        if len(encoded) > 64 * 1024:
            raise ValueError("payload must not exceed 64 KiB")
        return value


class WorkerFailureManifest(APIModel):
    binding: ResultBinding
    error_code: Literal[
        "worker_workflow_failed",
        "worker_analysis_failed",
        "worker_publication_failed",
    ]
    error_message: str = Field(min_length=1, max_length=1000)
    provider_run_id: str = Field(min_length=1, max_length=200)
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurredAt must include a timezone")
        return value


class RunResultResponse(APIModel):
    project_id: str
    run_id: str
    status: Literal[RunStatus.PUBLISHED] = RunStatus.PUBLISHED
    input_schema_version: str
    input_schema_hash: str
    config_hash_algorithm: str
    config_hash: str
    effective_config_hash: str
    requested_inputs: dict[str, Any]
    normalized_inputs: dict[str, Any]
    effective_inputs: dict[str, Any]
    ignored_inputs: list[str] = Field(default_factory=list)
    allow_fallback: bool
    fallbacks: list[FallbackEvent] = Field(default_factory=list)
    fallback_used: bool
    fallback_reason: str | None = None
    data_as_of: date
    calculated_at: datetime
    code_version: str
    data_identity: DataIdentity
    artifact: ArtifactIdentity
    payload: dict[str, Any]
