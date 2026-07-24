from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from .models import ArtifactIdentity, DataIdentity, FallbackEvent, RunStatus, WorkerResultManifest

VALID_RUN_TRANSITIONS = {
    RunStatus.QUEUED: {
        RunStatus.DISPATCHED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.DISPATCHED: {
        RunStatus.RUNNING,
        RunStatus.VALIDATING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.RUNNING: {
        RunStatus.VALIDATING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.VALIDATING: {
        RunStatus.PUBLISHED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
}


def utc_now() -> datetime:
    return datetime.now(UTC)


class RunNotFoundError(KeyError):
    pass


class IdempotencyConflictError(ValueError):
    pass


class ConcurrentUpdateError(RuntimeError):
    pass


class InvalidRunTransitionError(RuntimeError):
    pass


class DispatchLeaseLostError(RuntimeError):
    pass


class DispatchOutboxStatus(StrEnum):
    PENDING = "pending"
    LEASED = "leased"
    ACKNOWLEDGED = "acknowledged"
    DEAD_LETTER = "dead_letter"


@dataclass
class RunRecord:
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
    ignored_inputs: list[str]
    allow_fallback: bool
    provider: str
    idempotency_key_digest: str
    request_digest: str
    created_at: datetime
    updated_at: datetime
    project_name: str | None = None
    provider_run_id: str | None = None
    fallbacks: list[FallbackEvent] = field(default_factory=list)
    fallback_used: bool = False
    fallback_reason: str | None = None
    data_as_of: date | None = None
    calculated_at: datetime | None = None
    code_version: str | None = None
    data_identity: DataIdentity | None = None
    artifact: ArtifactIdentity | None = None
    error_code: str | None = None
    error_message: str | None = None
    result_manifest: WorkerResultManifest | None = None


@dataclass
class DispatchOutboxRecord:
    run_id: str
    project_id: str
    provider: str
    status: DispatchOutboxStatus
    attempt_count: int
    max_attempts: int
    available_at: datetime
    created_at: datetime
    updated_at: datetime
    lease_owner: str | None = None
    lease_token: str | None = None
    lease_expires_at: datetime | None = None
    last_attempt_started_at: datetime | None = None
    acknowledged_at: datetime | None = None
    provider_run_id: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None


@dataclass(frozen=True)
class DispatchLease:
    run: RunRecord
    outbox: DispatchOutboxRecord


@dataclass(frozen=True)
class DispatchRetryResult:
    run: RunRecord
    outbox: DispatchOutboxRecord
    dead_lettered: bool


class RunStore(Protocol):
    async def create_or_replay(
        self,
        record: RunRecord,
        *,
        dispatch_max_attempts: int = 5,
    ) -> tuple[RunRecord, bool]: ...

    async def get(self, run_id: str) -> RunRecord: ...

    async def update(self, run_id: str, **changes: Any) -> RunRecord: ...

    async def claim_dispatch(
        self,
        *,
        lease_owner: str,
        lease_seconds: int,
        run_id: str | None = None,
        now: datetime | None = None,
    ) -> DispatchLease | None: ...

    async def acknowledge_dispatch(
        self,
        *,
        run_id: str,
        lease_token: str,
        provider_run_id: str,
        now: datetime | None = None,
    ) -> RunRecord: ...

    async def confirm_dispatch_from_callback(
        self,
        *,
        run_id: str,
        provider_run_id: str,
        now: datetime | None = None,
    ) -> RunRecord: ...

    async def reschedule_dispatch(
        self,
        *,
        run_id: str,
        lease_token: str,
        error_code: str,
        error_message: str,
        base_delay_seconds: int,
        max_delay_seconds: int,
        now: datetime | None = None,
    ) -> DispatchRetryResult: ...

    async def fail_run_from_worker(
        self,
        *,
        run_id: str,
        provider_run_id: str,
        error_code: str,
        error_message: str,
        now: datetime | None = None,
    ) -> RunRecord: ...

    async def expire_stuck_runs(
        self,
        *,
        timeout_seconds: int,
        limit: int,
        now: datetime | None = None,
    ) -> list[RunRecord]: ...

    async def check_ready(self) -> None: ...

    async def close(self) -> None: ...


class InMemoryRunStore:
    """Concurrency-safe, process-local preview store for development/tests."""

    def __init__(self, *, clock: Callable[[], datetime] = utc_now) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._idempotency: dict[tuple[str, str], tuple[str, str]] = {}
        self._outbox: dict[str, DispatchOutboxRecord] = {}
        self._lock = asyncio.Lock()
        self._clock = clock

    async def create_or_replay(
        self,
        record: RunRecord,
        *,
        dispatch_max_attempts: int = 5,
    ) -> tuple[RunRecord, bool]:
        if not 1 <= dispatch_max_attempts <= 20:
            raise ValueError("dispatch_max_attempts must be between 1 and 20")
        key = (record.project_id, record.idempotency_key_digest)
        async with self._lock:
            prior = self._idempotency.get(key)
            if prior is not None:
                prior_digest, prior_run_id = prior
                if prior_digest != record.request_digest:
                    raise IdempotencyConflictError(
                        "Idempotency-Key was already used with a different normalized request"
                    )
                return replace(self._runs[prior_run_id]), True
            self._runs[record.run_id] = record
            self._idempotency[key] = (record.request_digest, record.run_id)
            self._outbox[record.run_id] = DispatchOutboxRecord(
                run_id=record.run_id,
                project_id=record.project_id,
                provider=record.provider,
                status=DispatchOutboxStatus.PENDING,
                attempt_count=0,
                max_attempts=dispatch_max_attempts,
                available_at=record.created_at,
                created_at=record.created_at,
                updated_at=record.created_at,
            )
            return replace(record), False

    async def get(self, run_id: str) -> RunRecord:
        async with self._lock:
            try:
                return replace(self._runs[run_id])
            except KeyError as exc:
                raise RunNotFoundError(run_id) from exc

    async def update(self, run_id: str, **changes: Any) -> RunRecord:
        async with self._lock:
            try:
                current = self._runs[run_id]
            except KeyError as exc:
                raise RunNotFoundError(run_id) from exc
            next_status = changes.get("status", current.status)
            if current.status in {
                RunStatus.PUBLISHED,
                RunStatus.FAILED,
                RunStatus.CANCELLED,
            }:
                raise InvalidRunTransitionError(f"{current.status.value} run is immutable")
            if next_status != current.status and next_status not in VALID_RUN_TRANSITIONS[current.status]:
                raise InvalidRunTransitionError(
                    f"invalid run transition: {current.status.value} -> {next_status.value}"
                )
            updated = replace(current, updated_at=self._clock(), **changes)
            self._runs[run_id] = updated
            return replace(updated)

    async def claim_dispatch(
        self,
        *,
        lease_owner: str,
        lease_seconds: int,
        run_id: str | None = None,
        now: datetime | None = None,
    ) -> DispatchLease | None:
        if not lease_owner or len(lease_owner) > 200:
            raise ValueError("lease_owner must contain 1-200 characters")
        if not 5 <= lease_seconds <= 300:
            raise ValueError("lease_seconds must be between 5 and 300")
        current_time = now or self._clock()
        async with self._lock:
            if run_id is not None:
                candidate = self._outbox.get(run_id)
                candidates = [candidate] if candidate is not None else []
            else:
                candidates = sorted(
                    self._outbox.values(),
                    key=lambda item: (item.available_at, item.created_at, item.run_id),
                )
            for current in candidates:
                run = self._runs[current.run_id]
                if run.status != RunStatus.QUEUED:
                    continue
                claimable = (
                    current.status == DispatchOutboxStatus.PENDING and current.available_at <= current_time
                ) or (
                    current.status == DispatchOutboxStatus.LEASED
                    and current.lease_expires_at is not None
                    and current.lease_expires_at <= current_time
                )
                if not claimable:
                    continue
                if current.attempt_count >= current.max_attempts:
                    dead_outbox, failed_run = self._dead_letter(current, run, current_time)
                    self._outbox[current.run_id] = dead_outbox
                    self._runs[current.run_id] = failed_run
                    continue
                token = str(uuid.uuid4())
                leased = replace(
                    current,
                    status=DispatchOutboxStatus.LEASED,
                    attempt_count=current.attempt_count + 1,
                    lease_owner=lease_owner,
                    lease_token=token,
                    lease_expires_at=current_time + timedelta(seconds=lease_seconds),
                    last_attempt_started_at=current_time,
                    updated_at=current_time,
                )
                self._outbox[current.run_id] = leased
                return DispatchLease(run=replace(run), outbox=replace(leased))
            return None

    async def acknowledge_dispatch(
        self,
        *,
        run_id: str,
        lease_token: str,
        provider_run_id: str,
        now: datetime | None = None,
    ) -> RunRecord:
        current_time = now or self._clock()
        async with self._lock:
            try:
                outbox = self._outbox[run_id]
                run = self._runs[run_id]
            except KeyError as exc:
                raise RunNotFoundError(run_id) from exc
            if outbox.status == DispatchOutboxStatus.ACKNOWLEDGED:
                if outbox.provider_run_id == provider_run_id:
                    return replace(run)
                raise DispatchLeaseLostError("dispatch was already acknowledged with a different provider run")
            if outbox.status != DispatchOutboxStatus.LEASED or outbox.lease_token != lease_token:
                raise DispatchLeaseLostError("dispatch lease is no longer owned by this worker")
            if run.status != RunStatus.QUEUED:
                raise InvalidRunTransitionError(f"cannot acknowledge dispatch for a {run.status.value} run")
            updated_run = replace(
                run,
                status=RunStatus.DISPATCHED,
                provider_run_id=provider_run_id,
                updated_at=current_time,
                error_code=None,
                error_message=None,
            )
            self._runs[run_id] = updated_run
            self._outbox[run_id] = replace(
                outbox,
                status=DispatchOutboxStatus.ACKNOWLEDGED,
                acknowledged_at=current_time,
                provider_run_id=provider_run_id,
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                last_error_code=None,
                last_error_message=None,
                updated_at=current_time,
            )
            return replace(updated_run)

    async def confirm_dispatch_from_callback(
        self,
        *,
        run_id: str,
        provider_run_id: str,
        now: datetime | None = None,
    ) -> RunRecord:
        """Atomically turn callback evidence into a durable dispatch ack.

        This closes the crash window where the external worker starts and
        calls back before the API persists the provider dispatch receipt.
        """

        current_time = now or self._clock()
        async with self._lock:
            try:
                outbox = self._outbox[run_id]
                run = self._runs[run_id]
            except KeyError as exc:
                raise RunNotFoundError(run_id) from exc
            if run.status == RunStatus.QUEUED:
                updated_run = replace(
                    run,
                    status=RunStatus.DISPATCHED,
                    provider_run_id=provider_run_id,
                    updated_at=current_time,
                    error_code=None,
                    error_message=None,
                )
                self._runs[run_id] = updated_run
                self._outbox[run_id] = replace(
                    outbox,
                    status=DispatchOutboxStatus.ACKNOWLEDGED,
                    acknowledged_at=current_time,
                    provider_run_id=provider_run_id,
                    lease_owner=None,
                    lease_token=None,
                    lease_expires_at=None,
                    last_error_code=None,
                    last_error_message=None,
                    updated_at=current_time,
                )
                return replace(updated_run)
            if run.status in {
                RunStatus.DISPATCHED,
                RunStatus.RUNNING,
                RunStatus.VALIDATING,
            }:
                if run.provider_run_id == provider_run_id:
                    return replace(run)
                raise DispatchLeaseLostError(
                    "run was dispatched with a different provider correlation"
                )
            raise InvalidRunTransitionError(
                f"cannot confirm dispatch for a {run.status.value} run"
            )

    async def reschedule_dispatch(
        self,
        *,
        run_id: str,
        lease_token: str,
        error_code: str,
        error_message: str,
        base_delay_seconds: int,
        max_delay_seconds: int,
        now: datetime | None = None,
    ) -> DispatchRetryResult:
        if not 1 <= base_delay_seconds <= max_delay_seconds <= 3600:
            raise ValueError("dispatch retry delays are outside the supported bounds")
        current_time = now or self._clock()
        safe_code = error_code[:120]
        safe_message = error_message[:1000]
        async with self._lock:
            try:
                outbox = self._outbox[run_id]
                run = self._runs[run_id]
            except KeyError as exc:
                raise RunNotFoundError(run_id) from exc
            if outbox.status != DispatchOutboxStatus.LEASED or outbox.lease_token != lease_token:
                raise DispatchLeaseLostError("dispatch lease is no longer owned by this worker")
            if outbox.attempt_count >= outbox.max_attempts:
                dead_outbox, failed_run = self._dead_letter(
                    outbox,
                    run,
                    current_time,
                    error_code=safe_code,
                    error_message=safe_message,
                )
                self._outbox[run_id] = dead_outbox
                self._runs[run_id] = failed_run
                return DispatchRetryResult(
                    run=replace(failed_run),
                    outbox=replace(dead_outbox),
                    dead_lettered=True,
                )
            delay = min(
                max_delay_seconds,
                base_delay_seconds * (2 ** max(0, outbox.attempt_count - 1)),
            )
            pending = replace(
                outbox,
                status=DispatchOutboxStatus.PENDING,
                available_at=current_time + timedelta(seconds=delay),
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                last_error_code=safe_code,
                last_error_message=safe_message,
                updated_at=current_time,
            )
            self._outbox[run_id] = pending
            return DispatchRetryResult(
                run=replace(run),
                outbox=replace(pending),
                dead_lettered=False,
            )

    async def get_dispatch_outbox(self, run_id: str) -> DispatchOutboxRecord:
        """Bounded diagnostic hook used by local contract tests."""
        async with self._lock:
            try:
                return replace(self._outbox[run_id])
            except KeyError as exc:
                raise RunNotFoundError(run_id) from exc

    async def fail_run_from_worker(
        self,
        *,
        run_id: str,
        provider_run_id: str,
        error_code: str,
        error_message: str,
        now: datetime | None = None,
    ) -> RunRecord:
        current_time = now or self._clock()
        async with self._lock:
            try:
                run = self._runs[run_id]
            except KeyError as exc:
                raise RunNotFoundError(run_id) from exc
            if run.status in {RunStatus.PUBLISHED, RunStatus.FAILED, RunStatus.CANCELLED}:
                raise InvalidRunTransitionError(f"{run.status.value} run is immutable")
            failed = replace(
                run,
                status=RunStatus.FAILED,
                provider_run_id=run.provider_run_id or provider_run_id,
                error_code=error_code[:120],
                error_message=error_message[:1000],
                updated_at=current_time,
            )
            self._runs[run_id] = failed
            outbox = self._outbox.get(run_id)
            if outbox is not None and outbox.status in {
                DispatchOutboxStatus.PENDING,
                DispatchOutboxStatus.LEASED,
            }:
                self._outbox[run_id] = replace(
                    outbox,
                    status=DispatchOutboxStatus.ACKNOWLEDGED,
                    acknowledged_at=current_time,
                    provider_run_id=provider_run_id,
                    lease_owner=None,
                    lease_token=None,
                    lease_expires_at=None,
                    last_error_code=None,
                    last_error_message=None,
                    updated_at=current_time,
                )
            return replace(failed)

    async def expire_stuck_runs(
        self,
        *,
        timeout_seconds: int,
        limit: int,
        now: datetime | None = None,
    ) -> list[RunRecord]:
        if not 300 <= timeout_seconds <= 86400:
            raise ValueError("timeout_seconds must be between 300 and 86400")
        if not 1 <= limit <= 100:
            raise ValueError("expiry limit must be between 1 and 100")
        current_time = now or self._clock()
        cutoff = current_time - timedelta(seconds=timeout_seconds)
        expired: list[RunRecord] = []
        async with self._lock:
            candidates = sorted(
                self._outbox.values(),
                key=lambda item: (
                    item.acknowledged_at or datetime.max.replace(tzinfo=UTC),
                    item.run_id,
                ),
            )
            for outbox in candidates:
                if len(expired) >= limit:
                    break
                run = self._runs[outbox.run_id]
                if (
                    outbox.status != DispatchOutboxStatus.ACKNOWLEDGED
                    or outbox.acknowledged_at is None
                    or outbox.acknowledged_at > cutoff
                    or run.status
                    not in {
                        RunStatus.DISPATCHED,
                        RunStatus.RUNNING,
                        RunStatus.VALIDATING,
                    }
                ):
                    continue
                failed = replace(
                    run,
                    status=RunStatus.FAILED,
                    error_code="worker_result_timeout",
                    error_message="Worker did not publish a result or failure callback before the deadline",
                    updated_at=current_time,
                )
                self._runs[run.run_id] = failed
                expired.append(replace(failed))
        return expired

    @staticmethod
    def _dead_letter(
        outbox: DispatchOutboxRecord,
        run: RunRecord,
        now: datetime,
        *,
        error_code: str = "dispatch_retry_exhausted",
        error_message: str = "Dispatch lease expired before acknowledgment",
    ) -> tuple[DispatchOutboxRecord, RunRecord]:
        dead_outbox = replace(
            outbox,
            status=DispatchOutboxStatus.DEAD_LETTER,
            lease_owner=None,
            lease_token=None,
            lease_expires_at=None,
            last_error_code=error_code,
            last_error_message=error_message,
            updated_at=now,
        )
        failed_run = replace(
            run,
            status=RunStatus.FAILED,
            error_code="worker_dispatch_retry_exhausted",
            error_message=error_message,
            updated_at=now,
        )
        return dead_outbox, failed_run

    async def close(self) -> None:
        return None

    async def check_ready(self) -> None:
        return None


def digest_idempotency_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
