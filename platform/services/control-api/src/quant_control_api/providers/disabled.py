from __future__ import annotations

from .base import (
    DispatchEnvelope,
    DispatchReceipt,
    ProviderObservation,
    ProviderUnavailableError,
)


class DisabledWorkerProvider:
    name = "disabled"
    run_creation_enabled = False
    supports_fallback_rejection = True
    status_tracking = "disabled"

    async def dispatch(self, envelope: DispatchEnvelope) -> DispatchReceipt:
        del envelope
        raise ProviderUnavailableError("analysis worker provider is disabled")

    async def reconcile_dispatch(
        self,
        envelope: DispatchEnvelope,
    ) -> DispatchReceipt | None:
        del envelope
        return None

    async def check_ready(self) -> None:
        raise ProviderUnavailableError("analysis worker provider is disabled")

    async def inspect(self, provider_run_id: str) -> ProviderObservation:
        del provider_run_id
        raise ProviderUnavailableError("analysis worker provider is disabled")
