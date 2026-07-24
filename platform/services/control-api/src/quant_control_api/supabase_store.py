from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from typing import Any

import httpx

from .models import ArtifactIdentity, DataIdentity, FallbackEvent, RunStatus
from .store import (
    ConcurrentUpdateError,
    DispatchLease,
    DispatchLeaseLostError,
    DispatchOutboxRecord,
    DispatchOutboxStatus,
    DispatchRetryResult,
    IdempotencyConflictError,
    InvalidRunTransitionError,
    RunNotFoundError,
    RunRecord,
)
from .supabase_auth import supabase_admin_headers


class SupabaseRunStore:
    """Durable multi-instance RunStore backed by server-only RPCs."""

    def __init__(
        self,
        *,
        url: str,
        service_role_key: str,
        client: httpx.AsyncClient | None = None,
        max_update_retries: int = 3,
    ) -> None:
        if not url or not service_role_key:
            raise ValueError(
                "SupabaseRunStore requires URL and a secret or legacy service-role key"
            )
        self._owns_client = client is None
        admin_headers = supabase_admin_headers(service_role_key)
        self._client = client or httpx.AsyncClient(
            base_url=f"{url.rstrip('/')}/rest/v1",
            timeout=httpx.Timeout(15.0),
            headers=admin_headers,
        )
        self.max_update_retries = max_update_retries

    async def create_or_replay(
        self,
        record: RunRecord,
        *,
        dispatch_max_attempts: int = 5,
    ) -> tuple[RunRecord, bool]:
        response = await self._rpc(
            "control_create_or_replay_analysis_run",
            {
                "p_run": {
                    **_record_payload(record),
                    "dispatch_max_attempts": dispatch_max_attempts,
                }
            },
        )
        outcome = response.get("outcome")
        if outcome == "conflict":
            raise IdempotencyConflictError("Idempotency-Key was already used with a different normalized request")
        if outcome not in {"created", "replayed"}:
            raise RuntimeError(f"unexpected create/replay RPC outcome: {outcome}")
        if outcome == "replayed" and response["run"].get("status") == RunStatus.PUBLISHED.value:
            return await self.get(response["run"]["id"]), True
        return _record_from_row(response["run"]), outcome == "replayed"

    async def get(self, run_id: str) -> RunRecord:
        rows = await self._select("analysis_runs", {"id": f"eq.{run_id}", "select": "*"})
        if not rows:
            raise RunNotFoundError(run_id)
        row = rows[0]
        artifact_row: dict[str, Any] | None = None
        snapshot_row: dict[str, Any] | None = None
        if row.get("status") == RunStatus.PUBLISHED.value:
            artifacts = await self._select(
                "analysis_artifacts",
                {"run_id": f"eq.{run_id}", "select": "*", "limit": "1"},
            )
            snapshots = await self._select(
                "data_snapshots",
                {"run_id": f"eq.{run_id}", "select": "*", "limit": "1"},
            )
            artifact_row = artifacts[0] if artifacts else None
            snapshot_row = snapshots[0] if snapshots else None
            if artifact_row is None or snapshot_row is None:
                raise RuntimeError("published run is missing durable artifact or data snapshot identity")
        return _record_from_row(row, artifact_row=artifact_row, snapshot_row=snapshot_row)

    async def update(self, run_id: str, **changes: Any) -> RunRecord:
        for _ in range(self.max_update_retries):
            current = await self.get(run_id)
            candidate = replace(current, **changes)
            response = await self._rpc(
                "control_update_analysis_run",
                {
                    "p_run": _record_payload(candidate),
                    "p_expected_updated_at": current.updated_at.isoformat(),
                },
            )
            outcome = response.get("outcome")
            if outcome == "updated":
                return _record_from_row(
                    response["run"],
                    artifact_row=response.get("artifact"),
                    snapshot_row=response.get("snapshot"),
                    result_manifest=candidate.result_manifest,
                )
            if outcome == "invalid_transition":
                raise InvalidRunTransitionError(str(response.get("message") or "invalid run state transition"))
            if outcome == "not_found":
                raise RunNotFoundError(run_id)
            if outcome != "conflict":
                raise RuntimeError(f"unexpected update RPC outcome: {outcome}")
        raise ConcurrentUpdateError(f"run {run_id} changed concurrently too many times")

    async def claim_dispatch(
        self,
        *,
        lease_owner: str,
        lease_seconds: int,
        run_id: str | None = None,
        now: datetime | None = None,
    ) -> DispatchLease | None:
        response = await self._rpc(
            "control_claim_analysis_dispatch",
            {
                "p_run_id": run_id,
                "p_lease_owner": lease_owner,
                "p_lease_seconds": lease_seconds,
                "p_now": now.isoformat() if now is not None else None,
            },
        )
        outcome = response.get("outcome")
        if outcome in {"none", "busy", "not_ready", "acknowledged", "dead_letter"}:
            return None
        if outcome != "claimed":
            raise RuntimeError(f"unexpected dispatch claim RPC outcome: {outcome}")
        return DispatchLease(
            run=_record_from_row(response["run"]),
            outbox=_outbox_from_row(response["outbox"]),
        )

    async def acknowledge_dispatch(
        self,
        *,
        run_id: str,
        lease_token: str,
        provider_run_id: str,
        now: datetime | None = None,
    ) -> RunRecord:
        response = await self._rpc(
            "control_ack_analysis_dispatch",
            {
                "p_run_id": run_id,
                "p_lease_token": lease_token,
                "p_provider_run_id": provider_run_id,
                "p_now": now.isoformat() if now is not None else None,
            },
        )
        outcome = response.get("outcome")
        if outcome in {"acknowledged", "replayed"}:
            return _record_from_row(response["run"])
        if outcome == "not_found":
            raise RunNotFoundError(run_id)
        if outcome == "lease_lost":
            raise DispatchLeaseLostError("dispatch lease is no longer owned by this worker")
        if outcome == "invalid_transition":
            raise InvalidRunTransitionError(str(response.get("message") or "cannot acknowledge dispatch"))
        raise RuntimeError(f"unexpected dispatch acknowledgment RPC outcome: {outcome}")

    async def confirm_dispatch_from_callback(
        self,
        *,
        run_id: str,
        provider_run_id: str,
        now: datetime | None = None,
    ) -> RunRecord:
        response = await self._rpc(
            "control_confirm_dispatch_from_callback",
            {
                "p_run_id": run_id,
                "p_provider_run_id": provider_run_id,
                "p_now": now.isoformat() if now is not None else None,
            },
        )
        outcome = response.get("outcome")
        if outcome in {"acknowledged", "replayed"}:
            return _record_from_row(response["run"])
        if outcome == "not_found":
            raise RunNotFoundError(run_id)
        if outcome == "provider_conflict":
            raise DispatchLeaseLostError(
                "run was dispatched with a different provider correlation"
            )
        if outcome == "invalid_transition":
            raise InvalidRunTransitionError(
                str(response.get("message") or "cannot confirm callback dispatch")
            )
        raise RuntimeError(
            f"unexpected callback dispatch confirmation RPC outcome: {outcome}"
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
        response = await self._rpc(
            "control_reschedule_analysis_dispatch",
            {
                "p_run_id": run_id,
                "p_lease_token": lease_token,
                "p_error_code": error_code[:120],
                "p_error_message": error_message[:1000],
                "p_base_delay_seconds": base_delay_seconds,
                "p_max_delay_seconds": max_delay_seconds,
                "p_now": now.isoformat() if now is not None else None,
            },
        )
        outcome = response.get("outcome")
        if outcome in {"retry_scheduled", "dead_letter"}:
            return DispatchRetryResult(
                run=_record_from_row(response["run"]),
                outbox=_outbox_from_row(response["outbox"]),
                dead_lettered=outcome == "dead_letter",
            )
        if outcome == "not_found":
            raise RunNotFoundError(run_id)
        if outcome == "lease_lost":
            raise DispatchLeaseLostError("dispatch lease is no longer owned by this worker")
        raise RuntimeError(f"unexpected dispatch reschedule RPC outcome: {outcome}")

    async def fail_run_from_worker(
        self,
        *,
        run_id: str,
        provider_run_id: str,
        error_code: str,
        error_message: str,
        now: datetime | None = None,
    ) -> RunRecord:
        response = await self._rpc(
            "control_fail_analysis_run",
            {
                "p_run_id": run_id,
                "p_provider_run_id": provider_run_id,
                "p_error_code": error_code,
                "p_error_message": error_message,
                "p_now": now.isoformat() if now is not None else None,
            },
        )
        outcome = response.get("outcome")
        if outcome in {"failed", "replayed"}:
            return _record_from_row(response["run"])
        if outcome == "not_found":
            raise RunNotFoundError(run_id)
        if outcome == "invalid_transition":
            raise InvalidRunTransitionError(str(response.get("message") or "cannot fail run"))
        raise RuntimeError(f"unexpected worker failure RPC outcome: {outcome}")

    async def expire_stuck_runs(
        self,
        *,
        timeout_seconds: int,
        limit: int,
        now: datetime | None = None,
    ) -> list[RunRecord]:
        response = await self._rpc(
            "control_expire_stuck_analysis_runs",
            {
                "p_timeout_seconds": timeout_seconds,
                "p_limit": limit,
                "p_now": now.isoformat() if now is not None else None,
            },
        )
        if response.get("outcome") != "expired":
            raise RuntimeError(f"unexpected stuck-run expiry RPC outcome: {response.get('outcome')}")
        rows = response.get("runs")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise TypeError("unexpected stuck-run expiry rows")
        return [_record_from_row(row) for row in rows]

    async def _rpc(self, function: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(f"/rpc/{function}", json=payload)
        response.raise_for_status()
        body = response.json()
        if isinstance(body, list):
            if len(body) != 1 or not isinstance(body[0], dict):
                raise RuntimeError(f"unexpected {function} response")
            return body[0]
        if not isinstance(body, dict):
            raise TypeError(f"unexpected {function} response")
        return body

    async def _select(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        response = await self._client.get(f"/{table}", params=params)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, list) or any(not isinstance(row, dict) for row in body):
            raise RuntimeError(f"unexpected {table} response")
        return body

    async def check_ready(self) -> None:
        await self._select("analysis_runs", {"select": "id", "limit": "1"})

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _record_payload(record: RunRecord) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": record.run_id,
        "project_id": record.project_id,
        "project_display_name": record.project_name or record.project_id,
        "status": record.status.value,
        "idempotency_key_digest": record.idempotency_key_digest,
        "request_digest": record.request_digest,
        "input_schema_version": record.input_schema_version,
        "input_schema_hash": record.input_schema_hash,
        "config_hash_algorithm": record.config_hash_algorithm,
        "config_hash": record.config_hash,
        "effective_config_hash": record.effective_config_hash,
        "requested_inputs": record.requested_inputs,
        "normalized_inputs": record.normalized_inputs,
        "effective_inputs": record.effective_inputs,
        "ignored_inputs": record.ignored_inputs,
        "allow_fallback": record.allow_fallback,
        "fallbacks": [event.model_dump(mode="json") for event in record.fallbacks],
        "fallback_used": record.fallback_used,
        "fallback_reason": record.fallback_reason,
        "provider": record.provider,
        "provider_run_id": record.provider_run_id,
        "data_as_of": record.data_as_of.isoformat() if record.data_as_of else None,
        "calculated_at": record.calculated_at.isoformat() if record.calculated_at else None,
        "code_version": record.code_version,
        "error_code": record.error_code,
        "error_message": record.error_message,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }
    if record.status == RunStatus.PUBLISHED:
        if record.artifact is None or record.data_identity is None:
            raise ValueError("published run requires artifact and data identity")
        payload["artifact"] = {
            "url": str(record.artifact.url),
            "sha256": record.artifact.sha256,
            "byte_size": record.artifact.byte_size,
            "contract_version": record.artifact.contract_version,
        }
        payload["snapshot"] = {
            "data_as_of": record.data_identity.data_as_of.isoformat(),
            "source": record.data_identity.source,
            "source_hash": record.data_identity.source_hash,
            "summary": (
                record.result_manifest.payload
                if record.result_manifest is not None
                else {}
            ),
        }
    return payload


def _record_from_row(
    row: dict[str, Any],
    *,
    artifact_row: dict[str, Any] | None = None,
    snapshot_row: dict[str, Any] | None = None,
    result_manifest: Any = None,
) -> RunRecord:
    artifact = None
    if artifact_row is not None:
        artifact = ArtifactIdentity(
            url=artifact_row["url"],
            sha256=artifact_row["sha256"],
            byte_size=artifact_row["byte_size"],
            contract_version=artifact_row["contract_version"],
        )
    data_identity = None
    if snapshot_row is not None:
        data_identity = DataIdentity(
            source=snapshot_row["source"],
            source_hash=snapshot_row["source_hash"],
            data_as_of=snapshot_row["data_as_of"],
        )
    return RunRecord(
        project_id=row["project_id"],
        run_id=row["id"],
        status=RunStatus(row["status"]),
        input_schema_version=row["input_schema_version"],
        input_schema_hash=row["input_schema_hash"],
        config_hash_algorithm=row["config_hash_algorithm"],
        config_hash=row["config_hash"],
        effective_config_hash=row["effective_config_hash"],
        requested_inputs=row["requested_inputs"],
        normalized_inputs=row["normalized_inputs"],
        effective_inputs=row["effective_inputs"],
        ignored_inputs=row.get("ignored_inputs") or [],
        allow_fallback=bool(row["allow_fallback"]),
        provider=row["provider"],
        idempotency_key_digest=row["idempotency_key_digest"],
        request_digest=row["request_digest"],
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
        project_name=None,
        provider_run_id=row.get("provider_run_id"),
        fallbacks=[FallbackEvent.model_validate(event) for event in (row.get("fallbacks") or [])],
        fallback_used=bool(row.get("fallback_used")),
        fallback_reason=row.get("fallback_reason"),
        data_as_of=_date(row.get("data_as_of")),
        calculated_at=_datetime(row.get("calculated_at")) if row.get("calculated_at") else None,
        code_version=row.get("code_version"),
        data_identity=data_identity,
        artifact=artifact,
        error_code=row.get("error_code"),
        error_message=row.get("error_message"),
        result_manifest=result_manifest,
    )


def _datetime(value: str | datetime) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


def _date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _outbox_from_row(row: dict[str, Any]) -> DispatchOutboxRecord:
    return DispatchOutboxRecord(
        run_id=row["run_id"],
        project_id=row["project_id"],
        provider=row["provider"],
        status=DispatchOutboxStatus(row["status"]),
        attempt_count=int(row["attempt_count"]),
        max_attempts=int(row["max_attempts"]),
        available_at=_datetime(row["available_at"]),
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
        lease_owner=row.get("lease_owner"),
        lease_token=row.get("lease_token"),
        lease_expires_at=(_datetime(row["lease_expires_at"]) if row.get("lease_expires_at") else None),
        last_attempt_started_at=(
            _datetime(row["last_attempt_started_at"]) if row.get("last_attempt_started_at") else None
        ),
        acknowledged_at=(_datetime(row["acknowledged_at"]) if row.get("acknowledged_at") else None),
        provider_run_id=row.get("provider_run_id"),
        last_error_code=row.get("last_error_code"),
        last_error_message=row.get("last_error_message"),
    )
