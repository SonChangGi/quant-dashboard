from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from .models import ProjectCapabilities
from .store import RunRecord
from .supabase_auth import supabase_admin_headers

logger = logging.getLogger(__name__)
NAMESPACE = uuid.UUID("51e2578f-3dc4-42d2-9458-4c4bd9e2b33b")


class DualWritePublisher(Protocol):
    def publish_project(self, capability: ProjectCapabilities) -> bool: ...

    def publish_run(self, record: RunRecord) -> bool: ...

    def publish_result(self, record: RunRecord) -> bool: ...

    async def close(self) -> None: ...


class NullDualWritePublisher:
    def publish_project(self, capability: ProjectCapabilities) -> bool:
        del capability
        return False

    def publish_run(self, record: RunRecord) -> bool:
        del record
        return False

    def publish_result(self, record: RunRecord) -> bool:
        del record
        return False

    async def close(self) -> None:
        return None


@dataclass(frozen=True)
class _WriteEvent:
    kind: str
    payload: dict[str, Any]


class SupabaseDualWritePublisher:
    """Best-effort PostgREST mirror.

    `publish_*` only performs `put_nowait`; request success and GitHub Pages
    fallback never depend on Supabase. Failures are logged without tokens and
    are intentionally not retried in-process. A durable outbox is required
    before promoting this mirror to the authoritative run store.
    """

    def __init__(
        self,
        *,
        url: str,
        service_role_key: str,
        queue_size: int = 256,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = client is None
        admin_headers = supabase_admin_headers(service_role_key)
        self._client = client or httpx.AsyncClient(
            base_url=f"{url.rstrip('/')}/rest/v1",
            timeout=httpx.Timeout(10.0),
            headers=admin_headers,
        )
        self._queue: asyncio.Queue[_WriteEvent | None] = asyncio.Queue(maxsize=queue_size)
        self._task: asyncio.Task[None] | None = None
        self.dropped_events = 0
        self.failed_events = 0

    def _ensure_worker(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._worker(), name="supabase-dual-write")

    def _enqueue(self, event: _WriteEvent) -> bool:
        self._ensure_worker()
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self.dropped_events += 1
            logger.warning("Supabase dual-write queue is full; event dropped", extra={"kind": event.kind})
            return False
        return True

    def publish_project(self, capability: ProjectCapabilities) -> bool:
        return self._enqueue(
            _WriteEvent(
                "project",
                {
                    "id": capability.project_id,
                    "display_name": capability.project_name,
                    "input_schema_version": capability.input_schema_version,
                    "capability": capability.model_dump(mode="json", by_alias=True),
                    "active": True,
                },
            )
        )

    def publish_run(self, record: RunRecord) -> bool:
        return self._enqueue(_WriteEvent("run", _run_payload(record)))

    def publish_result(self, record: RunRecord) -> bool:
        if record.result_manifest is None:
            return False
        return self._enqueue(_WriteEvent("result", _result_payload(record)))

    async def _worker(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                if event is None:
                    return
                await self._write_event(event)
            except Exception as exc:  # noqa: BLE001 - mirror failure must never fail the API request
                self.failed_events += 1
                logger.warning(
                    "Supabase dual-write failed",
                    extra={"kind": event.kind if event else "shutdown", "errorType": type(exc).__name__},
                )
            finally:
                self._queue.task_done()

    async def _write_event(self, event: _WriteEvent) -> None:
        if event.kind == "project":
            await self._upsert("projects", event.payload, "id")
            return
        if event.kind == "run":
            await self._upsert(
                "analysis_configs",
                event.payload["config"],
                "project_id,input_schema_version,config_hash",
            )
            await self._upsert("analysis_runs", event.payload["run"], "id")
            return
        if event.kind == "result":
            await self._upsert("data_snapshots", event.payload["snapshot"], "id")
            await self._upsert("analysis_artifacts", event.payload["artifact"], "run_id")
            await self._upsert("analysis_runs", event.payload["run"], "id")
            return
        raise ValueError(f"unknown dual-write event: {event.kind}")

    async def _upsert(self, table: str, payload: dict[str, Any], conflict: str) -> None:
        response = await self._client.post(
            f"/{table}",
            params={"on_conflict": conflict},
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            json=payload,
        )
        response.raise_for_status()

    async def close(self) -> None:
        if self._task is not None and not self._task.done():
            await self._queue.put(None)
            await self._task
        if self._owns_client:
            await self._client.aclose()


class SupabaseProjectMetadataPublisher(SupabaseDualWritePublisher):
    """Publish only public project capabilities beside the authoritative store.

    Run and result state must continue through guarded Supabase RPCs. This
    narrow publisher prevents the public capability view from remaining an
    empty placeholder without duplicating or bypassing lifecycle writes.
    """

    def publish_run(self, record: RunRecord) -> bool:
        del record
        return False

    def publish_result(self, record: RunRecord) -> bool:
        del record
        return False


def _config_id(record: RunRecord) -> str:
    return str(uuid.uuid5(NAMESPACE, f"config:{record.project_id}:{record.input_schema_version}:{record.config_hash}"))


def _snapshot_id(record: RunRecord) -> str:
    return str(uuid.uuid5(NAMESPACE, f"snapshot:{record.run_id}"))


def _run_payload(record: RunRecord) -> dict[str, Any]:
    config_id = _config_id(record)
    return {
        "config": {
            "id": config_id,
            "project_id": record.project_id,
            "input_schema_version": record.input_schema_version,
            "input_schema_hash": record.input_schema_hash,
            "config_hash_algorithm": record.config_hash_algorithm,
            "config_hash": record.config_hash,
            "normalized_inputs": record.normalized_inputs,
        },
        "run": {
            "id": record.run_id,
            "project_id": record.project_id,
            "config_id": config_id,
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
        },
    }


def _result_payload(record: RunRecord) -> dict[str, Any]:
    assert record.result_manifest is not None
    manifest = record.result_manifest
    base = _run_payload(record)
    snapshot_id = _snapshot_id(record)
    base["snapshot"] = {
        "id": snapshot_id,
        "project_id": record.project_id,
        "run_id": record.run_id,
        "data_as_of": manifest.data_as_of.isoformat(),
        "source": manifest.data_identity.source,
        "source_hash": manifest.data_identity.source_hash,
        "artifact_url": str(manifest.artifact.url),
        "artifact_sha256": manifest.artifact.sha256,
        "byte_size": manifest.artifact.byte_size,
        "contract_version": manifest.artifact.contract_version,
        "summary": manifest.payload,
        "published": True,
    }
    base["artifact"] = {
        "id": str(uuid.uuid5(NAMESPACE, f"artifact:{record.run_id}")),
        "run_id": record.run_id,
        "snapshot_id": snapshot_id,
        "url": str(manifest.artifact.url),
        "sha256": manifest.artifact.sha256,
        "byte_size": manifest.artifact.byte_size,
        "contract_version": manifest.artifact.contract_version,
        "published": True,
    }
    return base
