from __future__ import annotations

import re
from typing import Protocol
from urllib.parse import urlparse

import httpx

from .models import ArtifactIdentity

MAX_ARTIFACT_BYTES = 15 * 1024 * 1024
BEST_FACTOR_IMMUTABLE_PATH = re.compile(r"^/SonChangGi/best-factor/[0-9a-f]{40}/docs/data/latest-results\.json$")
MOMENTUM_IMMUTABLE_PATH = re.compile(
    r"^/momentum-factor-lab/data/control-runs/v1/"
    r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}/[0-9a-f]{64}\.json$"
)


class ArtifactVerificationError(ValueError):
    pass


class ArtifactFetcher(Protocol):
    async def fetch(self, artifact: ArtifactIdentity) -> bytes: ...


class HttpArtifactFetcher:
    """Fetch exact published bytes from an allowlisted public artifact URL."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        max_bytes: int = MAX_ARTIFACT_BYTES,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(20.0),
            follow_redirects=False,
            headers={"User-Agent": "quant-control-api-artifact-verifier/0.1"},
        )
        self.max_bytes = max_bytes

    async def fetch(self, artifact: ArtifactIdentity) -> bytes:
        url = str(artifact.url)
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ArtifactVerificationError("artifact URL must use HTTPS")
        if parsed.username is not None or parsed.password is not None:
            raise ArtifactVerificationError("artifact URL must not contain user information")
        if parsed.port not in (None, 443):
            raise ArtifactVerificationError("artifact URL must use the standard HTTPS port")
        if parsed.query or parsed.fragment:
            raise ArtifactVerificationError("artifact URL must not contain a query or fragment")
        allowlisted = (
            parsed.hostname == "raw.githubusercontent.com"
            and BEST_FACTOR_IMMUTABLE_PATH.fullmatch(parsed.path)
        ) or (
            parsed.hostname == "sonchanggi.github.io"
            and MOMENTUM_IMMUTABLE_PATH.fullmatch(parsed.path)
        )
        if not allowlisted:
            raise ArtifactVerificationError("artifact host/path is not allowlisted")
        if artifact.byte_size > self.max_bytes:
            raise ArtifactVerificationError("artifact byteSize exceeds the verification limit")

        async with self._client.stream("GET", url) as response:
            if response.status_code != 200:
                raise ArtifactVerificationError(f"artifact fetch failed with status {response.status_code}")
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError as exc:
                    raise ArtifactVerificationError("artifact Content-Length is malformed") from exc
                if declared_length < 0 or declared_length > self.max_bytes:
                    raise ArtifactVerificationError("artifact Content-Length exceeds the verification limit")
            chunks: list[bytes] = []
            received = 0
            async for chunk in response.aiter_bytes():
                received += len(chunk)
                if received > self.max_bytes:
                    raise ArtifactVerificationError("artifact response exceeds the verification limit")
                chunks.append(chunk)
        return b"".join(chunks)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


class MappingArtifactFetcher:
    """Exact-byte verifier fixture for tests."""

    def __init__(self, artifacts: dict[str, bytes] | None = None) -> None:
        self.artifacts = artifacts or {}

    async def fetch(self, artifact: ArtifactIdentity) -> bytes:
        try:
            return self.artifacts[str(artifact.url)]
        except KeyError as exc:
            raise ArtifactVerificationError("test artifact URL is not registered") from exc

    async def close(self) -> None:
        return None
