from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from quant_control_api.artifacts import MappingArtifactFetcher
from quant_control_api.best_factor import DEFAULT_CONFIG
from quant_control_api.dual_write import NullDualWritePublisher
from quant_control_api.models import RunCreateRequest, RunStatus
from quant_control_api.providers.base import (
    DispatchEnvelope,
    DispatchReceipt,
    ProviderDispatchError,
    ProviderObservation,
)
from quant_control_api.providers.fake import FakeWorkerProvider
from quant_control_api.service import ControlPlaneService
from quant_control_api.store import DispatchOutboxStatus, InMemoryRunStore


class MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 24, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, *, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


class RecoverableProvider:
    name = "recoverable"
    run_creation_enabled = True
    supports_fallback_rejection = True
    status_tracking = "adapter-required"

    def __init__(
        self,
        external_dispatches: dict[str, DispatchEnvelope] | None = None,
        *,
        always_fail: bool = False,
    ) -> None:
        self.external_dispatches = external_dispatches if external_dispatches is not None else {}
        self.always_fail = always_fail
        self.dispatch_calls = 0
        self.reconcile_calls = 0

    async def dispatch(self, envelope: DispatchEnvelope) -> DispatchReceipt:
        self.dispatch_calls += 1
        if self.always_fail:
            raise ProviderDispatchError("simulated provider outage")
        self.external_dispatches[envelope.run_id] = envelope
        return DispatchReceipt(provider_run_id=f"{self.name}:{envelope.run_id}")

    async def reconcile_dispatch(
        self,
        envelope: DispatchEnvelope,
    ) -> DispatchReceipt | None:
        self.reconcile_calls += 1
        if envelope.run_id not in self.external_dispatches:
            return None
        return DispatchReceipt(provider_run_id=f"{self.name}:{envelope.run_id}")

    async def inspect(self, provider_run_id: str) -> ProviderObservation:
        del provider_run_id
        return ProviderObservation(status=RunStatus.DISPATCHED)

    async def check_ready(self) -> None:
        return None


class SimulatedProcessCrash(BaseException):
    pass


def submission() -> RunCreateRequest:
    return RunCreateRequest(
        input_schema_version="best-factor/v1",
        inputs=DEFAULT_CONFIG,
        allow_fallback=False,
    )


def service(
    *,
    provider: RecoverableProvider,
    store: InMemoryRunStore,
    dispatcher_id: str,
    before_hook=None,
    after_hook=None,
    max_attempts: int = 3,
    clock=None,
) -> ControlPlaneService:
    return ControlPlaneService(
        provider=provider,
        store=store,
        publisher=NullDualWritePublisher(),
        artifact_fetcher=MappingArtifactFetcher(),
        dispatcher_id=dispatcher_id,
        dispatch_lease_seconds=5,
        dispatch_max_attempts=max_attempts,
        dispatch_retry_base_seconds=2,
        dispatch_retry_max_seconds=30,
        dispatch_before_provider_hook=before_hook,
        dispatch_after_provider_hook=after_hook,
        clock=clock or datetime.now,
    )


def test_atomic_outbox_recovers_crash_before_provider_dispatch() -> None:
    async def scenario() -> None:
        clock = MutableClock()
        store = InMemoryRunStore(clock=clock)
        run_ids: list[str] = []

        def crash_before(lease) -> None:
            run_ids.append(lease.run.run_id)
            raise SimulatedProcessCrash()

        crashed = service(
            provider=RecoverableProvider(),
            store=store,
            dispatcher_id="instance-before-crash",
            before_hook=crash_before,
            clock=clock,
        )
        with pytest.raises(SimulatedProcessCrash):
            await crashed.create_run(
                "best-factor",
                submission(),
                "crash-before-dispatch-001",
            )

        run_id = run_ids[0]
        leased = await store.get_dispatch_outbox(run_id)
        assert leased.status == DispatchOutboxStatus.LEASED
        assert leased.attempt_count == 1

        clock.advance(seconds=5)
        recovered_provider = RecoverableProvider()
        recovered = service(
            provider=recovered_provider,
            store=store,
            dispatcher_id="instance-after-crash",
            clock=clock,
        )
        dispatched = await recovered.dispatch_pending_once(run_id=run_id)
        assert dispatched is not None
        assert dispatched.status == RunStatus.DISPATCHED
        assert recovered_provider.dispatch_calls == 1
        acknowledged = await store.get_dispatch_outbox(run_id)
        assert acknowledged.status == DispatchOutboxStatus.ACKNOWLEDGED
        assert acknowledged.attempt_count == 2

    asyncio.run(scenario())


def test_crash_after_provider_dispatch_reconciles_without_duplicate_dispatch() -> None:
    async def scenario() -> None:
        clock = MutableClock()
        store = InMemoryRunStore(clock=clock)
        external: dict[str, DispatchEnvelope] = {}
        run_ids: list[str] = []

        def crash_after(receipt: DispatchReceipt) -> None:
            run_ids.append(receipt.provider_run_id.rsplit(":", 1)[-1])
            raise SimulatedProcessCrash()

        first_provider = RecoverableProvider(external)
        crashed = service(
            provider=first_provider,
            store=store,
            dispatcher_id="instance-after-provider",
            after_hook=crash_after,
            clock=clock,
        )
        with pytest.raises(SimulatedProcessCrash):
            await crashed.create_run(
                "best-factor",
                submission(),
                "crash-after-dispatch-001",
            )
        assert first_provider.dispatch_calls == 1

        clock.advance(seconds=5)
        recovered_provider = RecoverableProvider(external)
        recovered = service(
            provider=recovered_provider,
            store=store,
            dispatcher_id="instance-reconcile",
            clock=clock,
        )
        dispatched = await recovered.dispatch_pending_once(run_id=run_ids[0])
        assert dispatched is not None
        assert dispatched.status == RunStatus.DISPATCHED
        assert recovered_provider.reconcile_calls == 1
        assert recovered_provider.dispatch_calls == 0
        assert len(external) == 1

    asyncio.run(scenario())


def test_expired_lease_has_only_one_concurrent_reclaimer() -> None:
    async def scenario() -> None:
        clock = MutableClock()
        store = InMemoryRunStore(clock=clock)
        run_ids: list[str] = []

        def crash_before(lease) -> None:
            run_ids.append(lease.run.run_id)
            raise SimulatedProcessCrash()

        with pytest.raises(SimulatedProcessCrash):
            await service(
                provider=RecoverableProvider(),
                store=store,
                dispatcher_id="initial-claimer",
                before_hook=crash_before,
                clock=clock,
            ).create_run("best-factor", submission(), "concurrent-reclaim-001")

        clock.advance(seconds=5)
        shared_external: dict[str, DispatchEnvelope] = {}
        provider_one = RecoverableProvider(shared_external)
        provider_two = RecoverableProvider(shared_external)
        worker_one = service(
            provider=provider_one,
            store=store,
            dispatcher_id="reclaimer-one",
            clock=clock,
        )
        worker_two = service(
            provider=provider_two,
            store=store,
            dispatcher_id="reclaimer-two",
            clock=clock,
        )
        results = await asyncio.gather(
            worker_one.dispatch_pending_once(run_id=run_ids[0]),
            worker_two.dispatch_pending_once(run_id=run_ids[0]),
        )
        assert sum(result is not None for result in results) == 1
        assert provider_one.dispatch_calls + provider_two.dispatch_calls == 1
        assert len(shared_external) == 1

    asyncio.run(scenario())


def test_retry_backoff_exhaustion_dead_letters_and_fails_run() -> None:
    async def scenario() -> None:
        clock = MutableClock()
        store = InMemoryRunStore(clock=clock)
        provider = RecoverableProvider(always_fail=True)
        control = service(
            provider=provider,
            store=store,
            dispatcher_id="retry-worker",
            max_attempts=3,
            clock=clock,
        )
        created = await control.create_run(
            "best-factor",
            submission(),
            "retry-exhaustion-001",
        )
        assert created.status == RunStatus.QUEUED
        outbox = await store.get_dispatch_outbox(created.run_id)
        assert outbox.available_at == clock() + timedelta(seconds=2)

        clock.advance(seconds=2)
        await control.dispatch_pending_once(run_id=created.run_id)
        outbox = await store.get_dispatch_outbox(created.run_id)
        assert outbox.available_at == clock() + timedelta(seconds=4)

        clock.advance(seconds=4)
        failed = await control.dispatch_pending_once(run_id=created.run_id)
        assert failed is not None
        assert failed.status == RunStatus.FAILED
        assert failed.error_code == "worker_dispatch_retry_exhausted"
        outbox = await store.get_dispatch_outbox(created.run_id)
        assert outbox.status == DispatchOutboxStatus.DEAD_LETTER
        assert outbox.attempt_count == 3
        assert provider.dispatch_calls == 3

        replay = await control.create_run(
            "best-factor",
            submission(),
            "retry-exhaustion-001",
        )
        assert replay.replayed is True
        assert replay.run_id == created.run_id
        assert provider.dispatch_calls == 3

    asyncio.run(scenario())


def test_acknowledged_run_expires_without_result_or_failure_callback() -> None:
    async def scenario() -> None:
        clock = MutableClock()
        store = InMemoryRunStore(clock=clock)
        provider = RecoverableProvider()
        control = service(
            provider=provider,
            store=store,
            dispatcher_id="expiry-worker",
            clock=clock,
        )
        created = await control.create_run(
            "best-factor",
            submission(),
            "stuck-run-expiry-001",
        )
        assert created.status == RunStatus.DISPATCHED

        clock.advance(seconds=300)
        expired = await control.expire_stuck_runs_once(
            timeout_seconds=300,
            limit=10,
            now=clock(),
        )
        assert [record.run_id for record in expired] == [created.run_id]
        assert expired[0].status == RunStatus.FAILED
        assert expired[0].error_code == "worker_result_timeout"

        replay = await control.create_run(
            "best-factor",
            submission(),
            "stuck-run-expiry-001",
        )
        assert replay.replayed is True
        assert replay.status == RunStatus.FAILED
        assert provider.dispatch_calls == 1

        second_expiry = await control.expire_stuck_runs_once(
            timeout_seconds=300,
            limit=10,
            now=clock(),
        )
        assert second_expiry == []

    asyncio.run(scenario())


def test_callback_closes_crash_after_provider_before_ack_window() -> None:
    async def scenario() -> None:
        clock = MutableClock()
        store = InMemoryRunStore(clock=clock)
        provider = FakeWorkerProvider(auto_complete=True)
        fetcher = MappingArtifactFetcher()

        def crash_after_provider(receipt: DispatchReceipt) -> None:
            del receipt
            raise SimulatedProcessCrash()

        crashed = ControlPlaneService(
            provider=provider,
            store=store,
            publisher=NullDualWritePublisher(),
            artifact_fetcher=fetcher,
            dispatcher_id="callback-crash-window",
            dispatch_lease_seconds=5,
            dispatch_after_provider_hook=crash_after_provider,
            clock=clock,
        )
        with pytest.raises(SimulatedProcessCrash):
            await crashed.create_run(
                "best-factor",
                submission(),
                "callback-crash-window-001",
            )

        provider_run_id, envelope = next(iter(provider.dispatched.items()))
        manifest = provider.make_manifest(envelope)
        from quant_control_api.best_factor import canonical_json_bytes

        fetcher.artifacts[str(manifest.artifact.url)] = canonical_json_bytes(
            manifest.payload
        )
        recovered = service(
            provider=provider,  # type: ignore[arg-type]
            store=store,
            dispatcher_id="callback-recovery",
            clock=clock,
        )
        recovered.artifact_fetcher = fetcher
        published = await recovered.accept_result_manifest(
            envelope.run_id,
            manifest,
        )
        assert published.status == RunStatus.PUBLISHED
        assert published.provider_run_id == provider_run_id
        outbox = await store.get_dispatch_outbox(envelope.run_id)
        assert outbox.status == DispatchOutboxStatus.ACKNOWLEDGED
        assert outbox.provider_run_id == provider_run_id

    asyncio.run(scenario())


def test_validating_run_never_regresses_and_can_resume_or_expire() -> None:
    async def scenario() -> None:
        clock = MutableClock()
        store = InMemoryRunStore(clock=clock)
        provider = FakeWorkerProvider(auto_complete=False)
        fetcher = MappingArtifactFetcher()
        control = ControlPlaneService(
            provider=provider,
            store=store,
            publisher=NullDualWritePublisher(),
            artifact_fetcher=fetcher,
            dispatcher_id="validation-recovery",
            dispatch_lease_seconds=5,
            clock=clock,
        )
        first = await control.create_run(
            "best-factor",
            submission(),
            "validating-resume-001",
        )
        await store.update(first.run_id, status=RunStatus.VALIDATING)

        observed = await control.get_status(first.run_id)
        assert observed.status == RunStatus.VALIDATING

        envelope = provider.dispatched[first.provider_run_id]
        manifest = provider.make_manifest(envelope)
        from quant_control_api.best_factor import canonical_json_bytes

        fetcher.artifacts[str(manifest.artifact.url)] = canonical_json_bytes(
            manifest.payload
        )
        resumed = await control.accept_result_manifest(first.run_id, manifest)
        assert resumed.status == RunStatus.PUBLISHED

        second = await control.create_run(
            "best-factor",
            submission(),
            "validating-expiry-001",
        )
        await store.update(second.run_id, status=RunStatus.VALIDATING)
        clock.advance(seconds=300)
        expired = await control.expire_stuck_runs_once(
            timeout_seconds=300,
            limit=10,
            now=clock(),
        )
        assert [record.run_id for record in expired] == [second.run_id]
        assert expired[0].error_code == "worker_result_timeout"

    asyncio.run(scenario())
