from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any, ClassVar

from ..canonical import canonical_json_bytes
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
                    artifact_bytes=self.artifact_bytes(manifest),
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

    _artifact_bytes: ClassVar[dict[str, bytes]] = {}

    @classmethod
    def artifact_bytes(cls, manifest: WorkerResultManifest) -> bytes:
        return cls._artifact_bytes[str(manifest.artifact.url)]

    @classmethod
    def make_manifest(
        cls,
        envelope: DispatchEnvelope,
        *,
        payload_overrides: dict[str, Any] | None = None,
    ) -> WorkerResultManifest:
        from ..adapters.fear_greed import (
            CANONICAL_JSON_VERSION,
            METHODOLOGY_VERSION,
            RESULT_CONTRACT_VERSION,
            RESULT_IDENTITY_VERSION,
            _bounded_result_payload,
            canonical_sha256,
        )

        if envelope.project_id != "fear-greed":
            raise ValueError("The automatic fixture models Fear & Greed; use a project-owned fixture otherwise")
        calculated_at = datetime(2026, 7, 24, 0, 0, tzinfo=UTC)
        data_as_of = date(2026, 7, 23)
        data = {
            "source": "fearngreed-python-control-inputs",
            "sourceHash": "a" * 64,
            "dataAsOf": data_as_of.isoformat(),
        }
        binding = ResultBinding(
            project_id=envelope.project_id,
            run_id=envelope.run_id,
            input_schema_version=envelope.input_schema_version,
            input_schema_hash=envelope.input_schema_hash,
            config_hash_algorithm=envelope.config_hash_algorithm,
            config_hash=envelope.config_hash,
        )
        key_parts = {
            "identityVersion": RESULT_IDENTITY_VERSION,
            "canonicalJsonVersion": CANONICAL_JSON_VERSION,
            "binding": {**binding.model_dump(mode="json", by_alias=True), "effectiveConfigHash": envelope.config_hash},
            "dataIdentity": data,
            "codeIdentity": {
                "repository": "SonChangGi/fearNgreed",
                "commitSha": "d" * 40,
                "methodologyVersion": METHODOLOGY_VERSION,
            },
        }
        result_key = canonical_sha256(key_parts)
        payload: dict[str, Any] = {
            "schemaVersion": 1,
            "contract": RESULT_CONTRACT_VERSION,
            "projectId": "fear-greed",
            "resultKey": result_key,
            "resultIdentity": {
                "identityVersion": RESULT_IDENTITY_VERSION,
                "resultKey": result_key,
                "keyParts": key_parts,
            },
            "requestedInputs": envelope.requested_inputs,
            "normalizedInputs": envelope.normalized_inputs,
            "effectiveInputs": envelope.effective_inputs,
            "data": data,
            "calculatedAt": calculated_at.isoformat(),
            "signals": [],
            "event": {
                "asset": envelope.effective_inputs["eventAsset"],
                "sample": envelope.effective_inputs["eventSample"],
            },
            "strategy": {"position": "cash"},
            "summary": {
                "eventAsset": envelope.effective_inputs["eventAsset"],
                "eventSample": envelope.effective_inputs["eventSample"],
                "methodologyVersion": METHODOLOGY_VERSION,
            },
        }
        if payload_overrides:
            payload.update(payload_overrides)
        artifact_bytes = canonical_json_bytes(payload)
        import hashlib

        url = f"https://sonchanggi.github.io/fearNgreed/data/control-runs/v1/{envelope.run_id}/{result_key}.json"
        cls._artifact_bytes[url] = artifact_bytes
        return WorkerResultManifest(
            binding=binding,
            requested_inputs=envelope.requested_inputs,
            normalized_inputs=envelope.normalized_inputs,
            effective_inputs=envelope.effective_inputs,
            effective_config_hash=envelope.config_hash,
            ignored_inputs=[],
            fallbacks=[],
            fallback_used=False,
            data_as_of=data_as_of,
            calculated_at=calculated_at,
            code_version=f"github:SonChangGi/fearNgreed@{'d' * 40}",
            data_identity=DataIdentity.model_validate(data),
            artifact=ArtifactIdentity(
                url=url,
                sha256=hashlib.sha256(artifact_bytes).hexdigest(),
                byte_size=len(artifact_bytes),
                contract_version=RESULT_CONTRACT_VERSION,
            ),
            payload=_bounded_result_payload(payload),
        )
