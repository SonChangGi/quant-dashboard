"""Run inside the built image without production environment variables or secrets."""

import asyncio
import json
import os
import ssl
import subprocess
import sys

import certifi
import httpx

from quant_control_api.providers.github_actions import GitHubActionsWorkerProvider
from quant_control_api.supabase_store import SupabaseRunStore

REJECT_URLS = (
    "https://dv-g3b-emudhra.we-have-a-problem.com/",
    "https://dv-g3b-aaa-emudhra.we-have-a-problem.com/",
)
RETIRED_ROOTS = {"emSign ECC Root CA - G3", "AAA Certificate Services"}


def verify_image_versions():
    assert sys.version_info[:3] == (3, 11, 18), sys.version
    assert certifi.__version__ == "2026.10.23"
    assert httpx.__version__ == "0.28.1"
    assert os.getuid() != 0, "runtime must remain non-root"
    ca_version = subprocess.check_output(
        ["dpkg-query", "-W", "-f=${Version}", "ca-certificates"], text=True
    ).strip()
    subprocess.run(
        ["dpkg", "--compare-versions", ca_version, "ge", "20250419~deb12u2"], check=True
    )
    # The runtime venv has no pip; inspect the base image's separate installation.
    pip_info = json.loads(subprocess.check_output([
        "/usr/local/bin/python", "-c",
        ("import json,pip; from pip._vendor import certifi; "
         "print(json.dumps({'version':pip.__version__,'ca_file':certifi.where()}))"),
    ], text=True))
    assert pip_info["version"] == "26.2.2"
    print(json.dumps({
        "python": sys.version.split()[0], "openssl": ssl.OPENSSL_VERSION,
        "pip": pip_info["version"], "certifi": certifi.__version__,
        "httpx": httpx.__version__, "debian_ca_certificates": ca_version,
        "non_root": True,
    }), flush=True)
    return pip_info["ca_file"]


def verify_context(context):
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname
    names = {
        value for cert in context.get_ca_certs()
        for rdn in cert["subject"] for key, value in rdn if key == "commonName"
    }
    assert not names & RETIRED_ROOTS, names & RETIRED_ROOTS


async def probe(name, client):
    async with client:
        verify_context(client._transport._pool._ssl_context)
        for url in ("https://pypi.org/", *REJECT_URLS):
            # send(Request) does not merge client default authentication headers.
            request = httpx.Request("GET", url, extensions={
                "timeout": {"connect": 15, "read": 15, "write": 15, "pool": 15}
            })
            assert set(request.headers) == {"host"}
            try:
                response = await client.send(request, follow_redirects=False)
            except httpx.ConnectError as exc:
                if url not in REJECT_URLS or "CERTIFICATE_VERIFY_FAILED" not in str(exc):
                    raise
                print(json.dumps({"client": name, "url": url, "result": "CERTIFICATE_VERIFY_FAILED"}), flush=True)
            else:
                await response.aclose()
                assert url not in REJECT_URLS, f"{name}: compromised certificate accepted"
                assert response.status_code == 200, response.status_code
                print(json.dumps({"client": name, "url": url, "status": 200}), flush=True)


async def main():
    # CI runs a clean image. Do not silently ignore an unexpected trust override.
    assert not any(os.environ.get(name) for name in (
        "SSL_CERT_FILE", "SSL_CERT_DIR", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
        "http_proxy", "https_proxy", "all_proxy",
    )), "run this image check without custom trust/proxy environment variables"
    pip_ca_file = verify_image_versions()
    await probe("github-service-client", GitHubActionsWorkerProvider(
        enabled=True, token="test-only", owner="test", repo="test", workflow="test.yml", ref="test"
    ).client)
    await probe("supabase-service-client", SupabaseRunStore(
        url="https://example.invalid", service_role_key="test-only"
    )._client)
    await probe("system-ca", httpx.AsyncClient(verify=ssl.create_default_context()))
    await probe("pip-vendored-ca", httpx.AsyncClient(verify=ssl.create_default_context(cafile=pip_ca_file)))


if __name__ == "__main__":
    asyncio.run(main())
