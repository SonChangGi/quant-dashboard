from __future__ import annotations

import asyncio
import hmac
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .adapters import ProjectAdapterRegistry, default_project_adapters
from .artifacts import ArtifactFetcher, HttpArtifactFetcher
from .dual_write import (
    NullDualWritePublisher,
    SupabaseDualWritePublisher,
    SupabaseProjectMetadataPublisher,
)
from .models import (
    ProjectCapabilities,
    RunCreateRequest,
    RunResultResponse,
    RunStatusResponse,
    WorkerFailureManifest,
    WorkerResultManifest,
)
from .providers import DisabledWorkerProvider, GitHubActionsWorkerProvider
from .providers.base import ProviderUnavailableError, WorkerProvider
from .service import ControlPlaneError, ControlPlaneService
from .settings import Settings
from .store import InMemoryRunStore, RunStore
from .supabase_store import SupabaseRunStore

logger = logging.getLogger(__name__)


def _providers_from_settings(
    settings: Settings,
    adapters: ProjectAdapterRegistry,
) -> dict[str, WorkerProvider]:
    if settings.provider == "github-actions":
        providers: dict[str, WorkerProvider] = {}
        for adapter in adapters:
            if adapter.project_id == "momentum":
                providers[adapter.project_id] = GitHubActionsWorkerProvider(
                    enabled=settings.github_enabled,
                    token=settings.github_token,
                    owner=settings.momentum_github_owner,
                    repo=settings.momentum_github_repo,
                    workflow=settings.momentum_github_workflow,
                    ref=settings.momentum_github_ref,
                    workflow_inputs_builder=adapter.workflow_inputs,
                    correlation_builder=lambda run_id: f"Controlled Momentum · {run_id}",
                    correlation_requires_exact_title=True,
                )
            else:
                providers[adapter.project_id] = GitHubActionsWorkerProvider(
                    enabled=settings.github_enabled,
                    token=settings.github_token,
                    owner=settings.github_owner,
                    repo=settings.github_repo,
                    workflow=settings.github_workflow,
                    ref=settings.github_ref,
                    workflow_inputs_builder=adapter.workflow_inputs,
                )
        return providers
    disabled = DisabledWorkerProvider()
    return {project_id: disabled for project_id in adapters.project_ids}


def create_app(
    *,
    settings: Settings | None = None,
    provider: WorkerProvider | None = None,
    providers: dict[str, WorkerProvider] | None = None,
    adapters: ProjectAdapterRegistry | None = None,
    store: RunStore | None = None,
    publisher: object | None = None,
    artifact_fetcher: ArtifactFetcher | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    resolved_settings.validate()
    resolved_adapters = adapters or default_project_adapters()
    if provider is not None and providers is not None:
        raise ValueError("pass either provider or providers, not both")
    if providers is None:
        if provider is not None:
            providers = {
                project_id: provider
                for project_id in resolved_adapters.project_ids
            }
        else:
            providers = _providers_from_settings(
                resolved_settings,
                resolved_adapters,
            )
    if store is not None:
        resolved_store = store
    elif resolved_settings.store_backend == "supabase":
        resolved_store = SupabaseRunStore(
            url=resolved_settings.supabase_url,
            service_role_key=resolved_settings.supabase_service_role_key,
        )
    else:
        resolved_store = InMemoryRunStore()
    if resolved_settings.environment == "production" and isinstance(resolved_store, InMemoryRunStore):
        raise ValueError("Production cannot use the development-only InMemoryRunStore")
    resolved_artifact_fetcher = artifact_fetcher or HttpArtifactFetcher()
    if publisher is None:
        if isinstance(resolved_store, SupabaseRunStore):
            publisher = SupabaseProjectMetadataPublisher(
                url=resolved_settings.supabase_url,
                service_role_key=resolved_settings.supabase_service_role_key,
            )
        elif resolved_settings.supabase_dual_write_enabled:
            publisher = SupabaseDualWritePublisher(
                url=resolved_settings.supabase_url,
                service_role_key=resolved_settings.supabase_service_role_key,
            )
        else:
            publisher = NullDualWritePublisher()

    service = ControlPlaneService(
        providers=providers,
        adapters=resolved_adapters,
        store=resolved_store,
        publisher=publisher,  # type: ignore[arg-type]
        artifact_fetcher=resolved_artifact_fetcher,
        dispatch_lease_seconds=resolved_settings.dispatch_lease_seconds,
        dispatch_max_attempts=resolved_settings.dispatch_max_attempts,
        dispatch_retry_base_seconds=resolved_settings.dispatch_retry_base_seconds,
        dispatch_retry_max_seconds=resolved_settings.dispatch_retry_max_seconds,
    )

    async def dispatch_pump(stop: asyncio.Event) -> None:
        poll_seconds = resolved_settings.dispatch_poll_milliseconds / 1000
        next_expiry_scan = 0.0
        while not stop.is_set():
            processed = 0
            try:
                for _ in range(resolved_settings.dispatch_batch_size):
                    if await service.dispatch_pending_once() is None:
                        break
                    processed += 1
                loop_time = asyncio.get_running_loop().time()
                if loop_time >= next_expiry_scan:
                    await service.expire_stuck_runs_once(
                        timeout_seconds=resolved_settings.worker_result_timeout_seconds,
                        limit=resolved_settings.worker_expiry_batch_size,
                    )
                    next_expiry_scan = loop_time + resolved_settings.worker_expiry_scan_seconds
            except Exception as exc:
                logger.exception(
                    "dispatch pump iteration failed",
                    extra={"errorType": type(exc).__name__},
                )
            if processed >= resolved_settings.dispatch_batch_size:
                await asyncio.sleep(0)
                continue
            try:
                await asyncio.wait_for(stop.wait(), timeout=poll_seconds)
            except TimeoutError:
                pass

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        del application
        stop = asyncio.Event()
        pump_task: asyncio.Task[None] | None = None
        if resolved_settings.dispatch_pump_enabled and any(
            item.run_creation_enabled for item in providers.values()
        ):
            pump_task = asyncio.create_task(
                dispatch_pump(stop),
                name="analysis-dispatch-outbox",
            )
        yield
        stop.set()
        if pump_task is not None:
            await pump_task
        closed_provider_ids: set[int] = set()
        for item in providers.values():
            if id(item) in closed_provider_ids:
                continue
            closed_provider_ids.add(id(item))
            close_provider = getattr(item, "close", None)
            if close_provider is not None:
                await close_provider()
        await publisher.close()  # type: ignore[attr-defined]
        await resolved_artifact_fetcher.close()  # type: ignore[attr-defined]
        await resolved_store.close()

    application = FastAPI(
        title="Quant Research Control API",
        version="0.1.0",
        description=(
            "Validates analysis inputs and dispatches external workers. "
            "This process never executes project analysis."
        ),
        lifespan=lifespan,
    )
    application.state.control_service = service
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    def authorize(authorization: Annotated[str | None, Header()] = None) -> None:
        token = resolved_settings.run_api_token
        if not token:
            return
        expected = f"Bearer {token}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise ControlPlaneError(
                status_code=401,
                code="unauthorized",
                message="Owner authorization is required to create an analysis run",
            )

    def authorize_worker(authorization: Annotated[str | None, Header()] = None) -> None:
        token = resolved_settings.worker_callback_token
        if not token:
            if resolved_settings.provider == "github-actions":
                raise ControlPlaneError(
                    status_code=503,
                    code="worker_callback_disabled",
                    message="Worker callback token is not configured",
                )
            return
        expected = f"Bearer {token}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise ControlPlaneError(
                status_code=401,
                code="unauthorized_worker",
                message="Worker callback authorization is required",
            )

    @application.exception_handler(ControlPlaneError)
    async def control_error_handler(request: Request, exc: ControlPlaneError) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @application.get("/healthz", tags=["operations"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/readyz", tags=["operations"])
    async def readyz() -> JSONResponse:
        if resolved_settings.environment == "production":
            if not isinstance(resolved_store, SupabaseRunStore):
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "reason": "durable_store_required"},
                )
            if resolved_settings.provider != "github-actions":
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "reason": "worker_provider_required"},
                )
            if not resolved_settings.dispatch_pump_enabled:
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "reason": "dispatch_pump_required"},
                )
        try:
            await resolved_store.check_ready()
            checked_provider_ids: set[int] = set()
            for item in providers.values():
                if (
                    not item.run_creation_enabled
                    or id(item) in checked_provider_ids
                ):
                    continue
                checked_provider_ids.add(id(item))
                await item.check_ready()
        except (
            httpx.HTTPError,
            ProviderUnavailableError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "reason": "dependency_unavailable",
                    "dependencyType": type(exc).__name__,
                },
            )
        return JSONResponse(status_code=200, content={"status": "ready"})

    @application.get(
        "/v1/projects/{project_id}/capabilities",
        response_model=ProjectCapabilities,
        response_model_exclude_none=True,
        tags=["projects"],
    )
    async def capabilities(project_id: str) -> ProjectCapabilities:
        return service.capabilities(project_id)

    @application.post(
        "/v1/projects/{project_id}/runs",
        response_model=RunStatusResponse,
        response_model_exclude_none=True,
        status_code=202,
        tags=["runs"],
        dependencies=[Depends(authorize)],
    )
    async def create_run(
        project_id: str,
        body: RunCreateRequest,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    ) -> RunStatusResponse:
        return await service.create_run(project_id, body, idempotency_key)

    @application.get(
        "/v1/runs/{run_id}",
        response_model=RunStatusResponse,
        response_model_exclude_none=True,
        tags=["runs"],
    )
    async def run_status(run_id: str) -> RunStatusResponse:
        return await service.get_status(run_id)

    @application.get(
        "/v1/runs/{run_id}/result",
        response_model=RunResultResponse,
        response_model_exclude_none=True,
        tags=["runs"],
    )
    async def run_result(run_id: str) -> RunResultResponse:
        return await service.get_result(run_id)

    @application.post(
        "/v1/internal/runs/{run_id}/result-manifest",
        response_model=RunStatusResponse,
        response_model_exclude_none=True,
        tags=["internal"],
        dependencies=[Depends(authorize_worker)],
    )
    async def result_manifest_callback(
        run_id: str,
        body: WorkerResultManifest,
    ) -> RunStatusResponse:
        return await service.accept_result_manifest(run_id, body)

    @application.post(
        "/v1/internal/runs/{run_id}/failure",
        response_model=RunStatusResponse,
        response_model_exclude_none=True,
        tags=["internal"],
        dependencies=[Depends(authorize_worker)],
    )
    async def worker_failure_callback(
        run_id: str,
        body: WorkerFailureManifest,
    ) -> RunStatusResponse:
        return await service.accept_worker_failure(run_id, body)

    return application


app = create_app()
