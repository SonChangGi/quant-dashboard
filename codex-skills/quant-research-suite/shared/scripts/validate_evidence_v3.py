#!/usr/bin/env python3
"""Validate capability-derived evidence receipt schema v3."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from capability_model import (
    ASSURANCE_LEVELS,
    ASSURANCE_RANK,
    CAPABILITY_GATES,
    CapabilityError,
    DELIVERY_LEVELS,
    PAID_TRANSITION_FIELDS,
    PROJECT_CAPABILITIES,
    RUNTIME_CAPABILITIES,
    ZERO_SPEND_POLICY,
    policy_violations,
    prohibited_paid_data_reasons,
    resolve,
)
from validate_project import validate as validate_project_contract


SHA256 = re.compile(r"^[0-9a-f]{64}$")
GATE_NAME = re.compile(r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$")
MAX_FUTURE_CLOCK_SKEW = timedelta(minutes=5)
TOP_LEVEL_FIELDS = {
    "$schema",
    "schema_version",
    "project_id",
    "objective",
    "scope",
    "required_gates",
    "gates",
    "cost_authority",
    "context",
    "goal_binding",
    "completed_at",
}
SCOPE_FIELDS = {
    "capabilities",
    "assurance",
    "delivery",
    "remote_actions",
    "analysis_control_ids",
}
COST_FIELDS = {
    "policy",
    "classification",
    "decision",
    "paid_action_requested",
    "actions",
}
COST_ACTION_FIELDS = {
    "action_id",
    "provider",
    "account_or_project",
    "resource_or_sku",
    "evidence_source",
    "evidence_checked_at",
    "classification",
    "decision",
    "billing_mode",
    "remaining_free_quota",
    "planned_usage",
    "hard_stop_enabled",
    "maximum_cost",
    *PAID_TRANSITION_FIELDS,
}
CONTEXT_FIELDS = {
    "manifest_sha256",
    "plan_sha256",
    "base_commit",
    "head_commit",
}
GOAL_BINDING_FIELDS = {
    "goal_id",
    "objective_sha256",
    "ledger_tail_sha256",
    "acceptance_ids",
    "acceptance_claims",
}
ACCEPTANCE_CLAIM_FIELDS = {
    "gate",
    "evidence_index",
    "evidence_sha256",
}
GATE_FIELDS = {"status", "evidence"}
EVIDENCE_FIELDS = {
    "kind",
    "status",
    "summary",
    "source",
    "checked_at",
    "command",
    "command_argv",
    "exit_code",
    "capture_sha256",
    "artifact_path",
    "artifact_sha256",
    "release_identity",
    "public_readback",
    "schedule_identity",
    "publication_identity",
    "data_identity",
    "extensions",
}
RELEASE_IDENTITY_FIELDS = {
    "provider",
    "target",
    "action",
    "account_or_project",
    "before_identity",
    "after_identity",
    "operation_id",
    "remote",
    "status",
}
PUBLIC_READBACK_FIELDS = {
    "url",
    "response_sha256",
    "response_size",
    "result_identity",
}
SCHEDULE_IDENTITY_FIELDS = {
    "schedule_id",
    "entrypoint_sha256",
    "declared_schedule",
    "timezone",
    "active_revision",
    "enabled",
    "cost_preflight_verified",
}
PUBLICATION_IDENTITY_FIELDS = {
    "target_id",
    "artifact_sha256",
    "published_identity",
    "ordering_verified",
    "last_good_preserved",
}
DATA_IDENTITY_FIELDS = {
    "source_ids",
    "artifact_sha256",
    "rights_checked",
    "collected_at",
    "source_as_of",
    "freshness_status",
}
INPUT_CAPTURE_FIELDS = {
    "$schema",
    "schema_version",
    "project_id",
    "generated_at",
    "analysis_entrypoint",
    "capture_driver",
    "controls",
}
INPUT_ENTRYPOINT_FIELDS = {"path", "sha256"}
INPUT_DRIVER_FIELDS = {
    "adapter_id",
    "tool",
    "tool_version",
    "runner_path",
    "runner_sha256",
    "runner_argv_index",
    "command_argv",
    "exit_code",
}
INPUT_CONTROL_FIELDS = {
    "control_id",
    "baseline",
    "repeat",
    "variant",
    "baseline_runtime",
    "variant_runtime",
}
INPUT_RUN_FIELDS = {
    "entrypoint_sha256",
    "input_path",
    "input_sha256",
    "result_path",
    "result_sha256",
    "invocation_artifact",
    "execution_trace_artifact",
    "run_id",
    "started_at",
    "completed_at",
    "exit_code",
}
RUNTIME_PHASE_FIELDS = {
    "capture_id",
    "session_id",
    "started_at",
    "control_committed_at",
    "dispatch_observed_at",
    "result_observed_at",
    "view_bound_at",
    "completed_at",
    "dispatch_artifact",
    "adopted_result_artifact",
    "view_artifact",
    "trace_artifact",
}
RUNTIME_ARTIFACT_FIELDS = {
    "path",
    "size",
    "sha256",
    "media_type",
}
INVOCATION_DOCUMENT_FIELDS = {
    "$schema",
    "schema_version",
    "project_id",
    "run_id",
    "entrypoint_path",
    "entrypoint_sha256",
    "input_path",
    "input_sha256",
    "result_path",
    "result_sha256",
    "started_at",
    "completed_at",
    "exit_code",
    "binding",
}
INVOCATION_BINDING_FIELDS = {
    "kind",
    "argv",
    "entrypoint_argv_index",
    "source_artifact",
}
EXECUTION_BINDING_KINDS = {
    "argv-option",
    "json-payload",
    "config-json",
}
TEAM_EVIDENCE_FIELDS = {
    "kind",
    "status",
    "summary",
    "source",
    "checked_at",
    "extensions",
}
TEAM_EXTENSION_FIELDS = {
    "schema_version",
    "team_run_id",
    "packet_sha256",
    "packet_file_sha256",
    "deliveries",
    "integration_receipt_sha256",
    "integration_file_sha256",
    "integration_owner",
    "project_binding_sha256",
    "current_workspace_sha256",
    "goal_binding",
    "integration_completed_at",
}
TEAM_DELIVERY_BINDING_FIELDS = {
    "assignment_id",
    "receipt_sha256",
    "file_sha256",
}
TEAM_GOAL_BINDING_FIELDS = {
    "goal_id",
    "plan_revision",
    "acceptance_revision",
    "workspace_sha256",
}
GOAL_LEDGER_EVIDENCE_FIELDS = {
    "goal_id",
    "workspace_sha256",
    "plan_revision",
    "acceptance_revision",
}
TEAM_EVIDENCE_SOURCE = "team_protocol.validate_integration"


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def reject_unknown_keys(
    value: dict[str, Any],
    allowed: set[str] | frozenset[str],
    label: str,
    errors: list[str],
) -> None:
    unknown = sorted(str(key) for key in set(value) - set(allowed))
    if unknown:
        errors.append(f"unknown {label} fields: " + ", ".join(unknown))


def unique_nonempty_strings(
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = True,
) -> list[str]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or not all(nonempty(item) for item in value)
    ):
        qualifier = "non-empty " if not allow_empty else ""
        errors.append(f"{label} must be a {qualifier}string array")
        return []
    normalized = [item.strip() for item in value]
    if len(normalized) != len(set(normalized)):
        errors.append(f"{label} must not contain duplicates")
        return []
    return normalized


def effective_delivery(
    assurance: Any,
    capabilities: Any,
    *,
    explicit: Any = None,
    remote_actions: Any = False,
) -> str:
    """Return the current delivery axis with legacy receipt compatibility."""

    if explicit in DELIVERY_LEVELS:
        return explicit
    scoped_capabilities = (
        capabilities if isinstance(capabilities, list) else []
    )
    if (
        assurance == "release"
        or "remote-release" in scoped_capabilities
        or remote_actions is True
    ):
        return "release"
    return "local"


def goal_state_delivery(state: dict[str, Any]) -> str:
    explicit = state.get("delivery")
    policy = state.get("proof_policy")
    capabilities = (
        policy.get("required_capabilities", [])
        if isinstance(policy, dict)
        else state.get("required_capabilities", [])
    )
    return effective_delivery(
        state.get("assurance"),
        capabilities,
        explicit=explicit,
    )


def valid_http_url(value: Any) -> bool:
    if not nonempty(value) or value != value.strip():
        return False
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and parsed.username is None
        and parsed.password is None
        and not any(character.isspace() for character in value)
    )


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256.fullmatch(value))


def git_value(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode:
        return None
    return completed.stdout.strip()


def parse_time(value: Any) -> datetime | None:
    if not nonempty(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def unique_json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def same_physical_file(left: Path, right: Path) -> bool:
    """Fail closed if identity cannot be re-read during validation."""

    try:
        return left.samefile(right)
    except OSError:
        return True


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


def load_json(path: Path) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise ValueError(f"non-finite JSON value is prohibited: {value}")

    loaded = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject,
        object_pairs_hook=unique_json_object,
    )
    if not isinstance(loaded, dict):
        raise ValueError("JSON root must be an object")
    return loaded


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def team_directory(
    value: Any,
    label: str,
    errors: list[str],
) -> Path | None:
    if not nonempty(value):
        errors.append(f"{label} is required")
        return None
    declared = Path(os.path.abspath(Path(value).expanduser()))
    if declared.is_symlink():
        errors.append(f"{label} must not be a symbolic link")
        return None
    try:
        resolved = declared.resolve(strict=True)
    except OSError as exc:
        errors.append(f"{label} is invalid: {exc}")
        return None
    if not resolved.is_dir():
        errors.append(f"{label} must be a directory")
        return None
    return resolved


def team_proof_file(
    value: Any,
    label: str,
    project_root: Path,
    allowed_roots: list[Path],
    errors: list[str],
) -> Path | None:
    """Resolve a proof file without permitting symlink traversal or escape."""

    if not nonempty(value):
        errors.append(f"{label} is required")
        return None
    raw = value.strip()
    supplied = Path(raw).expanduser()
    if "\\" in raw or ".." in supplied.parts:
        errors.append(f"{label} must not contain traversal syntax")
        return None
    declared = supplied if supplied.is_absolute() else project_root / supplied
    declared = Path(os.path.abspath(declared))
    if declared.is_symlink():
        errors.append(f"{label} must not be a symbolic link")
        return None
    try:
        resolved = declared.resolve(strict=True)
    except OSError as exc:
        errors.append(f"{label} is invalid: {exc}")
        return None
    if not resolved.is_file():
        errors.append(f"{label} must be a file")
        return None

    selected_root: Path | None = None
    for allowed_root in sorted(
        set(allowed_roots),
        key=lambda item: len(item.parts),
        reverse=True,
    ):
        if not path_is_within(resolved, allowed_root):
            continue
        lexical_root: Path | None = None
        for ancestor in [declared.parent, *declared.parents]:
            try:
                same_root = ancestor.resolve(strict=True) == allowed_root
            except OSError:
                same_root = False
            if same_root and not ancestor.is_symlink():
                lexical_root = ancestor
                break
        if lexical_root is None:
            errors.append(
                f"{label} reaches an allowed root through a symbolic-link alias"
            )
            return None
        relative = declared.relative_to(lexical_root)
        current = lexical_root
        for segment in relative.parts:
            current = current / segment
            if current.is_symlink():
                errors.append(
                    f"{label} traverses a symbolic-link component"
                )
                return None
        selected_root = allowed_root
        break
    if selected_root is None:
        errors.append(
            f"{label} must stay within the project, bound Goal state, "
            "or explicit team artifact root"
        )
        return None
    return resolved


def team_cli_requested(args: Any) -> bool:
    return any(
        (
            getattr(args, "team_packet", None),
            getattr(args, "team_delivery", None),
            getattr(args, "team_integration", None),
            getattr(args, "team_artifact_root", None),
            getattr(args, "team_workspace_root", None),
            getattr(args, "team_baseline_root", None),
            getattr(args, "team_worker_root", None),
        )
    )


def team_worker_directories(
    values: Any,
    errors: list[str],
) -> dict[str, Path]:
    if not isinstance(values, list):
        errors.append("--team-worker-root must be repeatable strings")
        return {}
    roots: dict[str, Path] = {}
    for index, value in enumerate(values):
        label = f"--team-worker-root[{index}]"
        if not nonempty(value) or "=" not in value:
            errors.append(
                f"{label} must use assignment-id=path"
            )
            continue
        assignment_id, path_value = value.split("=", 1)
        if not re.fullmatch(
            r"[a-z0-9][a-z0-9_-]{0,127}",
            assignment_id,
        ):
            errors.append(f"{label} assignment ID is invalid")
            continue
        if assignment_id in roots:
            errors.append(
                "--team-worker-root repeats assignment ID: "
                + assignment_id
            )
            continue
        root = team_directory(path_value, label, errors)
        if root is not None:
            roots[assignment_id] = root
    return roots


def project_file(
    root: Path,
    value: Any,
    label: str,
    errors: list[str],
) -> Path | None:
    if not nonempty(value):
        errors.append(f"{label} must be a non-empty project-relative path")
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "\\" in value:
        errors.append(f"{label} must stay within project root")
        return None
    if pure.as_posix() != value:
        errors.append(
            f"{label} must be a canonical project-relative path"
        )
        return None
    resolved = (root / value).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        errors.append(f"{label} resolves outside project root")
        return None
    if not resolved.is_file():
        errors.append(f"{label} does not exist: {value}")
        return None
    return resolved


def json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("JSON Pointer must be empty or begin with /")
    current = document
    for raw in pointer.split("/")[1:]:
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not token.isdigit():
                raise ValueError(f"array pointer token is not an index: {token}")
            index = int(token)
            if index >= len(current):
                raise ValueError(f"array pointer index is out of range: {token}")
            current = current[index]
        elif isinstance(current, dict):
            if token not in current:
                raise ValueError(f"JSON Pointer token is missing: {token}")
            current = current[token]
        else:
            raise ValueError(f"JSON Pointer crosses scalar at: {token}")
    return current


def json_values_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int equality coercion."""

    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return (
            set(left) == set(right)
            and all(
                json_values_equal(left[key], right[key])
                for key in left
            )
        )
    if isinstance(left, list):
        return (
            len(left) == len(right)
            and all(
                json_values_equal(left_item, right_item)
                for left_item, right_item in zip(left, right)
            )
        )
    return left == right


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def json_diff_pointers(
    baseline: Any,
    variant: Any,
    pointer: str = "",
) -> set[str]:
    """Return leaf-level JSON Pointers whose values differ."""

    if type(baseline) is not type(variant):
        return {pointer}
    if isinstance(baseline, dict):
        differences: set[str] = set()
        for key in sorted(set(baseline) | set(variant)):
            child = pointer + "/" + _pointer_token(str(key))
            if key not in baseline or key not in variant:
                differences.add(child)
            else:
                differences.update(
                    json_diff_pointers(
                        baseline[key],
                        variant[key],
                        child,
                    )
                )
        return differences
    if isinstance(baseline, list):
        differences = set()
        for index in range(max(len(baseline), len(variant))):
            child = pointer + f"/{index}"
            if index >= len(baseline) or index >= len(variant):
                differences.add(child)
            else:
                differences.update(
                    json_diff_pointers(
                        baseline[index],
                        variant[index],
                        child,
                    )
                )
        return differences
    return set() if json_values_equal(baseline, variant) else {pointer}


def pointer_is_within(pointer: str, allowed: str) -> bool:
    return pointer == allowed or pointer.startswith(allowed + "/")


def validate_evidence_items(
    gate_name: str,
    value: Any,
    completed: datetime,
    root: Path,
    errors: list[str],
) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"gate {gate_name!r} requires evidence")
        return
    for index, item in enumerate(value):
        label = f"gates.{gate_name}.evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        reject_unknown_keys(item, EVIDENCE_FIELDS, label, errors)
        if item.get("kind") not in {"command", "inspection", "artifact"}:
            errors.append(f"{label}.kind is invalid")
        if item.get("status") not in {"passed", "verified"}:
            errors.append(f"{label}.status must be passed or verified")
        for field in ("summary", "source"):
            if not nonempty(item.get(field)):
                errors.append(f"{label}.{field} is required")
            elif isinstance(item.get(field), str):
                errors.extend(
                    f"{label}.{field}: {reason}"
                    for reason in prohibited_paid_data_reasons(
                        item[field]
                    )
                )
        checked = parse_time(item.get("checked_at"))
        if checked is None:
            errors.append(f"{label}.checked_at must be timezone-aware")
        elif checked > completed:
            errors.append(f"{label}.checked_at is after receipt completion")
        if item.get("kind") == "command":
            if not nonempty(item.get("command")):
                errors.append(f"{label}.command is required")
            elif isinstance(item.get("command"), str):
                errors.extend(
                    f"{label}.command: {reason}"
                    for reason in prohibited_paid_data_reasons(
                        item["command"]
                    )
                )
            exit_code = item.get("exit_code")
            if not isinstance(exit_code, int) or isinstance(exit_code, bool):
                errors.append(f"{label}.exit_code must be an integer")
            elif exit_code != 0:
                errors.append(f"{label}.exit_code must be zero")
        if "command_argv" in item:
            command_argv = item.get("command_argv")
            if (
                not isinstance(command_argv, list)
                or not command_argv
                or not all(nonempty(value) for value in command_argv)
            ):
                errors.append(
                    f"{label}.command_argv must be a non-empty string array"
                )
        for field in ("capture_sha256", "artifact_sha256"):
            if field in item and not is_sha256(item.get(field)):
                errors.append(f"{label}.{field} must be SHA-256")
        if "artifact_path" in item and not nonempty(
            item.get("artifact_path")
        ):
            errors.append(f"{label}.artifact_path must be non-empty")
        artifact_path: Path | None = None
        if nonempty(item.get("artifact_path")):
            artifact_path = project_file(
                root,
                item["artifact_path"],
                f"{label}.artifact_path",
                errors,
            )
        if artifact_path is not None:
            actual_sha = sha256_bytes(artifact_path.read_bytes())
            if item.get("artifact_sha256") != actual_sha:
                errors.append(
                    f"{label}.artifact_sha256 does not match bytes"
                )
        elif "artifact_sha256" in item and "artifact_path" not in item:
            errors.append(
                f"{label}.artifact_sha256 requires artifact_path"
            )
        if "extensions" in item and not isinstance(
            item.get("extensions"), dict
        ):
            errors.append(f"{label}.extensions must be an object")


def validate_cost(
    receipt: dict[str, Any],
    remote_actions: bool,
    completed: datetime,
    errors: list[str],
) -> None:
    value = receipt.get("cost_authority")
    if not isinstance(value, dict):
        errors.append("cost_authority must be an object")
        return
    reject_unknown_keys(value, COST_FIELDS, "cost_authority", errors)
    if value.get("policy") != ZERO_SPEND_POLICY:
        errors.append("cost_authority.policy is invalid")
    if value.get("paid_action_requested") is not False:
        errors.append(
            "receipt v3 cannot manufacture or record paid-action authority"
        )
    actions = value.get("actions")
    if not isinstance(actions, list):
        errors.append("cost_authority.actions must be an array")
        return
    if not remote_actions:
        if value.get("classification") != "no_billable_action":
            errors.append(
                "local scope cost classification must be no_billable_action"
            )
        if value.get("decision") != "allow":
            errors.append("local scope cost decision must be allow")
        if actions:
            errors.append("local scope cannot contain remote/provider actions")
        return

    if value.get("classification") != "verified_zero_charge":
        errors.append(
            "remote scope requires verified_zero_charge classification"
        )
    if value.get("decision") != "allow":
        errors.append("remote scope cost decision must be allow")
    if not actions:
        errors.append("remote scope requires enumerated cost actions")
        return
    action_ids: list[str] = []
    for index, action in enumerate(actions):
        label = f"cost_authority.actions[{index}]"
        if not isinstance(action, dict):
            errors.append(f"{label} must be an object")
            continue
        reject_unknown_keys(action, COST_ACTION_FIELDS, label, errors)
        for field in (
            "action_id",
            "provider",
            "account_or_project",
            "resource_or_sku",
            "evidence_source",
            "billing_mode",
        ):
            if not nonempty(action.get(field)):
                errors.append(f"{label}.{field} is required")
        if nonempty(action.get("action_id")):
            action_ids.append(action["action_id"].strip())
        if action.get("classification") != "verified_zero_charge":
            errors.append(f"{label}.classification must be verified_zero_charge")
        if action.get("decision") != "allow":
            errors.append(f"{label}.decision must be allow")
        if action.get("hard_stop_enabled") is not True:
            errors.append(f"{label}.hard_stop_enabled must be true")
        maximum_cost = action.get("maximum_cost")
        if (
            not isinstance(maximum_cost, (int, float))
            or isinstance(maximum_cost, bool)
            or not math.isfinite(maximum_cost)
            or maximum_cost != 0
        ):
            errors.append(f"{label}.maximum_cost must equal zero")
        checked = parse_time(action.get("evidence_checked_at"))
        if checked is None:
            errors.append(
                f"{label}.evidence_checked_at must be timezone-aware"
            )
        elif checked > completed:
            errors.append(
                f"{label}.evidence_checked_at is after completion"
            )
        if action.get("billing_mode") != "hard-free-no-overage":
            errors.append(
                f"{label}.billing_mode must be hard-free-no-overage"
            )
        remaining = action.get("remaining_free_quota")
        planned = action.get("planned_usage")
        for field, number in (
            ("remaining_free_quota", remaining),
            ("planned_usage", planned),
        ):
            if (
                not isinstance(number, (int, float))
                or isinstance(number, bool)
                or not math.isfinite(number)
                or number < 0
            ):
                errors.append(
                    f"{label}.{field} must be a finite non-negative number"
                )
        if (
            isinstance(remaining, (int, float))
            and not isinstance(remaining, bool)
            and isinstance(planned, (int, float))
            and not isinstance(planned, bool)
            and math.isfinite(remaining)
            and math.isfinite(planned)
            and planned > remaining
        ):
            errors.append(f"{label}.planned_usage exceeds free quota")
        for field in PAID_TRANSITION_FIELDS:
            if action.get(field) is not False:
                errors.append(f"{label}.{field} must be false")
    if len(action_ids) != len(set(action_ids)):
        errors.append("cost_authority action_id values must be unique")


def control_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    configs = manifest.get("capability_config")
    binding = (
        configs.get("analysis-input-binding")
        if isinstance(configs, dict)
        else None
    )
    controls = binding.get("controls") if isinstance(binding, dict) else None
    if not isinstance(controls, list):
        return {}
    return {
        item["id"]: item
        for item in controls
        if isinstance(item, dict) and nonempty(item.get("id"))
    }


def capture_item_files(
    root: Path,
    item: dict[str, Any],
    label: str,
    completed: datetime,
    errors: list[str],
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
    str,
    str,
    datetime | None,
    Path | None,
    Path | None,
]:
    reject_unknown_keys(item, INPUT_RUN_FIELDS, label, errors)
    if item.get("exit_code") != 0:
        errors.append(f"{label}.exit_code must equal zero")
    started = parse_time(item.get("started_at"))
    ended = parse_time(item.get("completed_at"))
    if started is None or ended is None:
        errors.append(f"{label} timestamps must be timezone-aware")
    elif not started <= ended <= completed:
        errors.append(f"{label} timestamps are outside the valid interval")
    input_path = project_artifact_file(
        root, item.get("input_path"), f"{label}.input_path", errors
    )
    result_path = project_artifact_file(
        root, item.get("result_path"), f"{label}.result_path", errors
    )
    input_value: dict[str, Any] | None = None
    result_value: dict[str, Any] | None = None
    input_sha = ""
    result_sha = ""
    if input_path is not None:
        input_sha = sha256_bytes(input_path.read_bytes())
        if item.get("input_sha256") != input_sha:
            errors.append(f"{label}.input_sha256 does not match bytes")
        try:
            input_value = load_json(input_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{label}.input_path is invalid JSON: {exc}")
    if result_path is not None:
        result_sha = sha256_bytes(result_path.read_bytes())
        if item.get("result_sha256") != result_sha:
            errors.append(f"{label}.result_sha256 does not match bytes")
        try:
            result_value = load_json(result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{label}.result_path is invalid JSON: {exc}")
    if not nonempty(item.get("run_id")):
        errors.append(f"{label}.run_id is required")
    return (
        input_value,
        result_value,
        input_sha,
        result_sha,
        ended,
        input_path,
        result_path,
    )


def project_artifact_file(
    root: Path,
    value: Any,
    label: str,
    errors: list[str],
) -> Path | None:
    path = project_file(root, value, label, errors)
    if path is None or not nonempty(value):
        return None
    current = root
    for part in PurePosixPath(value).parts:
        current = current / part
        if current.is_symlink():
            errors.append(f"{label} must not contain a symlink component")
            return None
    if not path.is_file():
        errors.append(f"{label} must identify a regular file")
        return None
    return path


def runtime_artifact(
    root: Path,
    value: Any,
    label: str,
    errors: list[str],
    *,
    require_json: bool,
) -> tuple[Path | None, bytes | None, dict[str, Any] | None]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return None, None, None
    reject_unknown_keys(value, RUNTIME_ARTIFACT_FIELDS, label, errors)
    path = project_artifact_file(
        root,
        value.get("path"),
        f"{label}.path",
        errors,
    )
    expected_size = value.get("size")
    if (
        not isinstance(expected_size, int)
        or isinstance(expected_size, bool)
        or expected_size < 1
    ):
        errors.append(f"{label}.size must be a positive integer")
    if not is_sha256(value.get("sha256")):
        errors.append(f"{label}.sha256 must be lowercase SHA-256")
    if not nonempty(value.get("media_type")):
        errors.append(f"{label}.media_type must be a non-empty string")
    if require_json and value.get("media_type") != "application/json":
        errors.append(f"{label}.media_type must equal application/json")
    if path is None:
        return None, None, None
    content = path.read_bytes()
    if expected_size != len(content):
        errors.append(f"{label}.size does not match bytes")
    if value.get("sha256") != sha256_bytes(content):
        errors.append(f"{label}.sha256 does not match bytes")
    document: dict[str, Any] | None = None
    if require_json:
        try:
            document = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{label}.path is invalid JSON: {exc}")
    return path, content, document


def decoded_argv_binding(
    argv: Any,
    locator: Any,
    label: str,
    errors: list[str],
) -> tuple[bool, Any]:
    if (
        not isinstance(argv, list)
        or not argv
        or not all(nonempty(value) for value in argv)
    ):
        errors.append(f"{label}.argv must be a non-empty string array")
        return False, None
    if (
        not nonempty(locator)
        or not locator.startswith("--")
        or locator == "--"
    ):
        errors.append(f"{label} manifest argv locator is invalid")
        return False, None
    candidates: list[str] = []
    for index, token in enumerate(argv):
        if token == locator:
            if index + 1 >= len(argv):
                errors.append(f"{label}.argv option has no value")
                continue
            candidates.append(argv[index + 1])
        elif token.startswith(locator + "="):
            candidates.append(token[len(locator) + 1 :])
    if len(candidates) != 1:
        errors.append(
            f"{label}.argv must contain the declared option exactly once"
        )
        return False, None
    raw_value = candidates[0]
    try:
        return True, json.loads(raw_value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return True, raw_value


def validate_invocation_document(
    *,
    document: Any,
    source_document: dict[str, Any] | None,
    run: dict[str, Any],
    input_value: dict[str, Any],
    input_sha: str,
    result_sha: str,
    definition: dict[str, Any],
    entrypoint: dict[str, Any],
    receipt: dict[str, Any],
    label: str,
    errors: list[str],
) -> tuple[bool, Any]:
    initial_error_count = len(errors)
    if not isinstance(document, dict):
        errors.append(f"{label} must contain a JSON object")
        return False, None
    reject_unknown_keys(
        document,
        INVOCATION_DOCUMENT_FIELDS,
        label,
        errors,
    )
    expected_fields = {
        "schema_version": 1,
        "project_id": receipt.get("project_id"),
        "run_id": run.get("run_id"),
        "entrypoint_path": entrypoint.get("path"),
        "entrypoint_sha256": run.get("entrypoint_sha256"),
        "input_path": run.get("input_path"),
        "input_sha256": input_sha,
        "result_path": run.get("result_path"),
        "result_sha256": result_sha,
        "exit_code": 0,
    }
    for field, expected in expected_fields.items():
        if not json_values_equal(document.get(field), expected):
            errors.append(f"{label}.{field} does not match the authoritative run")

    run_started = parse_time(run.get("started_at"))
    run_completed = parse_time(run.get("completed_at"))
    invocation_started = parse_time(document.get("started_at"))
    invocation_completed = parse_time(document.get("completed_at"))
    if (
        run_started is None
        or run_completed is None
        or invocation_started is None
        or invocation_completed is None
    ):
        errors.append(f"{label} timestamps must be timezone-aware")
    elif not (
        run_started
        <= invocation_started
        <= invocation_completed
        <= run_completed
    ):
        errors.append(
            f"{label} timestamps must stay within the authoritative run"
        )

    execution_binding = definition.get("execution_binding")
    if not isinstance(execution_binding, dict):
        errors.append(f"{label} manifest execution_binding is missing")
        return False, None
    expected_kind = execution_binding.get("kind")
    locator = execution_binding.get("locator")
    binding = document.get("binding")
    if not isinstance(binding, dict):
        errors.append(f"{label}.binding must be an object")
        return False, None
    reject_unknown_keys(
        binding,
        INVOCATION_BINDING_FIELDS,
        f"{label}.binding",
        errors,
    )
    kind = binding.get("kind")
    if kind != expected_kind or kind not in EXECUTION_BINDING_KINDS:
        errors.append(
            f"{label}.binding.kind does not match the manifest execution kind"
        )
        return False, None

    argv = binding.get("argv")
    entrypoint_argv_index = binding.get("entrypoint_argv_index")
    if (
        not isinstance(argv, list)
        or not argv
        or not all(nonempty(value) for value in argv)
    ):
        errors.append(f"{label}.binding.argv must be a non-empty string array")
    if (
        not isinstance(entrypoint_argv_index, int)
        or isinstance(entrypoint_argv_index, bool)
        or entrypoint_argv_index < 0
        or not isinstance(argv, list)
        or entrypoint_argv_index >= len(argv)
    ):
        errors.append(
            f"{label}.binding.entrypoint_argv_index is outside argv"
        )
    elif argv[entrypoint_argv_index] != entrypoint.get("path"):
        errors.append(
            f"{label}.binding argv does not invoke analysis_entrypoint.path"
        )

    extracted = False
    executed_value: Any = None
    if kind == "argv-option":
        if "source_artifact" in binding:
            errors.append(
                f"{label}.binding.source_artifact is invalid for argv-option"
            )
        extracted, executed_value = decoded_argv_binding(
            argv,
            locator,
            f"{label}.binding",
            errors,
        )
    else:
        if not isinstance(binding.get("source_artifact"), dict):
            errors.append(
                f"{label}.binding.source_artifact is required for {kind}"
            )
        elif source_document is None:
            errors.append(
                f"{label}.binding source artifact is not valid JSON"
            )
        elif not isinstance(locator, str):
            errors.append(f"{label} manifest JSON locator is invalid")
        else:
            try:
                executed_value = json_pointer(source_document, locator)
                extracted = True
            except (KeyError, ValueError) as exc:
                errors.append(
                    f"{label}.binding locator extraction failed: {exc}"
                )

    try:
        canonical_value = json_pointer(
            input_value,
            definition["input_pointer"],
        )
    except (KeyError, ValueError) as exc:
        errors.append(f"{label} canonical input pointer failed: {exc}")
        extracted = False
        canonical_value = None
    if extracted and not json_values_equal(executed_value, canonical_value):
        errors.append(
            f"{label} executed parameter does not match canonical input"
        )
    return len(errors) == initial_error_count and extracted, executed_value


def matching_runtime_evidence(
    evidence: Any,
    artifact: dict[str, Any],
    driver: dict[str, Any],
    runtime_completed: datetime | None,
    capture_generated: datetime | None,
) -> bool:
    if not isinstance(evidence, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("kind") == "command"
        and item.get("status") in {"passed", "verified"}
        and item.get("artifact_path") == artifact.get("path")
        and item.get("artifact_sha256") == artifact.get("sha256")
        and item.get("source") == driver.get("adapter_id")
        and nonempty(item.get("command"))
        and item.get("command_argv") == driver.get("command_argv")
        and item.get("exit_code") == 0
        and (checked := parse_time(item.get("checked_at"))) is not None
        and runtime_completed is not None
        and capture_generated is not None
        and runtime_completed <= checked <= capture_generated
        for item in evidence
    )


def matching_analysis_execution_evidence(
    evidence: Any,
    trace_artifact: Any,
    invocation: Any,
    capture_generated: datetime | None,
) -> bool:
    """Bind a run to a separately captured command trace and identity."""

    if (
        not isinstance(evidence, list)
        or not isinstance(trace_artifact, dict)
        or not isinstance(invocation, dict)
    ):
        return False
    binding = invocation.get("binding")
    argv = binding.get("argv") if isinstance(binding, dict) else None
    completed = parse_time(invocation.get("completed_at"))
    expected_identity = {
        "run_id": invocation.get("run_id"),
        "entrypoint_sha256": invocation.get("entrypoint_sha256"),
        "input_sha256": invocation.get("input_sha256"),
        "result_sha256": invocation.get("result_sha256"),
    }
    if (
        not isinstance(argv, list)
        or not argv
        or completed is None
        or capture_generated is None
    ):
        return False
    for item in evidence:
        if not isinstance(item, dict):
            continue
        extensions = item.get("extensions")
        identity = (
            extensions.get("analysis_execution")
            if isinstance(extensions, dict)
            else None
        )
        checked = parse_time(item.get("checked_at"))
        if (
            item.get("kind") == "command"
            and item.get("status") in {"passed", "verified"}
            and item.get("artifact_path") == trace_artifact.get("path")
            and item.get("artifact_sha256") == trace_artifact.get("sha256")
            and item.get("source") == invocation.get("entrypoint_path")
            and item.get("command") == argv[0]
            and json_values_equal(item.get("command_argv"), argv)
            and json_values_equal(item.get("exit_code"), 0)
            and json_values_equal(identity, expected_identity)
            and checked is not None
            and completed <= checked <= capture_generated
        ):
            return True
    return False


def validate_runtime_phase(
    *,
    root: Path,
    phase: str,
    runtime: Any,
    run: dict[str, Any],
    input_value: dict[str, Any],
    result_value: dict[str, Any],
    result_sha: str,
    effective_value: Any,
    executed_value: Any,
    executed_value_valid: bool,
    definition: dict[str, Any],
    receipt: dict[str, Any],
    driver: dict[str, Any],
    gate_evidence: Any,
    generated: datetime | None,
    completed: datetime,
    used_capture_ids: set[str],
    used_session_ids: set[str],
    used_artifact_paths: list[Path],
    errors: list[str],
) -> None:
    label = f"runtime {definition.get('id')} {phase}"
    if not isinstance(runtime, dict):
        errors.append(f"{label} must be an object")
        return
    reject_unknown_keys(runtime, RUNTIME_PHASE_FIELDS, label, errors)
    for field, used in (
        ("capture_id", used_capture_ids),
        ("session_id", used_session_ids),
    ):
        value = runtime.get(field)
        if not nonempty(value):
            errors.append(f"{label}.{field} must be a non-empty string")
        elif value in used:
            errors.append(f"{label}.{field} must be unique")
        else:
            used.add(value)

    times = {
        field: parse_time(runtime.get(field))
        for field in (
            "started_at",
            "control_committed_at",
            "dispatch_observed_at",
            "result_observed_at",
            "view_bound_at",
            "completed_at",
        )
    }
    if any(value is None for value in times.values()):
        errors.append(f"{label} timestamps must be timezone-aware")
    run_started = parse_time(run.get("started_at"))
    run_completed = parse_time(run.get("completed_at"))
    sequence = [
        times["started_at"],
        times["control_committed_at"],
        times["dispatch_observed_at"],
        run_started,
        run_completed,
        times["result_observed_at"],
        times["view_bound_at"],
        times["completed_at"],
        generated,
        completed,
    ]
    if all(value is not None for value in sequence) and any(
        earlier > later
        for earlier, later in zip(sequence, sequence[1:])
    ):
        errors.append(f"{label} timestamps are out of causal order")

    artifacts: dict[str, tuple[Path | None, bytes | None, Any]] = {}
    for field, require_json in (
        ("dispatch_artifact", True),
        ("adopted_result_artifact", True),
        ("view_artifact", True),
        ("trace_artifact", False),
    ):
        spec = runtime.get(field)
        artifacts[field] = runtime_artifact(
            root,
            spec,
            f"{label}.{field}",
            errors,
            require_json=require_json,
        )
        artifact_path = artifacts[field][0]
        if artifact_path is not None:
            if any(
                same_physical_file(artifact_path, existing)
                for existing in used_artifact_paths
            ):
                errors.append(
                    f"{label}.{field}.path must not reuse a reserved or "
                    "runtime artifact"
                )
            else:
                used_artifact_paths.append(artifact_path)

    contract = definition.get("runtime_binding_contract")
    if not isinstance(contract, dict):
        errors.append(f"{label} manifest runtime binding contract is missing")
        return
    dispatch = artifacts["dispatch_artifact"][2]
    if dispatch is not None:
        dispatch_pointer = contract.get("dispatch_input_pointer")
        if not isinstance(dispatch_pointer, str):
            errors.append(f"{label} dispatch input pointer is invalid")
            dispatch_pointer = ""
        try:
            observed_input = json_pointer(dispatch, dispatch_pointer)
            if not json_values_equal(observed_input, input_value):
                errors.append(
                    f"{label} dispatched canonical input does not match run input"
                )
            if executed_value_valid:
                dispatched_value = json_pointer(
                    observed_input,
                    definition["input_pointer"],
                )
                if not json_values_equal(dispatched_value, executed_value):
                    errors.append(
                        f"{label} UI dispatch value does not match the "
                        "authoritative executed parameter"
                    )
        except (KeyError, ValueError) as exc:
            errors.append(f"{label} dispatch pointer failed: {exc}")
        execution_binding = definition.get("execution_binding")
        execution_locator = (
            execution_binding.get("locator")
            if isinstance(execution_binding, dict)
            else None
        )
        dispatch_contract_values = {
            "dispatch_frontend_field_pointer": definition.get(
                "frontend_field"
            ),
            "dispatch_canonical_field_pointer": definition.get(
                "canonical_field"
            ),
            "dispatch_execution_mapping_pointer": definition.get(
                "execution_mapping"
            ),
            "dispatch_entrypoint_sha256_pointer": run.get(
                "entrypoint_sha256"
            ),
        }
        dispatch_contract_values[
            "dispatch_execution_mapping_pointer"
        ] = execution_locator
        for pointer_field, expected_value in dispatch_contract_values.items():
            pointer = contract.get(pointer_field)
            if not isinstance(pointer, str):
                errors.append(f"{label} {pointer_field} is invalid")
                continue
            try:
                if not json_values_equal(
                    json_pointer(dispatch, pointer), expected_value
                ):
                    errors.append(
                        f"{label} dispatch value at {pointer_field} does not "
                        "match the manifest/run contract"
                    )
            except (KeyError, ValueError) as exc:
                errors.append(f"{label} dispatch contract pointer failed: {exc}")

    adopted_path, adopted_bytes, _ = artifacts[
        "adopted_result_artifact"
    ]
    authoritative_path = project_artifact_file(
        root,
        run.get("result_path"),
        f"{label}.authoritative_result_path",
        errors,
    )
    if (
        adopted_path is not None
        and authoritative_path is not None
        and same_physical_file(adopted_path, authoritative_path)
    ):
        errors.append(
            f"{label} adopted result must be an independent runtime capture"
        )
    if authoritative_path is not None and adopted_bytes is not None:
        if adopted_bytes != authoritative_path.read_bytes():
            errors.append(
                f"{label} adopted result is not byte-identical to authoritative "
                "result"
            )

    view = artifacts["view_artifact"][2]
    if view is not None:
        expected = {
            "view_control_field_pointer": definition.get("frontend_field"),
            "view_applied_value_pointer": effective_value,
            "view_binding_status_pointer": "bound",
            "view_project_id_pointer": receipt.get("project_id"),
            "view_run_id_pointer": run.get("run_id"),
            "view_result_sha256_pointer": result_sha,
        }
        for pointer_field, expected_value in expected.items():
            pointer = contract.get(pointer_field)
            if not isinstance(pointer, str):
                errors.append(f"{label} {pointer_field} is invalid")
                continue
            try:
                observed = json_pointer(view, pointer)
                if not json_values_equal(observed, expected_value):
                    errors.append(
                        f"{label} view value at {pointer_field} does not match"
                    )
            except (KeyError, ValueError) as exc:
                errors.append(f"{label} view pointer failed: {exc}")
        try:
            result_values_pointer = contract.get(
                "view_result_values_pointer"
            )
            if not isinstance(result_values_pointer, str):
                raise ValueError("view_result_values_pointer is invalid")
            observed_values = json_pointer(
                view, result_values_pointer
            )
            raw_result_paths = definition.get("result_paths", [])
            result_paths = (
                raw_result_paths
                if isinstance(raw_result_paths, list)
                and all(isinstance(value, str) for value in raw_result_paths)
                else []
            )
            if not isinstance(observed_values, dict) or set(
                observed_values
            ) != set(result_paths):
                errors.append(
                    f"{label} view result values must exactly cover result_paths"
                )
            else:
                for pointer in result_paths:
                    if not json_values_equal(
                        observed_values[pointer],
                        json_pointer(result_value, pointer),
                    ):
                        errors.append(
                            f"{label} view result value {pointer!r} does not "
                            "match authoritative result"
                        )
        except (KeyError, ValueError) as exc:
            errors.append(f"{label} view result pointer failed: {exc}")

    trace = runtime.get("trace_artifact")
    if not isinstance(trace, dict) or not matching_runtime_evidence(
        gate_evidence,
        trace,
        driver,
        times.get("completed_at"),
        generated,
    ):
        errors.append(
            f"{label} trace must be bound to passed runtime_trace evidence"
        )


def validate_input_binding_capture(
    receipt: dict[str, Any],
    manifest: dict[str, Any],
    manifest_path: Path,
    root: Path,
    capture_path_value: str | None,
    completed: datetime,
    assurance: str,
    errors: list[str],
) -> None:
    scope = receipt["scope"]
    scoped_ids = unique_nonempty_strings(
        scope.get("analysis_control_ids"),
        "analysis-input-binding scope analysis_control_ids",
        errors,
        allow_empty=False,
    )
    if not scoped_ids:
        return
    controls = control_map(manifest)
    capability_config = manifest.get("capability_config")
    raw_analysis_config = (
        capability_config.get("analysis")
        if isinstance(capability_config, dict)
        else {}
    )
    analysis_config = (
        raw_analysis_config
        if isinstance(raw_analysis_config, dict)
        else {}
    )
    result_identity_pointers = (
        analysis_config.get("result_identity_pointers", [])
    )
    if not (
        isinstance(result_identity_pointers, list)
        and all(
            isinstance(pointer, str)
            for pointer in result_identity_pointers
        )
    ):
        result_identity_pointers = []
    missing_manifest = sorted(set(scoped_ids) - set(controls))
    if missing_manifest:
        errors.append(
            "analysis controls are not declared by the manifest: "
            + ", ".join(missing_manifest)
        )
    if assurance == "release":
        missing_scope = sorted(set(controls) - set(scoped_ids))
        if missing_scope:
            errors.append(
                "release input-binding scope must include every analysis "
                "control: " + ", ".join(missing_scope)
            )
    if not capture_path_value:
        errors.append(
            "analysis-input-binding completion requires --input-binding-capture"
        )
        return
    capture_candidate = Path(capture_path_value).expanduser()
    if capture_candidate.is_symlink():
        errors.append("input-binding capture must not be a symlink")
        return
    capture_path = capture_candidate.resolve()
    try:
        capture_path.relative_to(root)
    except ValueError:
        errors.append("input-binding capture must stay within project root")
        return
    if not capture_path.is_file():
        errors.append("input-binding capture does not exist")
        return
    try:
        capture = load_json(capture_path)
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        json.JSONDecodeError,
    ) as exc:
        errors.append(f"invalid input-binding capture: {exc}")
        return
    reject_unknown_keys(
        capture,
        INPUT_CAPTURE_FIELDS,
        "input-binding capture",
        errors,
    )
    errors.extend(
        policy_violations(capture, "input-binding capture")
    )
    capture_sha = sha256_bytes(capture_path.read_bytes())
    gate = receipt.get("gates", {}).get("input_binding", {})
    evidence = gate.get("evidence") if isinstance(gate, dict) else None
    capture_relative = capture_path.relative_to(root).as_posix()
    if not isinstance(evidence, list) or not any(
        isinstance(item, dict)
        and item.get("capture_sha256") == capture_sha
        and item.get("artifact_path") == capture_relative
        and item.get("artifact_sha256") == capture_sha
        and item.get("status") in {"passed", "verified"}
        for item in evidence
    ):
        errors.append(
            "input_binding evidence must bind the capture path and SHA-256"
        )
    if capture.get("schema_version") != 2:
        errors.append("input-binding capture schema_version must equal 2")
    if capture.get("project_id") != receipt.get("project_id"):
        errors.append("input-binding capture project_id mismatch")
    generated = parse_time(capture.get("generated_at"))
    if generated is None or generated > completed:
        errors.append(
            "input-binding capture generated_at must precede completion"
        )
    binding_config = manifest.get("capability_config", {}).get(
        "analysis-input-binding", {}
    )
    maximum_age_seconds = (
        binding_config.get("maximum_capture_age_seconds", 86400)
        if isinstance(binding_config, dict)
        else 86400
    )
    if (
        generated is not None
        and generated <= completed
        and isinstance(maximum_age_seconds, int)
        and not isinstance(maximum_age_seconds, bool)
        and maximum_age_seconds > 0
        and completed - generated
        > timedelta(seconds=maximum_age_seconds)
    ):
        errors.append(
            "input-binding capture is older than "
            "maximum_capture_age_seconds"
        )

    entrypoint_path: Path | None = None
    entrypoint = capture.get("analysis_entrypoint")
    if not isinstance(entrypoint, dict):
        errors.append("input-binding capture analysis_entrypoint is required")
    else:
        reject_unknown_keys(
            entrypoint,
            INPUT_ENTRYPOINT_FIELDS,
            "analysis_entrypoint",
            errors,
        )
        entrypoint_path = project_artifact_file(
            root,
            entrypoint.get("path"),
            "analysis_entrypoint.path",
            errors,
        )
        authoritative = analysis_config.get("authoritative_entrypoints", [])
        if entrypoint.get("path") not in authoritative:
            errors.append(
                "capture entrypoint is not authoritative in the manifest"
            )
        if entrypoint_path is not None and entrypoint.get(
            "sha256"
        ) != sha256_bytes(entrypoint_path.read_bytes()):
            errors.append("analysis_entrypoint.sha256 does not match bytes")

    runner_path: Path | None = None
    driver = capture.get("capture_driver")
    if not isinstance(driver, dict):
        errors.append("input-binding capture capture_driver is required")
        driver = {}
    else:
        reject_unknown_keys(
            driver,
            INPUT_DRIVER_FIELDS,
            "capture_driver",
            errors,
        )
        for field in ("adapter_id", "tool", "tool_version"):
            if not nonempty(driver.get(field)):
                errors.append(f"capture_driver.{field} is required")
        argv = driver.get("command_argv")
        if (
            not isinstance(argv, list)
            or not argv
            or not all(nonempty(value) for value in argv)
        ):
            errors.append(
                "capture_driver.command_argv must be a non-empty string array"
            )
        runner_argv_index = driver.get("runner_argv_index")
        if (
            not isinstance(runner_argv_index, int)
            or isinstance(runner_argv_index, bool)
            or runner_argv_index != 0
        ):
            errors.append(
                "capture_driver.runner_argv_index must equal zero for direct "
                "runner execution"
            )
        elif (
            isinstance(argv, list)
            and argv
            and all(isinstance(value, str) for value in argv)
            and argv[0] != driver.get("runner_path")
        ):
            errors.append(
                "capture_driver command_argv must directly execute runner_path"
            )
        if driver.get("exit_code") != 0:
            errors.append("capture_driver.exit_code must equal zero")
        runner_path = project_artifact_file(
            root,
            driver.get("runner_path"),
            "capture_driver.runner_path",
            errors,
        )
        if runner_path is not None and driver.get(
            "runner_sha256"
        ) != sha256_bytes(runner_path.read_bytes()):
            errors.append("capture_driver.runner_sha256 does not match bytes")
        if runner_path is not None and not os.access(runner_path, os.X_OK):
            errors.append("capture_driver.runner_path must be executable")

    captured_controls = capture.get("controls")
    if not isinstance(captured_controls, list):
        errors.append("input-binding capture controls must be an array")
        return
    raw_captured_ids = [
        item.get("control_id")
        for item in captured_controls
        if isinstance(item, dict)
    ]
    captured_ids = unique_nonempty_strings(
        raw_captured_ids,
        "input-binding capture control IDs",
        errors,
    )
    if set(captured_ids) != set(scoped_ids):
        errors.append(
            "input-binding capture controls must exactly match scoped controls"
        )

    used_capture_ids: set[str] = set()
    used_session_ids: set[str] = set()
    used_artifact_paths: list[Path] = [
        capture_path,
        manifest_path,
        *(
            [entrypoint_path]
            if entrypoint_path is not None
            else []
        ),
        *([runner_path] if runner_path is not None else []),
    ]
    for item_index, captured_item in enumerate(captured_controls):
        if not isinstance(captured_item, dict):
            continue
        for phase in ("baseline", "repeat", "variant"):
            run_item = captured_item.get(phase)
            if not isinstance(run_item, dict):
                continue
            for path_field in ("input_path", "result_path"):
                reservation_errors: list[str] = []
                reserved_path = project_artifact_file(
                    root,
                    run_item.get(path_field),
                    (
                        f"capture.controls[{item_index}].{phase}."
                        f"{path_field}"
                    ),
                    reservation_errors,
                )
                if reserved_path is not None:
                    if any(
                        same_physical_file(reserved_path, existing)
                        for existing in used_artifact_paths
                    ):
                        errors.append(
                            f"capture.controls[{item_index}].{phase}."
                            f"{path_field} must not reuse a reserved or "
                            "authoritative run artifact"
                        )
                    else:
                        used_artifact_paths.append(reserved_path)
    invocation_records: dict[
        tuple[int, str],
        tuple[
            dict[str, Any] | None,
            dict[str, Any] | None,
            dict[str, Any] | None,
        ],
    ] = {}
    for item_index, captured_item in enumerate(captured_controls):
        if not isinstance(captured_item, dict):
            continue
        for phase in ("baseline", "repeat", "variant"):
            run_item = captured_item.get(phase)
            if not isinstance(run_item, dict):
                continue
            invocation_label = (
                f"capture.controls[{item_index}].{phase}."
                "invocation_artifact"
            )
            invocation_spec = run_item.get("invocation_artifact")
            invocation_path, _invocation_bytes, invocation_document = (
                runtime_artifact(
                    root,
                    invocation_spec,
                    invocation_label,
                    errors,
                    require_json=True,
                )
            )
            if invocation_path is not None:
                if any(
                    same_physical_file(invocation_path, existing)
                    for existing in used_artifact_paths
                ):
                    errors.append(
                        f"{invocation_label}.path must not reuse a reserved "
                        "or invocation artifact"
                    )
                else:
                    used_artifact_paths.append(invocation_path)
            source_document: dict[str, Any] | None = None
            binding = (
                invocation_document.get("binding")
                if isinstance(invocation_document, dict)
                else None
            )
            source_spec = (
                binding.get("source_artifact")
                if isinstance(binding, dict)
                else None
            )
            if source_spec is not None:
                source_label = f"{invocation_label}.binding.source_artifact"
                source_path, _source_bytes, source_document = runtime_artifact(
                    root,
                    source_spec,
                    source_label,
                    errors,
                    require_json=True,
                )
                if source_path is not None:
                    if any(
                        same_physical_file(source_path, existing)
                        for existing in used_artifact_paths
                    ):
                        errors.append(
                            f"{source_label}.path must not reuse a reserved "
                            "or invocation artifact"
                        )
                    else:
                        used_artifact_paths.append(source_path)
            trace_spec = run_item.get("execution_trace_artifact")
            trace_label = (
                f"capture.controls[{item_index}].{phase}."
                "execution_trace_artifact"
            )
            trace_path, _trace_bytes, _trace_document = runtime_artifact(
                root,
                trace_spec,
                trace_label,
                errors,
                require_json=False,
            )
            if trace_path is not None:
                if any(
                    same_physical_file(trace_path, existing)
                    for existing in used_artifact_paths
                ):
                    errors.append(
                        f"{trace_label}.path must not reuse a reserved or "
                        "execution artifact"
                    )
                else:
                    used_artifact_paths.append(trace_path)
            invocation_records[(item_index, phase)] = (
                invocation_document,
                source_document,
                trace_spec if isinstance(trace_spec, dict) else None,
            )
    for index, item in enumerate(captured_controls):
        label = f"capture.controls[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        reject_unknown_keys(item, INPUT_CONTROL_FIELDS, label, errors)
        control_id = item.get("control_id")
        if not nonempty(control_id):
            errors.append(f"{label}.control_id must be a non-empty string")
            continue
        definition = controls.get(control_id)
        if definition is None:
            continue
        baseline = item.get("baseline")
        repeat = item.get("repeat")
        variant = item.get("variant")
        if not all(
            isinstance(value, dict)
            for value in (baseline, repeat, variant)
        ):
            errors.append(
                f"{label} requires baseline, repeat, and variant objects"
            )
            continue
        declared_entrypoint_sha = (
            entrypoint.get("sha256")
            if isinstance(entrypoint, dict)
            else None
        )
        for phase, run_item in (
            ("baseline", baseline),
            ("repeat", repeat),
            ("variant", variant),
        ):
            if run_item.get("entrypoint_sha256") != declared_entrypoint_sha:
                errors.append(
                    f"{label}.{phase}.entrypoint_sha256 must match "
                    "analysis_entrypoint.sha256"
                )
        (
            baseline_input,
            baseline_result,
            baseline_input_sha,
            baseline_result_sha,
            baseline_ended,
            baseline_input_path,
            baseline_result_path,
        ) = capture_item_files(
            root,
            baseline,
            f"{label}.baseline",
            completed,
            errors,
        )
        (
            repeat_input,
            repeat_result,
            repeat_input_sha,
            repeat_result_sha,
            repeat_ended,
            repeat_input_path,
            repeat_result_path,
        ) = capture_item_files(
            root,
            repeat,
            f"{label}.repeat",
            completed,
            errors,
        )
        (
            variant_input,
            variant_result,
            variant_input_sha,
            variant_result_sha,
            variant_ended,
            variant_input_path,
            variant_result_path,
        ) = capture_item_files(
            root,
            variant,
            f"{label}.variant",
            completed,
            errors,
        )
        if generated is not None:
            for phase, ended in (
                ("baseline", baseline_ended),
                ("repeat", repeat_ended),
                ("variant", variant_ended),
            ):
                if ended is not None and generated < ended:
                    errors.append(
                        f"{label} capture generated before {phase} completed"
                    )
        if baseline_input_sha and baseline_input_sha != repeat_input_sha:
            errors.append(
                f"{label} baseline and repeat inputs must be byte-identical"
            )
        if baseline_input_sha and baseline_input_sha == variant_input_sha:
            errors.append(f"{label} baseline and variant inputs are identical")
        if baseline_result_sha and baseline_result_sha == variant_result_sha:
            errors.append(f"{label} baseline and variant results are identical")
        if baseline.get("run_id") == repeat.get("run_id"):
            errors.append(
                f"{label} repeat must use an independent run_id"
            )
        if baseline.get("run_id") == variant.get("run_id"):
            errors.append(f"{label} baseline and variant run_id must differ")
        if repeat.get("run_id") == variant.get("run_id"):
            errors.append(f"{label} repeat and variant run_id must differ")
        if not all(
            value is not None
            for value in (
                baseline_input,
                baseline_result,
                repeat_input,
                repeat_result,
                variant_input,
                variant_result,
            )
        ):
            continue
        for pointer in result_identity_pointers:
            for phase, result_document in (
                ("baseline", baseline_result),
                ("repeat", repeat_result),
                ("variant", variant_result),
            ):
                try:
                    json_pointer(result_document, pointer)
                except (KeyError, ValueError) as exc:
                    errors.append(
                        f"{label}.{phase} result identity pointer "
                        f"{pointer!r} failed: {exc}"
                    )
        executed_parameters: dict[str, tuple[bool, Any]] = {}
        for phase, run_item, phase_input, phase_input_sha, phase_result_sha in (
            (
                "baseline",
                baseline,
                baseline_input,
                baseline_input_sha,
                baseline_result_sha,
            ),
            (
                "repeat",
                repeat,
                repeat_input,
                repeat_input_sha,
                repeat_result_sha,
            ),
            (
                "variant",
                variant,
                variant_input,
                variant_input_sha,
                variant_result_sha,
            ),
        ):
            (
                invocation_document,
                source_document,
                execution_trace_artifact,
            ) = invocation_records.get(
                (index, phase),
                (None, None, None),
            )
            executed_parameters[phase] = validate_invocation_document(
                document=invocation_document,
                source_document=source_document,
                run=run_item,
                input_value=phase_input,
                input_sha=phase_input_sha,
                result_sha=phase_result_sha,
                definition=definition,
                entrypoint=entrypoint,
                receipt=receipt,
                label=(
                    f"{label}.{phase}.invocation_artifact.document"
                ),
                errors=errors,
            )
            if not matching_analysis_execution_evidence(
                evidence,
                execution_trace_artifact,
                invocation_document,
                generated,
            ):
                errors.append(
                    f"{label}.{phase} lacks matching authoritative "
                    "analysis command-trace evidence"
                )
        try:
            base_input_value = json_pointer(
                baseline_input, definition["input_pointer"]
            )
            variant_input_value = json_pointer(
                variant_input, definition["input_pointer"]
            )
            base_effective = json_pointer(
                baseline_result, definition["effective_value_pointer"]
            )
            repeat_input_value = json_pointer(
                repeat_input, definition["input_pointer"]
            )
            repeat_effective = json_pointer(
                repeat_result, definition["effective_value_pointer"]
            )
            variant_effective = json_pointer(
                variant_result, definition["effective_value_pointer"]
            )
        except (KeyError, ValueError) as exc:
            errors.append(f"{label} pointer validation failed: {exc}")
            continue
        if json_values_equal(base_input_value, variant_input_value):
            errors.append(f"{label} canonical input values did not change")
        if not json_values_equal(repeat_input_value, base_input_value):
            errors.append(f"{label} repeat canonical input value changed")
        if not json_values_equal(base_effective, base_input_value):
            errors.append(f"{label} baseline effective value mismatch")
        if not json_values_equal(repeat_effective, repeat_input_value):
            errors.append(f"{label} repeat effective value mismatch")
        if not json_values_equal(repeat_effective, base_effective):
            errors.append(f"{label} repeat effective value changed")
        if not json_values_equal(variant_effective, variant_input_value):
            errors.append(f"{label} variant effective value mismatch")
        if json_values_equal(base_effective, variant_effective):
            errors.append(f"{label} effective values did not change")
        baseline_executed_valid, baseline_executed = executed_parameters[
            "baseline"
        ]
        repeat_executed_valid, repeat_executed = executed_parameters["repeat"]
        variant_executed_valid, variant_executed = executed_parameters[
            "variant"
        ]
        if (
            baseline_executed_valid
            and repeat_executed_valid
            and not json_values_equal(
                baseline_executed, repeat_executed
            )
        ):
            errors.append(f"{label} repeat executed parameter changed")
        if (
            baseline_executed_valid
            and variant_executed_valid
            and json_values_equal(
                baseline_executed, variant_executed
            )
        ):
            errors.append(f"{label} variant executed parameter did not change")
        raw_allowed_input_pointers = definition.get(
            "allowed_variant_input_pointers",
            [definition["input_pointer"]],
        )
        allowed_input_pointers = (
            raw_allowed_input_pointers
            if isinstance(raw_allowed_input_pointers, list)
            and all(
                isinstance(pointer, str)
                for pointer in raw_allowed_input_pointers
            )
            else []
        )
        differences = json_diff_pointers(baseline_input, variant_input)
        unexpected_differences = sorted(
            pointer
            for pointer in differences
            if not any(
                pointer_is_within(pointer, allowed)
                for allowed in allowed_input_pointers
            )
        )
        if unexpected_differences:
            errors.append(
                f"{label} variant changed undeclared input paths: "
                + ", ".join(unexpected_differences)
            )
        changed_result_path = False
        for pointer in definition.get("result_paths", []):
            try:
                baseline_core = json_pointer(baseline_result, pointer)
                repeat_core = json_pointer(repeat_result, pointer)
                variant_core = json_pointer(variant_result, pointer)
                if not json_values_equal(repeat_core, baseline_core):
                    errors.append(
                        f"{label} repeat changed core result path {pointer!r}"
                    )
                if not json_values_equal(baseline_core, variant_core):
                    changed_result_path = True
            except ValueError as exc:
                errors.append(f"{label} result path {pointer!r}: {exc}")
        if not changed_result_path:
            errors.append(
                f"{label} no declared responsible result path changed"
            )
        run_pointer = definition.get("run_id_pointer", "/run_id")
        project_pointer = definition.get("project_id_pointer", "/project_id")
        try:
            if json_pointer(baseline_result, run_pointer) != baseline.get(
                "run_id"
            ):
                errors.append(f"{label} baseline result run_id mismatch")
            if json_pointer(repeat_result, run_pointer) != repeat.get(
                "run_id"
            ):
                errors.append(f"{label} repeat result run_id mismatch")
            if json_pointer(variant_result, run_pointer) != variant.get(
                "run_id"
            ):
                errors.append(f"{label} variant result run_id mismatch")
            if json_pointer(baseline_result, project_pointer) != receipt.get(
                "project_id"
            ):
                errors.append(f"{label} baseline result project_id mismatch")
            if json_pointer(repeat_result, project_pointer) != receipt.get(
                "project_id"
            ):
                errors.append(f"{label} repeat result project_id mismatch")
            if json_pointer(variant_result, project_pointer) != receipt.get(
                "project_id"
            ):
                errors.append(f"{label} variant result project_id mismatch")
        except ValueError as exc:
            errors.append(f"{label} identity pointer validation failed: {exc}")

        for (
            phase,
            runtime,
            run,
            run_input,
            run_result,
            effective,
            result_sha,
            executed_valid,
            executed,
        ) in (
            (
                "baseline",
                item.get("baseline_runtime"),
                baseline,
                baseline_input,
                baseline_result,
                base_effective,
                baseline_result_sha,
                baseline_executed_valid,
                baseline_executed,
            ),
            (
                "variant",
                item.get("variant_runtime"),
                variant,
                variant_input,
                variant_result,
                variant_effective,
                variant_result_sha,
                variant_executed_valid,
                variant_executed,
            ),
        ):
            validate_runtime_phase(
                root=root,
                phase=phase,
                runtime=runtime,
                run=run,
                input_value=run_input,
                result_value=run_result,
                result_sha=result_sha,
                effective_value=effective,
                executed_value=executed,
                executed_value_valid=executed_valid,
                definition=definition,
                receipt=receipt,
                driver=driver,
                gate_evidence=evidence,
                generated=generated,
                completed=completed,
                used_capture_ids=used_capture_ids,
                used_session_ids=used_session_ids,
                used_artifact_paths=used_artifact_paths,
                errors=errors,
            )


def typed_payloads(
    gates: dict[str, Any],
    gate_name: str,
    field: str,
    errors: list[str],
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    # A project-relative capture binds claims to immutable local bytes.  It
    # proves receipt integrity, not provider authenticity: the producing
    # workflow remains responsible for capturing the real provider response
    # and recording its provenance in source/summary.
    gate = gates.get(gate_name)
    evidence = gate.get("evidence") if isinstance(gate, dict) else None
    found: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    if isinstance(evidence, list):
        for index, item in enumerate(evidence):
            if not isinstance(item, dict) or field not in item:
                continue
            label = f"gates.{gate_name}.evidence[{index}].{field}"
            value = item.get(field)
            if not isinstance(value, dict):
                errors.append(f"{label} must be an object")
                continue
            if not nonempty(item.get("artifact_path")):
                errors.append(
                    f"{label} requires evidence artifact_path"
                )
            if not is_sha256(item.get("artifact_sha256")):
                errors.append(
                    f"{label} requires evidence artifact_sha256"
                )
            found.append((label, value, item))
    if not found:
        errors.append(
            f"gate {gate_name!r} requires typed {field} evidence"
        )
    return found


def validate_release_evidence(
    gates: dict[str, Any],
    cost_authority: Any,
    manifest: dict[str, Any],
    errors: list[str],
) -> None:
    actions = (
        cost_authority.get("actions")
        if isinstance(cost_authority, dict)
        else []
    )
    valid_actions = [
        item for item in actions if isinstance(item, dict)
    ] if isinstance(actions, list) else []
    configs = manifest.get("capability_config")
    release_config = (
        configs.get("remote-release")
        if isinstance(configs, dict)
        else None
    )
    project = manifest.get("project")
    repository = (
        project.get("repository") if isinstance(project, dict) else None
    )
    provider_targets: dict[str, dict[str, Any]] = {}
    if isinstance(release_config, dict):
        targets = release_config.get("targets")
        if isinstance(targets, list):
            provider_targets = {
                item["id"]: item
                for item in targets
                if isinstance(item, dict) and nonempty(item.get("id"))
            }
    for label, identity, _ in typed_payloads(
        gates, "release", "release_identity", errors
    ):
        reject_unknown_keys(
            identity, RELEASE_IDENTITY_FIELDS, label, errors
        )
        for field in (
            "provider",
            "target",
            "action",
            "account_or_project",
            "before_identity",
            "after_identity",
            "operation_id",
        ):
            if not nonempty(identity.get(field)):
                errors.append(f"{label}.{field} is required")
        if identity.get("remote") is not True:
            errors.append(f"{label}.remote must be true")
        if identity.get("status") != "succeeded":
            errors.append(f"{label}.status must equal succeeded")
        if identity.get("before_identity") == identity.get("after_identity"):
            errors.append(
                f"{label}.after_identity must differ from before_identity"
            )
        if valid_actions and not any(
            action.get("action_id") == identity.get("operation_id")
            and action.get("provider") == identity.get("provider")
            and action.get("account_or_project")
            == identity.get("account_or_project")
            for action in valid_actions
        ):
            errors.append(
                f"{label} does not match an enumerated zero-cost action"
            )
        if isinstance(release_config, dict):
            kind = release_config.get("kind")
            if kind == "scm" and nonempty(repository):
                if identity.get("target") != repository:
                    errors.append(
                        f"{label}.target does not match project repository"
                    )
            elif kind == "provider" and provider_targets:
                target = provider_targets.get(identity.get("target"))
                if target is None:
                    errors.append(f"{label}.target is not declared")
                else:
                    for field in (
                        "provider",
                        "account_or_project",
                        "action",
                    ):
                        if identity.get(field) != target.get(field):
                            errors.append(
                                f"{label}.{field} does not match manifest target"
                            )


def validate_public_readback_evidence(
    gates: dict[str, Any],
    manifest: dict[str, Any],
    root: Path,
    errors: list[str],
) -> None:
    declared_urls: set[str] = set()
    configs = manifest.get("capability_config")
    if isinstance(configs, dict):
        publication = configs.get("publication")
        if isinstance(publication, dict):
            targets = publication.get("targets")
            if isinstance(targets, list):
                declared_urls.update(
                    target["public_url"]
                    for target in targets
                    if isinstance(target, dict)
                    and valid_http_url(target.get("public_url"))
                )
        release = configs.get("remote-release")
        if isinstance(release, dict):
            declared_urls.update(
                release[field]
                for field in ("preview_url", "production_url")
                if valid_http_url(release.get(field))
            )
    for label, readback, item in typed_payloads(
        gates, "public_readback", "public_readback", errors
    ):
        reject_unknown_keys(
            readback, PUBLIC_READBACK_FIELDS, label, errors
        )
        if not valid_http_url(readback.get("url")):
            errors.append(f"{label}.url is invalid")
        elif declared_urls and readback["url"] not in declared_urls:
            errors.append(f"{label}.url is not a declared public target")
        if not is_sha256(readback.get("response_sha256")):
            errors.append(f"{label}.response_sha256 must be SHA-256")
        elif readback.get("response_sha256") != item.get(
            "artifact_sha256"
        ):
            errors.append(
                f"{label}.response_sha256 must match captured bytes"
            )
        size = readback.get("response_size")
        if (
            not isinstance(size, int)
            or isinstance(size, bool)
            or size <= 0
        ):
            errors.append(f"{label}.response_size must be an integer > 0")
        elif nonempty(item.get("artifact_path")):
            captured = project_file(
                root,
                item["artifact_path"],
                f"{label}.response_capture",
                errors,
            )
            if captured is not None and size != captured.stat().st_size:
                errors.append(
                    f"{label}.response_size does not match captured bytes"
                )
        if not nonempty(readback.get("result_identity")):
            errors.append(f"{label}.result_identity is required")


def validate_schedule_evidence(
    gates: dict[str, Any],
    manifest: dict[str, Any],
    root: Path,
    errors: list[str],
) -> None:
    declared: dict[str, dict[str, Any]] = {}
    configs = manifest.get("capability_config")
    automation = (
        configs.get("scheduled-automation")
        if isinstance(configs, dict)
        else None
    )
    schedules = (
        automation.get("schedules")
        if isinstance(automation, dict)
        else None
    )
    if isinstance(schedules, list):
        declared = {
            item["id"]: item
            for item in schedules
            if isinstance(item, dict) and nonempty(item.get("id"))
        }
    for label, identity, _ in typed_payloads(
        gates, "schedule", "schedule_identity", errors
    ):
        reject_unknown_keys(
            identity, SCHEDULE_IDENTITY_FIELDS, label, errors
        )
        for field in (
            "schedule_id",
            "declared_schedule",
            "timezone",
            "active_revision",
        ):
            if not nonempty(identity.get(field)):
                errors.append(f"{label}.{field} is required")
        if not is_sha256(identity.get("entrypoint_sha256")):
            errors.append(f"{label}.entrypoint_sha256 must be SHA-256")
        if identity.get("enabled") is not True:
            errors.append(f"{label}.enabled must be true")
        if identity.get("cost_preflight_verified") is not True:
            errors.append(
                f"{label}.cost_preflight_verified must be true"
            )
        schedule = declared.get(identity.get("schedule_id"))
        if declared and schedule is None:
            errors.append(f"{label}.schedule_id is not declared")
        elif schedule is not None:
            for evidence_field, manifest_field in (
                ("declared_schedule", "schedule"),
                ("timezone", "timezone"),
            ):
                if identity.get(evidence_field) != schedule.get(
                    manifest_field
                ):
                    errors.append(
                        f"{label}.{evidence_field} does not match manifest"
                    )
            entrypoint = project_file(
                root,
                schedule.get("entrypoint"),
                f"{label}.entrypoint",
                errors,
            )
            if entrypoint is not None and identity.get(
                "entrypoint_sha256"
            ) != sha256_bytes(entrypoint.read_bytes()):
                errors.append(
                    f"{label}.entrypoint_sha256 does not match bytes"
                )


def validate_publication_evidence(
    gates: dict[str, Any],
    manifest: dict[str, Any],
    errors: list[str],
) -> None:
    declared_ids: set[str] = set()
    configs = manifest.get("capability_config")
    publication = (
        configs.get("publication") if isinstance(configs, dict) else None
    )
    targets = (
        publication.get("targets")
        if isinstance(publication, dict)
        else None
    )
    if isinstance(targets, list):
        declared_ids = {
            item["id"]
            for item in targets
            if isinstance(item, dict) and nonempty(item.get("id"))
        }
    for label, identity, item in typed_payloads(
        gates, "publication", "publication_identity", errors
    ):
        reject_unknown_keys(
            identity, PUBLICATION_IDENTITY_FIELDS, label, errors
        )
        for field in ("target_id", "published_identity"):
            if not nonempty(identity.get(field)):
                errors.append(f"{label}.{field} is required")
        if declared_ids and identity.get("target_id") not in declared_ids:
            errors.append(f"{label}.target_id is not declared")
        if not is_sha256(identity.get("artifact_sha256")):
            errors.append(f"{label}.artifact_sha256 must be SHA-256")
        elif identity.get("artifact_sha256") != item.get(
            "artifact_sha256"
        ):
            errors.append(
                f"{label}.artifact_sha256 must match captured bytes"
            )
        if identity.get("ordering_verified") is not True:
            errors.append(f"{label}.ordering_verified must be true")
        if identity.get("last_good_preserved") is not True:
            errors.append(f"{label}.last_good_preserved must be true")


def validate_data_evidence(
    gates: dict[str, Any],
    manifest: dict[str, Any],
    completed: datetime,
    errors: list[str],
) -> None:
    required_sources: set[str] = set()
    configs = manifest.get("capability_config")
    external = (
        configs.get("external-data") if isinstance(configs, dict) else None
    )
    sources = (
        external.get("sources") if isinstance(external, dict) else None
    )
    if isinstance(sources, list):
        required_sources = {
            item["id"]
            for item in sources
            if isinstance(item, dict)
            and item.get("role") == "required"
            and nonempty(item.get("id"))
        }
    for gate_name in ("collection", "freshness"):
        for label, identity, item in typed_payloads(
            gates, gate_name, "data_identity", errors
        ):
            reject_unknown_keys(
                identity, DATA_IDENTITY_FIELDS, label, errors
            )
            source_ids = unique_nonempty_strings(
                identity.get("source_ids"),
                f"{label}.source_ids",
                errors,
                allow_empty=False,
            )
            if required_sources - set(source_ids):
                errors.append(
                    f"{label}.source_ids omits required manifest sources: "
                    + ", ".join(sorted(required_sources - set(source_ids)))
                )
            if not is_sha256(identity.get("artifact_sha256")):
                errors.append(f"{label}.artifact_sha256 must be SHA-256")
            elif identity.get("artifact_sha256") != item.get(
                "artifact_sha256"
            ):
                errors.append(
                    f"{label}.artifact_sha256 must match captured bytes"
                )
            if identity.get("rights_checked") is not True:
                errors.append(f"{label}.rights_checked must be true")
            collected = parse_time(identity.get("collected_at"))
            source_as_of = parse_time(identity.get("source_as_of"))
            if collected is None:
                errors.append(
                    f"{label}.collected_at must be timezone-aware"
                )
            elif collected > completed:
                errors.append(f"{label}.collected_at is after completion")
            if source_as_of is None:
                errors.append(
                    f"{label}.source_as_of must be timezone-aware"
                )
            elif collected is not None and source_as_of > collected:
                errors.append(
                    f"{label}.source_as_of is after collected_at"
                )
            if identity.get("freshness_status") not in {
                "current",
                "explicit-degraded",
                "unavailable",
            }:
                errors.append(f"{label}.freshness_status is invalid")


def validate_agent_team_evidence(
    capabilities: list[str],
    gates: dict[str, Any],
    receipt: dict[str, Any],
    root: Path,
    completed: datetime,
    goal_info: dict[str, Any] | None,
    args: Any,
    errors: list[str],
) -> None:
    """Validate the one typed proof that can activate agent-team execution."""

    capability = "agent-team-execution"
    active = capability in capabilities
    requested = team_cli_requested(args)
    if requested and not active:
        errors.append(
            "agent-team CLI artifacts require agent-team-execution scope"
        )
        return
    if not active:
        return
    try:
        import team_protocol
    except ImportError as exc:
        errors.append(f"agent-team protocol import failed: {exc}")
        return

    packet_value = getattr(args, "team_packet", None)
    delivery_values = getattr(args, "team_delivery", None)
    integration_value = getattr(args, "team_integration", None)
    artifact_root_value = getattr(args, "team_artifact_root", None)
    workspace_root_value = getattr(args, "team_workspace_root", None)
    baseline_root_value = getattr(args, "team_baseline_root", None)
    worker_root_values = getattr(args, "team_worker_root", None)
    if not nonempty(packet_value):
        errors.append(
            "agent-team-execution requires --team-packet"
        )
    if (
        not isinstance(delivery_values, list)
        or not delivery_values
        or not all(nonempty(value) for value in delivery_values)
    ):
        errors.append(
            "agent-team-execution requires one or more --team-delivery paths"
        )
        delivery_values = []
    if not nonempty(integration_value):
        errors.append(
            "agent-team-execution requires --team-integration"
        )

    artifact_root = team_directory(
        artifact_root_value,
        "--team-artifact-root",
        errors,
    )
    workspace_root = team_directory(
        workspace_root_value,
        "--team-workspace-root",
        errors,
    )
    baseline_root = team_directory(
        baseline_root_value,
        "--team-baseline-root",
        errors,
    )
    worker_roots = team_worker_directories(
        worker_root_values,
        errors,
    )
    if workspace_root is not None and not same_physical_file(
        workspace_root, root
    ):
        errors.append(
            "--team-workspace-root must identify the verified project root"
        )
    if artifact_root is not None:
        filesystem_root = Path(artifact_root.anchor)
        if artifact_root == filesystem_root:
            errors.append("--team-artifact-root is too broad")
        elif artifact_root != root and path_is_within(root, artifact_root):
            errors.append(
                "--team-artifact-root must not contain the project root"
            )

    allowed_roots = [root]
    state_dir = (
        goal_info.get("state_dir")
        if isinstance(goal_info, dict)
        else None
    )
    if isinstance(state_dir, Path):
        allowed_roots.append(state_dir)
    if artifact_root is not None:
        allowed_roots.append(artifact_root)

    packet_path = (
        team_proof_file(
            packet_value,
            "--team-packet",
            root,
            allowed_roots,
            errors,
        )
        if nonempty(packet_value)
        else None
    )
    delivery_paths = [
        path
        for index, value in enumerate(delivery_values)
        if (
            path := team_proof_file(
                value,
                f"--team-delivery[{index}]",
                root,
                allowed_roots,
                errors,
            )
        )
        is not None
    ]
    integration_path = (
        team_proof_file(
            integration_value,
            "--team-integration",
            root,
            allowed_roots,
            errors,
        )
        if nonempty(integration_value)
        else None
    )
    proof_paths = [
        path
        for path in [packet_path, *delivery_paths, integration_path]
        if path is not None
    ]
    for index, path in enumerate(proof_paths):
        for prior in proof_paths[:index]:
            if same_physical_file(path, prior):
                errors.append(
                    "agent-team proof files must be distinct physical files"
                )
                break

    def read_team_json(
        path: Path | None,
        label: str,
    ) -> dict[str, Any] | None:
        if path is None:
            return None
        try:
            return team_protocol.strict_json(path)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"invalid {label}: {exc}")
            return None

    packet = read_team_json(packet_path, "Team Run Packet")
    delivery_documents: list[tuple[dict[str, Any], Path]] = []
    for index, path in enumerate(delivery_paths):
        document = read_team_json(
            path, f"worker Delivery Receipt {index}"
        )
        if document is not None:
            delivery_documents.append((document, path))
    deliveries = [document for document, _ in delivery_documents]
    integration = read_team_json(
        integration_path, "Team Integration Receipt"
    )

    gate = gates.get("team_integration")
    if not isinstance(gate, dict):
        errors.append(
            "agent-team-execution requires a passed team_integration gate"
        )
        return
    evidence = gate.get("evidence")
    if (
        not isinstance(evidence, list)
        or len(evidence) != 1
        or not isinstance(evidence[0], dict)
    ):
        errors.append(
            "team_integration must contain exactly one typed evidence item"
        )
        return
    item = evidence[0]
    missing_item_fields = sorted(TEAM_EVIDENCE_FIELDS - set(item))
    unknown_item_fields = sorted(set(item) - TEAM_EVIDENCE_FIELDS)
    if missing_item_fields:
        errors.append(
            "team_integration typed evidence is missing fields: "
            + ", ".join(missing_item_fields)
        )
    if unknown_item_fields:
        errors.append(
            "team_integration typed evidence contains unknown fields: "
            + ", ".join(unknown_item_fields)
        )
    if item.get("kind") != "artifact":
        errors.append(
            "team_integration typed evidence kind must be artifact"
        )
    if item.get("status") != "verified":
        errors.append(
            "team_integration typed evidence status must be verified"
        )
    if item.get("source") != TEAM_EVIDENCE_SOURCE:
        errors.append(
            "team_integration typed evidence source is invalid"
        )
    extensions = item.get("extensions")
    if not isinstance(extensions, dict):
        errors.append(
            "team_integration typed evidence extensions must be an object"
        )
        return
    expected_extension_names = {"agent_team_execution"}
    if goal_info is not None:
        expected_extension_names.add("goal_ledger")
    if set(extensions) != expected_extension_names:
        errors.append(
            "team_integration typed evidence extensions must contain exactly: "
            + ", ".join(sorted(expected_extension_names))
        )
    extension = extensions.get("agent_team_execution")
    if not isinstance(extension, dict):
        errors.append(
            "extensions.agent_team_execution must be an object"
        )
        return
    missing_extension_fields = sorted(
        TEAM_EXTENSION_FIELDS - set(extension)
    )
    unknown_extension_fields = sorted(
        set(extension) - TEAM_EXTENSION_FIELDS
    )
    if missing_extension_fields:
        errors.append(
            "extensions.agent_team_execution is missing fields: "
            + ", ".join(missing_extension_fields)
        )
    if unknown_extension_fields:
        errors.append(
            "extensions.agent_team_execution contains unknown fields: "
            + ", ".join(unknown_extension_fields)
        )

    if (
        packet is None
        or integration is None
        or packet_path is None
        or integration_path is None
        or artifact_root is None
        or workspace_root is None
        or baseline_root is None
    ):
        return

    protocol_issues = team_protocol.validate_integration(
        packet,
        deliveries,
        integration,
        artifact_root=artifact_root,
        workspace_root=workspace_root,
        project_root=root,
        baseline_root=baseline_root,
        worker_roots=worker_roots,
        require_live_handoff=True,
    )
    errors.extend(
        "agent-team protocol: " + issue for issue in protocol_issues
    )
    if integration.get("status") != "ready_for_review":
        errors.append(
            "team_integration evidence requires ready_for_review status"
        )

    assignments = {
        assignment.get("id"): assignment
        for assignment in packet.get("assignments", [])
        if isinstance(assignment, dict)
        and nonempty(assignment.get("id"))
    }
    expected_objective_sha256 = canonical_sha256(
        receipt.get("objective")
    )
    if packet.get("objective_sha256") != expected_objective_sha256:
        errors.append(
            "agent-team packet does not bind the completion objective"
        )
    receipt_scope = receipt.get("scope")
    receipt_assurance = (
        receipt_scope.get("assurance")
        if isinstance(receipt_scope, dict)
        else None
    )
    receipt_risk_assurance = (
        "strict" if receipt_assurance == "release" else receipt_assurance
    )
    if team_protocol.packet_risk_assurance(
        packet
    ) != receipt_risk_assurance:
        errors.append(
            "agent-team packet risk assurance does not match receipt scope"
        )
    receipt_delivery = (
        receipt_scope.get("delivery")
        if isinstance(receipt_scope, dict)
        and receipt_scope.get("delivery") in {"local", "release"}
        else (
            "release"
            if (
                receipt_assurance == "release"
                or (
                    isinstance(receipt_scope, dict)
                    and receipt_scope.get("remote_actions") is True
                    and isinstance(
                        receipt_scope.get("capabilities"), list
                    )
                    and "remote-release"
                    in receipt_scope.get("capabilities", [])
                )
            )
            else "local"
        )
    )
    if team_protocol.packet_delivery(packet) != receipt_delivery:
        errors.append(
            "agent-team packet delivery does not match receipt scope"
        )
    join = packet.get("join")
    raw_join_order = (
        join.get("integration_order")
        if isinstance(join, dict)
        and isinstance(join.get("integration_order"), list)
        else []
    )
    join_order = [
        assignment_id
        for assignment_id in raw_join_order
        if isinstance(assignment_id, str)
    ]
    delivery_by_assignment: dict[str, tuple[dict[str, Any], Path]] = {}
    seen_receipt_hashes: set[str] = set()
    for delivery, path in delivery_documents:
        assignment_id = delivery.get("assignment_id")
        receipt_sha256 = delivery.get("receipt_sha256")
        if nonempty(assignment_id):
            if assignment_id in delivery_by_assignment:
                errors.append(
                    "agent-team Delivery Receipt assignment is reused: "
                    + assignment_id
                )
            else:
                delivery_by_assignment[assignment_id] = (delivery, path)
        if is_sha256(receipt_sha256):
            if receipt_sha256 in seen_receipt_hashes:
                errors.append(
                    "agent-team Delivery Receipt hash is reused"
                )
            seen_receipt_hashes.add(receipt_sha256)
    if set(delivery_by_assignment) != set(assignments):
        errors.append(
            "explicit --team-delivery paths must cover every packet assignment"
        )

    artifact_paths: list[Path] = []
    for delivery_index, delivery in enumerate(deliveries):
        artifacts = delivery.get("delivery_artifacts")
        if not isinstance(artifacts, list):
            continue
        for artifact_index, artifact in enumerate(artifacts):
            reference = (
                artifact.get("ref")
                if isinstance(artifact, dict)
                else None
            )
            if not nonempty(reference):
                continue
            candidate = (artifact_root / reference).resolve()
            if (
                not path_is_within(candidate, artifact_root)
                or not candidate.is_file()
            ):
                continue
            if any(
                same_physical_file(candidate, prior)
                for prior in [*proof_paths, *artifact_paths]
            ):
                errors.append(
                    "agent-team artifact file is reused by a proof or "
                    "another delivery: "
                    f"{delivery_index}:{artifact_index}"
                )
            artifact_paths.append(candidate)

    actual_project_binding = team_protocol.project_binding(root).get(
        "identity_sha256"
    )
    snapshot = integration.get("canonical_snapshot")
    current_workspace_sha256 = (
        snapshot.get("post_workspace_sha256")
        if isinstance(snapshot, dict)
        else None
    )
    expected_goal_binding: dict[str, Any] | None = None
    if goal_info is None:
        if packet.get("owner") != "standalone_developer":
            errors.append(
                "standalone agent-team packet owner must be "
                "standalone_developer"
            )
        if packet.get("goal_binding") is not None:
            errors.append("standalone agent-team packet must not bind a Goal")
    elif goal_info.get("runtime_kind") != "host-ledger-v1":
        errors.append(
            "Goal-bound agent-team evidence requires the host-aligned "
            "Goal ledger"
        )
    else:
        try:
            import goal_ledger
        except ImportError as exc:
            errors.append(f"host Goal ledger import failed: {exc}")
        else:
            state = goal_info.get("state", {})
            current = goal_info.get("current", {})
            expected_packet_goal = {
                "goal_id": state.get("goal_id"),
                "plan_revision": goal_ledger.current_plan_revision(state),
                "acceptance_revision": state.get("acceptance_revision"),
            }
            expected_goal_binding = {
                **expected_packet_goal,
                "workspace_sha256": current.get("sha256"),
            }
            if packet.get("owner") != "goal":
                errors.append("Goal-bound agent-team packet owner must be goal")
            if not json_values_equal(
                packet.get("goal_binding"), expected_packet_goal
            ):
                errors.append(
                    "agent-team packet does not bind the current Goal "
                    "plan and acceptance revisions"
                )
            if packet.get("objective_sha256") != state.get(
                "objective_sha256"
            ):
                errors.append(
                    "agent-team packet does not bind the current Goal objective"
                )
            goal_acceptance_ids = {
                item.get("id")
                for item in state.get("acceptance", [])
                if isinstance(item, dict) and nonempty(item.get("id"))
            }
            packet_acceptance_ids = {
                acceptance_id
                for assignment in assignments.values()
                for acceptance_id in assignment.get("acceptance_ids", [])
                if nonempty(acceptance_id)
            }
            unknown_acceptance = sorted(
                packet_acceptance_ids - goal_acceptance_ids
            )
            if unknown_acceptance:
                errors.append(
                    "agent-team packet references acceptance IDs outside "
                    "the current Goal: " + ", ".join(unknown_acceptance)
                )
            receipt_goal_binding = receipt.get("goal_binding")
            acceptance_claims = (
                receipt_goal_binding.get("acceptance_claims")
                if isinstance(receipt_goal_binding, dict)
                else None
            )
            expected_team_claim = {
                "gate": "team_integration",
                "evidence_index": 0,
                "evidence_sha256": canonical_sha256(item),
            }
            for acceptance_id in sorted(packet_acceptance_ids):
                claims = (
                    acceptance_claims.get(acceptance_id)
                    if isinstance(acceptance_claims, dict)
                    else None
                )
                if not isinstance(claims, list) or not any(
                    json_values_equal(claim, expected_team_claim)
                    for claim in claims
                ):
                    errors.append(
                        "Goal acceptance does not cite current team "
                        "integration evidence: " + acceptance_id
                    )
            ledger_extension = extensions.get("goal_ledger")
            if (
                not isinstance(ledger_extension, dict)
                or set(ledger_extension) != GOAL_LEDGER_EVIDENCE_FIELDS
                or not json_values_equal(
                    ledger_extension, expected_goal_binding
                )
            ):
                errors.append(
                    "team_integration goal_ledger extension does not exactly "
                    "bind the current Goal snapshot"
                )

    expected_deliveries = [
        {
            "assignment_id": assignment_id,
            "receipt_sha256": delivery_by_assignment[assignment_id][0].get(
                "receipt_sha256"
            ),
            "file_sha256": sha256_bytes(
                delivery_by_assignment[assignment_id][1].read_bytes()
            ),
        }
        for assignment_id in join_order
        if assignment_id in delivery_by_assignment
    ]
    raw_extension_deliveries = extension.get("deliveries")
    if not isinstance(raw_extension_deliveries, list):
        errors.append(
            "extensions.agent_team_execution.deliveries must be an array"
        )
        raw_extension_deliveries = []
    for index, binding in enumerate(raw_extension_deliveries):
        if not isinstance(binding, dict):
            errors.append(
                f"extensions.agent_team_execution.deliveries[{index}] "
                "must be an object"
            )
        elif set(binding) != TEAM_DELIVERY_BINDING_FIELDS:
            errors.append(
                f"extensions.agent_team_execution.deliveries[{index}] "
                "fields are invalid"
            )
    expected_extension = {
        "schema_version": 1,
        "team_run_id": packet.get("team_run_id"),
        "packet_sha256": packet.get("packet_sha256"),
        "packet_file_sha256": sha256_bytes(packet_path.read_bytes()),
        "deliveries": expected_deliveries,
        "integration_receipt_sha256": integration.get("receipt_sha256"),
        "integration_file_sha256": sha256_bytes(
            integration_path.read_bytes()
        ),
        "integration_owner": integration.get("integration_owner"),
        "project_binding_sha256": actual_project_binding,
        "current_workspace_sha256": current_workspace_sha256,
        "goal_binding": expected_goal_binding,
        "integration_completed_at": integration.get("completed_at"),
    }
    if not json_values_equal(extension, expected_extension):
        errors.append(
            "extensions.agent_team_execution does not exactly bind the "
            "validated packet, deliveries, integration, project, workspace, "
            "Goal, and timestamp"
        )
    if item.get("checked_at") != integration.get("completed_at"):
        errors.append(
            "team_integration checked_at must equal integration completed_at"
        )
    if parse_time(integration.get("completed_at")) is None:
        errors.append(
            "team integration completed_at must be timezone-aware"
        )
    elif parse_time(integration.get("completed_at")) > completed:
        errors.append(
            "team integration completion is after evidence receipt completion"
        )


def validate_typed_evidence(
    capabilities: list[str],
    gates: dict[str, Any],
    receipt: dict[str, Any],
    manifest: dict[str, Any],
    root: Path,
    completed: datetime,
    cost_authority: Any,
    goal_info: dict[str, Any] | None,
    args: Any,
    errors: list[str],
) -> None:
    active = set(capabilities)
    if "remote-release" in active:
        validate_release_evidence(
            gates, cost_authority, manifest, errors
        )
    if "public-web" in active:
        validate_public_readback_evidence(gates, manifest, root, errors)
    if "scheduled-automation" in active:
        validate_schedule_evidence(gates, manifest, root, errors)
    if "publication" in active:
        validate_publication_evidence(gates, manifest, errors)
    if "external-data" in active:
        validate_data_evidence(gates, manifest, completed, errors)
    validate_agent_team_evidence(
        capabilities,
        gates,
        receipt,
        root,
        completed,
        goal_info,
        args,
        errors,
    )


def validate_goal_binding(
    receipt: dict[str, Any],
    goal_path: str | None,
    root: Path,
    manifest_path: Path | None,
    errors: list[str],
) -> dict[str, Any] | None:
    binding = receipt.get("goal_binding")
    if not goal_path:
        if binding is not None:
            errors.append("goal_binding must be null without --goal-state")
        return None
    if not isinstance(binding, dict):
        errors.append("goal state requires receipt.goal_binding")
        return None
    reject_unknown_keys(
        binding, GOAL_BINDING_FIELDS, "goal_binding", errors
    )
    path = Path(goal_path).expanduser().resolve()
    if path.name not in {"goal-state.json", "goal-ledger-state.json"}:
        errors.append(
            "--goal-state must name goal-state.json or "
            "goal-ledger-state.json"
        )
        return None
    try:
        preview = load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid goal state: {exc}")
        return None
    if preview.get("document_type") == "quant_goal_ledger_state":
        return validate_host_ledger_binding(
            receipt,
            binding,
            path,
            root,
            manifest_path,
            errors,
        )
    state_dir = path.parent
    try:
        import goal_runtime

        state, runtime_errors, current = goal_runtime.load_and_verify(
            root, state_dir, check_workspace=True
        )
        events, ledger_errors = goal_runtime.read_ledger(
            state_dir / goal_runtime.LEDGER_NAME
        )
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        json.JSONDecodeError,
    ) as exc:
        errors.append(f"invalid goal runtime: {exc}")
        return None
    if runtime_errors or ledger_errors:
        errors.extend(
            f"goal runtime: {error}"
            for error in [*runtime_errors, *ledger_errors]
        )
        return None
    if state is None or current is None:
        errors.append("goal runtime verification did not produce state")
        return None
    evaluation = goal_runtime.resume_evaluation(
        state, state_dir, current
    )
    if not evaluation.get("ok"):
        issues = evaluation.get("issues")
        if isinstance(issues, list):
            errors.extend(
                f"goal runtime: {issue}"
                for issue in issues
                if isinstance(issue, str)
            )
        else:
            errors.append("goal runtime workspace evaluation failed")
        return None
    if state.get("status") not in {"active", "complete"}:
        errors.append("goal state must be active or complete")
    open_story_ids = state.get("open_story_ids")
    if not isinstance(open_story_ids, list) or open_story_ids:
        errors.append("final evidence cannot bind an open goal story")
    if state.get("project_id") != receipt.get("project_id"):
        errors.append("goal project_id does not match receipt")
    if state.get("objective") != receipt.get("objective"):
        errors.append("goal objective does not match receipt")
    if binding.get("goal_id") != state.get("goal_id"):
        errors.append("goal_binding.goal_id mismatch")
    if binding.get("objective_sha256") != state.get("objective_sha256"):
        errors.append("goal_binding.objective_sha256 mismatch")
    ledger = state.get("ledger")
    expected_receipt_tail = (
        ledger.get("tail_sha256") if isinstance(ledger, dict) else None
    )
    if state.get("status") == "complete":
        completion_events = [
            event
            for event in events
            if event.get("type") == "status_changed"
            and goal_runtime.event_payload(event).get("status") == "complete"
        ]
        if len(completion_events) != 1:
            errors.append(
                "completed goal must have exactly one completion event"
            )
        else:
            completion = completion_events[0]
            completion_payload = goal_runtime.event_payload(completion)
            expected_receipt_tail = completion.get("previous_sha256")
            if completion_payload.get(
                "pre_completion_ledger_tail_sha256"
            ) != expected_receipt_tail:
                errors.append(
                    "completion event pre-completion ledger binding mismatch"
                )
            if completion_payload.get(
                "receipt_sha256"
            ) != canonical_sha256(receipt):
                errors.append(
                    "completion event receipt hash does not match receipt"
                )
    if (
        not isinstance(ledger, dict)
        or binding.get("ledger_tail_sha256") != expected_receipt_tail
    ):
        errors.append("goal_binding.ledger_tail_sha256 mismatch")

    acceptance = state.get("acceptance")
    expected_acceptance = (
        [
            item["id"]
            for item in acceptance
            if isinstance(item, dict) and nonempty(item.get("id"))
        ]
        if isinstance(acceptance, list)
        else []
    )
    bound_acceptance = unique_nonempty_strings(
        binding.get("acceptance_ids"),
        "goal_binding.acceptance_ids",
        errors,
        allow_empty=False,
    )
    if set(bound_acceptance) != set(expected_acceptance):
        errors.append(
            "goal_binding.acceptance_ids must match every goal acceptance"
        )

    required = unique_nonempty_strings(
        state.get("required_capabilities"),
        "goal required_capabilities",
        errors,
    )
    scoped = receipt.get("scope", {}).get("capabilities", [])
    if not isinstance(scoped, list):
        scoped = []
    if not set(required).issubset(
        {item for item in scoped if isinstance(item, str)}
    ):
        errors.append("receipt scope lowers goal required capabilities")
    goal_assurance = state.get("assurance")
    receipt_assurance = receipt.get("scope", {}).get("assurance")
    if (
        isinstance(goal_assurance, str)
        and goal_assurance in ASSURANCE_RANK
        and isinstance(receipt_assurance, str)
        and receipt_assurance in ASSURANCE_RANK
        and ASSURANCE_RANK[receipt_assurance]
        < ASSURANCE_RANK[goal_assurance]
    ):
        errors.append("receipt assurance is below goal assurance")
    receipt_scope = receipt.get("scope", {})
    if effective_delivery(
        receipt_assurance,
        (
            receipt_scope.get("capabilities", [])
            if isinstance(receipt_scope, dict)
            else []
        ),
        explicit=(
            receipt_scope.get("delivery")
            if isinstance(receipt_scope, dict)
            else None
        ),
        remote_actions=(
            receipt_scope.get("remote_actions")
            if isinstance(receipt_scope, dict)
            else False
        ),
    ) != goal_state_delivery(state):
        errors.append("receipt delivery does not match goal delivery")

    manifest_binding = state.get("manifest")
    if manifest_path is None:
        if manifest_binding is not None:
            errors.append("goal has a manifest binding but --manifest is absent")
    elif (
        not isinstance(manifest_binding, dict)
        or Path(manifest_binding.get("path_realpath", "")).resolve()
        != manifest_path
        or manifest_binding.get("sha256")
        != sha256_bytes(manifest_path.read_bytes())
    ):
        errors.append("receipt manifest does not match goal manifest binding")

    opened_write = {
        event.get("story_id")
        for event in events
        if event.get("type") in {"story_opened", "story_reopened"}
        and "multi-agent-write"
        in event.get("payload", {}).get("runtime_capabilities", [])
    }
    accepted = {
        event.get("story_id")
        for event in events
        if event.get("type") == "story_accepted"
    }
    proven_runtime: set[str] = set()
    if opened_write & accepted:
        proven_runtime.add("multi-agent-write")
    return {
        "state": state,
        "events": events,
        "current": current,
        "state_dir": state_dir,
        "proven_runtime_capabilities": proven_runtime,
        "runtime_kind": "legacy-v2",
    }


def validate_host_ledger_binding(
    receipt: dict[str, Any],
    binding: dict[str, Any],
    path: Path,
    root: Path,
    manifest_path: Path | None,
    errors: list[str],
) -> dict[str, Any] | None:
    """Validate the manifest-free host-aligned ledger without changing it."""

    if path.name != "goal-ledger-state.json":
        errors.append(
            "host-aligned ledger must use goal-ledger-state.json"
        )
        return None
    state_dir = path.parent
    try:
        import goal_ledger

        state, runtime_errors, current, events = goal_ledger.load_and_verify(
            root,
            state_dir,
            check_workspace=True,
            recover=False,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        json.JSONDecodeError,
    ) as exc:
        errors.append(f"invalid host Goal ledger: {exc}")
        return None
    if runtime_errors:
        errors.extend(
            f"host Goal ledger: {error}" for error in runtime_errors
        )
        return None
    if state is None or current is None:
        errors.append(
            "host Goal ledger verification did not produce state"
        )
        return None
    errors.extend(
        f"host Goal ledger: {error}"
        for error in goal_ledger.completion_context_issues(state, current)
    )
    if state.get("project_id") != receipt.get("project_id"):
        errors.append("goal project_id does not match receipt")
    if state.get("objective") != receipt.get("objective"):
        errors.append("goal objective does not match receipt")
    if binding.get("goal_id") != state.get("goal_id"):
        errors.append("goal_binding.goal_id mismatch")
    if binding.get("objective_sha256") != state.get("objective_sha256"):
        errors.append("goal_binding.objective_sha256 mismatch")
    ledger = state.get("ledger")
    expected_tail = (
        ledger.get("tail_sha256") if isinstance(ledger, dict) else None
    )
    completion = state.get("completion_ready")
    receipt_sha256 = canonical_sha256(receipt)
    if isinstance(completion, dict):
        if completion.get("receipt_sha256") != receipt_sha256:
            errors.append(
                "completion_ready event binds a different final receipt"
            )
        else:
            expected_tail = completion.get("pre_ledger_tail_sha256")
    if binding.get("ledger_tail_sha256") != expected_tail:
        errors.append("goal_binding.ledger_tail_sha256 mismatch")

    acceptance = state.get("acceptance")
    expected_acceptance = (
        [
            item["id"]
            for item in acceptance
            if isinstance(item, dict) and nonempty(item.get("id"))
        ]
        if isinstance(acceptance, list)
        else []
    )
    bound_acceptance = unique_nonempty_strings(
        binding.get("acceptance_ids"),
        "goal_binding.acceptance_ids",
        errors,
        allow_empty=False,
    )
    if set(bound_acceptance) != set(expected_acceptance):
        errors.append(
            "goal_binding.acceptance_ids must match every goal acceptance"
        )

    policy = state.get("proof_policy")
    required_capabilities = (
        policy.get("required_capabilities")
        if isinstance(policy, dict)
        else []
    )
    required = unique_nonempty_strings(
        required_capabilities,
        "goal required_capabilities",
        errors,
    )
    scope = receipt.get("scope")
    scoped = scope.get("capabilities", []) if isinstance(scope, dict) else []
    if not isinstance(scoped, list):
        scoped = []
    if not set(required).issubset(
        {item for item in scoped if isinstance(item, str)}
    ):
        errors.append("receipt scope lowers goal required capabilities")
    goal_assurance = state.get("assurance")
    receipt_assurance = (
        scope.get("assurance") if isinstance(scope, dict) else None
    )
    if (
        isinstance(goal_assurance, str)
        and goal_assurance in ASSURANCE_RANK
        and isinstance(receipt_assurance, str)
        and receipt_assurance in ASSURANCE_RANK
        and ASSURANCE_RANK[receipt_assurance]
        < ASSURANCE_RANK[goal_assurance]
    ):
        errors.append("receipt assurance is below goal assurance")
    if effective_delivery(
        receipt_assurance,
        (
            scope.get("capabilities", [])
            if isinstance(scope, dict)
            else []
        ),
        explicit=(
            scope.get("delivery") if isinstance(scope, dict) else None
        ),
        remote_actions=(
            scope.get("remote_actions") if isinstance(scope, dict) else False
        ),
    ) != goal_state_delivery(state):
        errors.append("receipt delivery does not match goal delivery")

    manifest_binding = (
        policy.get("manifest") if isinstance(policy, dict) else None
    )
    if manifest_path is None:
        if manifest_binding is not None:
            errors.append("goal has a manifest binding but --manifest is absent")
    elif (
        not isinstance(manifest_binding, dict)
        or Path(manifest_binding.get("path_realpath", "")).resolve()
        != manifest_path
        or manifest_binding.get("sha256")
        != sha256_bytes(manifest_path.read_bytes())
    ):
        errors.append("receipt manifest does not match goal manifest binding")

    return {
        "state": state,
        "events": events,
        "current": current,
        "state_dir": state_dir,
        "proven_runtime_capabilities": set(),
        "runtime_kind": "host-ledger-v1",
    }


def validate_host_ledger_evidence_bindings(
    receipt: dict[str, Any],
    goal_info: dict[str, Any],
    gates: dict[str, Any],
    errors: list[str],
) -> None:
    """Bind every required proof lane to one current Goal snapshot."""

    if goal_info.get("runtime_kind") != "host-ledger-v1":
        return
    try:
        import goal_ledger
    except ImportError as exc:
        errors.append(f"host Goal ledger import failed: {exc}")
        return
    state = goal_info["state"]
    current = goal_info["current"]
    policy = state.get("proof_policy")
    required_gates = (
        policy.get("required_gates")
        if isinstance(policy, dict)
        else []
    )
    plan_revision = goal_ledger.current_plan_revision(state)
    acceptance_revision = state.get("acceptance_revision")
    review_map = goal_ledger.current_review_map(
        state, current.get("sha256")
    )
    for gate_name in required_gates:
        gate = gates.get(gate_name)
        evidence = (
            gate.get("evidence") if isinstance(gate, dict) else None
        )
        if not isinstance(evidence, list):
            continue
        matched_snapshot = False
        matched_review = gate_name not in review_map
        for item in evidence:
            if not isinstance(item, dict):
                continue
            extensions = item.get("extensions")
            ledger_binding = (
                extensions.get("goal_ledger")
                if isinstance(extensions, dict)
                else None
            )
            if not isinstance(ledger_binding, dict):
                continue
            if (
                ledger_binding.get("goal_id") == state.get("goal_id")
                and ledger_binding.get("workspace_sha256")
                == current.get("sha256")
                and ledger_binding.get("plan_revision") == plan_revision
                and ledger_binding.get("acceptance_revision")
                == acceptance_revision
            ):
                matched_snapshot = True
                review = review_map.get(gate_name)
                if review is not None and ledger_binding.get(
                    "review_receipt_sha256"
                ) == review.get("receipt_sha256"):
                    matched_review = True
        if not matched_snapshot:
            errors.append(
                f"gate {gate_name!r} lacks current host-ledger "
                "snapshot binding"
            )
        if not matched_review:
            errors.append(
                f"gate {gate_name!r} does not bind the current "
                "Review Verdict"
            )
    errors.extend(
        "host Goal ledger: " + issue
        for issue in goal_ledger.completion_evidence_candidate_binding_issues(
            receipt,
            state,
            current,
        )
    )


def validate_acceptance_claims(
    binding: Any,
    state: dict[str, Any],
    gates: dict[str, Any],
    errors: list[str],
) -> None:
    if not isinstance(binding, dict):
        return
    acceptance = state.get("acceptance")
    expected = {
        item["id"]
        for item in acceptance
        if isinstance(item, dict) and nonempty(item.get("id"))
    } if isinstance(acceptance, list) else set()
    claims = binding.get("acceptance_claims")
    if not isinstance(claims, dict):
        errors.append("goal_binding.acceptance_claims must be an object")
        return
    claim_ids = {str(key) for key in claims}
    if claim_ids != expected:
        errors.append(
            "goal_binding.acceptance_claims must cover exactly every "
            "goal acceptance"
        )
    for acceptance_id in sorted(expected):
        value = claims.get(acceptance_id)
        label = f"goal_binding.acceptance_claims.{acceptance_id}"
        if not isinstance(value, list) or not value:
            errors.append(f"{label} must be a non-empty claim array")
            continue
        references: set[tuple[str, int]] = set()
        for index, claim in enumerate(value):
            claim_label = f"{label}[{index}]"
            if not isinstance(claim, dict):
                errors.append(f"{claim_label} must be an object")
                continue
            reject_unknown_keys(
                claim, ACCEPTANCE_CLAIM_FIELDS, claim_label, errors
            )
            gate_name = claim.get("gate")
            evidence_index = claim.get("evidence_index")
            if not nonempty(gate_name):
                errors.append(f"{claim_label}.gate is required")
                continue
            if (
                not isinstance(evidence_index, int)
                or isinstance(evidence_index, bool)
                or evidence_index < 0
            ):
                errors.append(
                    f"{claim_label}.evidence_index must be an integer >= 0"
                )
                continue
            gate = gates.get(gate_name)
            evidence = (
                gate.get("evidence") if isinstance(gate, dict) else None
            )
            if not isinstance(gate, dict) or gate.get("status") != "passed":
                errors.append(
                    f"{claim_label}.gate must reference a passed gate"
                )
                continue
            if (
                not isinstance(evidence, list)
                or evidence_index >= len(evidence)
                or not isinstance(evidence[evidence_index], dict)
            ):
                errors.append(
                    f"{claim_label}.evidence_index is out of range"
                )
                continue
            reference = (gate_name, evidence_index)
            if reference in references:
                errors.append(f"{claim_label} duplicates an evidence claim")
            references.add(reference)
            if claim.get("evidence_sha256") != canonical_sha256(
                evidence[evidence_index]
            ):
                errors.append(
                    f"{claim_label}.evidence_sha256 does not match evidence"
                )


def validate_context(
    receipt: dict[str, Any],
    context: Any,
    root: Path,
    manifest_path: Path | None,
    goal_info: dict[str, Any] | None,
    errors: list[str],
) -> None:
    if not isinstance(context, dict):
        errors.append("context must be an object")
        return
    reject_unknown_keys(context, CONTEXT_FIELDS, "context", errors)
    expected_manifest_sha = (
        sha256_bytes(manifest_path.read_bytes())
        if manifest_path is not None
        else ""
    )
    if context.get("manifest_sha256") != expected_manifest_sha:
        errors.append("context.manifest_sha256 does not match manifest bytes")

    plan_sha = context.get("plan_sha256")
    base_commit = context.get("base_commit")
    head_commit = context.get("head_commit")
    if goal_info is not None:
        state = goal_info["state"]
        plan = state.get("plan")
        expected_plan = (
            plan.get("sha256") if isinstance(plan, dict) else ""
        )
        if plan_sha != expected_plan:
            errors.append("context.plan_sha256 does not match goal plan")
        events = goal_info["events"]
        created_workspace = (
            events[0].get("workspace")
            if events and isinstance(events[0], dict)
            else None
        )
        expected_base = (
            created_workspace.get("head")
            if isinstance(created_workspace, dict)
            else None
        ) or ""
        expected_head = goal_info["current"].get("head") or ""
        if base_commit != expected_base:
            errors.append("context.base_commit does not match goal genesis")
        if head_commit != expected_head:
            errors.append("context.head_commit does not match current workspace")
        return

    if plan_sha not in {"", None}:
        errors.append(
            "standalone context cannot claim an unbound plan_sha256"
        )
    current_head = git_value(root, "rev-parse", "HEAD")
    if current_head is None:
        if base_commit not in {"", None} or head_commit not in {"", None}:
            errors.append(
                "non-Git standalone context must leave commits empty"
            )
        return
    if head_commit != current_head:
        errors.append("context.head_commit does not match current Git HEAD")
    if not (
        isinstance(base_commit, str)
        and len(base_commit) in {40, 64}
        and all(character in "0123456789abcdef" for character in base_commit)
    ):
        errors.append("context.base_commit must be a full Git commit")
        return
    try:
        ancestor = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "-C",
                str(root),
                "merge-base",
                "--is-ancestor",
                base_commit,
                current_head,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        errors.append("context.base_commit ancestry could not be verified")
    else:
        if ancestor.returncode != 0:
            errors.append(
                "context.base_commit is not an ancestor of current Git HEAD"
            )


def validate_receipt(
    receipt: dict[str, Any],
    args: Any,
) -> list[str]:
    errors: list[str] = []
    if receipt.get("schema_version") != 3:
        return ["schema_version must equal 3"]
    reject_unknown_keys(receipt, TOP_LEVEL_FIELDS, "receipt", errors)
    errors.extend(policy_violations(receipt))
    if not nonempty(receipt.get("project_id")):
        errors.append("project_id is required")
    if not nonempty(receipt.get("objective")):
        errors.append("objective is required")
    elif isinstance(receipt.get("objective"), str):
        errors.extend(
            f"objective: {reason}"
            for reason in prohibited_paid_data_reasons(
                receipt["objective"]
            )
        )
    completed = parse_time(receipt.get("completed_at"))
    if completed is None:
        errors.append("completed_at must be timezone-aware ISO-8601")
        completed = datetime.max.replace(tzinfo=timezone.utc)
    elif completed.astimezone(timezone.utc) > (
        datetime.now(timezone.utc) + MAX_FUTURE_CLOCK_SKEW
    ):
        errors.append("completed_at exceeds allowed future clock skew")

    if not args.project_root:
        return errors + ["receipt v3 requires --project-root"]
    root = Path(args.project_root).expanduser().resolve()
    if not root.is_dir():
        return errors + ["project root does not exist"]
    manifest_path: Path | None = None
    manifest: dict[str, Any] = {}
    if args.manifest:
        manifest_path = Path(args.manifest).expanduser().resolve()
        try:
            manifest_path.relative_to(root)
        except ValueError:
            return errors + ["manifest must stay within project root"]
        try:
            manifest = load_json(manifest_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return errors + [f"invalid manifest: {exc}"]
        if manifest.get("schema_version") != 2:
            errors.append("receipt v3 requires manifest schema_version 2")
        project_errors, _ = validate_project_contract(root, manifest)
        errors.extend(
            f"project contract: {error}" for error in project_errors
        )
        project = manifest.get("project")
        if not isinstance(project, dict) or project.get(
            "id"
        ) != receipt.get("project_id"):
            errors.append("receipt project_id does not match manifest")
    elif not getattr(args, "goal_state", None):
        errors.append(
            "receipt v3 requires --manifest unless a manifest-less "
            "--goal-state is fully verified"
        )

    scope = receipt.get("scope")
    if not isinstance(scope, dict):
        return errors + ["scope must be an object"]
    reject_unknown_keys(scope, SCOPE_FIELDS, "scope", errors)
    capabilities = unique_nonempty_strings(
        scope.get("capabilities"), "scope.capabilities", errors
    )
    analysis_control_ids = unique_nonempty_strings(
        scope.get("analysis_control_ids"),
        "scope.analysis_control_ids",
        errors,
    )
    if analysis_control_ids and "analysis-input-binding" not in capabilities:
        errors.append(
            "analysis_control_ids require analysis-input-binding scope"
        )
    assurance = scope.get("assurance")
    if assurance not in ASSURANCE_LEVELS:
        errors.append(
            "scope.assurance must be one of " + ", ".join(ASSURANCE_LEVELS)
        )
        assurance = "light"
    explicit_delivery = scope.get("delivery")
    if (
        explicit_delivery is not None
        and explicit_delivery not in DELIVERY_LEVELS
    ):
        errors.append(
            "scope.delivery must be one of " + ", ".join(DELIVERY_LEVELS)
        )
    remote_actions = scope.get("remote_actions")
    if not isinstance(remote_actions, bool):
        errors.append("scope.remote_actions must be boolean")
        remote_actions = False
    receipt_delivery = effective_delivery(
        assurance,
        capabilities,
        explicit=explicit_delivery,
        remote_actions=remote_actions,
    )

    goal_info = validate_goal_binding(
        receipt,
        getattr(args, "goal_state", None),
        root,
        manifest_path,
        errors,
    )
    if manifest_path is None and goal_info is None:
        errors.append(
            "manifest-less evidence requires a valid bound Goal runtime"
        )

    if manifest_path is not None:
        try:
            manifest_context = resolve(manifest)
        except CapabilityError as exc:
            errors.append(f"project context: {exc}")
            manifest_context = {
                "effective_capabilities": [],
                "assurance": "light",
                "delivery": "local",
            }
    elif goal_info is not None:
        state = goal_info["state"]
        proof_policy = state.get("proof_policy")
        state_capabilities = (
            proof_policy.get("required_capabilities", [])
            if isinstance(proof_policy, dict)
            else state.get("required_capabilities", [])
        )
        try:
            manifest_context = resolve(
                {},
                capabilities=state_capabilities,
                assurance=state.get("assurance"),
                delivery=goal_state_delivery(state),
            )
        except CapabilityError as exc:
            errors.append(f"goal-only context: {exc}")
            manifest_context = {
                "effective_capabilities": [],
                "assurance": "light",
                "delivery": "local",
            }
    else:
        manifest_context = {
            "effective_capabilities": [],
            "assurance": "light",
            "delivery": "local",
        }
    allowed_capabilities = set(manifest_context["effective_capabilities"])
    if "agent-team-execution" in capabilities:
        # This runtime capability is proven by the typed bundle below rather
        # than persisted as a project capability.
        allowed_capabilities.add("agent-team-execution")
    if goal_info is not None:
        allowed_capabilities.update(
            goal_info["proven_runtime_capabilities"]
        )
        omitted_runtime = sorted(
            goal_info["proven_runtime_capabilities"] - set(capabilities)
        )
        if omitted_runtime:
            errors.append(
                "receipt scope omits ledger-proven runtime capabilities: "
                + ", ".join(omitted_runtime)
            )
    unsupported = sorted(set(capabilities) - allowed_capabilities)
    if unsupported:
        errors.append(
            "receipt scope capabilities are not active in the verified "
            "project or Goal context: "
            + ", ".join(unsupported)
        )
    if receipt_delivery != manifest_context["delivery"]:
        errors.append(
            "receipt delivery does not match the verified project or Goal "
            "context"
        )
    required_cli = list(getattr(args, "require_capability", []) or [])
    if getattr(args, "require_automation", False):
        required_cli.append("scheduled-automation")
    if getattr(args, "require_release", False):
        required_cli.append("remote-release")
    missing_cli = sorted(set(required_cli) - set(capabilities))
    if missing_cli:
        errors.append(
            "receipt scope is missing CLI-required capabilities: "
            + ", ".join(missing_cli)
        )
    unknown_cli = sorted(
        capability
        for capability in required_cli
        if capability not in PROJECT_CAPABILITIES
        and capability not in RUNTIME_CAPABILITIES
        and not capability.startswith("x-")
    )
    if unknown_cli:
        errors.append(
            "unknown CLI-required capabilities: " + ", ".join(unknown_cli)
        )

    minimum = getattr(args, "minimum_assurance", None)
    ranks = [
        ASSURANCE_RANK[assurance],
        ASSURANCE_RANK[manifest_context["assurance"]],
    ]
    if (
        assurance in ASSURANCE_RANK
        and manifest_context["assurance"] in ASSURANCE_RANK
        and ASSURANCE_RANK[assurance]
        < ASSURANCE_RANK[manifest_context["assurance"]]
    ):
        errors.append(
            "receipt assurance is below the verified context assurance"
        )
    if minimum:
        ranks.append(ASSURANCE_RANK[minimum])
        if ASSURANCE_RANK[assurance] < ASSURANCE_RANK[minimum]:
            errors.append("receipt assurance is below CLI minimum")
    effective_assurance = ASSURANCE_LEVELS[max(ranks)]
    pseudo_manifest = {
        "schema_version": 2,
        "capabilities": capabilities,
        "profiles": [],
        "assurance": effective_assurance,
        "delivery": receipt_delivery,
        "adapters": {},
        "capability_config": manifest.get("capability_config", {}),
    }
    try:
        task_context = resolve(pseudo_manifest)
    except CapabilityError as exc:
        errors.append(f"receipt context: {exc}")
        task_context = {
            "required_gates": [],
            "effective_capabilities": [],
            "assurance": "light",
            "delivery": "local",
        }
    scoped_assurance = task_context.get("assurance")
    if (
        isinstance(scoped_assurance, str)
        and scoped_assurance in ASSURANCE_RANK
        and ASSURANCE_RANK[assurance] < ASSURANCE_RANK[scoped_assurance]
    ):
        errors.append(
            "receipt assurance is below scoped capability assurance"
        )
    standalone_effective = set(
        task_context.get("effective_capabilities", [])
    )
    standalone_effective.discard("agent-team-execution")
    if (
        goal_info is None
        and manifest_path is not None
        and standalone_effective
        != set(manifest_context["effective_capabilities"])
    ):
        errors.append(
            "standalone receipt scope must include all manifest capabilities"
        )

    if "remote-release" in capabilities and not remote_actions:
        errors.append("remote-release completion requires remote_actions=true")
    if remote_actions and "remote-release" not in capabilities:
        errors.append(
            "remote_actions=true requires remote-release in receipt scope"
        )
    expected_delivery = effective_delivery(
        assurance,
        capabilities,
        remote_actions=remote_actions,
    )
    if explicit_delivery in DELIVERY_LEVELS and (
        explicit_delivery != expected_delivery
    ):
        errors.append(
            "scope.delivery conflicts with assurance, capabilities, or "
            "remote_actions"
        )

    required = unique_nonempty_strings(
        receipt.get("required_gates"), "required_gates", errors
    )
    for name in required:
        if not GATE_NAME.fullmatch(name):
            errors.append(f"required gate name is not portable: {name!r}")
    if (
        goal_info is not None
        and goal_info.get("runtime_kind") == "host-ledger-v1"
    ):
        policy = goal_info["state"].get("proof_policy")
        computed = set(
            policy.get("required_gates", [])
            if isinstance(policy, dict)
            else []
        )
    else:
        computed = set(task_context["required_gates"])
    if "agent-team-execution" in capabilities:
        computed.update(CAPABILITY_GATES["agent-team-execution"])
    missing = sorted(computed - set(required))
    if missing:
        errors.append(
            "required_gates omits capability-derived gates: "
            + ", ".join(missing)
        )
    gates = receipt.get("gates")
    if not isinstance(gates, dict):
        errors.append("gates must be an object")
        gates = {}
    for name, gate in gates.items():
        if not isinstance(name, str) or not GATE_NAME.fullmatch(name):
            errors.append(f"gate name is not portable: {name!r}")
        if not isinstance(gate, dict):
            errors.append(f"gate {name!r} must be an object")
            continue
        reject_unknown_keys(gate, GATE_FIELDS, f"gate {name!r}", errors)
        if gate.get("status") != "passed":
            errors.append(
                f"supplied gate {name!r} must be passed, not "
                f"{gate.get('status')!r}"
            )
        validate_evidence_items(
            str(name), gate.get("evidence"), completed, root, errors
        )
    for name in required:
        if name not in gates:
            errors.append(f"required gate {name!r} is missing")

    if goal_info is not None:
        validate_host_ledger_evidence_bindings(
            receipt,
            goal_info,
            gates,
            errors,
        )
    validate_cost(receipt, remote_actions, completed, errors)
    validate_typed_evidence(
        capabilities,
        gates,
        receipt,
        manifest,
        root,
        completed,
        receipt.get("cost_authority"),
        goal_info,
        args,
        errors,
    )
    if "analysis-input-binding" in capabilities:
        if manifest_path is None:
            errors.append(
                "analysis-input-binding evidence requires a bound manifest"
            )
        else:
            validate_input_binding_capture(
                receipt,
                manifest,
                manifest_path,
                root,
                getattr(args, "input_binding_capture", None),
                completed,
                effective_assurance,
                errors,
            )
    elif getattr(args, "input_binding_capture", None):
        errors.append(
            "--input-binding-capture requires analysis-input-binding scope"
        )
    if goal_info is not None:
        validate_acceptance_claims(
            receipt.get("goal_binding"),
            goal_info["state"],
            gates,
            errors,
        )
    validate_context(
        receipt,
        receipt.get("context"),
        root,
        manifest_path,
        goal_info,
        errors,
    )
    return errors


def run(receipt: dict[str, Any], args: Any) -> int:
    errors = validate_receipt(receipt, args)
    if errors:
        print("EVIDENCE RECEIPT FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("EVIDENCE RECEIPT PASSED")
    print(f"project_id={receipt['project_id']}")
    print("validation_scope=capability-derived-v3")
    return 0
