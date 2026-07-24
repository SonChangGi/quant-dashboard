from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import InputFieldCapability

PROJECT_ID = "best-factor"
PROJECT_NAME = "Best Factor Lab"
INPUT_SCHEMA_VERSION = "best-factor/v1"
STATIC_FALLBACK_URL = "https://sonchanggi.github.io/best-factor/data/latest-results.json"
RESULT_CONTRACT_VERSION = "best-factor/latest-results/v1"
CONFIG_HASH_ALGORITHM = "best-factor-python-json-v1"


class _ConfigBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: Literal["2y", "5y", "10y"]
    rebalance: Literal["M", "W"]
    top_n: int = Field(ge=1, le=100)
    weighting: Literal["equal", "score"]
    factor_preset: Literal["core", "zoo"]
    factor_allowlist: list[str]
    min_market_cap: float = Field(ge=0, le=1e15)
    min_dollar_volume: float = Field(ge=0, le=1e15)
    eligibility_adv_window: int = Field(ge=5, le=252)
    transaction_cost_bps: float = Field(ge=0, le=1000)
    transaction_cost_model: Literal["one_way_notional", "portfolio_turnover"]

    @field_validator("top_n", "eligibility_adv_window", mode="before")
    @classmethod
    def reject_boolean_integer(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise TypeError("boolean is not an integer input")
        if isinstance(value, float) and not value.is_integer():
            raise ValueError("value must be an integer")
        if isinstance(value, str) and not re.fullmatch(r"[+-]?\d+", value.strip()):
            raise ValueError("value must be an integer")
        return value

    @field_validator("min_market_cap", "min_dollar_volume", "transaction_cost_bps", mode="before")
    @classmethod
    def reject_nonfinite_number(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise TypeError("boolean is not a numeric input")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("value must be a finite number") from exc
        if not math.isfinite(number):
            raise ValueError("value must be a finite number")
        return number

    @field_validator("factor_allowlist", mode="before")
    @classmethod
    def parse_factor_allowlist(cls, value: Any) -> list[str]:
        if value in (None, "", "__preset__"):
            return []
        if isinstance(value, str):
            values = [part for part in re.split(r"[,\s]+", value.strip()) if part]
        elif isinstance(value, list):
            values = []
            for item in value:
                if not isinstance(item, str):
                    raise TypeError("factor_allowlist entries must be strings")
                values.extend(part for part in re.split(r"[,\s]+", item.strip()) if part)
        else:
            raise TypeError("factor_allowlist must be a list or comma/space-separated string")
        unique = list(dict.fromkeys(values))
        invalid_syntax = [name for name in unique if not re.fullmatch(r"[A-Za-z0-9_]+", name)]
        if invalid_syntax:
            raise ValueError(f"invalid factor name syntax: {', '.join(invalid_syntax)}")
        if len(unique) > 1000:
            raise ValueError("factor_allowlist cannot contain more than 1000 names")
        return unique


class BestFactorConfig(_ConfigBase):
    period: Literal["2y", "5y", "10y"] = "5y"
    rebalance: Literal["M", "W"] = "M"
    top_n: int = Field(default=20, ge=1, le=100)
    weighting: Literal["equal", "score"] = "score"
    factor_preset: Literal["core", "zoo"] = "zoo"
    factor_allowlist: list[str] = Field(default_factory=list)
    min_market_cap: float = Field(default=10_000_000_000.0, ge=0, le=1e15)
    min_dollar_volume: float = Field(default=50_000_000.0, ge=0, le=1e15)
    eligibility_adv_window: int = Field(default=63, ge=5, le=252)
    transaction_cost_bps: float = Field(default=5.0, ge=0, le=1000)
    transaction_cost_model: Literal["one_way_notional", "portfolio_turnover"] = "one_way_notional"


DEFAULT_CONFIG = BestFactorConfig().model_dump(mode="json")


@dataclass(frozen=True)
class NormalizedConfig:
    requested: dict[str, Any]
    normalized: dict[str, Any]
    effective: dict[str, Any]
    config_hash: str


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def normalize_inputs(inputs: dict[str, Any]) -> NormalizedConfig:
    expected = set(DEFAULT_CONFIG)
    received = set(inputs)
    if received != expected:
        missing = sorted(expected - received)
        unknown = sorted(received - expected)
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown: {', '.join(unknown)}")
        raise ValueError(f"inputs must match the 11-field Best Factor contract ({'; '.join(details)})")
    normalized = BestFactorConfig.model_validate(inputs).model_dump(mode="json")
    requested = dict(normalized)
    effective = dict(normalized)
    return NormalizedConfig(
        requested=requested,
        normalized=normalized,
        effective=effective,
        config_hash=canonical_sha256(effective),
    )


INPUT_FIELDS = [
    InputFieldCapability(
        key="period",
        label="분석 기간",
        type="enum",
        default="5y",
        choices=["2y", "5y", "10y"],
        cli_argument="--period",
        workflow_input="period",
    ),
    InputFieldCapability(
        key="rebalance",
        label="리밸런싱",
        type="enum",
        default="M",
        choices=["M", "W"],
        cli_argument="--rebalance",
        workflow_input="rebalance",
    ),
    InputFieldCapability(
        key="top_n",
        label="분석 편입 상한",
        type="integer",
        default=20,
        minimum=1,
        maximum=100,
        unit="stocks",
        cli_argument="--top-n",
        workflow_input="top_n",
    ),
    InputFieldCapability(
        key="weighting",
        label="가중 방식",
        type="enum",
        default="score",
        choices=["equal", "score"],
        cli_argument="--weighting",
        workflow_input="weighting",
    ),
    InputFieldCapability(
        key="factor_preset",
        label="팩터 범위",
        type="enum",
        default="zoo",
        choices=["core", "zoo"],
        cli_argument="--factor-preset",
        workflow_input="factor_preset",
    ),
    InputFieldCapability(
        key="factor_allowlist",
        label="직접 선택 팩터",
        type="string-list",
        default=[],
        cli_argument="--factors",
        workflow_input="factor_allowlist",
    ),
    InputFieldCapability(
        key="min_market_cap",
        label="최소 시가총액",
        type="number",
        default=10_000_000_000.0,
        minimum=0,
        maximum=1e15,
        unit="USD",
        cli_argument="--min-market-cap",
        workflow_input="min_market_cap",
    ),
    InputFieldCapability(
        key="min_dollar_volume",
        label="최소 일평균 거래대금",
        type="number",
        default=50_000_000.0,
        minimum=0,
        maximum=1e15,
        unit="USD",
        cli_argument="--min-dollar-volume",
        workflow_input="min_dollar_volume",
    ),
    InputFieldCapability(
        key="eligibility_adv_window",
        label="ADV 관찰일",
        type="integer",
        default=63,
        minimum=5,
        maximum=252,
        unit="sessions",
        cli_argument="--eligibility-adv-window",
        workflow_input="eligibility_adv_window",
    ),
    InputFieldCapability(
        key="transaction_cost_bps",
        label="거래비용",
        type="number",
        default=5.0,
        minimum=0,
        maximum=1000,
        unit="bps",
        cli_argument="--transaction-cost-bps",
        workflow_input="transaction_cost_bps",
    ),
    InputFieldCapability(
        key="transaction_cost_model",
        label="비용 계산 방식",
        type="enum",
        default="one_way_notional",
        choices=["one_way_notional", "portfolio_turnover"],
        cli_argument="--transaction-cost-model",
        workflow_input="transaction_cost_model",
    ),
]

INPUT_SCHEMA_HASH = canonical_sha256(
    {
        "inputSchemaVersion": INPUT_SCHEMA_VERSION,
        "factorCatalogAuthority": "best_factor.factors.validate_factor_names at worker codeVersion",
        "fields": [field.model_dump(mode="json", by_alias=True) for field in INPUT_FIELDS],
    }
)
