from __future__ import annotations

import asyncio
import json
import uuid
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from quant_control_api.app import create_app
from quant_control_api.artifacts import MappingArtifactFetcher
from quant_control_api.best_factor import DEFAULT_CONFIG, canonical_json_bytes
from quant_control_api.dual_write import NullDualWritePublisher
from quant_control_api.models import RunCreateRequest, RunStatus
from quant_control_api.providers.fake import FakeWorkerProvider
from quant_control_api.service import ControlPlaneError, ControlPlaneService
from quant_control_api.settings import Settings
from quant_control_api.store import InvalidRunTransitionError
from quant_control_api.supabase_store import SupabaseRunStore


class MockSupabaseState:
    def __init__(self) -> None:
        self.runs: dict[str, dict[str, Any]] = {}
        self.idempotency: dict[tuple[str, str], str] = {}
        self.artifacts: dict[str, dict[str, Any]] = {}
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.outbox: dict[str, dict[str, Any]] = {}
        self.tick = 0
        self.conflict_next_update = False
        self.update_rpc_calls = 0

    def now(self) -> str:
        self.tick += 1
        return (datetime(2026, 7, 24, tzinfo=UTC) + timedelta(microseconds=self.tick)).isoformat()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/rpc/control_create_or_replay_analysis_run"):
            return self._create(request)
        if request.method == "POST" and path.endswith("/rpc/control_claim_analysis_dispatch"):
            return self._claim(request)
        if request.method == "POST" and path.endswith("/rpc/control_ack_analysis_dispatch"):
            return self._ack(request)
        if request.method == "POST" and path.endswith(
            "/rpc/control_confirm_dispatch_from_callback"
        ):
            return self._confirm_callback(request)
        if request.method == "POST" and path.endswith("/rpc/control_reschedule_analysis_dispatch"):
            return self._reschedule(request)
        if request.method == "POST" and path.endswith("/rpc/control_fail_analysis_run"):
            return self._fail(request)
        if request.method == "POST" and path.endswith("/rpc/control_expire_stuck_analysis_runs"):
            return self._expire(request)
        if request.method == "POST" and path.endswith("/rpc/control_update_analysis_run"):
            return self._update(request)
        if request.method == "GET" and path.endswith("/analysis_runs"):
            return self._select(request, self.runs, "id")
        if request.method == "GET" and path.endswith("/analysis_artifacts"):
            return self._select(request, self.artifacts, "run_id")
        if request.method == "GET" and path.endswith("/data_snapshots"):
            return self._select(request, self.snapshots, "run_id")
        if request.method == "GET" and path.endswith("/analysis_dispatch_outbox"):
            return self._select(request, self.outbox, "run_id")
        return httpx.Response(404, json={"message": f"unhandled {request.method} {path}"}, request=request)

    def _create(self, request: httpx.Request) -> httpx.Response:
        run = json.loads(request.read())["p_run"]
        key = (run["project_id"], run["idempotency_key_digest"])
        prior_id = self.idempotency.get(key)
        if prior_id is not None:
            prior = self.runs[prior_id]
            outcome = "replayed" if prior["request_digest"] == run["request_digest"] else "conflict"
            body = {"outcome": outcome}
            if outcome == "replayed":
                body["run"] = deepcopy(prior)
                body["outbox"] = deepcopy(self.outbox[prior_id])
            return httpx.Response(200, json=body, request=request)
        row = deepcopy(run)
        max_attempts = int(row.pop("dispatch_max_attempts"))
        row.pop("artifact", None)
        row.pop("snapshot", None)
        row["config_id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        row["created_at"] = self.now()
        row["updated_at"] = row["created_at"]
        self.runs[row["id"]] = row
        self.idempotency[key] = row["id"]
        outbox = {
            "run_id": row["id"],
            "project_id": row["project_id"],
            "provider": row["provider"],
            "status": "pending",
            "attempt_count": 0,
            "max_attempts": max_attempts,
            "available_at": row["created_at"],
            "lease_owner": None,
            "lease_token": None,
            "lease_expires_at": None,
            "last_attempt_started_at": None,
            "acknowledged_at": None,
            "provider_run_id": None,
            "last_error_code": None,
            "last_error_message": None,
            "created_at": row["created_at"],
            "updated_at": row["created_at"],
        }
        self.outbox[row["id"]] = outbox
        return httpx.Response(
            200,
            json={"outcome": "created", "run": deepcopy(row), "outbox": deepcopy(outbox)},
            request=request,
        )

    def _claim(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        now = self._request_time(body.get("p_now"))
        requested_id = body.get("p_run_id")
        candidates = (
            [self.outbox[requested_id]]
            if requested_id in self.outbox
            else sorted(self.outbox.values(), key=lambda row: (row["available_at"], row["run_id"]))
            if requested_id is None
            else []
        )
        for outbox in candidates:
            run = self.runs[outbox["run_id"]]
            if run["status"] != "queued":
                continue
            available = datetime.fromisoformat(outbox["available_at"])
            lease_expiry = datetime.fromisoformat(outbox["lease_expires_at"]) if outbox["lease_expires_at"] else None
            claimable = (outbox["status"] == "pending" and available <= now) or (
                outbox["status"] == "leased" and lease_expiry is not None and lease_expiry <= now
            )
            if not claimable:
                continue
            if outbox["attempt_count"] >= outbox["max_attempts"]:
                outbox.update(
                    status="dead_letter",
                    lease_owner=None,
                    lease_token=None,
                    lease_expires_at=None,
                    last_error_code="dispatch_retry_exhausted",
                    last_error_message="Dispatch lease expired before acknowledgment",
                    updated_at=now.isoformat(),
                )
                run.update(
                    status="failed",
                    error_code="worker_dispatch_retry_exhausted",
                    error_message="Dispatch lease expired before acknowledgment",
                    updated_at=now.isoformat(),
                )
                return httpx.Response(
                    200,
                    json={
                        "outcome": "dead_letter",
                        "run": deepcopy(run),
                        "outbox": deepcopy(outbox),
                    },
                    request=request,
                )
            token = str(uuid.uuid4())
            outbox.update(
                status="leased",
                attempt_count=outbox["attempt_count"] + 1,
                lease_owner=body["p_lease_owner"],
                lease_token=token,
                lease_expires_at=(now + timedelta(seconds=int(body["p_lease_seconds"]))).isoformat(),
                last_attempt_started_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
            return httpx.Response(
                200,
                json={
                    "outcome": "claimed",
                    "run": deepcopy(run),
                    "outbox": deepcopy(outbox),
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={"outcome": "none" if requested_id is None else "busy"},
            request=request,
        )

    def _ack(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        now = self._request_time(body.get("p_now")).isoformat()
        run = self.runs[body["p_run_id"]]
        outbox = self.outbox[body["p_run_id"]]
        if outbox["status"] == "acknowledged":
            outcome = "replayed" if outbox["provider_run_id"] == body["p_provider_run_id"] else "lease_lost"
            return httpx.Response(
                200,
                json={"outcome": outcome, "run": deepcopy(run)},
                request=request,
            )
        if outbox["status"] != "leased" or outbox["lease_token"] != body["p_lease_token"]:
            return httpx.Response(200, json={"outcome": "lease_lost"}, request=request)
        run.update(
            status="dispatched",
            provider_run_id=body["p_provider_run_id"],
            updated_at=now,
        )
        outbox.update(
            status="acknowledged",
            acknowledged_at=now,
            provider_run_id=body["p_provider_run_id"],
            lease_owner=None,
            lease_token=None,
            lease_expires_at=None,
            updated_at=now,
        )
        return httpx.Response(
            200,
            json={"outcome": "acknowledged", "run": deepcopy(run), "outbox": deepcopy(outbox)},
            request=request,
        )

    def _reschedule(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        now = self._request_time(body.get("p_now"))
        run = self.runs[body["p_run_id"]]
        outbox = self.outbox[body["p_run_id"]]
        if outbox["status"] != "leased" or outbox["lease_token"] != body["p_lease_token"]:
            return httpx.Response(200, json={"outcome": "lease_lost"}, request=request)
        error_code = body["p_error_code"][:120]
        error_message = body["p_error_message"][:1000]
        if outbox["attempt_count"] >= outbox["max_attempts"]:
            outbox.update(
                status="dead_letter",
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                last_error_code=error_code,
                last_error_message=error_message,
                updated_at=now.isoformat(),
            )
            run.update(
                status="failed",
                error_code="worker_dispatch_retry_exhausted",
                error_message=error_message,
                updated_at=now.isoformat(),
            )
            outcome = "dead_letter"
        else:
            delay = min(
                int(body["p_max_delay_seconds"]),
                int(body["p_base_delay_seconds"]) * 2 ** (outbox["attempt_count"] - 1),
            )
            outbox.update(
                status="pending",
                available_at=(now + timedelta(seconds=delay)).isoformat(),
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                last_error_code=error_code,
                last_error_message=error_message,
                updated_at=now.isoformat(),
            )
            outcome = "retry_scheduled"
        return httpx.Response(
            200,
            json={"outcome": outcome, "run": deepcopy(run), "outbox": deepcopy(outbox)},
            request=request,
        )

    def _confirm_callback(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        now = self._request_time(body.get("p_now")).isoformat()
        run = self.runs[body["p_run_id"]]
        outbox = self.outbox[body["p_run_id"]]
        if run["status"] == "queued":
            run.update(
                status="dispatched",
                provider_run_id=body["p_provider_run_id"],
                updated_at=now,
            )
            outbox.update(
                status="acknowledged",
                acknowledged_at=now,
                provider_run_id=body["p_provider_run_id"],
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                updated_at=now,
            )
            outcome = "acknowledged"
        elif (
            run["status"] in {"dispatched", "running", "validating"}
            and run["provider_run_id"] == body["p_provider_run_id"]
        ):
            outcome = "replayed"
        else:
            outcome = "provider_conflict"
        return httpx.Response(
            200,
            json={
                "outcome": outcome,
                "run": deepcopy(run),
                "outbox": deepcopy(outbox),
            },
            request=request,
        )

    def _fail(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        run = self.runs[body["p_run_id"]]
        now = self._request_time(body.get("p_now")).isoformat()
        if run["status"] in {"published", "cancelled"}:
            return httpx.Response(
                200,
                json={"outcome": "invalid_transition", "message": "terminal analysis runs are immutable"},
                request=request,
            )
        run.update(
            status="failed",
            provider_run_id=run.get("provider_run_id") or body["p_provider_run_id"],
            error_code=body["p_error_code"],
            error_message=body["p_error_message"],
            updated_at=now,
        )
        return httpx.Response(
            200,
            json={"outcome": "failed", "run": deepcopy(run)},
            request=request,
        )

    def _expire(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        now = self._request_time(body.get("p_now"))
        cutoff = now - timedelta(seconds=int(body["p_timeout_seconds"]))
        expired = []
        for run_id, outbox in self.outbox.items():
            if len(expired) >= int(body["p_limit"]):
                break
            run = self.runs[run_id]
            acknowledged = datetime.fromisoformat(outbox["acknowledged_at"]) if outbox["acknowledged_at"] else None
            if (
                outbox["status"] == "acknowledged"
                and acknowledged is not None
                and acknowledged <= cutoff
                and run["status"] in {"dispatched", "running", "validating"}
            ):
                run.update(
                    status="failed",
                    error_code="worker_result_timeout",
                    error_message="Worker did not publish a result or failure callback before the deadline",
                    updated_at=now.isoformat(),
                )
                expired.append(deepcopy(run))
        return httpx.Response(
            200,
            json={"outcome": "expired", "runs": expired},
            request=request,
        )

    def _request_time(self, raw: str | None) -> datetime:
        if raw:
            return datetime.fromisoformat(raw)
        return datetime.fromisoformat(self.now())

    def _update(self, request: httpx.Request) -> httpx.Response:
        self.update_rpc_calls += 1
        body = json.loads(request.read())
        candidate = body["p_run"]
        current = self.runs[candidate["id"]]
        allowed = {
            "queued": {"dispatched", "failed", "cancelled"},
            "dispatched": {"running", "validating", "failed", "cancelled"},
            "running": {"validating", "failed", "cancelled"},
            "validating": {"published", "failed", "cancelled"},
        }
        if current["status"] in {"published", "failed", "cancelled"}:
            return httpx.Response(
                200,
                json={"outcome": "invalid_transition", "message": "terminal analysis runs are immutable"},
                request=request,
            )
        if candidate["status"] != current["status"] and candidate["status"] not in allowed[current["status"]]:
            return httpx.Response(
                200,
                json={"outcome": "invalid_transition", "message": "invalid analysis run state transition"},
                request=request,
            )
        if self.conflict_next_update:
            self.conflict_next_update = False
            current["updated_at"] = self.now()
            return httpx.Response(
                200,
                json={"outcome": "conflict", "run": deepcopy(current)},
                request=request,
            )
        if current["updated_at"] != body["p_expected_updated_at"]:
            return httpx.Response(
                200,
                json={"outcome": "conflict", "run": deepcopy(current)},
                request=request,
            )
        updated = deepcopy(candidate)
        artifact = updated.pop("artifact", None)
        snapshot = updated.pop("snapshot", None)
        updated["config_id"] = current["config_id"]
        updated["created_at"] = current["created_at"]
        updated["updated_at"] = self.now()
        self.runs[updated["id"]] = updated
        artifact_row = None
        snapshot_row = None
        if updated["status"] == "published":
            assert artifact is not None and snapshot is not None
            snapshot_row = {
                "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "project_id": updated["project_id"],
                "run_id": updated["id"],
                **snapshot,
                "artifact_url": artifact["url"],
                "artifact_sha256": artifact["sha256"],
                "byte_size": artifact["byte_size"],
                "contract_version": artifact["contract_version"],
                "published": True,
            }
            artifact_row = {
                "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                "run_id": updated["id"],
                "snapshot_id": snapshot_row["id"],
                **artifact,
                "published": True,
            }
            self.snapshots[updated["id"]] = snapshot_row
            self.artifacts[updated["id"]] = artifact_row
        return httpx.Response(
            200,
            json={
                "outcome": "updated",
                "run": deepcopy(updated),
                "snapshot": deepcopy(snapshot_row),
                "artifact": deepcopy(artifact_row),
            },
            request=request,
        )

    @staticmethod
    def _select(
        request: httpx.Request,
        rows: dict[str, dict[str, Any]],
        filter_key: str,
    ) -> httpx.Response:
        raw = request.url.params.get(filter_key, "")
        value = raw.removeprefix("eq.")
        selected = [deepcopy(row) for row in rows.values() if str(row.get(filter_key)) == value]
        return httpx.Response(200, json=selected, request=request)


def make_store(state: MockSupabaseState) -> tuple[SupabaseRunStore, httpx.AsyncClient]:
    client = httpx.AsyncClient(
        base_url="https://project.supabase.co/rest/v1",
        transport=httpx.MockTransport(state),
    )
    return (
        SupabaseRunStore(
            url="https://project.supabase.co",
            service_role_key="service-role",
            client=client,
        ),
        client,
    )


def test_supabase_store_survives_restart_restores_result_and_idempotency() -> None:
    async def scenario() -> None:
        state = MockSupabaseState()
        store_one, client_one = make_store(state)
        store_two, client_two = make_store(state)
        worker_one = FakeWorkerProvider(auto_complete=False)
        worker_two = FakeWorkerProvider(auto_complete=False)
        artifacts = MappingArtifactFetcher()
        service_one = ControlPlaneService(
            provider=worker_one,
            store=store_one,
            publisher=NullDualWritePublisher(),
            artifact_fetcher=artifacts,
        )
        submission = RunCreateRequest(
            input_schema_version="best-factor/v1",
            inputs=DEFAULT_CONFIG,
            allow_fallback=False,
        )
        created = await service_one.create_run("best-factor", submission, "durable-run-0001")
        envelope = worker_one.dispatched[created.provider_run_id]
        manifest = worker_one.make_manifest(envelope)
        exact_bytes = canonical_json_bytes(manifest.payload)
        artifacts.artifacts[str(manifest.artifact.url)] = exact_bytes
        published = await service_one.accept_result_manifest(created.run_id, manifest)
        assert published.status == RunStatus.PUBLISHED
        with pytest.raises(InvalidRunTransitionError, match="immutable"):
            await store_one.update(created.run_id, status=RunStatus.FAILED)

        service_two = ControlPlaneService(
            provider=worker_two,
            store=store_two,
            publisher=NullDualWritePublisher(),
            artifact_fetcher=artifacts,
        )
        restored_status = await service_two.get_status(created.run_id)
        assert restored_status.status == RunStatus.PUBLISHED
        restored_result = await service_two.get_result(created.run_id)
        assert restored_result.payload == manifest.payload
        assert restored_result.artifact.sha256 == manifest.artifact.sha256

        replayed = await service_two.create_run("best-factor", submission, "durable-run-0001")
        assert replayed.replayed is True
        assert replayed.run_id == created.run_id
        assert worker_two.dispatched == {}

        changed = RunCreateRequest(
            input_schema_version="best-factor/v1",
            inputs={**DEFAULT_CONFIG, "top_n": 21},
            allow_fallback=False,
        )
        with pytest.raises(ControlPlaneError, match="different normalized request"):
            await service_two.create_run("best-factor", changed, "durable-run-0001")

        assert all("payload" not in row for row in state.runs.values())
        assert all("payload" not in row for row in state.snapshots.values())
        await store_one.close()
        await store_two.close()
        await client_one.aclose()
        await client_two.aclose()

    asyncio.run(scenario())


def test_supabase_store_retries_optimistic_update_conflict() -> None:
    async def scenario() -> None:
        state = MockSupabaseState()
        store, client = make_store(state)
        worker = FakeWorkerProvider(auto_complete=False)
        service = ControlPlaneService(
            provider=worker,
            store=store,
            publisher=NullDualWritePublisher(),
            artifact_fetcher=MappingArtifactFetcher(),
        )
        created = await service.create_run(
            "best-factor",
            RunCreateRequest(
                input_schema_version="best-factor/v1",
                inputs=DEFAULT_CONFIG,
                allow_fallback=False,
            ),
            "durable-race-0001",
        )
        state.conflict_next_update = True
        updated = await store.update(created.run_id, status=RunStatus.RUNNING)
        assert updated.status == RunStatus.RUNNING
        assert state.update_rpc_calls >= 2  # optimistic conflict plus retry
        await store.close()
        await client.aclose()

    asyncio.run(scenario())


def test_production_app_selects_authoritative_supabase_store() -> None:
    application = create_app(
        settings=Settings(
            environment="production",
            store_backend="supabase",
            supabase_url="https://project.supabase.co",
            supabase_service_role_key="service-role",
        ),
        provider=FakeWorkerProvider(auto_complete=False),
        publisher=NullDualWritePublisher(),
        artifact_fetcher=MappingArtifactFetcher(),
    )
    assert isinstance(application.state.control_service.store, SupabaseRunStore)
    with TestClient(application):
        pass
