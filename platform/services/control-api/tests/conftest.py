from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def golden_contract() -> dict[str, object]:
    path = Path(__file__).resolve().parents[3] / "fixtures" / "contracts" / "best-factor-v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def submission(golden_contract: dict[str, object]) -> dict[str, object]:
    return {
        "inputSchemaVersion": golden_contract["inputSchemaVersion"],
        "inputs": golden_contract["inputs"],
        "allowFallback": False,
    }


@pytest.fixture
def idempotency_headers() -> dict[str, str]:
    return {"Idempotency-Key": "test-request-0001"}
