from __future__ import annotations

import pytest
from pydantic import ValidationError

from quant_control_api.best_factor import (
    CONFIG_HASH_ALGORITHM,
    DEFAULT_CONFIG,
    INPUT_SCHEMA_VERSION,
    canonical_sha256,
    normalize_inputs,
)


def test_golden_config_hash_matches_published_contract(golden_contract: dict[str, object]) -> None:
    assert golden_contract["inputSchemaVersion"] == INPUT_SCHEMA_VERSION
    assert golden_contract["configHashAlgorithm"] == CONFIG_HASH_ALGORITHM
    assert canonical_sha256(golden_contract["inputs"]) == golden_contract["configHash"]
    normalized = normalize_inputs(golden_contract["inputs"])  # type: ignore[arg-type]
    assert normalized.config_hash == "082b5dbbe2c6cdf08d669733f9eacbc1518b0c88693d091f27574c8bc2f50750"
    assert normalized.requested == golden_contract["inputs"]
    assert normalized.normalized == golden_contract["inputs"]
    assert normalized.effective == golden_contract["inputs"]


def test_full_input_coerces_types_without_inheriting_server_defaults(
    golden_contract: dict[str, object],
) -> None:
    raw = {
        **golden_contract["inputs"],  # type: ignore[dict-item]
        "top_n": "30",
        "factor_allowlist": "momentum_6m, low_volatility",
    }
    normalized = normalize_inputs(raw)
    assert normalized.requested["top_n"] == 30
    assert normalized.requested["factor_allowlist"] == ["momentum_6m", "low_volatility"]
    assert normalized.normalized == normalized.effective
    assert normalized.effective["period"] == DEFAULT_CONFIG["period"]


def test_partial_input_is_rejected_even_when_defaults_exist() -> None:
    with pytest.raises(ValueError, match="missing:"):
        normalize_inputs({"top_n": 30})


@pytest.mark.parametrize(
    ("key", "value", "fragment"),
    [
        ("period", "1y", "Input should be"),
        ("top_n", 0, "greater than or equal to 1"),
        ("top_n", 2.5, "integer"),
        ("top_n", True, "boolean"),
        ("transaction_cost_bps", float("inf"), "finite"),
        ("factor_allowlist", "bad-name!", "invalid factor name syntax"),
    ],
)
def test_invalid_inputs_fail_closed(
    golden_contract: dict[str, object],
    key: str,
    value: object,
    fragment: str,
) -> None:
    inputs = {**golden_contract["inputs"], key: value}  # type: ignore[dict-item]
    with pytest.raises((ValidationError, TypeError, ValueError), match=fragment):
        normalize_inputs(inputs)


def test_unknown_input_is_rejected(golden_contract: dict[str, object]) -> None:
    inputs = {**golden_contract["inputs"], "unknown": 1}  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="unknown:"):
        normalize_inputs(inputs)


def test_factor_names_are_shape_checked_but_worker_remains_catalog_authority(
    golden_contract: dict[str, object],
) -> None:
    inputs = {
        **golden_contract["inputs"],  # type: ignore[dict-item]
        "factor_allowlist": ["future_factor_42", "future_factor_42"],
    }
    result = normalize_inputs(inputs)
    assert result.effective["factor_allowlist"] == ["future_factor_42"]
