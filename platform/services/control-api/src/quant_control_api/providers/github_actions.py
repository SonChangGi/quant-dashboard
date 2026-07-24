from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import httpx

from ..models import RunStatus
from .base import (
    DispatchEnvelope,
    DispatchReceipt,
    ProviderDispatchError,
    ProviderObservation,
    ProviderUnavailableError,
)


def _number(value: Any) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else format(number, ".15g")


def workflow_inputs(envelope: DispatchEnvelope) -> dict[str, str]:
    """Map the exact 11 inputs plus fallback and control identity to the worker."""

    effective = envelope.effective_inputs
    factor_allowlist = effective["factor_allowlist"]
    return {
        "period": str(effective["period"]),
        "rebalance": str(effective["rebalance"]),
        "top_n": str(effective["top_n"]),
        "weighting": str(effective["weighting"]),
        "factor_preset": str(effective["factor_preset"]),
        "factor_allowlist": ",".join(factor_allowlist) if factor_allowlist else "__preset__",
        "min_market_cap": _number(effective["min_market_cap"]),
        "min_dollar_volume": _number(effective["min_dollar_volume"]),
        "eligibility_adv_window": str(effective["eligibility_adv_window"]),
        "transaction_cost_bps": _number(effective["transaction_cost_bps"]),
        "transaction_cost_model": str(effective["transaction_cost_model"]),
        "allow_fallback": "true" if envelope.allow_fallback else "false",
        "control_run_id": envelope.run_id,
        "control_input_schema_version": envelope.input_schema_version,
        "control_input_schema_hash": envelope.input_schema_hash,
        "control_config_hash_algorithm": envelope.config_hash_algorithm,
        "control_config_hash": envelope.config_hash,
    }


class GitHubActionsWorkerProvider:
    """Thin dispatch adapter; it never executes analysis in the API process.

    GitHub's workflow-dispatch response has no workflow-run ID. Project
    workflows therefore carry the durable control run ID and post an exact
    success or failure callback. Until that callback arrives, status stays
    fail-closed at `dispatched`; it is never inferred from the newest run.
    """

    name = "github-actions"
    run_creation_enabled = True
    supports_fallback_rejection = True
    status_tracking = "adapter-required"

    def __init__(
        self,
        *,
        enabled: bool,
        token: str,
        owner: str,
        repo: str,
        workflow: str,
        ref: str,
        workflow_inputs_builder: Callable[[DispatchEnvelope], dict[str, str]] = workflow_inputs,
        correlation_builder: Callable[[str], str] | None = None,
        correlation_requires_exact_title: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not enabled:
            raise ProviderUnavailableError("GitHub Actions dispatch requires explicit enablement")
        if not token:
            raise ProviderUnavailableError("GitHub Actions dispatch requires a server-side token")
        self.owner = owner
        self.repo = repo
        self.workflow = workflow
        self.ref = ref
        self.workflow_inputs_builder = workflow_inputs_builder
        self.correlation_builder = correlation_builder or (
            lambda run_id: f"control={run_id}"
        )
        self.correlation_requires_exact_title = correlation_requires_exact_title
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            base_url="https://api.github.com",
            timeout=httpx.Timeout(15.0),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "quant-control-api/0.1",
            },
        )

    async def dispatch(self, envelope: DispatchEnvelope) -> DispatchReceipt:
        url = f"/repos/{self.owner}/{self.repo}/actions/workflows/{self.workflow}/dispatches"
        response = await self.client.post(
            url,
            json={
                "ref": self.ref,
                "inputs": self.workflow_inputs_builder(envelope),
            },
        )
        if response.status_code != 204:
            raise ProviderDispatchError(f"GitHub workflow dispatch failed with status {response.status_code}")
        provider_run_id = f"github-actions:{envelope.run_id}"
        return DispatchReceipt(provider_run_id=provider_run_id, status=RunStatus.DISPATCHED)

    async def reconcile_dispatch(
        self,
        envelope: DispatchEnvelope,
    ) -> DispatchReceipt | None:
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/actions/workflows/{self.workflow}/runs",
            params={
                "event": "workflow_dispatch",
                "branch": self.ref,
                "per_page": "100",
            },
        )
        if response.status_code != 200:
            raise ProviderUnavailableError(f"GitHub workflow reconciliation failed with status {response.status_code}")
        body = response.json()
        runs = body.get("workflow_runs") if isinstance(body, dict) else None
        if not isinstance(runs, list) or len(runs) > 100:
            raise ProviderUnavailableError("GitHub workflow reconciliation returned an invalid run list")
        correlation = self.correlation_builder(envelope.run_id)
        for item in runs:
            if not isinstance(item, dict):
                continue
            if item.get("event") != "workflow_dispatch":
                continue
            if item.get("head_branch") not in (None, self.ref):
                continue
            title = item.get("display_title")
            matched = (
                title == correlation
                if self.correlation_requires_exact_title
                else isinstance(title, str) and correlation in title
            )
            if matched:
                return DispatchReceipt(
                    provider_run_id=f"github-actions:{envelope.run_id}",
                    status=RunStatus.DISPATCHED,
                )
        return None

    async def check_ready(self) -> None:
        response = await self.client.get(f"/repos/{self.owner}/{self.repo}/actions/workflows/{self.workflow}")
        if response.status_code != 200:
            raise ProviderUnavailableError(f"GitHub workflow readiness failed with status {response.status_code}")

    async def inspect(self, provider_run_id: str) -> ProviderObservation:
        prefix, separator, raw_run_id = provider_run_id.partition(":")
        try:
            parsed_run_id = uuid.UUID(raw_run_id)
        except ValueError:
            parsed_run_id = None
        if prefix != "github-actions" or separator != ":" or parsed_run_id is None:
            return ProviderObservation(
                status=RunStatus.FAILED,
                error_code="unknown_provider_run",
                error_message="GitHub dispatch correlation is malformed",
            )
        # workflow_dispatch does not return a GitHub run ID. The callback is
        # authoritative, so a valid durable control-run correlation remains
        # dispatched across API process restarts rather than being guessed.
        return ProviderObservation(status=RunStatus.DISPATCHED)

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()
