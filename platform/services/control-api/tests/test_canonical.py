import math

import pytest

from quant_control_api.canonical import canonical_json_bytes, canonical_sha256


def test_strict_record_hash_is_deterministic_and_preserves_python_json_contract():
    assert canonical_json_bytes({"b": 2, "a": "한글"}) == b'{"a":"\\ud55c\\uae00","b":2}'
    assert canonical_sha256({"b": 2, "a": 1}) == canonical_sha256({"a": 1, "b": 2})
    assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 1.0})


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, {"nested": math.nan}])
def test_control_record_serialization_rejects_nonfinite_values(value):
    with pytest.raises(ValueError):
        canonical_json_bytes(value)
