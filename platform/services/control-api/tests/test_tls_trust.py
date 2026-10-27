"""Inspect real HTTPX transports without sending credentials or network requests."""

import asyncio
import ssl
from pathlib import Path

import certifi
import httpx
import pytest
from packaging.version import Version

from quant_control_api.artifacts import HttpArtifactFetcher
from quant_control_api.dual_write import SupabaseDualWritePublisher
from quant_control_api.providers.github_actions import GitHubActionsWorkerProvider
from quant_control_api.supabase_store import SupabaseRunStore


@pytest.fixture(autouse=True)
def isolated_tls_environment(monkeypatch):
    for name in ("SSL_CERT_FILE", "SSL_CERT_DIR", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)


def service_client(kind):
    if kind == "github":
        return GitHubActionsWorkerProvider(
            enabled=True, token="test-only", owner="test", repo="test", workflow="test.yml", ref="test"
        ).client
    if kind == "supabase":
        return SupabaseRunStore(url="https://example.invalid", service_role_key="test-only")._client
    if kind == "mirror":
        return SupabaseDualWritePublisher(url="https://example.invalid", service_role_key="test-only")._client
    return HttpArtifactFetcher()._client


@pytest.mark.parametrize("kind", ["github", "supabase", "mirror", "artifact"])
def test_service_clients_verify_hosts_with_patched_certifi(kind):
    client = service_client(kind)
    try:
        # Deliberately inspect the real httpx 0.28/httpcore transport, not a mock.
        context = client._transport._pool._ssl_context
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        expected = ssl.create_default_context(cafile=certifi.where())
        assert set(context.get_ca_certs(binary_form=True)) == set(expected.get_ca_certs(binary_form=True))
        assert Version(certifi.__version__) >= Version("2026.10.19")
        names = {
            value for cert in context.get_ca_certs()
            for rdn in cert["subject"] for key, value in rdn if key == "commonName"
        }
        assert "emSign ECC Root CA - G3" not in names
        assert "AAA Certificate Services" not in names
    finally:
        asyncio.run(client.aclose())


def test_httpx_honors_explicit_ca_file(monkeypatch, tmp_path):
    # One public root makes an override distinguishable from the complete bundle.
    root = Path(certifi.where()).read_text().split("-----END CERTIFICATE-----", 1)[0]
    bundle = tmp_path / "single-public-root.pem"
    bundle.write_text(root + "-----END CERTIFICATE-----\n")
    monkeypatch.setenv("SSL_CERT_FILE", str(bundle))
    with httpx.Client() as client:
        context = client._transport._pool._ssl_context
        assert len(context.get_ca_certs()) == 1
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname


def test_httpx_honors_explicit_ca_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("SSL_CERT_DIR", str(tmp_path))
    with httpx.Client() as client:
        context = client._transport._pool._ssl_context
        # An empty override directory must not silently add the certifi bundle.
        assert context.get_ca_certs() == []
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
