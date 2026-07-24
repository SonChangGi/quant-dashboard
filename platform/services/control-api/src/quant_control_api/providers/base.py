from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..models import RunStatus, WorkerResultManifest


class ProviderUnavailableError(RuntimeError):
    pass


class ProviderDispatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class DispatchEnvelope:
    project_id: str
    run_id: str
    input_schema_version: str
    input_schema_hash: str
    config_hash_algorithm: str
    config_hash: str
    requested_inputs: dict[str, Any]
    normalized_inputs: dict[str, Any]
    effective_inputs: dict[str, Any]
    allow_fallback: bool


@dataclass(frozen=True)
class DispatchReceipt:
    provider_run_id: str
    status: RunStatus = RunStatus.DISPATCHED


@dataclass(frozen=True)
class ProviderObservation:
    status: RunStatus
    manifest: WorkerResultManifest | None = None
    artifact_bytes: bytes | None = None
    error_code: str | None = None
    error_message: str | None = None


class WorkerProvider(Protocol):
    name: str
    run_creation_enabled: bool
    supports_fallback_rejection: bool
    status_tracking: str

    async def dispatch(self, envelope: DispatchEnvelope) -> DispatchReceipt: ...

    async def reconcile_dispatch(
        self,
        envelope: DispatchEnvelope,
    ) -> DispatchReceipt | None: ...

    async def check_ready(self) -> None: ...

    async def inspect(self, provider_run_id: str) -> ProviderObservation: ...
