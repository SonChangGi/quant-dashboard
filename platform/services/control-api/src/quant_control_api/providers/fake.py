from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any

from ..best_factor import RESULT_CONTRACT_VERSION, canonical_json_bytes
from ..models import (
    ArtifactIdentity,
    DataIdentity,
    ResultBinding,
    RunStatus,
    WorkerResultManifest,
)
from .base import DispatchEnvelope, DispatchReceipt, ProviderObservation


class FakeWorkerProvider:
    """Deterministic worker used only by tests and local contract demos."""

    name = "fake"
    run_creation_enabled = True
    supports_fallback_rejection = True
    status_tracking = "native"

    def __init__(self, *, auto_complete: bool = True) -> None:
        self.auto_complete = auto_complete
        self.dispatched: dict[str, DispatchEnvelope] = {}
        self.observations: dict[str, ProviderObservation] = {}
        self._lock = asyncio.Lock()

    async def dispatch(self, envelope: DispatchEnvelope) -> DispatchReceipt:
        provider_run_id = f"fake:{envelope.run_id}"
        async with self._lock:
            self.dispatched[provider_run_id] = envelope
            if self.auto_complete:
                manifest = self.make_manifest(envelope)
                self.observations[provider_run_id] = ProviderObservation(
                    status=RunStatus.VALIDATING,
                    manifest=manifest,
                    artifact_bytes=canonical_json_bytes(manifest.payload),
                )
            else:
                self.observations[provider_run_id] = ProviderObservation(status=RunStatus.DISPATCHED)
        return DispatchReceipt(provider_run_id=provider_run_id)

    async def reconcile_dispatch(
        self,
        envelope: DispatchEnvelope,
    ) -> DispatchReceipt | None:
        provider_run_id = f"fake:{envelope.run_id}"
        async with self._lock:
            if provider_run_id not in self.dispatched:
                return None
        return DispatchReceipt(provider_run_id=provider_run_id)

    async def check_ready(self) -> None:
        return None

    async def inspect(self, provider_run_id: str) -> ProviderObservation:
        async with self._lock:
            return self.observations[provider_run_id]

    async def set_observation(self, provider_run_id: str, observation: ProviderObservation) -> None:
        async with self._lock:
            self.observations[provider_run_id] = observation

    @staticmethod
    def make_manifest(
        envelope: DispatchEnvelope,
        *,
        payload_overrides: dict[str, Any] | None = None,
    ) -> WorkerResultManifest:
        calculated_at = datetime(2026, 7, 24, 0, 0, tzinfo=UTC)
        data_as_of = date(2026, 7, 23)
        payload: dict[str, Any] = {
            "schema_version": 1,
            "generated_at": calculated_at.isoformat().replace("+00:00", "Z"),
            "summary": {
                "best_factor": "momentum_6m",
                "data_end_date": data_as_of.isoformat(),
                "source_hash": "a54e4adee3d58bc3",
            },
        }
        if payload_overrides:
            payload.update(payload_overrides)
        artifact_bytes = canonical_json_bytes(payload)
        import hashlib

        artifact_sha = hashlib.sha256(artifact_bytes).hexdigest()
        return WorkerResultManifest(
            binding=ResultBinding(
                project_id=envelope.project_id,
                run_id=envelope.run_id,
                input_schema_version=envelope.input_schema_version,
                input_schema_hash=envelope.input_schema_hash,
                config_hash_algorithm=envelope.config_hash_algorithm,
                config_hash=envelope.config_hash,
            ),
            requested_inputs=envelope.requested_inputs,
            normalized_inputs=envelope.normalized_inputs,
            effective_inputs=envelope.effective_inputs,
            effective_config_hash=envelope.config_hash,
            ignored_inputs=[],
            fallbacks=[],
            fallback_used=False,
            data_as_of=data_as_of,
            calculated_at=calculated_at,
            code_version="d" * 40,
            data_identity=DataIdentity(
                source="fake-best-factor-fixture",
                source_hash="a54e4adee3d58bc3",
                data_as_of=data_as_of,
            ),
            artifact=ArtifactIdentity(
                url=(
                    "https://raw.githubusercontent.com/SonChangGi/best-factor/"
                    f"{'d' * 40}/docs/data/latest-results.json"
                ),
                sha256=artifact_sha,
                byte_size=len(artifact_bytes),
                contract_version=RESULT_CONTRACT_VERSION,
            ),
            payload=payload,
        )
