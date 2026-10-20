from __future__ import annotations

import asyncio
import re
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from quant_control_api.adapters.momentum import (
    CODE_VERSION_PATTERN,
    CONFIG_HASH_ALGORITHM,
    INPUT_SCHEMA_VERSION,
    PROJECT_ID,
    PROJECT_NAME,
    RESULT_CONTRACT_VERSION,
    STATIC_FALLBACK_URL,
    MomentumAdapter,
)
from quant_control_api.artifacts import ArtifactVerificationError, HttpArtifactFetcher
from quant_control_api.models import ArtifactIdentity
from quant_control_api.settings import Settings

RUN_ID = "11111111-1111-4111-8111-111111111111"
RESULT_KEY = "a" * 64


def artifact_url(repository: str) -> str:
    return f"https://sonchanggi.github.io/{repository}/data/control-runs/v1/{RUN_ID}/{RESULT_KEY}.json"


def artifact(url: str) -> ArtifactIdentity:
    return ArtifactIdentity(url=url, sha256="0" * 64, byte_size=2, contract_version=RESULT_CONTRACT_VERSION)


def test_factor_defaults_keep_legacy_control_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUANT_CONTROL_MOMENTUM_GITHUB_REPO", raising=False)
    assert Settings().momentum_github_repo == Settings.from_env().momentum_github_repo == "factor"
    assert PROJECT_NAME == "Factor"
    assert STATIC_FALLBACK_URL == "https://sonchanggi.github.io/factor/data/dashboard.json"
    assert PROJECT_ID == "momentum"
    assert INPUT_SCHEMA_VERSION == "momentum/v3"
    assert CONFIG_HASH_ALGORITHM == "momentum-research-inputs-rfc8785-v1"
    assert RESULT_CONTRACT_VERSION == "momentum/schema-v5-control-result-v1"
    # An explicit deployment setting remains authoritative during a staged rollout.
    monkeypatch.setenv("QUANT_CONTROL_MOMENTUM_GITHUB_REPO", "momentum-factor-lab")
    assert Settings.from_env().momentum_github_repo == "momentum-factor-lab"


@pytest.mark.parametrize("repository", ["factor", "momentum-factor-lab"])
def test_current_and_historical_immutable_paths_reach_only_exact_allowlisted_url(repository: str) -> None:
    url = artifact_url(repository)
    record = SimpleNamespace(run_id=RUN_ID, result_manifest=None)
    MomentumAdapter().validate_artifact_url(record, artifact(url))
    requests: list[str] = []

    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(str(request.url))
            return httpx.Response(200, content=b"{}")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert await HttpArtifactFetcher(client=client).fetch(artifact(url)) == b"{}"

    asyncio.run(scenario())
    assert requests == [url]


@pytest.mark.parametrize(
    "url",
    [
        artifact_url("factor-copy"),
        artifact_url("Factor"),
        artifact_url("factor.evil"),
        artifact_url("nested/factor"),
        artifact_url("%66actor"),
        artifact_url("factor").replace("sonchanggi.github.io", "attacker.example"),
        artifact_url("factor").replace("https://", "https://attacker@"),
        artifact_url("factor").replace(".io/", ".io:8443/"),
        artifact_url("factor") + "?latest=1",
        artifact_url("factor") + "#result",
        artifact_url("factor").replace(RESULT_KEY, "b" * 63),
        artifact_url("factor").replace(RUN_ID, "invalid"),
    ],
)
def test_factor_lookalikes_and_mutable_urls_fail_before_any_network(url: str) -> None:
    record = SimpleNamespace(run_id=RUN_ID, result_manifest=None)
    with pytest.raises(ValueError, match="immutable"):
        MomentumAdapter().validate_artifact_url(record, artifact(url))
    requests: list[str] = []

    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(str(request.url))
            return httpx.Response(200, content=b"{}")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(ArtifactVerificationError):
                await HttpArtifactFetcher(client=client).fetch(artifact(url))

    asyncio.run(scenario())
    assert not requests


@pytest.mark.parametrize("repository", ["factor", "momentum-factor-lab"])
def test_repository_rename_does_not_relax_run_or_result_binding(repository: str) -> None:
    url = artifact_url(repository)
    adapter = MomentumAdapter()
    with pytest.raises(ValueError, match="different control run"):
        adapter.validate_artifact_url(SimpleNamespace(run_id="other-run-001", result_manifest=None), artifact(url))
    record = SimpleNamespace(run_id=RUN_ID, result_manifest=SimpleNamespace(payload={"resultKey": "b" * 64}))
    with pytest.raises(ValueError, match="result key"):
        adapter.validate_artifact_url(record, artifact(url))


@pytest.mark.parametrize(
    ("code_version", "accepted"),
    [
        (f"github:SonChangGi/factor@{'c' * 40}", True),
        (f"github:SonChangGi/momentum-factor-lab@{'c' * 40}", True),
        (f"github:OtherOwner/factor@{'c' * 40}", False),
        (f"github:SonChangGi/factor-copy@{'c' * 40}", False),
        (f"github:SonChangGi/best-factor@{'c' * 40}", False),
        (f"github:SonChangGi/factor@{'c' * 39}", False),
        (f"github:SonChangGi/factor@{'C' * 40}", False),
        ("github:SonChangGi/factor@main", False),
    ],
)
def test_new_additive_sql_and_api_allow_the_same_exact_repository_identities(code_version: str, accepted: bool) -> None:
    path = Path(__file__).resolve().parents[3] / "infra/supabase/migrations/202610200001_allow_factor_repository.sql"
    migration = path.read_text()
    sql_pattern = next(pattern for pattern in re.findall(r"code_version ~ '([^']+)'", migration) if "(factor|" in pattern)
    assert bool(CODE_VERSION_PATTERN.fullmatch(code_version)) is accepted
    assert bool(re.fullmatch(sql_pattern, code_version)) is accepted
    assert "project_id = 'momentum'" in migration
    assert "project_id = 'best-factor'" in migration
    assert "project_id = 'fear-greed'" in migration
    assert "drop constraint analysis_runs_code_version_format" in migration
    assert not re.search(r"\b(update|delete|insert)\s", migration, re.IGNORECASE)


@pytest.mark.parametrize("status", [301, 302, 307, 308, 404, 410])
def test_historical_immutable_url_uses_only_exact_current_alias(status: int) -> None:
    old = artifact_url("momentum-factor-lab")
    current = artifact_url("factor")
    requests: list[str] = []

    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(str(request.url))
            if str(request.url) == old:
                return httpx.Response(status, headers={"Location": current})
            return httpx.Response(200, content=b"{}")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            original = artifact(old)
            assert await HttpArtifactFetcher(client=client).fetch(original) == b"{}"
            assert str(original.url) == old

    asyncio.run(scenario())
    assert requests == [old, current]


@pytest.mark.parametrize("status,location", [(302, "https://attacker.example/result"), (302, artifact_url("factor-copy")), (500, "")])
def test_historical_url_never_follows_arbitrary_redirect_or_masks_server_failure(status: int, location: str) -> None:
    requests: list[str] = []

    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(str(request.url))
            return httpx.Response(status, headers={"Location": location})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(ArtifactVerificationError):
                await HttpArtifactFetcher(client=client).fetch(artifact(artifact_url("momentum-factor-lab")))

    asyncio.run(scenario())
    assert requests == [artifact_url("momentum-factor-lab")]
