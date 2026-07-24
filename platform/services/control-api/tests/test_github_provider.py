from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from quant_control_api.adapters import default_project_adapters
from quant_control_api.app import _providers_from_settings
from quant_control_api.best_factor import (
    CONFIG_HASH_ALGORITHM,
    INPUT_SCHEMA_HASH,
    INPUT_SCHEMA_VERSION,
    normalize_inputs,
)
from quant_control_api.providers.base import DispatchEnvelope, ProviderUnavailableError
from quant_control_api.providers.github_actions import GitHubActionsWorkerProvider, workflow_inputs
from quant_control_api.settings import Settings


def envelope() -> DispatchEnvelope:
    from quant_control_api.best_factor import DEFAULT_CONFIG

    normalized = normalize_inputs(DEFAULT_CONFIG)
    return DispatchEnvelope(
        project_id="best-factor",
        run_id="11111111-1111-4111-8111-111111111111",
        input_schema_version=INPUT_SCHEMA_VERSION,
        input_schema_hash=INPUT_SCHEMA_HASH,
        config_hash_algorithm=CONFIG_HASH_ALGORITHM,
        config_hash=normalized.config_hash,
        requested_inputs=normalized.requested,
        normalized_inputs=normalized.normalized,
        effective_inputs=normalized.effective,
        allow_fallback=False,
    )


def test_workflow_input_mapping_has_11_analysis_and_control_identity_fields() -> None:
    values = workflow_inputs(envelope())
    assert values["period"] == "5y"
    assert values["top_n"] == "20"
    assert values["factor_allowlist"] == "__preset__"
    assert values["min_market_cap"] == "10000000000"
    assert values["transaction_cost_bps"] == "5"
    assert values["allow_fallback"] == "false"
    assert values["control_run_id"] == envelope().run_id
    assert values["control_input_schema_hash"] == INPUT_SCHEMA_HASH
    assert values["control_config_hash_algorithm"] == CONFIG_HASH_ALGORITHM
    assert len(values) == 17


def test_github_provider_is_gated_and_dispatches_without_running_analysis() -> None:
    try:
        GitHubActionsWorkerProvider(
            enabled=False,
            token="secret",
            owner="SonChangGi",
            repo="best-factor",
            workflow="update-dashboard.yml",
            ref="main",
        )
    except ProviderUnavailableError:
        pass
    else:  # pragma: no cover
        raise AssertionError("disabled provider must not initialize")

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    async def scenario() -> None:
        client = httpx.AsyncClient(
            base_url="https://api.github.com",
            transport=httpx.MockTransport(handler),
        )
        provider = GitHubActionsWorkerProvider(
            enabled=True,
            token="server-only-token",
            owner="SonChangGi",
            repo="best-factor",
            workflow="update-dashboard.yml",
            ref="main",
            client=client,
        )
        receipt = await provider.dispatch(envelope())
        assert receipt.provider_run_id == f"github-actions:{envelope().run_id}"
        restarted_provider = GitHubActionsWorkerProvider(
            enabled=True,
            token="server-only-token",
            owner="SonChangGi",
            repo="best-factor",
            workflow="update-dashboard.yml",
            ref="main",
            client=client,
        )
        observation = await restarted_provider.inspect(receipt.provider_run_id)
        assert observation.status == "dispatched"
        malformed = await restarted_provider.inspect("github-actions:not-a-uuid")
        assert malformed.status == "failed"
        assert malformed.error_code == "unknown_provider_run"
        await client.aclose()

    asyncio.run(scenario())
    assert len(requests) == 1
    payload = json.loads(requests[0].content)
    assert payload["ref"] == "main"
    assert payload["inputs"]["control_run_id"] == envelope().run_id


def test_provider_registry_keeps_project_targets_and_workflow_mappers_isolated() -> None:
    settings = Settings(
        provider="github-actions",
        github_enabled=True,
        github_token="server-only",
        run_api_token="owner",
        worker_callback_token="worker",
    )
    providers = _providers_from_settings(settings, default_project_adapters())
    assert set(providers) == {"best-factor", "momentum", "fear-greed"}
    best = providers["best-factor"]
    momentum = providers["momentum"]
    fear = providers["fear-greed"]
    assert (best.owner, best.repo, best.workflow, best.ref) == (  # type: ignore[attr-defined]
        "SonChangGi",
        "best-factor",
        "update-dashboard.yml",
        "main",
    )
    assert (  # type: ignore[attr-defined]
        momentum.owner,
        momentum.repo,
        momentum.workflow,
        momentum.ref,
    ) == (
        "SonChangGi",
        "momentum-factor-lab",
        "controlled-analysis.yml",
        "main",
    )
    assert (  # type: ignore[attr-defined]
        fear.owner,
        fear.repo,
        fear.workflow,
        fear.ref,
    ) == (
        "SonChangGi",
        "fearNgreed",
        "controlled-analysis.yml",
        "main",
    )
    assert fear.correlation_builder(  # type: ignore[attr-defined]
        "11111111-1111-4111-8111-111111111111"
    ) == (
        "Controlled Fear & Greed · 11111111-1111-4111-8111-111111111111"
    )
    assert fear.correlation_requires_exact_title is True  # type: ignore[attr-defined]

    async def close() -> None:
        await best.close()  # type: ignore[attr-defined]
        await momentum.close()  # type: ignore[attr-defined]
        await fear.close()  # type: ignore[attr-defined]

    asyncio.run(close())


def test_fear_provider_target_can_be_configured_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUANT_CONTROL_FEAR_GITHUB_OWNER", "ExampleOwner")
    monkeypatch.setenv("QUANT_CONTROL_FEAR_GITHUB_REPO", "fear-worker")
    monkeypatch.setenv(
        "QUANT_CONTROL_FEAR_GITHUB_WORKFLOW",
        "fear-control.yml",
    )
    monkeypatch.setenv("QUANT_CONTROL_FEAR_GITHUB_REF", "release")
    settings = Settings.from_env()
    assert (
        settings.fear_github_owner,
        settings.fear_github_repo,
        settings.fear_github_workflow,
        settings.fear_github_ref,
    ) == (
        "ExampleOwner",
        "fear-worker",
        "fear-control.yml",
        "release",
    )
