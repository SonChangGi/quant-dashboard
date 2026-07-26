#!/usr/bin/env python3
"""Validate a schema-v2 completion receipt against project-owned evidence.

The validator checks contract shape, identity binding, local/captured bytes, cost
envelopes, and time ordering. It does not manufacture user billing authority and
does not contact providers. Provider responses and public readbacks must be
captured by the owning workflow and supplied as evidence files.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from validate_project import validate as validate_project_contract


V2_BASE_GATES = {"contract", "tests", "product", "cost"}
V2_AUTOMATION_GATES = {
    "collection",
    "freshness",
    "analysis_result",
    "schedule",
    "publication",
    "public_readback",
}
V2_RELEASE_GATES = {"release", "public_readback"}
V2_COST_POLICY = "zero-spend-unless-user-first-requests-specific-paid-action"
V2_COST_CLASSES = {
    "no_billable_action",
    "verified_zero_charge",
    "explicit_user_paid_command",
    "unknown_or_unapproved",
}
LOCAL_CANONICALIZATION = "canonical-json-v1"
HEX = frozenset("0123456789abcdef")


def reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number is prohibited: {value}")


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def parse_time(value: Any) -> datetime | None:
    if not nonempty(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


def parse_date_or_time(value: Any) -> datetime | None:
    parsed = parse_time(value)
    if parsed is not None:
        return parsed
    if not nonempty(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def utc_naive(value: datetime) -> datetime:
    if value.utcoffset() is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def lag_seconds(observed: Any, expected: Any) -> int | None:
    observed_time = parse_date_or_time(observed)
    expected_time = parse_date_or_time(expected)
    if observed_time is None or expected_time is None:
        return None
    delta = utc_naive(expected_time) - utc_naive(observed_time)
    return max(0, int(delta.total_seconds()))


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in HEX for character in value.lower())
    )


def is_full_git_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(character in HEX for character in value.lower())
    )


def finite_number(value: Any, *, minimum: float = 0) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) >= minimum
    )


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_pointer(value: Any, pointer: str) -> tuple[bool, Any]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return False, None
    current = value
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit():
            index = int(token)
            if index >= len(current):
                return False, None
            current = current[index]
        else:
            return False, None
    return True, current


def url_without_query(value: Any) -> str:
    if not nonempty(value):
        return ""
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def url_host(value: Any) -> str:
    if not nonempty(value):
        return ""
    parts = urlsplit(value)
    return parts.netloc.lower() if parts.scheme in {"http", "https"} else ""


def load_object(
    value: str | None,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    if not value:
        return None
    path = Path(value).expanduser().resolve()
    try:
        loaded = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_nonfinite_json,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"invalid {label}: {exc}")
        return None
    if not isinstance(loaded, dict):
        errors.append(f"{label} must contain an object")
        return None
    return loaded


def evidence_for(gates: dict[str, Any], gate_name: str) -> list[dict[str, Any]]:
    gate = gates.get(gate_name)
    evidence = gate.get("evidence") if isinstance(gate, dict) else None
    if not isinstance(evidence, list):
        return []
    return [item for item in evidence if isinstance(item, dict)]


def matching_kind(
    gates: dict[str, Any],
    gate_name: str,
    kind: str,
) -> list[dict[str, Any]]:
    return [
        item
        for item in evidence_for(gates, gate_name)
        if item.get("kind") == kind
    ]


def validate_generic_evidence(
    gate_name: str,
    evidence: Any,
    completed: datetime | None,
    errors: list[str],
) -> None:
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"passed gate {gate_name!r} needs structured evidence")
        return
    for index, item in enumerate(evidence):
        prefix = f"gate {gate_name!r} evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("kind", "summary", "source", "checked_at"):
            if not nonempty(item.get(field)):
                errors.append(f"{prefix}.{field} is required")
        checked = parse_time(item.get("checked_at"))
        if checked is None:
            errors.append(f"{prefix}.checked_at must be timezone-aware ISO-8601")
        elif completed is not None and checked > completed:
            errors.append(f"{prefix}.checked_at occurs after completed_at")


def expected_remote_scope_ids(
    manifest: dict[str, Any] | None,
    scope: dict[str, Any],
) -> set[str]:
    expected: set[str] = set()
    if manifest is None:
        return expected
    if scope.get("automated_data_to_web") is True:
        data = manifest.get("data")
        sources = data.get("sources") if isinstance(data, dict) else []
        if isinstance(sources, list):
            for source in sources:
                if isinstance(source, dict) and nonempty(source.get("id")):
                    expected.add(f"source:{source['id']}")
        automation = manifest.get("automation")
        if isinstance(automation, dict):
            workflows = automation.get("workflows")
            if isinstance(workflows, list):
                expected.update(
                    f"automation:{workflow}"
                    for workflow in workflows
                    if nonempty(workflow)
                )
            urls = automation.get("public_readback_urls")
            if isinstance(urls, list):
                expected.update(
                    f"publish:{url_host(url)}" for url in urls if url_host(url)
                )
        project = manifest.get("project")
        if isinstance(project, dict) and url_host(project.get("public_url")):
            expected.add(f"frontend:{url_host(project['public_url'])}")
    if scope.get("remote_release") is True:
        expected.add("release:github")
        release = manifest.get("release")
        project = manifest.get("project")
        production = (
            release.get("production")
            if isinstance(release, dict)
            else project.get("public_url")
            if isinstance(project, dict)
            else ""
        )
        if url_host(production):
            expected.add(f"deploy:{url_host(production)}")
            expected.add(f"readback:{url_host(production)}")
        automation = manifest.get("automation")
        urls = (
            automation.get("public_readback_urls")
            if isinstance(automation, dict)
            else []
        )
        if isinstance(urls, list):
            expected.update(
                f"readback:{url_host(url)}" for url in urls if url_host(url)
            )
    return expected


def expected_remote_scope_providers(
    manifest: dict[str, Any] | None,
    scope: dict[str, Any],
) -> dict[str, str]:
    expected: dict[str, str] = {}
    if manifest is None:
        return expected
    if scope.get("automated_data_to_web") is True:
        data = manifest.get("data")
        sources = data.get("sources") if isinstance(data, dict) else []
        if isinstance(sources, list):
            for source in sources:
                if (
                    isinstance(source, dict)
                    and nonempty(source.get("id"))
                    and nonempty(source.get("provider"))
                ):
                    expected[f"source:{source['id']}"] = source["provider"]
        automation = manifest.get("automation")
        if isinstance(automation, dict):
            workflows = automation.get("workflows")
            if isinstance(workflows, list):
                for workflow in workflows:
                    if nonempty(workflow):
                        expected[f"automation:{workflow}"] = "github"
            urls = automation.get("public_readback_urls")
            if isinstance(urls, list):
                for url in urls:
                    if url_host(url):
                        expected[f"publish:{url_host(url)}"] = url_host(url)
        project = manifest.get("project")
        if isinstance(project, dict) and url_host(project.get("public_url")):
            host = url_host(project["public_url"])
            expected[f"frontend:{host}"] = host
    if scope.get("remote_release") is True:
        expected["release:github"] = "github"
        release = manifest.get("release")
        project = manifest.get("project")
        production = (
            release.get("production")
            if isinstance(release, dict)
            else project.get("public_url")
            if isinstance(project, dict)
            else ""
        )
        if url_host(production):
            host = url_host(production)
            expected[f"deploy:{host}"] = host
            expected[f"readback:{host}"] = host
        automation = manifest.get("automation")
        urls = (
            automation.get("public_readback_urls")
            if isinstance(automation, dict)
            else []
        )
        if isinstance(urls, list):
            for url in urls:
                if url_host(url):
                    expected[f"readback:{url_host(url)}"] = url_host(url)
    return expected


def validate_zero_cost_action(
    action: dict[str, Any],
    completed: datetime | None,
    errors: list[str],
    prefix: str,
) -> set[str]:
    for field in (
        "action_id",
        "provider",
        "account_or_project",
        "resource_or_sku",
        "normalized_redacted_action",
    ):
        if not nonempty(action.get(field)):
            errors.append(f"{prefix}.{field} is required")
    if action.get("remote_or_provider_action") is not True:
        errors.append(f"{prefix}.remote_or_provider_action must be true")
    if action.get("classification") != "verified_zero_charge":
        errors.append(f"{prefix}.classification must be verified_zero_charge")
    if action.get("decision") != "allow":
        errors.append(f"{prefix}.decision must be allow")

    scopes = action.get("scope_ids")
    if (
        not isinstance(scopes, list)
        or not scopes
        or not all(nonempty(item) for item in scopes)
        or len(scopes) != len(set(scopes))
    ):
        errors.append(f"{prefix}.scope_ids must be unique non-empty strings")
        scope_set: set[str] = set()
    else:
        scope_set = set(scopes)
        if len(scopes) != 1:
            errors.append(
                f"{prefix}.scope_ids must contain exactly one remote action scope"
            )

    action_without_hash = dict(action)
    claimed_action_sha = action_without_hash.pop(
        "canonical_action_envelope_sha256",
        None,
    )
    if not is_sha256(claimed_action_sha):
        errors.append(f"{prefix}.canonical_action_envelope_sha256 must be SHA-256")
    else:
        try:
            calculated_action_sha = canonical_sha256(action_without_hash)
        except (TypeError, ValueError):
            errors.append(f"{prefix} contains non-canonical JSON values")
        else:
            if claimed_action_sha != calculated_action_sha:
                errors.append(f"{prefix}.canonical_action_envelope_sha256 mismatch")

    pricing = action.get("pricing_and_quota")
    if not isinstance(pricing, dict):
        errors.append(f"{prefix}.pricing_and_quota must be an object")
        pricing = {}
    pricing_string_fields = (
        "official_or_account_visible_evidence",
        "checked_at",
        "billing_mode",
        "cap_unit",
    )
    pricing_number_fields = (
        "hard_free_cap",
        "remaining_free_quota",
        "planned_usage_per_run",
    )
    pricing_false_flags = (
        "trial_or_credit_required",
        "auto_renewing_trial_active",
        "payment_method_change_required",
        "payment_method_registration_required",
        "automatic_upgrade_possible",
        "plan_upgrade_required",
        "overage_possible",
        "pay_as_you_go_enabled",
        "free_quota_exceedance_allowed",
        "paid_add_on_active",
        "spend_cap_disabled",
    )
    allowed_pricing_fields = {
        *pricing_string_fields,
        *pricing_number_fields,
        *pricing_false_flags,
    }
    unexpected_pricing_fields = sorted(set(pricing) - allowed_pricing_fields)
    if unexpected_pricing_fields:
        errors.append(
            f"{prefix}.pricing_and_quota has unexpected fields: "
            + ", ".join(unexpected_pricing_fields)
        )
    for field in pricing_string_fields:
        if not nonempty(pricing.get(field)):
            errors.append(f"{prefix}.pricing_and_quota.{field} is required")
    if pricing.get("billing_mode") != "hard-free-no-overage":
        errors.append(
            f"{prefix}.pricing_and_quota.billing_mode must be hard-free-no-overage"
        )
    checked = parse_time(pricing.get("checked_at"))
    if checked is None:
        errors.append(f"{prefix}.pricing_and_quota.checked_at is invalid")
    elif completed is not None:
        if checked > completed:
            errors.append(f"{prefix} pricing evidence occurs after completion")
        if completed - checked > timedelta(hours=24):
            errors.append(f"{prefix} pricing/quota evidence is older than 24 hours")
    cap = pricing.get("hard_free_cap")
    remaining = pricing.get("remaining_free_quota")
    per_run = pricing.get("planned_usage_per_run")
    for field, value in (
        ("hard_free_cap", cap),
        ("remaining_free_quota", remaining),
        ("planned_usage_per_run", per_run),
    ):
        if not finite_number(value):
            errors.append(
                f"{prefix}.pricing_and_quota.{field} must be finite and nonnegative"
            )
    if finite_number(per_run) and float(per_run) <= 0:
        errors.append(f"{prefix}.planned_usage_per_run must be greater than zero")
    if finite_number(cap) and finite_number(remaining) and float(remaining) > float(cap):
        errors.append(f"{prefix} remaining quota cannot exceed hard free cap")
    for flag in pricing_false_flags:
        if pricing.get(flag) is not False:
            errors.append(f"{prefix}.pricing_and_quota.{flag} must be false")

    ceilings = action.get("numeric_ceilings")
    if not isinstance(ceilings, dict):
        errors.append(f"{prefix}.numeric_ceilings must be an object")
        ceilings = {}
    numeric_fields = (
        "maximum_cost_per_run",
        "maximum_total_cost",
        "maximum_runs",
        "maximum_provider_calls_per_run",
        "maximum_retry_attempts",
        "maximum_concurrency",
        "maximum_compute_seconds_per_run",
        "maximum_storage_bytes",
        "maximum_egress_bytes_per_run",
        "maximum_retention_days",
    )
    for field in numeric_fields:
        if not finite_number(ceilings.get(field)):
            errors.append(f"{prefix}.numeric_ceilings.{field} must be finite")
    if ceilings.get("maximum_cost_per_run") != 0:
        errors.append(f"{prefix}.maximum_cost_per_run must equal zero")
    if ceilings.get("maximum_total_cost") != 0:
        errors.append(f"{prefix}.maximum_total_cost must equal zero")
    integer_bounds = {
        "maximum_runs": (1, 100000),
        "maximum_provider_calls_per_run": (1, 100000),
        "maximum_retry_attempts": (0, 10),
        "maximum_concurrency": (1, 10),
        "maximum_compute_seconds_per_run": (1, 86400),
        "maximum_storage_bytes": (0, 10**15),
        "maximum_egress_bytes_per_run": (0, 10**15),
        "maximum_retention_days": (0, 3650),
    }
    for field, (minimum, maximum) in integer_bounds.items():
        value = ceilings.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < minimum
            or value > maximum
        ):
            errors.append(
                f"{prefix}.numeric_ceilings.{field} must be integer "
                f"{minimum}..{maximum}"
            )
    if (
        finite_number(per_run)
        and finite_number(remaining)
        and isinstance(ceilings.get("maximum_runs"), int)
        and float(per_run) * ceilings["maximum_runs"] > float(remaining)
    ):
        errors.append(f"{prefix} planned recurring usage exceeds remaining free quota")

    schedule = action.get("schedule")
    if not isinstance(schedule, dict):
        errors.append(f"{prefix}.schedule must be an object")
        schedule = {}
    recurring = schedule.get("recurring")
    if not isinstance(recurring, bool):
        errors.append(f"{prefix}.schedule.recurring must be boolean")
    elif recurring:
        if not nonempty(schedule.get("cadence")):
            errors.append(f"{prefix}.schedule.cadence is required when recurring")
        end_at = parse_time(schedule.get("end_at"))
        if end_at is None:
            errors.append(f"{prefix}.schedule.end_at must be timezone-aware")
        elif completed is not None and end_at <= completed:
            errors.append(f"{prefix}.schedule.end_at must be after completion")
    elif schedule.get("cadence") not in {"", None} or schedule.get("end_at") not in {
        "",
        None,
    }:
        errors.append(f"{prefix} non-recurring schedule must not set cadence/end_at")
    if recurring is False and ceilings.get("maximum_runs") != 1:
        errors.append(f"{prefix} non-recurring action maximum_runs must equal 1")

    hard_stop = action.get("hard_stop")
    if not isinstance(hard_stop, dict):
        errors.append(f"{prefix}.hard_stop must be an object")
        hard_stop = {}
    hard_stop_true_flags = (
        "enabled",
        "check_quota_before_each_run",
        "block_when_price_or_quota_unknown",
        "block_when_free_quota_exhausted",
        "block_when_projected_cost_exceeds_ceiling",
        "block_when_trial_or_credit_required",
        "block_when_auto_renewing_trial_active",
        "block_when_payment_method_registration_required",
        "block_when_plan_upgrade_required",
        "block_when_overage_possible",
        "block_when_pay_as_you_go_enabled",
        "block_when_free_quota_exceedance_possible",
        "block_when_paid_add_on_active",
        "require_spend_cap_enabled",
    )
    hard_stop_false_flags = (
        "paid_fallback_enabled",
        "automatic_upgrade_enabled",
        "plan_upgrade_enabled",
        "paid_add_on_enabled",
        "spend_cap_disablement_enabled",
    )
    allowed_hard_stop_fields = {
        *hard_stop_true_flags,
        *hard_stop_false_flags,
    }
    unexpected_hard_stop_fields = sorted(
        set(hard_stop) - allowed_hard_stop_fields
    )
    if unexpected_hard_stop_fields:
        errors.append(
            f"{prefix}.hard_stop has unexpected fields: "
            + ", ".join(unexpected_hard_stop_fields)
        )
    for flag in hard_stop_true_flags:
        if hard_stop.get(flag) is not True:
            errors.append(f"{prefix}.hard_stop.{flag} must be true")
    for flag in hard_stop_false_flags:
        if hard_stop.get(flag) is not False:
            errors.append(f"{prefix}.hard_stop.{flag} must be false")
    return scope_set


def validate_cost_capture(
    path_value: str | None,
    cost: dict[str, Any],
    receipt: dict[str, Any],
    completed: datetime | None,
    errors: list[str],
) -> None:
    if not path_value:
        errors.append("verified_zero_charge requires --cost-evidence")
        return
    path = Path(path_value).expanduser().resolve()
    try:
        raw = path.read_bytes()
        capture = json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_nonfinite_json,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"invalid cost evidence capture: {exc}")
        return
    capture_sha = hashlib.sha256(raw).hexdigest()
    if cost.get("cost_evidence_sha256") != capture_sha:
        errors.append("cost evidence capture SHA-256 mismatch")
    if not isinstance(capture, dict) or capture.get("schema_version") != 1:
        errors.append("cost evidence capture must be a schema-v1 object")
        return
    if capture.get("capture_origin") not in {
        "official-account-api",
        "official-account-console",
        "official-pricing-document",
    }:
        errors.append("cost evidence capture origin is not trusted for review")
    for field in ("capture_tool", "source_reference", "captured_at"):
        if not nonempty(capture.get(field)):
            errors.append(f"cost evidence capture {field} is required")
    captured = parse_time(capture.get("captured_at"))
    if captured is None:
        errors.append("cost evidence captured_at is invalid")
    elif completed is not None:
        if captured > completed:
            errors.append("cost evidence capture occurs after completion")
        elif completed - captured > timedelta(hours=24):
            errors.append("cost evidence capture is older than 24 hours")

    scope = receipt.get("scope")
    automation = receipt.get("automation_identity")
    release = receipt.get("release_identity")
    expected_workflow_run = (
        automation.get("run_id")
        if isinstance(scope, dict)
        and scope.get("automated_data_to_web") is True
        and isinstance(automation, dict)
        else None
    )
    expected_release_run = (
        release.get("ci_run_id")
        if isinstance(scope, dict)
        and scope.get("remote_release") is True
        and isinstance(release, dict)
        else None
    )
    if capture.get("workflow_run_id") != expected_workflow_run:
        errors.append("cost capture workflow_run_id mismatch")
    if capture.get("release_ci_run_id") != expected_release_run:
        errors.append("cost capture release_ci_run_id mismatch")
    expected_automation_preflight = (
        automation.get("cost_preflight_completed_at")
        if expected_workflow_run is not None
        else None
    )
    expected_release_preflight = (
        release.get("cost_preflight_completed_at")
        if expected_release_run is not None
        else None
    )
    if capture.get(
        "automation_cost_preflight_completed_at"
    ) != expected_automation_preflight:
        errors.append("cost capture automation preflight time mismatch")
    if capture.get(
        "release_cost_preflight_completed_at"
    ) != expected_release_preflight:
        errors.append("cost capture release preflight time mismatch")
    for label, value in (
        ("automation", expected_automation_preflight),
        ("release", expected_release_preflight),
    ):
        preflight_time = parse_time(value) if value is not None else None
        if value is not None and preflight_time is None:
            errors.append(f"{label} cost preflight time is invalid")
        elif captured is not None and preflight_time is not None:
            if captured > preflight_time:
                errors.append(
                    f"cost evidence was captured after {label} preflight"
                )
            elif preflight_time - captured > timedelta(hours=24):
                errors.append(
                    f"cost evidence is older than 24 hours at {label} preflight"
                )

    actions = cost.get("actions")
    captured_actions = capture.get("actions")
    if not isinstance(actions, list) or not isinstance(captured_actions, list):
        errors.append("cost evidence capture actions must be an array")
        return
    captured_by_id = {
        item.get("action_id"): item
        for item in captured_actions
        if isinstance(item, dict) and nonempty(item.get("action_id"))
    }
    if len(captured_by_id) != len(captured_actions):
        errors.append("cost evidence capture action IDs must be unique")
    for action in actions:
        if not isinstance(action, dict):
            continue
        captured_action = captured_by_id.get(action.get("action_id"))
        if not isinstance(captured_action, dict):
            errors.append(
                f"cost capture missing action {action.get('action_id')!r}"
            )
            continue
        expected = {
            "provider": action.get("provider"),
            "account_or_project": action.get("account_or_project"),
            "resource_or_sku": action.get("resource_or_sku"),
            "pricing_and_quota": action.get("pricing_and_quota"),
        }
        for field, expected_value in expected.items():
            if captured_action.get(field) != expected_value:
                errors.append(
                    f"cost capture action {action.get('action_id')!r} "
                    f"{field} mismatch"
                )
        pricing = captured_action.get("pricing_and_quota")
        if (
            isinstance(pricing, dict)
            and pricing.get("checked_at") != capture.get("captured_at")
        ):
            errors.append(
                f"cost capture action {action.get('action_id')!r} "
                "pricing timestamp does not match capture"
            )
    if len(captured_actions) != len(actions):
        errors.append("cost capture action count mismatch")


def validate_cost(
    receipt: dict[str, Any],
    gates: dict[str, Any],
    manifest: dict[str, Any] | None,
    goal: dict[str, Any] | None,
    completed: datetime | None,
    cost_evidence_path: str | None,
    errors: list[str],
) -> None:
    scope = receipt.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
        return
    for field in ("automated_data_to_web", "remote_release", "paid_action"):
        if not isinstance(scope.get(field), bool):
            errors.append(f"scope.{field} must be boolean")

    cost = receipt.get("cost_authority")
    if not isinstance(cost, dict):
        errors.append("cost_authority must be an object")
        return
    if cost.get("policy") != V2_COST_POLICY:
        errors.append("cost_authority.policy is invalid")
    classification = cost.get("classification")
    decision = cost.get("decision")
    if classification not in V2_COST_CLASSES:
        errors.append("cost_authority.classification is invalid")
    if decision not in {"allow", "block"}:
        errors.append("cost_authority.decision must be allow or block")
    if not isinstance(cost.get("paid_action_requested"), bool):
        errors.append("cost_authority.paid_action_requested must be boolean")

    if goal is not None:
        goal_cost = goal.get("cost_authority")
        if not isinstance(goal_cost, dict):
            errors.append("goal state cost_authority must be an object")
        else:
            if goal_cost.get("policy") != cost.get("policy"):
                errors.append("goal and receipt cost policies do not match")
            if goal_cost.get("paid_action_requested") != cost.get(
                "paid_action_requested"
            ):
                errors.append("goal and receipt paid_action_requested do not match")

    remote_scope = bool(
        scope.get("automated_data_to_web") or scope.get("remote_release")
    )
    if classification == "explicit_user_paid_command" or scope.get("paid_action"):
        errors.append(
            "paid completion is blocked: no trusted runtime authority envelope "
            "is available to this local validator"
        )
    if remote_scope and classification == "no_billable_action":
        errors.append(
            "remote/provider scope cannot use no_billable_action; "
            "verified_zero_charge is required"
        )
    if classification == "unknown_or_unapproved" or decision != "allow":
        errors.append("cost gate remains blocked or unapproved")

    actions = cost.get("actions")
    if not isinstance(actions, list):
        errors.append("cost_authority.actions must be an array")
        actions = []
    envelope = cost.get("canonical_actions_envelope")
    if not isinstance(envelope, dict):
        errors.append("cost_authority.canonical_actions_envelope must be an object")
        envelope = {}
    if envelope.get("canonicalization") != LOCAL_CANONICALIZATION:
        errors.append("cost envelope canonicalization must be canonical-json-v1")
    if envelope.get("action_count") != len(actions):
        errors.append("cost envelope action_count mismatch")
    try:
        envelope_sha = canonical_sha256(actions)
    except (TypeError, ValueError):
        errors.append("cost actions contain non-canonical JSON values")
        envelope_sha = ""
    if envelope.get("sha256") != envelope_sha:
        errors.append("cost_authority canonical actions SHA-256 mismatch")
    if envelope.get("authoritative_for_cost_gate") is not True:
        errors.append("cost envelope must be authoritative for cost gate")

    covered_scopes: set[str] = set()
    action_ids: list[str] = []
    if classification == "no_billable_action":
        if remote_scope or actions:
            errors.append("no_billable_action requires no remote scope and no actions")
        if cost.get("paid_action_requested") is not False:
            errors.append("no_billable_action requires paid_action_requested=false")
        if cost.get("authority_origin") != "none":
            errors.append("no_billable_action requires authority_origin=none")
    elif classification == "verified_zero_charge":
        if not remote_scope:
            errors.append("verified_zero_charge requires a remote/provider scope")
        if not actions:
            errors.append("verified_zero_charge requires actions")
        if cost.get("paid_action_requested") is not False:
            errors.append("verified_zero_charge requires paid_action_requested=false")
        if cost.get("authority_origin") != "none":
            errors.append("verified_zero_charge requires authority_origin=none")
        expected_providers = expected_remote_scope_providers(manifest, scope)
        for index, action in enumerate(actions):
            if not isinstance(action, dict):
                errors.append(f"cost_authority.actions[{index}] must be an object")
                continue
            action_id = action.get("action_id")
            if nonempty(action_id):
                action_ids.append(action_id)
            action_scopes = validate_zero_cost_action(
                action,
                completed,
                errors,
                f"cost_authority.actions[{index}]",
            )
            covered_scopes.update(action_scopes)
            for scope_id in action_scopes:
                expected_provider = expected_providers.get(scope_id)
                if expected_provider and action.get("provider") != expected_provider:
                    errors.append(
                        f"cost action provider {action.get('provider')!r} "
                        f"does not match {scope_id} provider "
                        f"{expected_provider!r}"
                    )
        if len(action_ids) != len(set(action_ids)):
            errors.append("cost action IDs must be unique")
        expected_scopes = expected_remote_scope_ids(manifest, scope)
        missing_scopes = sorted(expected_scopes - covered_scopes)
        unknown_scopes = sorted(covered_scopes - expected_scopes)
        if missing_scopes:
            errors.append(
                "cost actions do not cover remote scopes: "
                + ", ".join(missing_scopes)
            )
        if unknown_scopes:
            errors.append(
                "cost actions contain scopes outside the manifest: "
                + ", ".join(unknown_scopes)
            )
        validate_cost_capture(
            cost_evidence_path,
            cost,
            receipt,
            completed,
            errors,
        )

    cost_evidence = matching_kind(gates, "cost", "cost_preflight")
    if not any(
        item.get("classification") == classification
        and item.get("decision") == decision
        and item.get("canonical_actions_envelope_sha256") == envelope_sha
        and item.get("cost_evidence_sha256")
        == cost.get("cost_evidence_sha256")
        and item.get("all_remote_or_provider_actions_enumerated") is True
        and item.get("all_numeric_ceilings_validated") is True
        and item.get("all_hard_stops_enabled") is True
        and item.get("trusted_runtime_paid_authority_verified") is False
        for item in cost_evidence
    ):
        errors.append("cost gate lacks a matching complete cost_preflight record")


def validate_context(
    receipt: dict[str, Any],
    manifest: dict[str, Any] | None,
    goal: dict[str, Any] | None,
    *,
    force_automation: bool,
    force_release: bool,
    errors: list[str],
) -> None:
    if manifest is None:
        errors.append("schema v2 completion requires --manifest")
    else:
        project = manifest.get("project")
        project_id = project.get("id") if isinstance(project, dict) else None
        if project_id != receipt.get("project_id"):
            errors.append("receipt project_id does not match manifest")
    if goal is None:
        errors.append("schema v2 completion requires --goal-state")
        return
    for field in ("project_id", "objective", "scope"):
        if goal.get(field) != receipt.get(field):
            errors.append(f"receipt {field} does not match goal state")
    scope = receipt.get("scope")
    outcomes = goal.get("required_outcomes")
    if not isinstance(outcomes, dict):
        errors.append("goal state required_outcomes must be an object")
    elif not all(
        isinstance(outcomes.get(field), bool)
        for field in ("automated_data_to_web", "remote_release")
    ):
        errors.append("goal required_outcomes values must be boolean")
    elif isinstance(scope, dict):
        if outcomes.get("automated_data_to_web") is True and not scope.get(
            "automated_data_to_web"
        ):
            errors.append("goal requires automated_data_to_web but receipt downgraded it")
        if outcomes.get("remote_release") is True and not scope.get(
            "remote_release"
        ):
            errors.append("goal requires remote_release but receipt downgraded it")
    if force_automation and (
        not isinstance(scope, dict) or not scope.get("automated_data_to_web")
    ):
        errors.append("--require-automation requires automation scope")
    if force_release and (
        not isinstance(scope, dict) or not scope.get("remote_release")
    ):
        errors.append("--require-release requires remote release scope")
    approval = goal.get("approval_gates")
    if not isinstance(approval, dict):
        errors.append("goal state approval_gates must be an object")
    elif isinstance(scope, dict) and scope.get("remote_release") is True:
        if approval.get("release") not in {"approved", "completed"}:
            errors.append("remote release requires an approved release gate")
    automation_state = goal.get("automation_state")
    if not isinstance(automation_state, dict) or not isinstance(
        automation_state.get("in_scope") if isinstance(automation_state, dict) else None,
        bool,
    ):
        errors.append("goal automation_state.in_scope must be boolean")
    elif isinstance(scope, dict):
        if bool(automation_state.get("in_scope")) != bool(
            scope.get("automated_data_to_web")
        ):
            errors.append("goal automation_state.in_scope does not match receipt")
        if scope.get("automated_data_to_web") is True:
            if automation_state.get("scope_status") != "in-scope":
                errors.append(
                    "automated goal automation_state.scope_status must be in-scope"
                )
            last_good = automation_state.get("last_good_result_identity")
            automation_identity = receipt.get("automation_identity")
            if not isinstance(last_good, dict):
                errors.append(
                    "automated goal requires last_good_result_identity"
                )
            elif isinstance(automation_identity, dict):
                expected_last_good = {
                    "generation": automation_identity.get(
                        "previous_generation"
                    ),
                    "result_artifact_sha256": automation_identity.get(
                        "previous_public_result_sha256"
                    ),
                    "data_as_of": automation_identity.get(
                        "previous_data_as_of"
                    ),
                    "published_result_key": automation_identity.get(
                        "previous_published_result_key"
                    ),
                }
                if last_good != expected_last_good:
                    errors.append(
                        "goal last_good_result_identity does not match "
                        "automation baseline"
                    )
        else:
            if automation_state.get("scope_status") != (
                "explicitly-out-of-scope"
            ):
                errors.append(
                    "non-automation goal must explicitly mark automation "
                    "out of scope"
                )
            if not nonempty(automation_state.get("scope_exclusion_reason")):
                errors.append(
                    "non-automation goal requires a scope exclusion reason"
                )


def validate_capture(
    value: str | None,
    label: str,
    expected_sha: Any,
    expected_size: Any,
    errors: list[str],
    *,
    within: Path | None = None,
) -> None:
    if not value:
        errors.append(f"{label} evidence file is required")
        return
    path = Path(value).expanduser().resolve()
    if within is not None:
        try:
            path.relative_to(within)
        except ValueError:
            errors.append(f"{label} must stay within project root")
    if not path.is_file():
        errors.append(f"{label} evidence file does not exist")
        return
    if file_sha256(path) != expected_sha:
        errors.append(f"{label} SHA-256 does not match receipt")
    if expected_size is not None and path.stat().st_size != expected_size:
        errors.append(f"{label} size does not match receipt")


def load_json_capture(
    value: str | None,
    label: str,
    errors: list[str],
    *,
    within: Path | None = None,
) -> tuple[Path | None, dict[str, Any] | None]:
    if not value:
        return None, None
    path = Path(value).expanduser().resolve()
    if within is not None:
        try:
            path.relative_to(within)
        except ValueError:
            errors.append(f"{label} must stay within project root")
            return path, None
    try:
        loaded = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_nonfinite_json,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
        return path, None
    if not isinstance(loaded, dict):
        errors.append(f"{label} must contain an object")
        return path, None
    return path, loaded


def relative_project_path(
    value: Any,
    root: Path,
    label: str,
    errors: list[str],
) -> Path | None:
    if not nonempty(value):
        errors.append(f"{label} is required")
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        errors.append(f"{label} escapes project root")
        return None
    return candidate


def validate_provider_run(
    value: str | None,
    identity: dict[str, Any],
    completed: datetime | None,
    errors: list[str],
) -> None:
    if not value:
        errors.append("workflow run evidence file is required")
        return
    path = Path(value).expanduser().resolve()
    try:
        run = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid workflow run evidence: {exc}")
        return
    if not isinstance(run, dict):
        errors.append("workflow run evidence must contain an object")
        return
    if file_sha256(path) != identity.get("workflow_run_evidence_sha256"):
        errors.append("workflow run evidence SHA-256 mismatch")
    expected = {
        "run_id": identity.get("run_id"),
        "run_url": identity.get("run_url"),
        "event": "schedule",
        "default_branch": identity.get("default_branch"),
        "head_sha": identity.get("head_sha"),
        "conclusion": "success",
        "steps_completed": identity.get("steps_completed"),
        "workflow_file_sha256": identity.get("workflow_file_sha256"),
        "started_at": identity.get("workflow_started_at"),
    }
    for field, expected_value in expected.items():
        if run.get(field) != expected_value:
            errors.append(f"workflow run evidence {field} mismatch")
    if not isinstance(run.get("steps_completed"), int) or run["steps_completed"] < 1:
        errors.append("workflow run evidence steps_completed must be >= 1")
    jobs = run.get("jobs")
    listed_successful_steps = sum(
        1
        for job in jobs
        if isinstance(job, dict) and isinstance(job.get("steps"), list)
        for step in job["steps"]
        if isinstance(step, dict) and step.get("conclusion") == "success"
    ) if isinstance(jobs, list) else 0
    if run.get("steps_completed") != listed_successful_steps:
        errors.append(
            "workflow steps_completed does not match listed successful steps"
        )
    matching_jobs = [
        job
        for job in jobs
        if isinstance(job, dict) and job.get("job_id") == identity.get("job_id")
    ] if isinstance(jobs, list) else []
    if len(matching_jobs) != 1 or matching_jobs[0].get("conclusion") != "success":
        errors.append("workflow run evidence lacks the successful required job")
    else:
        steps = matching_jobs[0].get("steps")
        step_map = {
            step.get("step_id"): step
            for step in steps
            if isinstance(step, dict)
        } if isinstance(steps, list) else {}
        for field in ("cost_preflight_step_id", "entrypoint_step_id"):
            step = step_map.get(identity.get(field))
            if (
                not isinstance(step, dict)
                or step.get("outcome") != "success"
                or step.get("conclusion") != "success"
            ):
                errors.append(
                    f"workflow run required step {identity.get(field)!r} "
                    "did not have successful outcome and conclusion"
                )
        step_by_id = {
            step.get("step_id"): step
            for step in steps
            if isinstance(step, dict) and nonempty(step.get("step_id"))
        } if isinstance(steps, list) else {}
        cost_step = step_by_id.get(identity.get("cost_preflight_step_id"))
        entrypoint_step = step_by_id.get(identity.get("entrypoint_step_id"))
        if isinstance(cost_step, dict) and cost_step.get(
            "completed_at"
        ) != identity.get("cost_preflight_completed_at"):
            errors.append("workflow cost preflight completion time mismatch")
        if isinstance(entrypoint_step, dict) and entrypoint_step.get(
            "started_at"
        ) != identity.get("entrypoint_started_at"):
            errors.append("workflow entrypoint start time mismatch")
        cost_finished = parse_time(
            cost_step.get("completed_at")
            if isinstance(cost_step, dict)
            else None
        )
        entry_started = parse_time(
            entrypoint_step.get("started_at")
            if isinstance(entrypoint_step, dict)
            else None
        )
        if cost_finished is None:
            errors.append("workflow cost preflight completed_at is invalid")
        if entry_started is None:
            errors.append("workflow entrypoint started_at is invalid")
        if (
            cost_finished is not None
            and entry_started is not None
            and cost_finished > entry_started
        ):
            errors.append("workflow entrypoint started before cost preflight ended")
    finished = parse_time(run.get("completed_at"))
    if finished is None:
        errors.append("workflow run evidence completed_at is invalid")
    elif completed is not None and finished > completed:
        errors.append("workflow run completed after receipt completion")
    elif finished != parse_time(identity.get("schedule_last_success_at")):
        errors.append("workflow completion time does not match schedule success")


def validate_automation(
    receipt: dict[str, Any],
    gates: dict[str, Any],
    manifest: dict[str, Any] | None,
    completed: datetime | None,
    args: argparse.Namespace,
    errors: list[str],
) -> None:
    identity = receipt.get("automation_identity")
    if not isinstance(identity, dict):
        errors.append("automation_identity is required")
        return
    strings = (
        "source_manifest_sha256",
        "run_id",
        "run_url",
        "workflow_run_evidence_sha256",
        "workflow_file_sha256",
        "workflow_started_at",
        "cost_preflight_completed_at",
        "entrypoint_started_at",
        "default_branch",
        "head_sha",
        "job_id",
        "cost_preflight_step_id",
        "entrypoint_step_id",
        "data_as_of",
        "analysis_code_version",
        "analysis_entrypoint_sha256",
        "analysis_input_sha256",
        "analysis_input_validation_sha256",
        "analysis_request_manifest_sha256",
        "result_manifest_sha256",
        "config_hash",
        "effective_config_hash",
        "input_schema_version",
        "input_schema_sha256",
        "data_schema_version",
        "result_schema_version",
        "result_artifact_sha256",
        "published_result_key",
        "publication_state",
        "schedule_id",
        "workflow",
        "schedule_last_success_at",
        "deployment_id",
        "public_url",
        "public_response_sha256",
        "frontend_url",
        "frontend_response_sha256",
        "frontend_binding_evidence_sha256",
        "frontend_dom_snapshot_sha256",
        "public_pointer_before_sha256",
        "public_pointer_after_sha256",
        "publication_ordering_evidence_sha256",
        "publication_ordering_test_output_sha256",
        "previous_public_result_sha256",
        "previous_data_as_of",
        "previous_published_result_key",
        "public_verified_at",
    )
    for field in strings:
        if not nonempty(identity.get(field)):
            errors.append(f"automation_identity.{field} is required")
    for field in (
        "source_manifest_sha256",
        "workflow_run_evidence_sha256",
        "workflow_file_sha256",
        "analysis_input_sha256",
        "analysis_input_validation_sha256",
        "analysis_entrypoint_sha256",
        "analysis_request_manifest_sha256",
        "result_manifest_sha256",
        "config_hash",
        "effective_config_hash",
        "input_schema_sha256",
        "result_artifact_sha256",
        "public_response_sha256",
        "frontend_response_sha256",
        "frontend_binding_evidence_sha256",
        "frontend_dom_snapshot_sha256",
        "public_pointer_before_sha256",
        "public_pointer_after_sha256",
        "publication_ordering_evidence_sha256",
        "publication_ordering_test_output_sha256",
        "previous_public_result_sha256",
    ):
        if identity.get(field) and not is_sha256(identity[field]):
            errors.append(f"automation_identity.{field} must be SHA-256")
    if identity.get("head_sha") and not is_full_git_sha(identity["head_sha"]):
        errors.append("automation_identity.head_sha must be a full commit SHA")
    if not is_full_git_sha(identity.get("analysis_code_version")):
        errors.append(
            "automation_identity.analysis_code_version must be a full commit SHA"
        )
    elif identity.get("analysis_code_version") != identity.get("head_sha"):
        errors.append(
            "automation analysis_code_version must equal workflow head_sha"
        )
    if identity.get("publication_state") not in {"ready", "degraded"}:
        errors.append("automation_identity.publication_state is invalid")
    if parse_date_or_time(identity.get("data_as_of")) is None:
        errors.append("automation_identity.data_as_of is invalid")
    schedule_time = parse_time(identity.get("schedule_last_success_at"))
    public_time = parse_time(identity.get("public_verified_at"))
    workflow_started = parse_time(identity.get("workflow_started_at"))
    cost_preflight_completed = parse_time(
        identity.get("cost_preflight_completed_at")
    )
    entrypoint_started = parse_time(identity.get("entrypoint_started_at"))
    if schedule_time is None:
        errors.append("automation_identity.schedule_last_success_at is invalid")
    if public_time is None:
        errors.append("automation_identity.public_verified_at is invalid")
    for field, value in (
        ("workflow_started_at", workflow_started),
        ("cost_preflight_completed_at", cost_preflight_completed),
        ("entrypoint_started_at", entrypoint_started),
    ):
        if value is None:
            errors.append(f"automation_identity.{field} is invalid")
    ordered_times = (
        workflow_started,
        cost_preflight_completed,
        entrypoint_started,
        schedule_time,
    )
    if all(value is not None for value in ordered_times) and list(
        ordered_times
    ) != sorted(ordered_times):
        errors.append(
            "workflow start, cost preflight, entrypoint, and completion "
            "times are out of order"
        )
    if schedule_time and public_time and schedule_time > public_time:
        errors.append("schedule success must precede public verification")
    if public_time and completed and public_time > completed:
        errors.append("public verification occurs after receipt completion")
    data_time = parse_date_or_time(identity.get("data_as_of"))
    if data_time and public_time:
        comparable_public = public_time.replace(tzinfo=None)
        comparable_data = data_time.replace(tzinfo=None)
        if comparable_data > comparable_public:
            errors.append("data_as_of occurs after public verification")

    for field in (
        "required_source_count",
        "failed_required_source_count",
        "steps_completed",
        "source_manifest_size",
        "analysis_input_size",
        "analysis_input_validation_size",
        "analysis_request_manifest_size",
        "result_manifest_size",
        "result_artifact_size",
        "public_response_size",
        "frontend_response_size",
        "frontend_binding_evidence_size",
        "frontend_dom_snapshot_size",
        "public_pointer_before_size",
        "public_pointer_after_size",
        "publication_ordering_evidence_size",
        "publication_ordering_test_output_size",
        "previous_generation",
        "candidate_generation",
    ):
        value = identity.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            errors.append(f"automation_identity.{field} must be nonnegative integer")
    if identity.get("required_source_count", 0) < 1:
        errors.append("automation_identity.required_source_count must be >= 1")
    if identity.get("failed_required_source_count") != 0:
        errors.append("automation_identity.failed_required_source_count must be 0")
    if identity.get("steps_completed", 0) < 1:
        errors.append("automation_identity.steps_completed must be >= 1")
    previous_generation = identity.get("previous_generation")
    candidate_generation = identity.get("candidate_generation")
    if (
        isinstance(previous_generation, int)
        and not isinstance(previous_generation, bool)
        and isinstance(candidate_generation, int)
        and not isinstance(candidate_generation, bool)
        and candidate_generation <= previous_generation
    ):
        errors.append(
            "automation candidate generation must exceed previous generation"
        )
    for field in (
        "source_manifest_size",
        "analysis_input_size",
        "analysis_input_validation_size",
        "analysis_request_manifest_size",
        "result_manifest_size",
        "result_artifact_size",
        "public_response_size",
        "frontend_response_size",
        "frontend_binding_evidence_size",
        "frontend_dom_snapshot_size",
        "public_pointer_before_size",
        "public_pointer_after_size",
        "publication_ordering_evidence_size",
        "publication_ordering_test_output_size",
    ):
        if identity.get(field, 0) < 1:
            errors.append(f"automation_identity.{field} must be >= 1")
    if identity.get("public_http_status") != 200:
        errors.append("automation_identity.public_http_status must be 200")
    if identity.get("frontend_http_status") != 200:
        errors.append("automation_identity.frontend_http_status must be 200")
    if identity.get("public_response_sha256") != identity.get(
        "result_artifact_sha256"
    ):
        errors.append("public result bytes must match authoritative artifact")
    if identity.get("public_response_size") != identity.get("result_artifact_size"):
        errors.append("public result size must match authoritative artifact")

    required_source_ids = identity.get("required_source_ids")
    if (
        not isinstance(required_source_ids, list)
        or not required_source_ids
        or not all(nonempty(item) for item in required_source_ids)
        or len(required_source_ids) != len(set(required_source_ids))
    ):
        errors.append("required_source_ids must be unique non-empty strings")
        required_source_ids = []
    if len(required_source_ids) != identity.get("required_source_count"):
        errors.append("required_source_count does not match required_source_ids")

    matching_schedule: dict[str, Any] | None = None
    manifest_source_roles: dict[str, str] = {}
    manifest_sources_by_id: dict[str, dict[str, Any]] = {}
    coherent_cutoff_policy = ""
    if manifest is not None:
        data = manifest.get("data")
        sources = data.get("sources") if isinstance(data, dict) else []
        coherent_cutoff_policy = (
            data.get("coherent_cutoff_policy")
            if isinstance(data, dict)
            else ""
        )
        manifest_source_roles = {
            source["id"]: source.get("role", "")
            for source in sources
            if isinstance(source, dict) and nonempty(source.get("id"))
        }
        manifest_sources_by_id = {
            source["id"]: source
            for source in sources
            if isinstance(source, dict) and nonempty(source.get("id"))
        }
        required_manifest_ids = sorted(
            source.get("id")
            for source in sources
            if isinstance(source, dict)
            and source.get("role") == "required"
            and nonempty(source.get("id"))
        )
        if sorted(required_source_ids) != required_manifest_ids:
            errors.append("automation source IDs do not match manifest")
        automation = manifest.get("automation")
        if not isinstance(automation, dict) or automation.get("mode") != "scheduled":
            errors.append("automation completion requires manifest mode=scheduled")
        else:
            schedules = automation.get("schedules")
            candidates = [
                item
                for item in schedules
                if isinstance(item, dict)
                and item.get("id") == identity.get("schedule_id")
            ] if isinstance(schedules, list) else []
            if len(candidates) != 1:
                errors.append("schedule_id does not resolve uniquely in manifest")
            else:
                matching_schedule = candidates[0]
                if matching_schedule.get("workflow") != identity.get("workflow"):
                    errors.append("workflow does not match manifest schedule")
                if matching_schedule.get("enabled_on_default_branch") is not True:
                    errors.append("manifest schedule is not enabled on default branch")
                for field in (
                    "job_id",
                    "cost_preflight_step_id",
                    "entrypoint_step_id",
                ):
                    if matching_schedule.get(field) != identity.get(field):
                        errors.append(
                            f"automation {field} does not match manifest schedule"
                        )
                if args.project_root_path is not None:
                    workflow_path = (
                        args.project_root_path / identity.get("workflow", "")
                    ).resolve()
                    if not workflow_path.is_file():
                        errors.append("automation workflow file does not exist")
                    elif file_sha256(workflow_path) != identity.get(
                        "workflow_file_sha256"
                    ):
                        errors.append("automation workflow file SHA-256 mismatch")
                    entrypoint_path = (
                        args.project_root_path
                        / str(matching_schedule.get("entrypoint", ""))
                    ).resolve()
                    try:
                        entrypoint_path.relative_to(args.project_root_path)
                    except ValueError:
                        errors.append(
                            "automation analysis entrypoint escapes project root"
                        )
                    else:
                        if not entrypoint_path.is_file():
                            errors.append(
                                "automation analysis entrypoint does not exist"
                            )
                        elif file_sha256(entrypoint_path) != identity.get(
                            "analysis_entrypoint_sha256"
                        ):
                            errors.append(
                                "automation analysis entrypoint SHA-256 mismatch"
                            )
            urls = automation.get("public_readback_urls")
            urls = urls if isinstance(urls, list) else []
            if url_without_query(identity.get("public_url")) not in {
                url_without_query(url) for url in urls
            }:
                errors.append("public_url is not a manifest readback target")
        project = manifest.get("project")
        expected_frontend = (
            project.get("public_url") if isinstance(project, dict) else ""
        )
        if url_without_query(identity.get("frontend_url")) != url_without_query(
            expected_frontend
        ):
            errors.append("frontend_url does not match manifest public_url")
        result_identity_fields = (
            manifest.get("analysis", {}).get("result_identity_fields", [])
            if isinstance(manifest.get("analysis"), dict)
            else []
        )
        receipt_identity = receipt.get("result_identity")
        if not isinstance(receipt_identity, dict):
            errors.append("result_identity must be an object for automation")
            receipt_identity = {}
        expected_identity = {
            "project_id": receipt.get("project_id"),
            "run_id": identity.get("run_id"),
            "data_as_of": identity.get("data_as_of"),
            "code_version": identity.get("analysis_code_version"),
            "data_manifest_sha256": identity.get("source_manifest_sha256"),
            "artifact_sha256": identity.get("result_artifact_sha256"),
            "analysis_input_sha256": identity.get("analysis_input_sha256"),
            "analysis_input_validation_sha256": identity.get(
                "analysis_input_validation_sha256"
            ),
            "config_hash": identity.get("config_hash"),
            "effective_config_hash": identity.get("effective_config_hash"),
            "input_schema_version": identity.get("input_schema_version"),
            "data_schema_version": identity.get("data_schema_version"),
            "result_schema_version": identity.get("result_schema_version"),
        }
        for field in result_identity_fields:
            expected_value = expected_identity.get(field)
            if expected_value is None:
                if not nonempty(receipt_identity.get(field)):
                    errors.append(
                        f"manifest result identity field {field!r} is unbound"
                    )
            elif receipt_identity.get(field) != expected_value:
                errors.append(
                    f"result_identity.{field} does not match automation identity"
                )

    expected = {
        "collection": (
            "source_collection",
            {
                "source_manifest_sha256": identity.get("source_manifest_sha256"),
                "source_manifest_size": identity.get("source_manifest_size"),
                "required_source_ids": required_source_ids,
                "required_source_count": identity.get("required_source_count"),
                "failed_required_source_count": 0,
            },
        ),
        "freshness": (
            "coherent_cutoff",
            {
                "data_as_of": identity.get("data_as_of"),
                "coherent_cutoff_policy": coherent_cutoff_policy,
                "publication_state": identity.get("publication_state"),
            },
        ),
        "analysis_result": (
            "authoritative_analysis",
            {
                "source_manifest_sha256": identity.get("source_manifest_sha256"),
                "analysis_input_sha256": identity.get("analysis_input_sha256"),
                "analysis_input_size": identity.get("analysis_input_size"),
                "analysis_input_validation_sha256": identity.get(
                    "analysis_input_validation_sha256"
                ),
                "analysis_input_validation_size": identity.get(
                    "analysis_input_validation_size"
                ),
                "analysis_request_manifest_sha256": identity.get(
                    "analysis_request_manifest_sha256"
                ),
                "analysis_request_manifest_size": identity.get(
                    "analysis_request_manifest_size"
                ),
                "result_manifest_sha256": identity.get("result_manifest_sha256"),
                "result_manifest_size": identity.get("result_manifest_size"),
                "result_artifact_sha256": identity.get("result_artifact_sha256"),
                "result_artifact_size": identity.get("result_artifact_size"),
                "data_as_of": identity.get("data_as_of"),
                "run_id": identity.get("run_id"),
                "code_version": identity.get("analysis_code_version"),
                "analysis_entrypoint_sha256": identity.get(
                    "analysis_entrypoint_sha256"
                ),
                "config_hash": identity.get("config_hash"),
                "effective_config_hash": identity.get("effective_config_hash"),
                "input_schema_version": identity.get("input_schema_version"),
                "input_schema_sha256": identity.get("input_schema_sha256"),
                "data_schema_version": identity.get("data_schema_version"),
                "result_schema_version": identity.get("result_schema_version"),
            },
        ),
        "schedule": (
            "workflow_schedule",
            {
                "schedule_id": identity.get("schedule_id"),
                "workflow": identity.get("workflow"),
                "event": "schedule",
                "default_branch": identity.get("default_branch"),
                "head_sha": identity.get("head_sha"),
                "enabled_on_default_branch": True,
                "last_success_at": identity.get("schedule_last_success_at"),
                "conclusion": "success",
                "run_id": identity.get("run_id"),
                "run_url": identity.get("run_url"),
                "workflow_run_evidence_sha256": identity.get(
                    "workflow_run_evidence_sha256"
                ),
                "workflow_file_sha256": identity.get("workflow_file_sha256"),
                "job_id": identity.get("job_id"),
                "cost_preflight_step_id": identity.get(
                    "cost_preflight_step_id"
                ),
                "entrypoint_step_id": identity.get("entrypoint_step_id"),
                "steps_completed": identity.get("steps_completed"),
                "workflow_started_at": identity.get("workflow_started_at"),
                "cost_preflight_completed_at": identity.get(
                    "cost_preflight_completed_at"
                ),
                "entrypoint_started_at": identity.get(
                    "entrypoint_started_at"
                ),
            },
        ),
        "publication": (
            "atomic_publication",
            {
                "published_result_key": identity.get("published_result_key"),
                "publication_state": identity.get("publication_state"),
                "result_artifact_sha256": identity.get("result_artifact_sha256"),
                "deployment_id": identity.get("deployment_id"),
                "monotonic_generation_checked": True,
                "previous_generation": identity.get("previous_generation"),
                "candidate_generation": identity.get("candidate_generation"),
                "previous_public_result_sha256": identity.get(
                    "previous_public_result_sha256"
                ),
                "public_pointer_before_sha256": identity.get(
                    "public_pointer_before_sha256"
                ),
                "public_pointer_after_sha256": identity.get(
                    "public_pointer_after_sha256"
                ),
                "publication_ordering_evidence_sha256": identity.get(
                    "publication_ordering_evidence_sha256"
                ),
                "publication_ordering_test_output_sha256": identity.get(
                    "publication_ordering_test_output_sha256"
                ),
            },
        ),
        "public_readback": (
            "public_readback",
            {
                "published_result_key": identity.get("published_result_key"),
                "publication_state": identity.get("publication_state"),
                "result_artifact_sha256": identity.get("result_artifact_sha256"),
                "data_as_of": identity.get("data_as_of"),
                "public_url": identity.get("public_url"),
                "http_status": 200,
                "response_sha256": identity.get("public_response_sha256"),
                "response_size": identity.get("public_response_size"),
                "cache_busted": True,
                "frontend_url": identity.get("frontend_url"),
                "frontend_http_status": 200,
                "frontend_response_sha256": identity.get(
                    "frontend_response_sha256"
                ),
                "frontend_response_size": identity.get("frontend_response_size"),
                "frontend_binding_evidence_sha256": identity.get(
                    "frontend_binding_evidence_sha256"
                ),
                "frontend_binding_evidence_size": identity.get(
                    "frontend_binding_evidence_size"
                ),
                "frontend_dom_snapshot_sha256": identity.get(
                    "frontend_dom_snapshot_sha256"
                ),
                "frontend_dom_snapshot_size": identity.get(
                    "frontend_dom_snapshot_size"
                ),
                "verified_at": identity.get("public_verified_at"),
            },
        ),
    }
    matched: dict[str, dict[str, Any]] = {}
    for gate_name, (kind, fields) in expected.items():
        items = matching_kind(gates, gate_name, kind)
        candidates = [
            item
            for item in items
            if all(item.get(field) == value for field, value in fields.items())
        ]
        if len(candidates) != 1:
            errors.append(
                f"gate {gate_name!r} needs one exact {kind} automation record"
            )
        else:
            matched[gate_name] = candidates[0]

    schedule_item = matched.get("schedule")
    if schedule_item is not None:
        if not isinstance(schedule_item.get("steps_completed"), int) or (
            schedule_item["steps_completed"] < 1
        ):
            errors.append("schedule steps_completed must be >= 1")

    def validated_freshness_row(
        source: dict[str, Any],
        prefix: str,
    ) -> dict[str, Any] | None:
        source_id = source.get("source_id")
        source_config = manifest_sources_by_id.get(source_id)
        if not isinstance(source_config, dict):
            errors.append(f"{prefix} is not declared in the project manifest")
            return None
        allowed_lag = source_config.get("allowed_lag_seconds")
        maximum_source_age = source_config.get(
            "maximum_source_age_seconds"
        )
        if (
            isinstance(allowed_lag, bool)
            or not isinstance(allowed_lag, int)
            or allowed_lag < 0
        ):
            errors.append(f"{prefix} manifest allowed_lag_seconds is invalid")
            return None
        if (
            isinstance(maximum_source_age, bool)
            or not isinstance(maximum_source_age, int)
            or maximum_source_age < allowed_lag
        ):
            errors.append(
                f"{prefix} manifest maximum_source_age_seconds is invalid"
            )
            return None
        if source.get("allowed_lag_seconds") != allowed_lag:
            errors.append(f"{prefix}.allowed_lag_seconds does not match manifest")
        if source.get("maximum_source_age_seconds") != maximum_source_age:
            errors.append(
                f"{prefix}.maximum_source_age_seconds does not match manifest"
            )
        observed = parse_date_or_time(source.get("source_as_of"))
        expected_source = parse_date_or_time(
            source.get("expected_source_as_of")
        )
        coherent_through = parse_date_or_time(source.get("coherent_through"))
        if observed is None:
            errors.append(f"{prefix}.source_as_of is invalid")
        if expected_source is None:
            errors.append(f"{prefix}.expected_source_as_of is invalid")
        if coherent_through is None:
            errors.append(f"{prefix}.coherent_through is invalid")
        calculated_lag = lag_seconds(
            source.get("source_as_of"),
            source.get("expected_source_as_of"),
        )
        if calculated_lag is None:
            return None
        if source.get("observed_lag_seconds") != calculated_lag:
            errors.append(f"{prefix}.observed_lag_seconds is incorrect")
        if calculated_lag > allowed_lag:
            errors.append(
                f"{prefix} is stale: lag {calculated_lag}s exceeds "
                f"{allowed_lag}s"
            )
        calculated_age = lag_seconds(
            source.get("source_as_of"),
            identity.get("schedule_last_success_at"),
        )
        if calculated_age is None:
            errors.append(f"{prefix}.observed_age_seconds cannot be calculated")
        else:
            if source.get("observed_age_seconds") != calculated_age:
                errors.append(f"{prefix}.observed_age_seconds is incorrect")
            if calculated_age > maximum_source_age:
                errors.append(
                    f"{prefix} is too old for this run: age "
                    f"{calculated_age}s exceeds {maximum_source_age}s"
                )
        if (
            expected_source is not None
            and schedule_time is not None
            and utc_naive(expected_source) > utc_naive(schedule_time)
        ):
            errors.append(f"{prefix}.expected_source_as_of is after run success")
        if (
            observed is not None
            and coherent_through is not None
            and utc_naive(coherent_through) < utc_naive(observed)
        ):
            errors.append(f"{prefix}.coherent_through precedes source_as_of")
        if (
            expected_source is not None
            and coherent_through is not None
            and utc_naive(coherent_through) > utc_naive(expected_source)
        ):
            errors.append(
                f"{prefix}.coherent_through exceeds expected_source_as_of"
            )
        return {
            "source_id": source_id,
            "source_as_of": source.get("source_as_of"),
            "expected_source_as_of": source.get("expected_source_as_of"),
            "coherent_through": source.get("coherent_through"),
            "observed_lag_seconds": source.get("observed_lag_seconds"),
            "allowed_lag_seconds": source.get("allowed_lag_seconds"),
            "observed_age_seconds": source.get("observed_age_seconds"),
            "maximum_source_age_seconds": source.get(
                "maximum_source_age_seconds"
            ),
        }

    source_receipts_by_id: dict[str, dict[str, Any]] = {}
    required_freshness_rows: list[dict[str, Any]] = []
    degraded_optional_ids: list[str] = []
    collection_item = matched.get("collection")
    if collection_item is not None:
        source_receipts = collection_item.get("required_source_receipts")
        if not isinstance(source_receipts, list):
            errors.append("collection requires per-source receipts")
        else:
            seen: list[str] = []
            for index, source in enumerate(source_receipts):
                prefix = f"required_source_receipts[{index}]"
                if not isinstance(source, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                seen.append(source.get("source_id", ""))
                if nonempty(source.get("source_id")):
                    if source["source_id"] in source_receipts_by_id:
                        errors.append(f"{prefix}.source_id is duplicated")
                    source_receipts_by_id[source["source_id"]] = source
                if source.get("role") != "required":
                    errors.append(f"{prefix}.role must be required")
                expected_role = manifest_source_roles.get(source.get("source_id"))
                if expected_role and expected_role != "required":
                    errors.append(f"{prefix}.role does not match manifest")
                if source.get("status") != "succeeded":
                    errors.append(f"{prefix}.status must be succeeded")
                freshness_row = validated_freshness_row(source, prefix)
                if freshness_row is not None:
                    required_freshness_rows.append(freshness_row)
                collected = parse_time(source.get("collected_at"))
                if collected is None:
                    errors.append(f"{prefix}.collected_at is invalid")
                elif schedule_time and collected > schedule_time:
                    errors.append(f"{prefix} collected after workflow success")
                if not is_sha256(source.get("artifact_sha256")):
                    errors.append(f"{prefix}.artifact_sha256 must be SHA-256")
                if (
                    isinstance(source.get("artifact_size"), bool)
                    or not isinstance(source.get("artifact_size"), int)
                    or source["artifact_size"] < 1
                ):
                    errors.append(f"{prefix}.artifact_size must be >= 1")
                artifact_path = source.get("artifact_path")
                if not nonempty(artifact_path):
                    errors.append(f"{prefix}.artifact_path is required")
                elif args.project_root_path is not None:
                    candidate = (
                        args.project_root_path / artifact_path
                    ).resolve()
                    try:
                        candidate.relative_to(args.project_root_path)
                    except ValueError:
                        errors.append(f"{prefix}.artifact_path escapes project root")
                    else:
                        validate_capture(
                            str(candidate),
                            prefix,
                            source.get("artifact_sha256"),
                            source.get("artifact_size"),
                            errors,
                            within=args.project_root_path,
                        )
            if sorted(seen) != sorted(required_source_ids):
                errors.append("source receipts do not cover required source IDs")
            optional_receipts = collection_item.get(
                "optional_source_receipts",
                [],
            )
            if not isinstance(optional_receipts, list):
                errors.append("optional_source_receipts must be an array")
            else:
                seen_optional_ids: list[str] = []
                for index, source in enumerate(optional_receipts):
                    prefix = f"optional_source_receipts[{index}]"
                    if not isinstance(source, dict):
                        errors.append(f"{prefix} must be an object")
                        continue
                    source_id = source.get("source_id")
                    if not nonempty(source_id):
                        errors.append(f"{prefix}.source_id is required")
                        continue
                    seen_optional_ids.append(source_id)
                    if source_id in source_receipts_by_id:
                        errors.append(f"{prefix}.source_id is duplicated")
                    role = source.get("role")
                    if role not in {"optional", "benchmark", "fallback"}:
                        errors.append(f"{prefix}.role is invalid")
                    if manifest_source_roles.get(source_id) != role:
                        errors.append(f"{prefix}.role does not match manifest")
                    status = source.get("status")
                    if status not in {
                        "succeeded",
                        "degraded",
                        "unavailable",
                        "skipped",
                    }:
                        errors.append(f"{prefix}.status is invalid")
                    if status != "succeeded":
                        degraded_optional_ids.append(source_id)
                        source_config = manifest_sources_by_id.get(source_id, {})
                        if source_config.get("fallback_policy") == "fail-closed":
                            errors.append(
                                f"{prefix} cannot degrade because its "
                                "fallback_policy is fail-closed"
                            )
                        if not nonempty(source.get("reason")):
                            errors.append(f"{prefix}.reason is required")
                        if not nonempty(source.get("impact")):
                            errors.append(f"{prefix}.impact is required")
                        if not isinstance(source.get("fallback_applied"), bool):
                            errors.append(
                                f"{prefix}.fallback_applied must be boolean"
                            )
                        if source.get("fallback_applied") is True and (
                            parse_date_or_time(
                                source.get("last_good_source_as_of")
                            )
                            is None
                        ):
                            errors.append(
                                f"{prefix}.last_good_source_as_of is required "
                                "when fallback is applied"
                            )
                        continue
                    source_receipts_by_id[source_id] = source
                    validated_freshness_row(source, prefix)
                    collected = parse_time(source.get("collected_at"))
                    if collected is None:
                        errors.append(f"{prefix}.collected_at is invalid")
                    elif schedule_time and collected > schedule_time:
                        errors.append(f"{prefix} collected after workflow success")
                    if not is_sha256(source.get("artifact_sha256")):
                        errors.append(f"{prefix}.artifact_sha256 must be SHA-256")
                    if (
                        isinstance(source.get("artifact_size"), bool)
                        or not isinstance(source.get("artifact_size"), int)
                        or source["artifact_size"] < 1
                    ):
                        errors.append(f"{prefix}.artifact_size must be >= 1")
                    artifact_path = source.get("artifact_path")
                    if not nonempty(artifact_path):
                        errors.append(f"{prefix}.artifact_path is required")
                    elif args.project_root_path is not None:
                        candidate = (
                            args.project_root_path / artifact_path
                        ).resolve()
                        try:
                            candidate.relative_to(args.project_root_path)
                        except ValueError:
                            errors.append(
                                f"{prefix}.artifact_path escapes project root"
                            )
                        else:
                            validate_capture(
                                str(candidate),
                                prefix,
                                source.get("artifact_sha256"),
                                source.get("artifact_size"),
                                errors,
                                within=args.project_root_path,
                            )
                expected_optional_ids = sorted(
                    source_id
                    for source_id, role in manifest_source_roles.items()
                    if role in {"optional", "benchmark", "fallback"}
                )
                if sorted(seen_optional_ids) != expected_optional_ids:
                    errors.append(
                        "optional source receipts do not cover every "
                        "optional/benchmark/fallback source"
                    )
    expected_publication_state = (
        "degraded" if degraded_optional_ids else "ready"
    )
    if identity.get("publication_state") != expected_publication_state:
        errors.append(
            "publication_state does not match optional-source outcomes"
        )
    freshness_item = matched.get("freshness")
    if freshness_item is not None:
        freshness_rows = freshness_item.get("required_source_freshness")
        if not isinstance(freshness_rows, list):
            errors.append(
                "freshness gate requires required_source_freshness rows"
            )
        elif sorted(
            freshness_rows,
            key=lambda row: row.get("source_id", "")
            if isinstance(row, dict)
            else "",
        ) != sorted(
            required_freshness_rows,
            key=lambda row: row.get("source_id", ""),
        ):
            errors.append(
                "freshness gate rows do not match required source receipts"
            )
        if freshness_item.get("cutoff_derivation") != (
            "minimum-required-coherent-through"
        ):
            errors.append("freshness cutoff_derivation is invalid")
        if not nonempty(freshness_item.get("calendar_evaluator")):
            errors.append("freshness calendar_evaluator is required")
        calendar_evaluated = parse_time(
            freshness_item.get("calendar_evaluated_at")
        )
        if calendar_evaluated is None:
            errors.append("freshness calendar_evaluated_at is invalid")
        elif schedule_time and calendar_evaluated > schedule_time:
            errors.append("freshness calendar evaluation is after run success")
    coherent_values = [
        parse_date_or_time(row.get("coherent_through"))
        for row in required_freshness_rows
    ]
    if coherent_values and all(value is not None for value in coherent_values):
        derived_cutoff = min(
            utc_naive(value)
            for value in coherent_values
            if value is not None
        )
        declared_cutoff = parse_date_or_time(identity.get("data_as_of"))
        if (
            declared_cutoff is None
            or utc_naive(declared_cutoff) != derived_cutoff
        ):
            errors.append(
                "data_as_of is not the minimum required coherent_through"
            )
    for gate_name, timestamp_field in (
        ("analysis_result", "calculated_at"),
        ("publication", "published_at"),
    ):
        item = matched.get(gate_name)
        if item is None:
            continue
        value = parse_time(item.get(timestamp_field))
        if value is None:
            errors.append(f"{gate_name}.{timestamp_field} is invalid")
        elif public_time and value > public_time:
            errors.append(f"{gate_name}.{timestamp_field} is after readback")

    if args.source_manifest and args.project_root_path is not None and manifest:
        data = manifest.get("data")
        expected_manifest_path = (
            data.get("data_manifest_path") if isinstance(data, dict) else ""
        )
        expected_manifest = (
            args.project_root_path / expected_manifest_path
        ).resolve() if nonempty(expected_manifest_path) else None
        actual_manifest = Path(args.source_manifest).expanduser().resolve()
        if expected_manifest is None or actual_manifest != expected_manifest:
            errors.append(
                "source manifest path does not match project data_manifest_path"
            )
    validate_capture(
        args.source_manifest,
        "source manifest",
        identity.get("source_manifest_sha256"),
        identity.get("source_manifest_size"),
        errors,
        within=args.project_root_path,
    )
    _, source_manifest_value = load_json_capture(
        args.source_manifest,
        "source manifest",
        errors,
        within=args.project_root_path,
    )
    if source_manifest_value is not None and args.project_root_path is not None:
        expected_manifest_values = {
            "project_id": receipt.get("project_id"),
            "data_as_of": identity.get("data_as_of"),
            "required_source_ids": required_source_ids,
            "analysis_input_sha256": identity.get("analysis_input_sha256"),
            "analysis_input_size": identity.get("analysis_input_size"),
        }
        for field, expected_value in expected_manifest_values.items():
            if source_manifest_value.get(field) != expected_value:
                errors.append(f"source manifest {field} mismatch")
        input_path = relative_project_path(
            source_manifest_value.get("analysis_input_path"),
            args.project_root_path,
            "source manifest analysis_input_path",
            errors,
        )
        if input_path is not None and args.analysis_input:
            if input_path != Path(args.analysis_input).expanduser().resolve():
                errors.append(
                    "source manifest analysis_input_path does not match capture"
                )
        source_entries = source_manifest_value.get("sources")
        if not isinstance(source_entries, list):
            errors.append("source manifest sources must be an array")
        else:
            manifest_by_id: dict[str, dict[str, Any]] = {}
            for index, source in enumerate(source_entries):
                prefix = f"source manifest sources[{index}]"
                if not isinstance(source, dict) or not nonempty(
                    source.get("source_id")
                ):
                    errors.append(f"{prefix}.source_id is required")
                    continue
                source_id = source["source_id"]
                if source_id in manifest_by_id:
                    errors.append(f"{prefix}.source_id is duplicated")
                    continue
                manifest_by_id[source_id] = source
                receipt_source = source_receipts_by_id.get(source_id)
                if receipt_source is None:
                    errors.append(
                        f"{prefix} is not backed by a collection receipt"
                    )
                    continue
                expected_role = manifest_source_roles.get(source_id)
                if source.get("role") != expected_role:
                    errors.append(f"{prefix}.role does not match project manifest")
                if source.get("role") != receipt_source.get("role"):
                    errors.append(
                        f"{prefix}.role does not match collection receipt"
                    )
                for field in (
                    "artifact_path",
                    "artifact_sha256",
                    "artifact_size",
                    "source_as_of",
                    "expected_source_as_of",
                    "coherent_through",
                    "observed_lag_seconds",
                    "allowed_lag_seconds",
                    "observed_age_seconds",
                    "maximum_source_age_seconds",
                    "collected_at",
                ):
                    if source.get(field) != receipt_source.get(field):
                        errors.append(
                            f"{prefix}.{field} does not match collection receipt"
                        )
            if not set(required_source_ids).issubset(manifest_by_id):
                errors.append(
                    "source manifest sources do not cover all required source IDs"
                )
            if set(manifest_by_id) != set(source_receipts_by_id):
                errors.append(
                    "source manifest sources must exactly match all succeeded "
                    "source receipts"
                )
    validate_capture(
        args.analysis_input,
        "analysis input",
        identity.get("analysis_input_sha256"),
        identity.get("analysis_input_size"),
        errors,
        within=args.project_root_path,
    )
    _, analysis_input_value = load_json_capture(
        args.analysis_input,
        "analysis input",
        errors,
        within=args.project_root_path,
    )
    validate_capture(
        args.analysis_input_validation,
        "analysis input validation",
        identity.get("analysis_input_validation_sha256"),
        identity.get("analysis_input_validation_size"),
        errors,
        within=args.project_root_path,
    )
    _, analysis_input_validation = load_json_capture(
        args.analysis_input_validation,
        "analysis input validation",
        errors,
        within=args.project_root_path,
    )
    if analysis_input_value is None:
        errors.append("analysis input must be a JSON object")
    if analysis_input_validation is not None:
        expected_validation = {
            "schema_version": 1,
            "project_id": receipt.get("project_id"),
            "run_id": identity.get("run_id"),
            "analysis_input_sha256": identity.get("analysis_input_sha256"),
            "input_schema_sha256": identity.get("input_schema_sha256"),
            "code_version": identity.get("analysis_code_version"),
            "analysis_entrypoint_sha256": identity.get(
                "analysis_entrypoint_sha256"
            ),
            "valid": True,
        }
        for field, expected_value in expected_validation.items():
            if analysis_input_validation.get(field) != expected_value:
                errors.append(f"analysis input validation {field} mismatch")
        for field in ("validator_name", "validator_version", "command"):
            if not nonempty(analysis_input_validation.get(field)):
                errors.append(f"analysis input validation {field} is required")
        validation_time = parse_time(
            analysis_input_validation.get("checked_at")
        )
        if validation_time is None:
            errors.append("analysis input validation checked_at is invalid")
        elif (
            entrypoint_started is not None
            and validation_time < entrypoint_started
        ):
            errors.append(
                "analysis input validation occurred before entrypoint start"
            )
        elif schedule_time and validation_time > schedule_time:
            errors.append(
                "analysis input validation occurred after workflow success"
            )
    validate_capture(
        args.analysis_request_manifest,
        "analysis request manifest",
        identity.get("analysis_request_manifest_sha256"),
        identity.get("analysis_request_manifest_size"),
        errors,
        within=args.project_root_path,
    )
    _, analysis_request = load_json_capture(
        args.analysis_request_manifest,
        "analysis request manifest",
        errors,
        within=args.project_root_path,
    )
    if analysis_request is not None and args.project_root_path is not None:
        expected_request = {
            "project_id": receipt.get("project_id"),
            "run_id": identity.get("run_id"),
            "code_version": identity.get("analysis_code_version"),
            "analysis_entrypoint_sha256": identity.get(
                "analysis_entrypoint_sha256"
            ),
            "input_schema_version": identity.get("input_schema_version"),
            "input_schema_sha256": identity.get("input_schema_sha256"),
            "data_manifest_sha256": identity.get("source_manifest_sha256"),
            "analysis_input_sha256": identity.get("analysis_input_sha256"),
            "analysis_input_validation_sha256": identity.get(
                "analysis_input_validation_sha256"
            ),
            "config_hash": identity.get("config_hash"),
            "effective_config_hash": identity.get("effective_config_hash"),
        }
        for field, expected_value in expected_request.items():
            if analysis_request.get(field) != expected_value:
                errors.append(f"analysis request manifest {field} mismatch")
        requested_config = analysis_request.get("requested_config")
        effective_config = analysis_request.get("effective_config")
        if not isinstance(requested_config, dict):
            errors.append("analysis request requested_config must be an object")
        elif canonical_sha256(requested_config) != identity.get("config_hash"):
            errors.append("analysis request requested_config hash mismatch")
        if not isinstance(effective_config, dict):
            errors.append("analysis request effective_config must be an object")
        elif canonical_sha256(effective_config) != identity.get(
            "effective_config_hash"
        ):
            errors.append("analysis request effective_config hash mismatch")
        fallback_applied = analysis_request.get("fallback_applied")
        if not isinstance(fallback_applied, bool):
            errors.append("analysis request fallback_applied must be boolean")
        elif (
            isinstance(requested_config, dict)
            and isinstance(effective_config, dict)
            and requested_config != effective_config
        ):
            if fallback_applied is not True:
                errors.append(
                    "requested/effective config differ without fallback_applied"
                )
            if not nonempty(analysis_request.get("fallback_reason")):
                errors.append(
                    "requested/effective config difference needs fallback_reason"
                )
        elif fallback_applied is not False:
            errors.append(
                "fallback_applied must be false when configs are identical"
            )
        analysis = manifest.get("analysis") if manifest is not None else None
        schema_contract = (
            analysis.get("input_schema_contract")
            if isinstance(analysis, dict)
            else ""
        )
        schema_path = relative_project_path(
            schema_contract,
            args.project_root_path,
            "analysis input schema contract",
            errors,
        )
        if schema_path is not None:
            if not schema_path.is_file():
                errors.append("analysis input schema contract does not exist")
            elif file_sha256(schema_path) != identity.get(
                "input_schema_sha256"
            ):
                errors.append("analysis input schema SHA-256 mismatch")
    validate_provider_run(
        args.workflow_run_evidence,
        identity,
        completed,
        errors,
    )
    validate_capture(
        args.result_artifact,
        "result artifact",
        identity.get("result_artifact_sha256"),
        identity.get("result_artifact_size"),
        errors,
        within=args.project_root_path,
    )
    result_artifact_path, result_artifact_value = load_json_capture(
        args.result_artifact,
        "result artifact",
        errors,
        within=args.project_root_path,
    )
    if (
        result_artifact_path is not None
        and result_artifact_value is not None
        and manifest is not None
    ):
        assertions = manifest.get("analysis", {}).get(
            "result_artifact_identity",
            [],
        )
        artifact_expected_identity = {
            "project_id": receipt.get("project_id"),
            "run_id": identity.get("run_id"),
            "data_as_of": identity.get("data_as_of"),
            "code_version": identity.get("analysis_code_version"),
            "analysis_entrypoint_sha256": identity.get(
                "analysis_entrypoint_sha256"
            ),
            "data_manifest_sha256": identity.get("source_manifest_sha256"),
            "analysis_input_sha256": identity.get("analysis_input_sha256"),
            "analysis_input_validation_sha256": identity.get(
                "analysis_input_validation_sha256"
            ),
            "config_hash": identity.get("config_hash"),
            "effective_config_hash": identity.get("effective_config_hash"),
            "input_schema_version": identity.get("input_schema_version"),
            "data_schema_version": identity.get("data_schema_version"),
            "result_schema_version": identity.get("result_schema_version"),
            "artifact_sha256": identity.get("result_artifact_sha256"),
        }
        for index, assertion in enumerate(assertions):
            if not isinstance(assertion, dict):
                continue
            found, observed = json_pointer(
                result_artifact_value,
                assertion.get("json_pointer", ""),
            )
            label = f"result artifact identity assertion[{index}]"
            if not found:
                errors.append(f"{label} JSON pointer was not found")
                continue
            expected_value = artifact_expected_identity.get(
                assertion.get("identity_field")
            )
            if observed != expected_value:
                errors.append(f"{label} does not match result identity")
    validate_capture(
        args.result_manifest,
        "result manifest",
        identity.get("result_manifest_sha256"),
        identity.get("result_manifest_size"),
        errors,
        within=args.project_root_path,
    )
    _, result_manifest_value = load_json_capture(
        args.result_manifest,
        "result manifest",
        errors,
        within=args.project_root_path,
    )
    if result_manifest_value is not None and args.project_root_path is not None:
        expected_result_values = {
            "project_id": receipt.get("project_id"),
            "run_id": identity.get("run_id"),
            "data_as_of": identity.get("data_as_of"),
            "code_version": identity.get("analysis_code_version"),
            "data_manifest_sha256": identity.get("source_manifest_sha256"),
            "analysis_input_sha256": identity.get("analysis_input_sha256"),
            "analysis_input_validation_sha256": identity.get(
                "analysis_input_validation_sha256"
            ),
            "analysis_request_manifest_sha256": identity.get(
                "analysis_request_manifest_sha256"
            ),
            "config_hash": identity.get("config_hash"),
            "effective_config_hash": identity.get("effective_config_hash"),
            "input_schema_version": identity.get("input_schema_version"),
            "input_schema_sha256": identity.get("input_schema_sha256"),
            "data_schema_version": identity.get("data_schema_version"),
            "result_schema_version": identity.get("result_schema_version"),
            "artifact_sha256": identity.get("result_artifact_sha256"),
            "artifact_size": identity.get("result_artifact_size"),
        }
        for field, expected_value in expected_result_values.items():
            if result_manifest_value.get(field) != expected_value:
                errors.append(f"result manifest {field} mismatch")
        result_path = relative_project_path(
            result_manifest_value.get("artifact_path"),
            args.project_root_path,
            "result manifest artifact_path",
            errors,
        )
        if result_path is not None and args.result_artifact:
            if result_path != Path(args.result_artifact).expanduser().resolve():
                errors.append("result manifest artifact_path does not match capture")
    for value, label, sha_field, size_field in (
        (
            args.public_pointer_before,
            "public pointer before",
            "public_pointer_before_sha256",
            "public_pointer_before_size",
        ),
        (
            args.public_pointer_after,
            "public pointer after",
            "public_pointer_after_sha256",
            "public_pointer_after_size",
        ),
        (
            args.publication_ordering_evidence,
            "publication ordering evidence",
            "publication_ordering_evidence_sha256",
            "publication_ordering_evidence_size",
        ),
        (
            args.publication_ordering_test_output,
            "publication ordering test output",
            "publication_ordering_test_output_sha256",
            "publication_ordering_test_output_size",
        ),
    ):
        validate_capture(
            value,
            label,
            identity.get(sha_field),
            identity.get(size_field),
            errors,
        )
    _, pointer_before = load_json_capture(
        args.public_pointer_before,
        "public pointer before",
        errors,
    )
    _, pointer_after = load_json_capture(
        args.public_pointer_after,
        "public pointer after",
        errors,
    )
    _, ordering_evidence = load_json_capture(
        args.publication_ordering_evidence,
        "publication ordering evidence",
        errors,
    )
    expected_before = {
        "project_id": receipt.get("project_id"),
        "generation": identity.get("previous_generation"),
        "published_result_key": identity.get("previous_published_result_key"),
        "data_as_of": identity.get("previous_data_as_of"),
        "result_artifact_sha256": identity.get(
            "previous_public_result_sha256"
        ),
    }
    expected_after = {
        "project_id": receipt.get("project_id"),
        "generation": identity.get("candidate_generation"),
        "published_result_key": identity.get("published_result_key"),
        "data_as_of": identity.get("data_as_of"),
        "result_artifact_sha256": identity.get("result_artifact_sha256"),
    }
    for label, value, expected_value in (
        ("public pointer before", pointer_before, expected_before),
        ("public pointer after", pointer_after, expected_after),
    ):
        if value is not None:
            for field, field_value in expected_value.items():
                if value.get(field) != field_value:
                    errors.append(f"{label} {field} mismatch")
    if ordering_evidence is not None:
        expected_ordering = {
            "schema_version": 1,
            "project_id": receipt.get("project_id"),
            "candidate_run_id": identity.get("run_id"),
            "previous_generation": identity.get("previous_generation"),
            "candidate_generation": identity.get("candidate_generation"),
            "previous_result_sha256": identity.get(
                "previous_public_result_sha256"
            ),
            "candidate_result_sha256": identity.get(
                "result_artifact_sha256"
            ),
            "selected_generation": identity.get("candidate_generation"),
            "older_candidate_rejected": True,
            "failed_candidate_preserved_previous": True,
        }
        for field, field_value in expected_ordering.items():
            if ordering_evidence.get(field) != field_value:
                errors.append(f"publication ordering evidence {field} mismatch")
        if not nonempty(ordering_evidence.get("test_source")):
            errors.append("publication ordering evidence test_source is required")
        for field in ("test_command", "isolated_test_namespace"):
            if not nonempty(ordering_evidence.get(field)):
                errors.append(
                    f"publication ordering evidence {field} is required"
                )
        if ordering_evidence.get("test_exit_code") != 0:
            errors.append(
                "publication ordering evidence test_exit_code must be 0"
            )
        if ordering_evidence.get(
            "test_output_sha256"
        ) != identity.get("publication_ordering_test_output_sha256"):
            errors.append(
                "publication ordering evidence test_output_sha256 mismatch"
            )
        if ordering_evidence.get(
            "test_output_size"
        ) != identity.get("publication_ordering_test_output_size"):
            errors.append(
                "publication ordering evidence test_output_size mismatch"
            )
        older = ordering_evidence.get("older_candidate_scenario")
        expected_older = {
            "newer_run_id": identity.get("run_id"),
            "newer_generation": identity.get("candidate_generation"),
            "older_generation": identity.get("previous_generation"),
            "pointer_before_sha256": identity.get(
                "public_pointer_after_sha256"
            ),
            "pointer_after_sha256": identity.get(
                "public_pointer_after_sha256"
            ),
            "selected_generation": identity.get("candidate_generation"),
        }
        if not isinstance(older, dict) or any(
            older.get(field) != value
            for field, value in expected_older.items()
        ):
            errors.append(
                "publication ordering older-candidate scenario mismatch"
            )
        elif (
            not nonempty(older.get("older_run_id"))
            or older.get("older_run_id") == identity.get("run_id")
        ):
            errors.append(
                "publication ordering older candidate needs a distinct run ID"
            )
        failed = ordering_evidence.get("failed_candidate_scenario")
        expected_failed = {
            "failure_stage": "analysis-or-readback",
            "pointer_before_sha256": identity.get(
                "public_pointer_before_sha256"
            ),
            "pointer_after_sha256": identity.get(
                "public_pointer_before_sha256"
            ),
            "preserved_result_sha256": identity.get(
                "previous_public_result_sha256"
            ),
        }
        if not isinstance(failed, dict) or any(
            failed.get(field) != value
            for field, value in expected_failed.items()
        ):
            errors.append(
                "publication ordering failed-candidate scenario mismatch"
            )
        elif (
            not nonempty(failed.get("failed_run_id"))
            or failed.get("failed_run_id") == identity.get("run_id")
            or (
                isinstance(older, dict)
                and failed.get("failed_run_id") == older.get("older_run_id")
            )
        ):
            errors.append(
                "publication ordering failed candidate needs a distinct run ID"
            )
    validate_capture(
        args.public_result_body,
        "public result body",
        identity.get("public_response_sha256"),
        identity.get("public_response_size"),
        errors,
    )
    validate_capture(
        args.frontend_body,
        "frontend body",
        identity.get("frontend_response_sha256"),
        identity.get("frontend_response_size"),
        errors,
    )
    validate_capture(
        args.frontend_binding_evidence,
        "frontend binding evidence",
        identity.get("frontend_binding_evidence_sha256"),
        identity.get("frontend_binding_evidence_size"),
        errors,
    )
    validate_capture(
        args.frontend_dom_snapshot,
        "frontend DOM snapshot",
        identity.get("frontend_dom_snapshot_sha256"),
        identity.get("frontend_dom_snapshot_size"),
        errors,
    )
    if args.frontend_dom_snapshot:
        try:
            dom_text = (
                Path(args.frontend_dom_snapshot)
                .expanduser()
                .resolve()
                .read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError) as exc:
            errors.append(f"frontend DOM snapshot cannot be read: {exc}")
        else:
            tag_match = re.search(
                r"<[^>]*\bdata-quant-result-binding(?:=(?:\"[^\"]*\"|'[^']*'))?"
                r"[^>]*>",
                dom_text,
            )
            if tag_match is None:
                errors.append(
                    "frontend DOM snapshot lacks data-quant-result-binding"
                )
            else:
                attributes = {
                    name: html.unescape(value)
                    for name, _, value in re.findall(
                        r"([A-Za-z_:][A-Za-z0-9_.:-]*)\s*=\s*"
                        r"([\"'])(.*?)\2",
                        tag_match.group(0),
                    )
                }
                expected_attributes = {
                    "data-quant-project-id": receipt.get("project_id"),
                    "data-quant-run-id": identity.get("run_id"),
                    "data-quant-as-of": identity.get("data_as_of"),
                    "data-quant-result-sha": identity.get(
                        "result_artifact_sha256"
                    ),
                    "data-quant-result-manifest-sha": identity.get(
                        "result_manifest_sha256"
                    ),
                    "data-quant-config-sha": identity.get("config_hash"),
                    "data-quant-effective-config-sha": identity.get(
                        "effective_config_hash"
                    ),
                    "data-quant-input-schema-version": identity.get(
                        "input_schema_version"
                    ),
                    "data-quant-analysis-entrypoint-sha": identity.get(
                        "analysis_entrypoint_sha256"
                    ),
                    "data-quant-publication-state": identity.get(
                        "publication_state"
                    ),
                }
                for field, expected_value in expected_attributes.items():
                    if attributes.get(field) != expected_value:
                        errors.append(
                            f"frontend DOM snapshot {field} mismatch"
                        )
    _, frontend_binding = load_json_capture(
        args.frontend_binding_evidence,
        "frontend binding evidence",
        errors,
    )
    if frontend_binding is not None:
        expected_binding = {
            "schema_version": 1,
            "binding_status": "bound",
            "captured_at": identity.get("public_verified_at"),
            "frontend_url": identity.get("frontend_url"),
            "frontend_response_sha256": identity.get(
                "frontend_response_sha256"
            ),
            "public_result_url": identity.get("public_url"),
            "public_result_sha256": identity.get("public_response_sha256"),
            "project_id": receipt.get("project_id"),
            "run_id": identity.get("run_id"),
            "data_as_of": identity.get("data_as_of"),
            "code_version": identity.get("analysis_code_version"),
            "analysis_entrypoint_sha256": identity.get(
                "analysis_entrypoint_sha256"
            ),
            "data_manifest_sha256": identity.get("source_manifest_sha256"),
            "result_manifest_sha256": identity.get("result_manifest_sha256"),
            "result_artifact_sha256": identity.get("result_artifact_sha256"),
            "analysis_input_sha256": identity.get("analysis_input_sha256"),
            "analysis_input_validation_sha256": identity.get(
                "analysis_input_validation_sha256"
            ),
            "analysis_request_manifest_sha256": identity.get(
                "analysis_request_manifest_sha256"
            ),
            "config_hash": identity.get("config_hash"),
            "effective_config_hash": identity.get("effective_config_hash"),
            "input_schema_version": identity.get("input_schema_version"),
            "input_schema_sha256": identity.get("input_schema_sha256"),
            "publication_state": identity.get("publication_state"),
            "dom_snapshot_sha256": identity.get(
                "frontend_dom_snapshot_sha256"
            ),
            "dom_snapshot_size": identity.get("frontend_dom_snapshot_size"),
        }
        for field, expected_value in expected_binding.items():
            if frontend_binding.get(field) != expected_value:
                errors.append(f"frontend binding evidence {field} mismatch")
        if frontend_binding.get("capture_origin") != "browser-runtime":
            errors.append(
                "frontend binding evidence capture_origin must be browser-runtime"
            )
        if not nonempty(frontend_binding.get("capture_tool")):
            errors.append("frontend binding evidence capture_tool is required")
        if frontend_binding.get("dom_selector") != (
            "[data-quant-result-binding]"
        ):
            errors.append("frontend binding evidence dom_selector mismatch")


def validate_release(
    receipt: dict[str, Any],
    gates: dict[str, Any],
    manifest: dict[str, Any] | None,
    completed: datetime | None,
    args: argparse.Namespace,
    errors: list[str],
) -> None:
    identity = receipt.get("release_identity")
    if not isinstance(identity, dict):
        errors.append("release_identity is required")
        return
    for field in (
        "repository",
        "account",
        "branch",
        "commit_sha",
        "ci_run_id",
        "ci_run_url",
        "deployment_id",
        "production_url",
        "frontend_response_sha256",
        "authoritative_result_url",
        "authoritative_result_sha256",
        "public_verified_at",
        "release_run_evidence_sha256",
        "job_id",
        "cost_preflight_step_id",
        "cost_preflight_completed_at",
        "remote_write_step_id",
        "remote_write_started_at",
        "run_completed_at",
    ):
        if not nonempty(identity.get(field)):
            errors.append(f"release_identity.{field} is required")
    if not is_full_git_sha(identity.get("commit_sha")):
        errors.append("release_identity.commit_sha must be a full commit SHA")
    for field in (
        "frontend_response_sha256",
        "authoritative_result_sha256",
        "release_run_evidence_sha256",
    ):
        if identity.get(field) and not is_sha256(identity[field]):
            errors.append(f"release_identity.{field} must be SHA-256")
    verified = parse_time(identity.get("public_verified_at"))
    if verified is None:
        errors.append("release_identity.public_verified_at is invalid")
    elif completed and verified > completed:
        errors.append("release public verification occurs after completion")
    release_preflight = parse_time(identity.get("cost_preflight_completed_at"))
    remote_write_started = parse_time(identity.get("remote_write_started_at"))
    release_completed = parse_time(identity.get("run_completed_at"))
    for field, value in (
        ("cost_preflight_completed_at", release_preflight),
        ("remote_write_started_at", remote_write_started),
        ("run_completed_at", release_completed),
    ):
        if value is None:
            errors.append(f"release_identity.{field} is invalid")
    if (
        release_preflight is not None
        and remote_write_started is not None
        and release_preflight > remote_write_started
    ):
        errors.append("release remote write started before cost preflight ended")
    if (
        remote_write_started is not None
        and release_completed is not None
        and remote_write_started > release_completed
    ):
        errors.append("release completion precedes remote write")
    if (
        release_completed is not None
        and verified is not None
        and release_completed > verified
    ):
        errors.append("release completed after public verification")
    if (
        release_completed is not None
        and completed is not None
        and release_completed > completed
    ):
        errors.append("release completed after receipt completion")
    for field in (
        "frontend_response_size",
        "authoritative_result_size",
        "steps_completed",
    ):
        if (
            isinstance(identity.get(field), bool)
            or not isinstance(identity.get(field), int)
            or identity[field] < (2 if field == "steps_completed" else 1)
        ):
            minimum = 2 if field == "steps_completed" else 1
            errors.append(f"release_identity.{field} must be >= {minimum}")
    if manifest is not None:
        project = manifest.get("project")
        release = manifest.get("release")
        production = (
            release.get("production")
            if isinstance(release, dict)
            else project.get("public_url")
            if isinstance(project, dict)
            else ""
        )
        if url_without_query(identity.get("production_url")) != url_without_query(
            production
        ):
            errors.append("release production_url does not match manifest")
        if isinstance(release, dict) and identity.get("branch") != release.get(
            "base_branch"
        ):
            errors.append("release branch does not match manifest base branch")
        if isinstance(project, dict) and identity.get("repository") != project.get(
            "repository"
        ):
            errors.append("release repository does not match manifest")
        if isinstance(release, dict) and identity.get("account") != release.get(
            "approved_account"
        ):
            errors.append("release account does not match manifest")
        automation = manifest.get("automation")
        urls = (
            automation.get("public_readback_urls")
            if isinstance(automation, dict)
            else []
        )
        urls = urls if isinstance(urls, list) else []
        if url_without_query(identity.get("authoritative_result_url")) not in {
            url_without_query(url) for url in urls
        }:
            errors.append("release result URL is not a manifest readback target")

    release_items = matching_kind(gates, "release", "github_release")
    if not any(
        item.get("repository") == identity.get("repository")
        and item.get("account") == identity.get("account")
        and item.get("branch") == identity.get("branch")
        and item.get("commit_sha") == identity.get("commit_sha")
        and item.get("ci_run_id") == identity.get("ci_run_id")
        and item.get("ci_run_url") == identity.get("ci_run_url")
        and item.get("deployment_id") == identity.get("deployment_id")
        and item.get("production_url") == identity.get("production_url")
        and item.get("conclusion") == "success"
        and item.get("release_run_evidence_sha256")
        == identity.get("release_run_evidence_sha256")
        and item.get("job_id") == identity.get("job_id")
        and item.get("steps_completed") == identity.get("steps_completed")
        and item.get("cost_preflight_step_id")
        == identity.get("cost_preflight_step_id")
        and item.get("cost_preflight_completed_at")
        == identity.get("cost_preflight_completed_at")
        and item.get("remote_write_step_id")
        == identity.get("remote_write_step_id")
        and item.get("remote_write_started_at")
        == identity.get("remote_write_started_at")
        and item.get("run_completed_at") == identity.get("run_completed_at")
        for item in release_items
    ):
        errors.append("release gate lacks exact github_release evidence")
    readback_items = matching_kind(gates, "public_readback", "public_readback")
    if not any(
        item.get("frontend_url") == identity.get("production_url")
        and item.get("frontend_http_status") == 200
        and item.get("frontend_response_sha256")
        == identity.get("frontend_response_sha256")
        and item.get("frontend_response_size")
        == identity.get("frontend_response_size")
        and item.get("authoritative_result_url")
        == identity.get("authoritative_result_url")
        and item.get("authoritative_result_http_status") == 200
        and item.get("authoritative_result_sha256")
        == identity.get("authoritative_result_sha256")
        and item.get("authoritative_result_size")
        == identity.get("authoritative_result_size")
        and item.get("cache_busted") is True
        and item.get("verified_at") == identity.get("public_verified_at")
        for item in readback_items
    ):
        errors.append("release public_readback evidence does not match identity")

    if not args.release_run_evidence:
        errors.append("release run evidence file is required")
    else:
        path = Path(args.release_run_evidence).expanduser().resolve()
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid release run evidence: {exc}")
        else:
            if file_sha256(path) != identity.get("release_run_evidence_sha256"):
                errors.append("release run evidence SHA-256 mismatch")
            if not isinstance(run, dict):
                errors.append("release run evidence must contain an object")
            else:
                expected = {
                    "repository": identity.get("repository"),
                    "account": identity.get("account"),
                    "branch": identity.get("branch"),
                    "commit_sha": identity.get("commit_sha"),
                    "ci_run_id": identity.get("ci_run_id"),
                    "ci_run_url": identity.get("ci_run_url"),
                    "conclusion": "success",
                    "deployment_id": identity.get("deployment_id"),
                    "steps_completed": identity.get("steps_completed"),
                    "cost_preflight_completed_at": identity.get(
                        "cost_preflight_completed_at"
                    ),
                    "remote_write_started_at": identity.get(
                        "remote_write_started_at"
                    ),
                    "completed_at": identity.get("run_completed_at"),
                }
                for field, value in expected.items():
                    if run.get(field) != value:
                        errors.append(f"release run evidence {field} mismatch")
                jobs = run.get("jobs")
                if not isinstance(jobs, list):
                    errors.append("release run evidence jobs must be an array")
                else:
                    matching_jobs = [
                        job
                        for job in jobs
                        if isinstance(job, dict)
                        and job.get("job_id") == identity.get("job_id")
                    ]
                    if len(matching_jobs) != 1:
                        errors.append(
                            "release run evidence must contain exactly one "
                            "matching job"
                        )
                    else:
                        job = matching_jobs[0]
                        if job.get("conclusion") != "success":
                            errors.append(
                                "release run evidence matching job did not succeed"
                            )
                        steps = job.get("steps")
                        if not isinstance(steps, list):
                            errors.append(
                                "release run evidence matching job steps "
                                "must be an array"
                            )
                        else:
                            successful_steps = [
                                step
                                for step in steps
                                if isinstance(step, dict)
                                and step.get("conclusion") == "success"
                            ]
                            if len(successful_steps) != identity.get(
                                "steps_completed"
                            ):
                                errors.append(
                                    "release run evidence successful step "
                                    "count mismatch"
                                )
                            step_ids = [
                                step.get("step_id")
                                for step in steps
                                if isinstance(step, dict)
                                and nonempty(step.get("step_id"))
                            ]
                            if len(step_ids) != len(set(step_ids)):
                                errors.append(
                                    "release run evidence step IDs must be unique"
                                )
                            step_by_id = {
                                step.get("step_id"): step
                                for step in steps
                                if isinstance(step, dict)
                                and nonempty(step.get("step_id"))
                            }
                            cost_step = step_by_id.get(
                                identity.get("cost_preflight_step_id")
                            )
                            remote_step = step_by_id.get(
                                identity.get("remote_write_step_id")
                            )
                            if not isinstance(cost_step, dict):
                                errors.append(
                                    "release run evidence is missing the cost "
                                    "preflight step"
                                )
                            elif (
                                cost_step.get("outcome") != "success"
                                or
                                cost_step.get("conclusion") != "success"
                                or cost_step.get("completed_at")
                                != identity.get("cost_preflight_completed_at")
                            ):
                                errors.append(
                                    "release cost preflight step success or "
                                    "completion time mismatch"
                                )
                            if not isinstance(remote_step, dict):
                                errors.append(
                                    "release run evidence is missing the remote "
                                    "write step"
                                )
                            elif (
                                remote_step.get("outcome") != "success"
                                or
                                remote_step.get("conclusion") != "success"
                                or remote_step.get("started_at")
                                != identity.get("remote_write_started_at")
                            ):
                                errors.append(
                                    "release remote write step success or start "
                                    "time mismatch"
                                )
                            if (
                                isinstance(cost_step, dict)
                                and isinstance(remote_step, dict)
                                and steps.index(cost_step) > steps.index(remote_step)
                            ):
                                errors.append(
                                    "release cost preflight step must precede "
                                    "the remote write step"
                                )
    validate_capture(
        args.public_result_body,
        "release authoritative result body",
        identity.get("authoritative_result_sha256"),
        identity.get("authoritative_result_size"),
        errors,
    )
    validate_capture(
        args.frontend_body,
        "release frontend body",
        identity.get("frontend_response_sha256"),
        identity.get("frontend_response_size"),
        errors,
    )


def validate_cross_scope(receipt: dict[str, Any], errors: list[str]) -> None:
    scope = receipt.get("scope")
    if not isinstance(scope, dict) or not (
        scope.get("automated_data_to_web") and scope.get("remote_release")
    ):
        return
    automation = receipt.get("automation_identity")
    release = receipt.get("release_identity")
    if not isinstance(automation, dict) or not isinstance(release, dict):
        return
    pairs = (
        ("head_sha", "commit_sha"),
        ("deployment_id", "deployment_id"),
        ("frontend_response_sha256", "frontend_response_sha256"),
        ("frontend_response_size", "frontend_response_size"),
        ("result_artifact_sha256", "authoritative_result_sha256"),
        ("result_artifact_size", "authoritative_result_size"),
    )
    for automation_field, release_field in pairs:
        if automation.get(automation_field) != release.get(release_field):
            errors.append(
                f"automation.{automation_field} does not match "
                f"release.{release_field}"
            )
    if url_without_query(automation.get("frontend_url")) != url_without_query(
        release.get("production_url")
    ):
        errors.append("automation frontend and release production URL differ")
    if url_without_query(automation.get("public_url")) != url_without_query(
        release.get("authoritative_result_url")
    ):
        errors.append("automation and release result URLs differ")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt")
    parser.add_argument("--manifest")
    parser.add_argument("--goal-state")
    parser.add_argument("--project-root")
    parser.add_argument("--require-automation", action="store_true")
    parser.add_argument("--require-release", action="store_true")
    parser.add_argument("--result-artifact")
    parser.add_argument("--source-manifest")
    parser.add_argument("--analysis-input")
    parser.add_argument("--analysis-input-validation")
    parser.add_argument("--analysis-request-manifest")
    parser.add_argument("--result-manifest")
    parser.add_argument("--public-pointer-before")
    parser.add_argument("--public-pointer-after")
    parser.add_argument("--publication-ordering-evidence")
    parser.add_argument("--publication-ordering-test-output")
    parser.add_argument("--public-result-body")
    parser.add_argument("--frontend-body")
    parser.add_argument("--frontend-binding-evidence")
    parser.add_argument("--frontend-dom-snapshot")
    parser.add_argument("--workflow-run-evidence")
    parser.add_argument("--release-run-evidence")
    parser.add_argument("--cost-evidence")
    parser.add_argument(
        "--allow-legacy-v1",
        action="store_true",
        help="Structural historical audit only; always exits non-zero",
    )
    args = parser.parse_args()

    path = Path(args.receipt).expanduser().resolve()
    try:
        loaded = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_nonfinite_json,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"EVIDENCE RECEIPT FAILED\n- invalid receipt: {exc}")
        return 2
    if not isinstance(loaded, dict):
        print("EVIDENCE RECEIPT FAILED\n- receipt root must be an object")
        return 2
    receipt: dict[str, Any] = loaded
    if receipt.get("schema_version") == 1:
        if not args.allow_legacy_v1:
            print(
                "EVIDENCE RECEIPT FAILED\n"
                "- legacy v1 is blocked; use --allow-legacy-v1 for a "
                "non-completion historical audit"
            )
            return 1
        print("HISTORICAL RECEIPT STRUCTURE ONLY")
        print("legacy_v1=historical-read-only-not-completion")
        return 3

    errors: list[str] = []
    if receipt.get("schema_version") != 2:
        errors.append("schema_version must equal 2")
    if not nonempty(receipt.get("project_id")):
        errors.append("project_id is required")
    if not nonempty(receipt.get("objective")):
        errors.append("objective is required")
    completed = parse_time(receipt.get("completed_at"))
    if completed is None:
        errors.append("completed_at must be timezone-aware ISO-8601")

    manifest = load_object(args.manifest, "manifest", errors)
    goal = load_object(args.goal_state, "goal state", errors)
    project_root: Path | None = None
    if not args.project_root:
        errors.append("schema v2 completion requires --project-root")
    else:
        project_root = Path(args.project_root).expanduser().resolve()
        if not project_root.is_dir():
            errors.append("project root does not exist")
    args.project_root_path = project_root
    if project_root is not None and args.manifest and manifest is not None:
        manifest_path = Path(args.manifest).expanduser().resolve()
        try:
            manifest_path.relative_to(project_root)
        except ValueError:
            errors.append("manifest must stay within project root")
        project_errors, _ = validate_project_contract(project_root, manifest)
        errors.extend(f"project contract: {error}" for error in project_errors)

    required = receipt.get("required_gates")
    gates = receipt.get("gates")
    if (
        not isinstance(required, list)
        or not required
        or not all(nonempty(name) for name in required)
        or len(required) != len(set(required))
    ):
        errors.append("required_gates must contain unique non-empty names")
        required = []
    if not isinstance(gates, dict):
        errors.append("gates must be an object")
        gates = {}

    validate_context(
        receipt,
        manifest,
        goal,
        force_automation=args.require_automation,
        force_release=args.require_release,
        errors=errors,
    )
    required_names = set(required)
    missing_base = sorted(V2_BASE_GATES - required_names)
    if missing_base:
        errors.append("required_gates missing: " + ", ".join(missing_base))

    scope = receipt.get("scope")
    automated = isinstance(scope, dict) and scope.get("automated_data_to_web") is True
    released = isinstance(scope, dict) and scope.get("remote_release") is True
    if automated:
        missing = sorted(V2_AUTOMATION_GATES - required_names)
        if missing:
            errors.append("automation gates missing: " + ", ".join(missing))
    if released:
        missing = sorted(V2_RELEASE_GATES - required_names)
        if missing:
            errors.append("release gates missing: " + ", ".join(missing))

    for name in required:
        gate = gates.get(name)
        if not isinstance(gate, dict):
            errors.append(f"required gate {name!r} is missing")
            continue
        if gate.get("status") != "passed":
            errors.append(f"required gate {name!r} must be passed")
        validate_generic_evidence(name, gate.get("evidence"), completed, errors)
    for name, gate in gates.items():
        if not isinstance(gate, dict):
            errors.append(f"gate {name!r} must be an object")
            continue
        if gate.get("status") not in {
            "pending",
            "passed",
            "failed",
            "blocked",
            "not_required",
        }:
            errors.append(f"gate {name!r} has an invalid status")
        if gate.get("status") == "passed" and name not in required:
            validate_generic_evidence(name, gate.get("evidence"), completed, errors)

    validate_cost(
        receipt,
        gates,
        manifest,
        goal,
        completed,
        args.cost_evidence,
        errors,
    )
    if automated:
        validate_automation(
            receipt,
            gates,
            manifest,
            completed,
            args,
            errors,
        )
    if released:
        validate_release(
            receipt,
            gates,
            manifest,
            completed,
            args,
            errors,
        )
    validate_cross_scope(receipt, errors)

    if errors:
        print("EVIDENCE RECEIPT FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("EVIDENCE RECEIPT PASSED")
    print(f"project_id={receipt['project_id']}")
    print("required_gates=" + ",".join(required))
    print("validation_scope=contract-identity-captured-bytes-cost-and-time")
    print(
        "provenance_note=provider authenticity depends on workflow-captured "
        "evidence supplied by the integration owner"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
