from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx

from .adapters import (
    AnalysisProjectAdapter,
    ProjectAdapterRegistry,
    ProjectRequestError,
    default_project_adapters,
)
from .artifacts import ArtifactFetcher, ArtifactVerificationError
from .binding import ResultBindingError
from .dual_write import DualWritePublisher
from .models import (
    TERMINAL_STATUSES,
    ProjectCapabilities,
    ProviderCapability,
    ResultBinding,
    RunCreateRequest,
    RunResultResponse,
    RunStatus,
    RunStatusResponse,
    WorkerFailureManifest,
    WorkerResultManifest,
)
from .providers.base import (
    DispatchEnvelope,
    DispatchReceipt,
    ProviderDispatchError,
    ProviderUnavailableError,
    WorkerProvider,
)
from .store import (
    DispatchLease,
    DispatchLeaseLostError,
    IdempotencyConflictError,
    InvalidRunTransitionError,
    RunNotFoundError,
    RunRecord,
    RunStore,
    digest_idempotency_key,
    utc_now,
)

IDEMPOTENCY_KEY_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}")


class ControlPlaneError(RuntimeError):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ControlPlaneService:
    def __init__(
        self,
        *,
        provider: WorkerProvider | None = None,
        providers: dict[str, WorkerProvider] | None = None,
        adapters: ProjectAdapterRegistry | None = None,
        store: RunStore,
        publisher: DualWritePublisher,
        artifact_fetcher: ArtifactFetcher,
        dispatcher_id: str | None = None,
        dispatch_lease_seconds: int = 30,
        dispatch_max_attempts: int = 5,
        dispatch_retry_base_seconds: int = 2,
        dispatch_retry_max_seconds: int = 300,
        dispatch_before_provider_hook: Callable[[DispatchLease], None] | None = None,
        dispatch_after_provider_hook: Callable[[DispatchReceipt], None] | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        if provider is not None and providers is not None:
            raise ValueError("pass either provider or providers, not both")
        self.adapters = adapters or default_project_adapters()
        if providers is None:
            if provider is None:
                raise ValueError("a worker provider or provider registry is required")
            providers = {
                project_id: provider
                for project_id in self.adapters.project_ids
            }
        missing_providers = set(self.adapters.project_ids) - set(providers)
        unknown_providers = set(providers) - set(self.adapters.project_ids)
        if missing_providers or unknown_providers:
            raise ValueError(
                "provider registry must exactly match project adapters "
                f"(missing={sorted(missing_providers)}, unknown={sorted(unknown_providers)})"
            )
        self.providers = dict(providers)
        # Backward-compatible handle for existing Best-only integration code.
        self.provider = self.providers["best-factor"]
        self.store = store
        self.publisher = publisher
        self.artifact_fetcher = artifact_fetcher
        self.dispatcher_id = dispatcher_id or f"control-api:{uuid.uuid4()}"
        self.dispatch_lease_seconds = dispatch_lease_seconds
        self.dispatch_max_attempts = dispatch_max_attempts
        self.dispatch_retry_base_seconds = dispatch_retry_base_seconds
        self.dispatch_retry_max_seconds = dispatch_retry_max_seconds
        self.dispatch_before_provider_hook = dispatch_before_provider_hook
        self.dispatch_after_provider_hook = dispatch_after_provider_hook
        self.clock = clock

    def capabilities(self, project_id: str) -> ProjectCapabilities:
        adapter = self._adapter_for(project_id)
        provider = self._provider_for(project_id)
        capability = ProjectCapabilities(
            project_id=adapter.project_id,
            project_name=adapter.project_name,
            input_schema_version=adapter.input_schema_version,
            input_schema_hash=adapter.input_schema_hash,
            config_hash_algorithm=adapter.config_hash_algorithm,
            accepts_runs=provider.run_creation_enabled,
            default_inputs=adapter.default_inputs,
            default_config_hash=adapter.canonical_sha256(adapter.default_inputs),
            inputs=adapter.input_fields,
            fallback=adapter.fallback_capability(provider),
            provider=ProviderCapability(
                name=provider.name,
                run_creation_enabled=provider.run_creation_enabled,
                executes_heavy_analysis_in_api=False,
                status_tracking=provider.status_tracking,  # type: ignore[arg-type]
                result_binding=("manifest-required" if provider.run_creation_enabled else "disabled"),
                owner=getattr(provider, "owner", None),
                repository=getattr(provider, "repo", None),
                workflow=getattr(provider, "workflow", None),
                ref=getattr(provider, "ref", None),
            ),
            endpoints={
                "createRun": f"/v1/projects/{adapter.project_id}/runs",
                "status": "/v1/runs/{runId}",
                "result": "/v1/runs/{runId}/result",
            },
            static_fallback_url=adapter.static_fallback_url,
        )
        self.publisher.publish_project(capability)
        return capability

    async def create_run(
        self,
        project_id: str,
        request: RunCreateRequest,
        idempotency_key: str,
    ) -> RunStatusResponse:
        adapter = self._adapter_for(project_id)
        provider = self._provider_for(project_id)
        if not provider.run_creation_enabled:
            raise ControlPlaneError(
                status_code=503,
                code="worker_provider_disabled",
                message="No analysis worker provider is enabled",
            )
        # Queue the project row before config/run rows so direct API clients do
        # not have to call capabilities first for the optional Supabase mirror.
        self.capabilities(project_id)
        if not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key):
            raise ControlPlaneError(
                status_code=400,
                code="invalid_idempotency_key",
                message="Idempotency-Key must be 8-128 safe ASCII characters",
            )
        if request.input_schema_version != adapter.input_schema_version:
            raise ControlPlaneError(
                status_code=409,
                code="input_schema_mismatch",
                message=f"Expected inputSchemaVersion {adapter.input_schema_version}",
            )
        try:
            normalized = adapter.normalize_inputs(request.inputs)
            adapter.validate_run_request(
                allow_fallback=request.allow_fallback,
                normalized=normalized,
                provider=provider,
            )
        except ProjectRequestError as exc:
            raise ControlPlaneError(
                status_code=exc.status_code,
                code=exc.code,
                message=exc.message,
            ) from exc

        request_digest = adapter.canonical_sha256(
            {
                "projectId": adapter.project_id,
                "inputSchemaVersion": adapter.input_schema_version,
                "effectiveInputs": normalized.effective,
                "allowFallback": request.allow_fallback,
            }
        )
        now = self.clock()
        record = RunRecord(
            project_id=adapter.project_id,
            run_id=str(uuid.uuid4()),
            status=RunStatus.QUEUED,
            input_schema_version=adapter.input_schema_version,
            input_schema_hash=adapter.input_schema_hash,
            config_hash_algorithm=adapter.config_hash_algorithm,
            config_hash=normalized.config_hash,
            effective_config_hash=normalized.config_hash,
            requested_inputs=normalized.requested,
            normalized_inputs=normalized.normalized,
            effective_inputs=normalized.effective,
            ignored_inputs=[],
            allow_fallback=request.allow_fallback,
            provider=provider.name,
            idempotency_key_digest=digest_idempotency_key(idempotency_key),
            request_digest=request_digest,
            created_at=now,
            updated_at=now,
            project_name=adapter.project_name,
        )
        try:
            stored, replayed = await self.store.create_or_replay(
                record,
                dispatch_max_attempts=self.dispatch_max_attempts,
            )
        except IdempotencyConflictError as exc:
            raise ControlPlaneError(
                status_code=409,
                code="idempotency_conflict",
                message=str(exc),
            ) from exc
        if replayed:
            if stored.status == RunStatus.QUEUED:
                await self.dispatch_pending_once(run_id=stored.run_id)
                stored = await self._get_run(stored.run_id)
            return self._status_response(stored, replayed=True)

        self.publisher.publish_run(stored)
        await self.dispatch_pending_once(run_id=stored.run_id)
        return self._status_response(await self._get_run(stored.run_id))

    async def dispatch_pending_once(
        self,
        *,
        run_id: str | None = None,
        now: datetime | None = None,
    ) -> RunRecord | None:
        """Claim and process at most one durable dispatch event."""
        lease = await self.store.claim_dispatch(
            lease_owner=self.dispatcher_id,
            lease_seconds=self.dispatch_lease_seconds,
            run_id=run_id,
            now=now,
        )
        if lease is None:
            return None
        if self.dispatch_before_provider_hook is not None:
            self.dispatch_before_provider_hook(lease)
        envelope = self._dispatch_envelope(lease.run)
        provider = self._provider_for(lease.run.project_id)
        try:
            receipt = None
            if lease.outbox.attempt_count > 1:
                receipt = await provider.reconcile_dispatch(envelope)
            if receipt is None:
                receipt = await provider.dispatch(envelope)
        except (
            ProviderDispatchError,
            ProviderUnavailableError,
            httpx.HTTPError,
            ValueError,
        ) as exc:
            retry = await self.store.reschedule_dispatch(
                run_id=lease.run.run_id,
                lease_token=lease.outbox.lease_token or "",
                error_code="worker_dispatch_failed",
                error_message=str(exc),
                base_delay_seconds=self.dispatch_retry_base_seconds,
                max_delay_seconds=self.dispatch_retry_max_seconds,
                now=now,
            )
            if retry.dead_lettered:
                self.publisher.publish_run(retry.run)
            return retry.run

        if self.dispatch_after_provider_hook is not None:
            self.dispatch_after_provider_hook(receipt)
        try:
            dispatched = await self.store.acknowledge_dispatch(
                run_id=lease.run.run_id,
                lease_token=lease.outbox.lease_token or "",
                provider_run_id=receipt.provider_run_id,
                now=now,
            )
        except DispatchLeaseLostError:
            return await self._get_run(lease.run.run_id)
        self.publisher.publish_run(dispatched)
        return dispatched

    @staticmethod
    def _dispatch_envelope(record: RunRecord) -> DispatchEnvelope:
        return DispatchEnvelope(
            project_id=record.project_id,
            run_id=record.run_id,
            input_schema_version=record.input_schema_version,
            input_schema_hash=record.input_schema_hash,
            config_hash_algorithm=record.config_hash_algorithm,
            config_hash=record.config_hash,
            requested_inputs=record.requested_inputs,
            normalized_inputs=record.normalized_inputs,
            effective_inputs=record.effective_inputs,
            allow_fallback=record.allow_fallback,
        )

    async def get_status(self, run_id: str) -> RunStatusResponse:
        record = await self._get_run(run_id)
        refreshed = await self._refresh(record)
        return self._status_response(refreshed)

    async def get_result(self, run_id: str) -> RunResultResponse:
        record = await self._refresh(await self._get_run(run_id))
        if record.status != RunStatus.PUBLISHED:
            raise ControlPlaneError(
                status_code=409,
                code="result_not_published",
                message=f"Run is {record.status.value}; a result is available only after published",
            )
        manifest = record.result_manifest or await self._restore_manifest(record)
        return RunResultResponse(
            project_id=record.project_id,
            run_id=record.run_id,
            input_schema_version=record.input_schema_version,
            input_schema_hash=record.input_schema_hash,
            config_hash_algorithm=record.config_hash_algorithm,
            config_hash=record.config_hash,
            effective_config_hash=record.effective_config_hash,
            requested_inputs=record.requested_inputs,
            normalized_inputs=record.normalized_inputs,
            effective_inputs=record.effective_inputs,
            ignored_inputs=record.ignored_inputs,
            allow_fallback=record.allow_fallback,
            fallbacks=record.fallbacks,
            fallback_used=bool(record.fallback_used),
            fallback_reason=record.fallback_reason,
            data_as_of=manifest.data_as_of,
            calculated_at=manifest.calculated_at,
            code_version=manifest.code_version,
            data_identity=manifest.data_identity,
            artifact=manifest.artifact,
            payload=manifest.payload,
        )

    async def accept_result_manifest(
        self,
        run_id: str,
        manifest: Any,
    ) -> RunStatusResponse:
        record = await self._get_run(run_id)
        if record.status == RunStatus.PUBLISHED:
            restored = record.result_manifest or await self._restore_manifest(record)
            if restored.model_dump(mode="json") == manifest.model_dump(mode="json"):
                return self._status_response(record, replayed=True)
            raise ControlPlaneError(
                status_code=409,
                code="published_result_conflict",
                message="Run already has a different published result",
            )
        if record.status in {RunStatus.FAILED, RunStatus.CANCELLED}:
            raise ControlPlaneError(
                status_code=409,
                code="terminal_run",
                message=f"Cannot attach a result to a {record.status.value} run",
            )
        if record.status == RunStatus.QUEUED:
            try:
                record = await self.store.confirm_dispatch_from_callback(
                    run_id=record.run_id,
                    provider_run_id=f"{record.provider}:{record.run_id}",
                )
            except (DispatchLeaseLostError, InvalidRunTransitionError) as exc:
                raise ControlPlaneError(
                    status_code=409,
                    code="callback_dispatch_conflict",
                    message=str(exc),
                ) from exc
        updated = await self._validate_and_publish(record, manifest)
        if updated.status == RunStatus.FAILED:
            raise ControlPlaneError(
                status_code=409,
                code=updated.error_code or "result_binding_failed",
                message=updated.error_message or "Worker result did not pass binding validation",
            )
        return self._status_response(updated)

    async def accept_worker_failure(
        self,
        run_id: str,
        manifest: WorkerFailureManifest,
    ) -> RunStatusResponse:
        record = await self._get_run(run_id)
        expected_binding = ResultBinding(
            project_id=record.project_id,
            run_id=record.run_id,
            input_schema_version=record.input_schema_version,
            input_schema_hash=record.input_schema_hash,
            config_hash_algorithm=record.config_hash_algorithm,
            config_hash=record.config_hash,
        )
        if manifest.binding != expected_binding:
            raise ControlPlaneError(
                status_code=409,
                code="worker_failure_binding_mismatch",
                message="Worker failure identity does not match the requested run",
            )
        if manifest.provider_run_id != f"{record.provider}:{record.run_id}":
            raise ControlPlaneError(
                status_code=409,
                code="worker_failure_provider_mismatch",
                message="Worker failure providerRunId does not match the run provider",
            )
        if record.status == RunStatus.FAILED:
            if record.error_code == manifest.error_code and record.error_message == manifest.error_message:
                return self._status_response(record, replayed=True)
            raise ControlPlaneError(
                status_code=409,
                code="worker_failure_conflict",
                message="Run already has different terminal failure evidence",
            )
        if record.status in {RunStatus.PUBLISHED, RunStatus.CANCELLED}:
            raise ControlPlaneError(
                status_code=409,
                code="terminal_run",
                message=f"Cannot fail a {record.status.value} run",
            )
        try:
            failed = await self.store.fail_run_from_worker(
                run_id=record.run_id,
                provider_run_id=manifest.provider_run_id,
                error_code=manifest.error_code,
                error_message=manifest.error_message,
            )
        except InvalidRunTransitionError as exc:
            raise ControlPlaneError(
                status_code=409,
                code="terminal_run",
                message=str(exc),
            ) from exc
        self.publisher.publish_run(failed)
        return self._status_response(failed)

    async def expire_stuck_runs_once(
        self,
        *,
        timeout_seconds: int,
        limit: int,
        now: datetime | None = None,
    ) -> list[RunRecord]:
        expired = await self.store.expire_stuck_runs(
            timeout_seconds=timeout_seconds,
            limit=limit,
            now=now,
        )
        for record in expired:
            self.publisher.publish_run(record)
        return expired

    async def _restore_manifest(self, record: RunRecord) -> WorkerResultManifest:
        if (
            record.artifact is None
            or record.data_identity is None
            or record.data_as_of is None
            or record.calculated_at is None
            or record.code_version is None
        ):
            raise ControlPlaneError(
                status_code=409,
                code="durable_result_identity_incomplete",
                message="Published run is missing durable data, code, or artifact identity",
            )
        try:
            adapter = self._adapter_for(record.project_id)
            adapter.validate_artifact_url(record, record.artifact)
            exact_bytes = await self.artifact_fetcher.fetch(record.artifact)
            artifact_payload = json.loads(
                exact_bytes,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-standard JSON number: {value}")),
            )
            if not isinstance(artifact_payload, dict):
                raise TypeError("artifact JSON root must be an object")
            payload = adapter.payload_from_artifact(record, artifact_payload)
            manifest = WorkerResultManifest(
                binding=ResultBinding(
                    project_id=record.project_id,
                    run_id=record.run_id,
                    input_schema_version=record.input_schema_version,
                    input_schema_hash=record.input_schema_hash,
                    config_hash_algorithm=record.config_hash_algorithm,
                    config_hash=record.config_hash,
                ),
                requested_inputs=record.requested_inputs,
                normalized_inputs=record.normalized_inputs,
                effective_inputs=record.effective_inputs,
                effective_config_hash=record.effective_config_hash,
                ignored_inputs=record.ignored_inputs,
                fallbacks=record.fallbacks,
                fallback_used=record.fallback_used,
                fallback_reason=record.fallback_reason,
                data_as_of=record.data_as_of,
                calculated_at=record.calculated_at,
                code_version=record.code_version,
                data_identity=record.data_identity,
                artifact=record.artifact,
                payload=payload,
            )
            adapter.validate_result_binding(record, manifest, exact_bytes)
            return manifest
        except (
            ArtifactVerificationError,
            ResultBindingError,
            TypeError,
            ValueError,
            httpx.HTTPError,
        ) as exc:
            raise ControlPlaneError(
                status_code=409,
                code="durable_result_restore_failed",
                message=str(exc),
            ) from exc

    async def _get_run(self, run_id: str) -> RunRecord:
        try:
            return await self.store.get(run_id)
        except RunNotFoundError as exc:
            raise ControlPlaneError(
                status_code=404,
                code="run_not_found",
                message="Run does not exist",
            ) from exc

    async def _refresh(self, record: RunRecord) -> RunRecord:
        if record.status in TERMINAL_STATUSES or not record.provider_run_id:
            return record
        try:
            observation = await self._provider_for(record.project_id).inspect(
                record.provider_run_id
            )
        except ProviderUnavailableError as exc:
            return await self.store.update(
                record.run_id,
                status=RunStatus.FAILED,
                error_code="worker_status_unavailable",
                error_message=str(exc),
            )

        if observation.status in {RunStatus.FAILED, RunStatus.CANCELLED}:
            updated = await self.store.update(
                record.run_id,
                status=observation.status,
                error_code=observation.error_code,
                error_message=observation.error_message,
            )
            self.publisher.publish_run(updated)
            return updated
        if observation.status in {RunStatus.DISPATCHED, RunStatus.RUNNING}:
            if record.status == RunStatus.VALIDATING:
                # A provider status read can lag the authenticated callback.
                # Never regress durable validation state back to an earlier
                # provider lifecycle observation.
                return record
            if observation.status == record.status:
                return record
            updated = await self.store.update(record.run_id, status=observation.status)
            self.publisher.publish_run(updated)
            return updated
        if observation.status not in {RunStatus.VALIDATING, RunStatus.PUBLISHED} or observation.manifest is None:
            updated = await self.store.update(
                record.run_id,
                status=RunStatus.FAILED,
                error_code="invalid_worker_state",
                error_message="Worker reached a result state without a bound manifest",
            )
            self.publisher.publish_run(updated)
            return updated

        return await self._validate_and_publish(
            record,
            observation.manifest,
            artifact_bytes=observation.artifact_bytes,
        )

    async def _validate_and_publish(
        self,
        record: RunRecord,
        manifest: Any,
        *,
        artifact_bytes: bytes | None = None,
    ) -> RunRecord:
        validating = await self.store.update(record.run_id, status=RunStatus.VALIDATING)
        self.publisher.publish_run(validating)
        try:
            adapter = self._adapter_for(record.project_id)
            adapter.validate_artifact_url(validating, manifest.artifact)
            exact_bytes = artifact_bytes
            if exact_bytes is None:
                exact_bytes = await self.artifact_fetcher.fetch(manifest.artifact)
            adapter.validate_result_binding(validating, manifest, exact_bytes)
        except (
            ResultBindingError,
            ArtifactVerificationError,
            TypeError,
            ValueError,
            httpx.HTTPError,
        ) as exc:
            failed = await self.store.update(
                record.run_id,
                status=RunStatus.FAILED,
                error_code="result_binding_failed",
                error_message=str(exc),
            )
            self.publisher.publish_run(failed)
            return failed

        published = await self.store.update(
            record.run_id,
            status=RunStatus.PUBLISHED,
            effective_inputs=manifest.effective_inputs,
            effective_config_hash=manifest.effective_config_hash,
            ignored_inputs=manifest.ignored_inputs,
            fallbacks=manifest.fallbacks,
            fallback_used=manifest.fallback_used,
            fallback_reason=manifest.fallback_reason,
            data_as_of=manifest.data_as_of,
            calculated_at=manifest.calculated_at,
            code_version=manifest.code_version,
            data_identity=manifest.data_identity,
            artifact=manifest.artifact,
            result_manifest=manifest,
            error_code=None,
            error_message=None,
        )
        self.publisher.publish_result(published)
        return published

    @staticmethod
    def _status_response(record: RunRecord, *, replayed: bool = False) -> RunStatusResponse:
        return RunStatusResponse(
            project_id=record.project_id,
            run_id=record.run_id,
            status=record.status,
            input_schema_version=record.input_schema_version,
            input_schema_hash=record.input_schema_hash,
            config_hash_algorithm=record.config_hash_algorithm,
            config_hash=record.config_hash,
            effective_config_hash=record.effective_config_hash,
            requested_inputs=record.requested_inputs,
            normalized_inputs=record.normalized_inputs,
            effective_inputs=record.effective_inputs,
            ignored_inputs=record.ignored_inputs,
            allow_fallback=record.allow_fallback,
            fallbacks=record.fallbacks,
            fallback_used=record.fallback_used,
            fallback_reason=record.fallback_reason,
            provider=record.provider,
            provider_run_id=record.provider_run_id,
            replayed=replayed,
            created_at=record.created_at,
            updated_at=record.updated_at,
            data_as_of=record.data_as_of,
            calculated_at=record.calculated_at,
            code_version=record.code_version,
            data_identity=record.data_identity,
            artifact=record.artifact,
            error_code=record.error_code,
            error_message=record.error_message,
        )

    def _adapter_for(self, project_id: str) -> AnalysisProjectAdapter:
        adapter = self.adapters.get(project_id)
        if adapter is None:
            raise ControlPlaneError(
                status_code=404,
                code="project_not_found",
                message="Project does not have an analysis-run capability",
            )
        return adapter

    def _provider_for(self, project_id: str) -> WorkerProvider:
        try:
            return self.providers[project_id]
        except KeyError as exc:  # pragma: no cover - constructor invariant
            raise ControlPlaneError(
                status_code=503,
                code="worker_provider_missing",
                message=f"No worker provider is registered for {project_id}",
            ) from exc
