FROM python:3.11.18-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Refresh the builder's system trust store before downloading dependencies.
RUN apt-get -o APT::Update::Error-Mode=any update \
    && apt-get install --yes --no-install-recommends ca-certificates \
    && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' ca-certificates)" ge '20250419~deb12u2' \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Hash-pinned bootstrap also replaces pip's separate, vendored CA bundle.
RUN python -m pip install --no-cache-dir --no-deps \
    "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70" \
    && python -m pip install --no-cache-dir uv==0.13.4

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv --version \
    && test "$(uv --version | cut -d ' ' -f 2)" = '0.13.4' \
    && uv sync --locked --no-dev --no-editable --no-cache

FROM python:3.11.18-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get -o APT::Update::Error-Mode=any update \
    && apt-get install --yes --no-install-recommends ca-certificates \
    && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' ca-certificates)" ge '20250419~deb12u2' \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system quant-control \
    && useradd --system --gid quant-control --home-dir /app quant-control

WORKDIR /app

# The base image's pip has its own CA bundle even though the API does not use it.
RUN python -m pip install --no-cache-dir --no-deps \
    "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"

COPY --from=builder /app/.venv /app/.venv

USER quant-control

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).read()"]

CMD ["uvicorn", "quant_control_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
