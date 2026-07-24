FROM python:3.11.15-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN python -m pip install --no-cache-dir uv==0.11.17

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --locked --no-dev --no-editable --no-cache

FROM python:3.11.15-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system quant-control \
    && useradd --system --gid quant-control --home-dir /app quant-control

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

USER quant-control

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).read()"]

CMD ["uvicorn", "quant_control_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
