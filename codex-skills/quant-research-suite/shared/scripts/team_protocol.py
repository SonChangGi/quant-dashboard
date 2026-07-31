#!/usr/bin/env python3
"""Validate optional, hash-bound host agent-team execution artifacts.

This module deliberately does not create workers, mutate a project, integrate
changes, or change Goal state.  It validates an immutable Team Run Packet,
worker Delivery Receipts, and the final Team Integration Receipt produced by
the host-native orchestration path.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:
    from capability_model import (
        literal_secret_reasons,
        policy_violations,
        prohibited_paid_data_reasons,
    )
    from goal_primitives import (
        digest,
        file_digest,
        git,
        git_value,
        portable_relative,
        project_binding,
        scope_pattern_selects_git_metadata,
        snapshot_paths,
        strict_json,
        verify_workspace_snapshot,
        workspace_snapshot,
    )
except ImportError:
    from .capability_model import (
        literal_secret_reasons,
        policy_violations,
        prohibited_paid_data_reasons,
    )
    from .goal_primitives import (
        digest,
        file_digest,
        git,
        git_value,
        portable_relative,
        project_binding,
        scope_pattern_selects_git_metadata,
        snapshot_paths,
        strict_json,
        verify_workspace_snapshot,
        workspace_snapshot,
    )


SHA256 = re.compile(r"^[0-9a-f]{64}$")
PORTABLE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
RISK_ASSURANCE_LEVELS = frozenset({"light", "standard", "strict"})
LEGACY_ASSURANCE_LEVELS = RISK_ASSURANCE_LEVELS | frozenset({"release"})
DELIVERY_LEVELS = frozenset({"local", "release"})
ASSIGNMENT_MODES = frozenset(
    {"read_only", "same_workspace_sequential_write", "isolated_write"}
)
DELIVERY_STATUSES = frozenset(
    {"ready_for_integration", "blocked", "failed"}
)
INTEGRATION_STATUSES = frozenset({"ready_for_review", "blocked", "failed"})
ACCEPTED_DISPOSITIONS = frozenset({"integrated", "accepted_read_only"})
ALL_DISPOSITIONS = ACCEPTED_DISPOSITIONS | frozenset(
    {"rejected", "superseded"}
)
GLOB_CHARACTERS = frozenset("*?[")
MAX_FUTURE_CLOCK_SKEW = timedelta(minutes=5)

PACKET_V1_FIELDS = {
    "document_type",
    "schema_version",
    "team_run_id",
    "owner",
    "goal_binding",
    "objective_sha256",
    "project_binding_sha256",
    "baseline",
    "baseline_snapshot",
    "snapshot_policy",
    "assurance",
    "activation_reason",
    "integration_owner",
    "assignments",
    "join",
    "created_at",
    "packet_sha256",
}
PACKET_V2_FIELDS = PACKET_V1_FIELDS | {"delivery"}
ASSIGNMENT_FIELDS = {
    "id",
    "role",
    "objective",
    "non_goals",
    "required",
    "acceptance_ids",
    "depends_on",
    "validation_group",
    "workspace_binding_sha256",
    "baseline_binding",
    "mode",
    "write_scope",
    "protected_scope",
    "expected_checks",
    "expected_evidence",
    "stop_conditions",
}
DELIVERY_FIELDS = {
    "document_type",
    "schema_version",
    "team_run_id",
    "assignment_id",
    "packet_sha256",
    "status",
    "source",
    "baseline_snapshot",
    "final_snapshot",
    "changed_paths",
    "delivery_artifacts",
    "claims",
    "evidence",
    "checks",
    "cleanup",
    "unverified",
    "blockers",
    "completed_at",
    "receipt_sha256",
}
INTEGRATION_FIELDS = {
    "document_type",
    "schema_version",
    "team_run_id",
    "packet_sha256",
    "integration_owner",
    "status",
    "delivery_results",
    "canonical_snapshot",
    "acceptance_claims",
    "evidence",
    "conflicts",
    "unverified",
    "blockers",
    "completed_at",
    "receipt_sha256",
}


def document_hash(value: dict[str, Any], hash_field: str) -> str:
    """Hash a protocol artifact without its schema locator or self hash."""

    unsigned = dict(value)
    unsigned.pop("$schema", None)
    unsigned.pop(hash_field, None)
    return digest(unsigned)


def packet_hash(value: dict[str, Any]) -> str:
    return document_hash(value, "packet_sha256")


def receipt_hash(value: dict[str, Any]) -> str:
    return document_hash(value, "receipt_sha256")


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def is_strict_integer(value: Any, minimum: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= minimum
    )


def is_portable_id(value: Any) -> bool:
    return isinstance(value, str) and PORTABLE_ID.fullmatch(value) is not None


def packet_risk_assurance(packet: dict[str, Any]) -> Any:
    """Return the risk-only assurance represented by a packet version."""

    assurance = packet.get("assurance")
    if packet.get("schema_version") == 1 and assurance == "release":
        return "strict"
    return assurance


def packet_delivery(packet: dict[str, Any]) -> Any:
    """Return the delivery dimension, including explicit v1 compatibility."""

    if packet.get("schema_version") == 2:
        return packet.get("delivery")
    if packet.get("schema_version") == 1:
        return "release" if packet.get("assurance") == "release" else "local"
    return None


def paid_data_prose_issues(
    label: str,
    values: Iterable[Any],
    *,
    allow_reported_violation: bool = False,
) -> list[str]:
    """Apply the shared actionable paid-data guard to typed prose fields."""

    errors: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        for reason in prohibited_paid_data_reasons(
            value,
            allow_reported_violation=allow_reported_violation,
        ):
            errors.append(f"{label} describes prohibited paid data: {reason}")
    return list(dict.fromkeys(errors))


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def is_implausibly_future(value: datetime) -> bool:
    return value.astimezone(timezone.utc) > (
        datetime.now(timezone.utc) + MAX_FUTURE_CLOCK_SKEW
    )


def exact_fields(
    value: Any,
    required: set[str],
    label: str,
    errors: list[str],
    *,
    optional: set[str] | None = None,
) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    optional_fields = optional or {"$schema"}
    observed = set(value)
    missing = sorted(required - observed)
    unknown = sorted(observed - required - optional_fields)
    if missing:
        errors.append(f"{label} is missing fields: " + ", ".join(missing))
    if unknown:
        errors.append(f"{label} contains unknown fields: " + ", ".join(unknown))
    return not missing and not unknown


def unique_strings(
    value: Any,
    label: str,
    errors: list[str],
    *,
    portable_ids: bool = False,
    allow_empty: bool = True,
) -> list[str]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or not all(isinstance(item, str) and item for item in value)
    ):
        qualifier = "non-empty " if not allow_empty else ""
        errors.append(f"{label} must be a {qualifier}array of non-empty strings")
        return []
    if len(value) != len(set(value)):
        errors.append(f"{label} must contain unique values")
    if portable_ids:
        invalid = sorted(
            item for item in value if not is_portable_id(item)
        )
        if invalid:
            errors.append(
                f"{label} contains invalid portable IDs: "
                + ", ".join(invalid)
            )
    return list(value)


def valid_scope_pattern(value: Any) -> bool:
    return (
        isinstance(value, str)
        and "\\" not in value
        and WINDOWS_DRIVE.match(value) is None
        and not value.startswith("//")
        and portable_relative(value)
        and not scope_pattern_selects_git_metadata(value)
        and "\x00" not in value
    )


def scope_patterns(
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool,
) -> list[str]:
    values = unique_strings(value, label, errors, allow_empty=allow_empty)
    invalid = sorted(item for item in values if not valid_scope_pattern(item))
    if invalid:
        errors.append(
            f"{label} contains escaping or reserved patterns: "
            + ", ".join(invalid)
        )
    return values


def valid_changed_path(value: Any) -> bool:
    return (
        isinstance(value, str)
        and "\\" not in value
        and WINDOWS_DRIVE.match(value) is None
        and not value.startswith("//")
        and portable_relative(value)
        and not any(character in value for character in GLOB_CHARACTERS)
        and ".git"
        not in {segment.casefold() for segment in PurePosixPath(value).parts}
    )


def changed_paths(
    value: Any,
    label: str,
    errors: list[str],
) -> list[str]:
    values = unique_strings(value, label, errors)
    invalid = sorted(item for item in values if not valid_changed_path(item))
    if invalid:
        errors.append(
            f"{label} contains escaping, glob, or reserved paths: "
            + ", ".join(invalid)
        )
    if values != sorted(values):
        errors.append(f"{label} must be sorted")
    return values


def excluded_root_path(
    root: Path,
    excluded_root: str | None,
    label: str,
    errors: list[str],
) -> Path | None:
    if excluded_root is None:
        return None
    if not valid_changed_path(excluded_root):
        errors.append(f"{label} must be a portable relative path")
        return None
    current = root
    for segment in PurePosixPath(excluded_root).parts:
        current = current / segment
        if current.is_symlink():
            errors.append(f"{label} must not traverse a symbolic link")
            return None
    try:
        current.resolve(strict=False).relative_to(root.resolve())
    except (OSError, ValueError):
        errors.append(f"{label} escapes the workspace root")
        return None
    if git_value(root, "rev-parse", "--is-inside-work-tree") == "true":
        ignored = git(root, "check-ignore", "-q", "--", excluded_root)
        if ignored.returncode != 0:
            errors.append(f"{label} must be Git-ignored")
            return None
    return current


def snapshot_delta_paths(
    baseline_snapshot: dict[str, Any],
    post_snapshot: dict[str, Any],
) -> list[str]:
    """Return changed paths, suppressing implied parent-directory changes."""

    baseline_paths = snapshot_paths(baseline_snapshot)
    post_paths = snapshot_paths(post_snapshot)
    changed = {
        path
        for path in set(baseline_paths) | set(post_paths)
        if baseline_paths.get(path) != post_paths.get(path)
    }
    retained: list[str] = []
    for path in sorted(changed):
        before = baseline_paths.get(path)
        after = post_paths.get(path)
        directory_change = (
            isinstance(before, dict) and before.get("kind") == "directory"
        ) or (
            isinstance(after, dict) and after.get("kind") == "directory"
        )
        if directory_change and any(
            other != path and other.startswith(path.rstrip("/") + "/")
            for other in changed
        ):
            continue
        retained.append(path)
    return retained


def segment_glob_matches(path: str, pattern: str) -> bool:
    path_segments = tuple(
        segment.casefold() for segment in path.rstrip("/").split("/")
    )
    pattern_segments = tuple(
        segment.casefold() for segment in pattern.rstrip("/").split("/")
    )
    memo: dict[tuple[int, int], bool] = {}

    def visit(pattern_index: int, path_index: int) -> bool:
        key = (pattern_index, path_index)
        if key in memo:
            return memo[key]
        if pattern_index == len(pattern_segments):
            result = path_index == len(path_segments)
        elif pattern_segments[pattern_index] == "**":
            result = visit(pattern_index + 1, path_index) or (
                path_index < len(path_segments)
                and visit(pattern_index, path_index + 1)
            )
        else:
            result = (
                path_index < len(path_segments)
                and fnmatch.fnmatchcase(
                    path_segments[path_index],
                    pattern_segments[pattern_index],
                )
                and visit(pattern_index + 1, path_index + 1)
            )
        memo[key] = result
        return result

    return visit(0, 0)


def path_matches(path: str, patterns: Iterable[str]) -> bool:
    return any(segment_glob_matches(path, pattern) for pattern in patterns)


def literal_prefix(pattern: str) -> tuple[str, ...]:
    prefix: list[str] = []
    for segment in PurePosixPath(pattern).parts:
        if segment == "**" or any(character in segment for character in "*?["):
            break
        prefix.append(segment.casefold())
    return tuple(prefix)


def patterns_may_overlap(first: str, second: str) -> bool:
    """Conservatively prove common simple scopes disjoint.

    A False result is returned only when literal prefixes diverge.  Ambiguous
    wildcard relationships fail closed as possible overlap.
    """

    first_prefix = literal_prefix(first)
    second_prefix = literal_prefix(second)
    shared = min(len(first_prefix), len(second_prefix))
    for index in range(shared):
        if first_prefix[index] != second_prefix[index]:
            return False
    if (
        len(first_prefix) == len(PurePosixPath(first).parts)
        and len(second_prefix) == len(PurePosixPath(second).parts)
    ):
        return first_prefix == second_prefix
    return True


def scopes_may_overlap(first: Iterable[str], second: Iterable[str]) -> bool:
    return any(
        patterns_may_overlap(left, right)
        for left in first
        for right in second
    )


def dependency_closure(
    assignments: dict[str, dict[str, Any]],
    assignment_id: str,
) -> set[str]:
    visited: set[str] = set()
    pending = list(assignments[assignment_id].get("depends_on", []))
    while pending:
        dependency = pending.pop()
        if dependency in visited or dependency not in assignments:
            continue
        visited.add(dependency)
        pending.extend(assignments[dependency].get("depends_on", []))
    return visited


def dependency_issues(
    assignments: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    for assignment_id, assignment in assignments.items():
        dependencies = assignment.get("depends_on", [])
        if not isinstance(dependencies, list):
            continue
        unknown = sorted(set(dependencies) - set(assignments))
        if unknown:
            errors.append(
                f"assignment {assignment_id} has unknown dependencies: "
                + ", ".join(unknown)
            )
        if assignment_id in dependencies:
            errors.append(
                f"assignment {assignment_id} cannot depend on itself"
            )

    colors: dict[str, int] = {}

    def visit(assignment_id: str, trail: list[str]) -> None:
        color = colors.get(assignment_id, 0)
        if color == 2:
            return
        if color == 1:
            cycle_start = trail.index(assignment_id)
            cycle = trail[cycle_start:] + [assignment_id]
            errors.append("assignment dependency cycle: " + " -> ".join(cycle))
            return
        colors[assignment_id] = 1
        assignment = assignments.get(assignment_id, {})
        for dependency in assignment.get("depends_on", []):
            if dependency in assignments:
                visit(dependency, [*trail, assignment_id])
        colors[assignment_id] = 2

    for assignment_id in assignments:
        if colors.get(assignment_id, 0) == 0:
            visit(assignment_id, [])
    return errors


def packet_assignment_map(
    packet: dict[str, Any],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    raw_assignments = packet.get("assignments")
    if not isinstance(raw_assignments, list) or not raw_assignments:
        errors.append("packet.assignments must be a non-empty array")
        return {}
    assignments: dict[str, dict[str, Any]] = {}
    for index, assignment in enumerate(raw_assignments):
        label = f"packet.assignments[{index}]"
        if not exact_fields(assignment, ASSIGNMENT_FIELDS, label, errors):
            continue
        assignment_id = assignment.get("id")
        if not is_portable_id(assignment_id):
            errors.append(f"{label}.id must be a portable ID")
            continue
        if assignment_id in assignments:
            errors.append(f"packet assignment ID is reused: {assignment_id}")
            continue
        if (
            not isinstance(assignment.get("role"), str)
            or not assignment["role"].strip()
        ):
            errors.append(f"{label}.role must be non-empty")
        if (
            not isinstance(assignment.get("objective"), str)
            or not assignment["objective"].strip()
        ):
            errors.append(f"{label}.objective must be non-empty")
        if not isinstance(assignment.get("required"), bool):
            errors.append(f"{label}.required must be boolean")
        unique_strings(
            assignment.get("non_goals"),
            f"{label}.non_goals",
            errors,
        )
        unique_strings(
            assignment.get("acceptance_ids"),
            f"{label}.acceptance_ids",
            errors,
            portable_ids=True,
            allow_empty=False,
        )
        unique_strings(
            assignment.get("depends_on"),
            f"{label}.depends_on",
            errors,
            portable_ids=True,
        )
        validation_group = assignment.get("validation_group")
        if validation_group is not None and not is_portable_id(validation_group):
            errors.append(
                f"{label}.validation_group must be null or a portable ID"
            )
        if not is_sha256(assignment.get("workspace_binding_sha256")):
            errors.append(f"{label}.workspace_binding_sha256 is invalid")
        baseline_binding = assignment.get("baseline_binding")
        if exact_fields(
            baseline_binding,
            {"kind", "assignment_id"},
            f"{label}.baseline_binding",
            errors,
            optional=set(),
        ):
            binding_kind = baseline_binding.get("kind")
            bound_assignment = baseline_binding.get("assignment_id")
            if binding_kind == "packet":
                if bound_assignment is not None:
                    errors.append(
                        f"{label}.baseline_binding packet reference must "
                        "have null assignment_id"
                    )
            elif binding_kind == "assignment_final":
                if not is_portable_id(bound_assignment):
                    errors.append(
                        f"{label}.baseline_binding assignment_id is invalid"
                    )
                elif bound_assignment not in assignment.get("depends_on", []):
                    errors.append(
                        f"{label}.baseline_binding must reference a dependency"
                    )
            else:
                errors.append(f"{label}.baseline_binding kind is invalid")
        mode = assignment.get("mode")
        if mode not in ASSIGNMENT_MODES:
            errors.append(f"{label}.mode is invalid")
        write_scope = scope_patterns(
            assignment.get("write_scope"),
            f"{label}.write_scope",
            errors,
            allow_empty=mode == "read_only",
        )
        protected_scope = scope_patterns(
            assignment.get("protected_scope"),
            f"{label}.protected_scope",
            errors,
            allow_empty=True,
        )
        if mode == "read_only" and write_scope:
            errors.append(f"{label} read-only assignment has write scope")
        if mode != "read_only" and not write_scope:
            errors.append(f"{label} write assignment requires write scope")
        if scopes_may_overlap(write_scope, protected_scope):
            errors.append(
                f"{label} write scope may overlap its protected scope"
            )
        for field in ("expected_checks", "expected_evidence"):
            unique_strings(
                assignment.get(field),
                f"{label}.{field}",
                errors,
                portable_ids=True,
                allow_empty=False,
            )
        unique_strings(
            assignment.get("stop_conditions"),
            f"{label}.stop_conditions",
            errors,
            allow_empty=False,
        )
        assignments[assignment_id] = assignment
    return assignments


def normalize_live_worker_roots(
    worker_roots: Any,
    errors: list[str],
) -> dict[str, Path]:
    """Normalize an assignment-to-root mapping supplied by a trusted caller."""

    if worker_roots is None:
        return {}
    if not isinstance(worker_roots, dict):
        errors.append(
            "live worker roots must be an assignment-to-path mapping"
        )
        return {}
    normalized: dict[str, Path] = {}
    for assignment_id, root_value in worker_roots.items():
        if not is_portable_id(assignment_id):
            errors.append(
                "live worker root mapping contains an invalid assignment ID: "
                f"{assignment_id!r}"
            )
            continue
        try:
            normalized[assignment_id] = Path(root_value)
        except TypeError:
            errors.append(
                "live worker root mapping contains an invalid path for "
                + assignment_id
            )
    return normalized


def resolve_live_directory(
    root: Path,
    label: str,
    errors: list[str],
) -> Path | None:
    expanded = root.expanduser()
    if expanded.is_symlink():
        errors.append(f"{label} must not be a symbolic link")
        return None
    try:
        resolved = expanded.resolve(strict=True)
    except OSError as exc:
        errors.append(f"{label} is unavailable: {exc}")
        return None
    if not resolved.is_dir():
        errors.append(f"{label} must be a directory")
        return None
    return resolved


def same_physical_directory(first: Path, second: Path) -> bool:
    try:
        return first.samefile(second)
    except OSError:
        return first.resolve(strict=False) == second.resolve(strict=False)


def validate_worker_preflight(
    packet: dict[str, Any],
    assignments: dict[str, dict[str, Any]],
    worker_roots: dict[str, Path],
    *,
    project_root: Path | None,
    workspace_root: Path | None,
    excluded_root: str | None,
    protected_patterns: list[str],
    required: bool,
    errors: list[str],
) -> None:
    """Bind structured writers to live roots before any worker mutation."""

    writer_ids = {
        assignment_id
        for assignment_id, assignment in assignments.items()
        if assignment.get("mode") != "read_only"
    }
    unknown_ids = sorted(set(worker_roots) - set(assignments))
    if unknown_ids:
        errors.append(
            "worker preflight has unknown assignment roots: "
            + ", ".join(unknown_ids)
        )
    if required:
        missing_ids = sorted(writer_ids - set(worker_roots))
        if missing_ids:
            errors.append(
                "worker preflight is missing writer roots: "
                + ", ".join(missing_ids)
            )
        if project_root is None or workspace_root is None:
            errors.append(
                "worker preflight requires exact project and issuance "
                "workspace roots"
            )

    canonical_binding = (
        project_binding(project_root) if project_root is not None else None
    )
    packet_baseline = packet.get("baseline", {}).get("workspace_sha256")
    resolved_roots: dict[str, Path] = {}
    for assignment_id, root in worker_roots.items():
        assignment = assignments.get(assignment_id)
        if assignment is None:
            continue
        resolved = resolve_live_directory(
            root,
            "worker preflight root " + assignment_id,
            errors,
        )
        if resolved is None:
            continue
        resolved_roots[assignment_id] = resolved
        observed_binding = project_binding(resolved)
        if observed_binding.get("identity_sha256") != assignment.get(
            "workspace_binding_sha256"
        ):
            errors.append(
                "worker preflight root binding does not match assignment: "
                + assignment_id
            )

        if canonical_binding is not None:
            canonical_git = canonical_binding.get("git_common_dir_realpath")
            worker_git = observed_binding.get("git_common_dir_realpath")
            canonical_origin = canonical_binding.get(
                "origin_fingerprint_sha256"
            )
            worker_origin = observed_binding.get("origin_fingerprint_sha256")
            if (canonical_git is None) != (worker_git is None):
                errors.append(
                    "worker preflight project kind does not match canonical "
                    "project: " + assignment_id
                )
            elif (
                canonical_git is not None
                and worker_git is not None
                and canonical_git != worker_git
                and (
                    canonical_origin is None
                    or worker_origin is None
                    or canonical_origin != worker_origin
                )
            ):
                errors.append(
                    "worker preflight project lineage does not match canonical "
                    "project: " + assignment_id
                )

        selected_excluded_root = excluded_root_path(
            resolved,
            excluded_root,
            "worker preflight excluded root " + assignment_id,
            errors,
        )
        try:
            observed_snapshot = workspace_snapshot(
                resolved,
                selected_excluded_root,
                protected_patterns,
                snapshot_version=2,
            )
        except (OSError, ValueError) as exc:
            errors.append(
                "worker preflight could not capture baseline for "
                f"{assignment_id}: {exc}"
            )
        else:
            if observed_snapshot.get("sha256") != packet_baseline:
                errors.append(
                    "worker preflight baseline does not match packet issuance "
                    "baseline: " + assignment_id
                )

    resolved_workspace = (
        resolve_live_directory(
            workspace_root,
            "worker preflight issuance workspace root",
            errors,
        )
        if required and workspace_root is not None
        else workspace_root
    )
    write_root_ids = sorted(writer_ids & set(resolved_roots))
    for assignment_id in write_root_ids:
        assignment = assignments[assignment_id]
        root = resolved_roots[assignment_id]
        if (
            assignment.get("mode") == "isolated_write"
            and resolved_workspace is not None
            and same_physical_directory(root, resolved_workspace)
        ):
            errors.append(
                "isolated writer root must be physically separate from the "
                "issuance workspace: " + assignment_id
            )

    for index, first_id in enumerate(write_root_ids):
        for second_id in write_root_ids[index + 1 :]:
            first_mode = assignments[first_id].get("mode")
            second_mode = assignments[second_id].get("mode")
            same_root = same_physical_directory(
                resolved_roots[first_id],
                resolved_roots[second_id],
            )
            if "isolated_write" in {first_mode, second_mode} and same_root:
                errors.append(
                    "isolated writer roots must be physically distinct: "
                    f"{first_id}, {second_id}"
                )
            if (
                first_mode == "same_workspace_sequential_write"
                and second_mode == "same_workspace_sequential_write"
                and not same_root
            ):
                errors.append(
                    "same-workspace writer roots must be physically identical: "
                    f"{first_id}, {second_id}"
                )


def validate_packet(
    packet: dict[str, Any],
    *,
    project_root: Path | None = None,
    workspace_root: Path | None = None,
    worker_roots: dict[str, Path] | None = None,
    require_worker_preflight: bool = False,
) -> list[str]:
    errors: list[str] = []
    schema_version = packet.get("schema_version")
    packet_fields = (
        PACKET_V1_FIELDS
        if schema_version == 1
        else PACKET_V2_FIELDS
        if schema_version == 2
        else PACKET_V2_FIELDS
    )
    exact_fields(packet, packet_fields, "packet", errors)
    if packet.get("document_type") != "quant_team_run_packet":
        errors.append("packet document_type is invalid")
    if (
        not is_strict_integer(schema_version, 1)
        or schema_version not in {1, 2}
    ):
        errors.append("packet schema_version must equal 1 or 2")
    if not is_portable_id(packet.get("team_run_id")):
        errors.append("packet team_run_id must be a portable ID")
    owner = packet.get("owner")
    if owner not in {"standalone_developer", "goal"}:
        errors.append("packet owner is invalid")
    goal_binding = packet.get("goal_binding")
    if owner == "goal":
        if not exact_fields(
            goal_binding,
            {"goal_id", "plan_revision", "acceptance_revision"},
            "packet.goal_binding",
            errors,
            optional=set(),
        ):
            pass
        elif (
            not is_portable_id(goal_binding.get("goal_id"))
            or not is_strict_integer(
                goal_binding.get("plan_revision"),
                0,
            )
            or not is_strict_integer(
                goal_binding.get("acceptance_revision"),
                1,
            )
        ):
            errors.append("packet goal_binding is invalid")
    elif goal_binding is not None:
        errors.append("standalone packet goal_binding must be null")
    if not is_sha256(packet.get("objective_sha256")):
        errors.append("packet objective_sha256 is invalid")
    if not is_sha256(packet.get("project_binding_sha256")):
        errors.append("packet project_binding_sha256 is invalid")
    raw_baseline = packet.get("baseline")
    if exact_fields(
        raw_baseline,
        {"workspace_sha256", "head", "branch"},
        "packet.baseline",
        errors,
        optional=set(),
    ):
        if not is_sha256(raw_baseline.get("workspace_sha256")):
            errors.append("packet baseline workspace_sha256 is invalid")
        for field in ("head", "branch"):
            value = raw_baseline.get(field)
            if value is not None and (
                not isinstance(value, str) or not value.strip()
            ):
                errors.append(f"packet baseline {field} is invalid")
    baseline = raw_baseline if isinstance(raw_baseline, dict) else {}
    baseline_snapshot = packet.get("baseline_snapshot")
    if not isinstance(baseline_snapshot, dict):
        errors.append("packet baseline_snapshot must be an object")
        baseline_snapshot = {}
    else:
        if not verify_workspace_snapshot(baseline_snapshot):
            errors.append("packet baseline_snapshot hash is invalid")
        if baseline_snapshot.get("snapshot_version") != 2:
            errors.append("packet baseline_snapshot must use version 2")
        if baseline_snapshot.get("sha256") != baseline.get(
            "workspace_sha256"
        ):
            errors.append(
                "packet baseline_snapshot does not match baseline identity"
            )
        for field in ("head", "branch"):
            if baseline_snapshot.get(field) != baseline.get(field):
                errors.append(
                    f"packet baseline_snapshot {field} does not match baseline"
                )
    assurance = packet.get("assurance")
    if schema_version == 1:
        if assurance not in LEGACY_ASSURANCE_LEVELS:
            errors.append("legacy packet assurance is invalid")
    else:
        if assurance not in RISK_ASSURANCE_LEVELS:
            errors.append(
                "packet v2 assurance must be light, standard, or strict"
            )
        if packet.get("delivery") not in DELIVERY_LEVELS:
            errors.append("packet v2 delivery must be local or release")
    if (
        not isinstance(packet.get("activation_reason"), str)
        or not packet["activation_reason"].strip()
    ):
        errors.append("packet activation_reason is required")
    errors.extend(
        paid_data_prose_issues(
            "packet instructions",
            [packet.get("activation_reason")],
        )
    )
    if not is_portable_id(packet.get("integration_owner")):
        errors.append("packet integration_owner must be a portable ID")
    assignments = packet_assignment_map(packet, errors)
    for assignment_id, assignment in assignments.items():
        non_goals = assignment.get("non_goals")
        stop_conditions = assignment.get("stop_conditions")
        errors.extend(
            paid_data_prose_issues(
                f"packet assignment {assignment_id} instructions",
                [
                    assignment.get("objective"),
                    *(non_goals if isinstance(non_goals, list) else []),
                    *(
                        stop_conditions
                        if isinstance(stop_conditions, list)
                        else []
                    ),
                ],
            )
        )
    errors.extend(dependency_issues(assignments))
    snapshot_policy = packet.get("snapshot_policy")
    protected_patterns: list[str] = []
    excluded_root: str | None = None
    if exact_fields(
        snapshot_policy,
        {"snapshot_version", "excluded_root", "protected_patterns"},
        "packet.snapshot_policy",
        errors,
        optional=set(),
    ):
        if snapshot_policy.get("snapshot_version") != 2:
            errors.append("packet snapshot_policy version must equal 2")
        excluded_root = snapshot_policy.get("excluded_root")
        if excluded_root is not None and not valid_changed_path(excluded_root):
            errors.append(
                "packet snapshot_policy excluded_root must be a portable path"
            )
        protected_patterns = scope_patterns(
            snapshot_policy.get("protected_patterns"),
            "packet.snapshot_policy.protected_patterns",
            errors,
            allow_empty=True,
        )
        expected_protected = sorted(
            {
                pattern
                for assignment in assignments.values()
                for pattern in assignment.get("protected_scope", [])
            }
        )
        if protected_patterns != expected_protected:
            errors.append(
                "packet snapshot policy must contain the sorted union of "
                "assignment protected scopes"
            )
        if baseline_snapshot.get("protected_patterns") != protected_patterns:
            errors.append(
                "packet baseline_snapshot protected patterns do not match policy"
            )
        if excluded_root is not None:
            excluded_scope = [
                excluded_root,
                excluded_root.rstrip("/") + "/**",
            ]
            for assignment_id, assignment in assignments.items():
                if scopes_may_overlap(
                    assignment.get("write_scope", []), excluded_scope
                ):
                    errors.append(
                        "assignment write scope may overlap excluded root: "
                        + assignment_id
                    )

    closures = {
        assignment_id: dependency_closure(assignments, assignment_id)
        for assignment_id in assignments
    }
    write_ids = sorted(
        assignment_id
        for assignment_id, assignment in assignments.items()
        if assignment.get("mode") != "read_only"
    )
    for index, first_id in enumerate(write_ids):
        for second_id in write_ids[index + 1 :]:
            ordered = (
                first_id in closures.get(second_id, set())
                or second_id in closures.get(first_id, set())
            )
            first = assignments[first_id]
            second = assignments[second_id]
            if not ordered and (
                first.get("mode") == "same_workspace_sequential_write"
                or second.get("mode") == "same_workspace_sequential_write"
            ):
                errors.append(
                    "unordered same-workspace write assignments: "
                    f"{first_id}, {second_id}"
                )
            if not ordered and scopes_may_overlap(
                first.get("write_scope", []),
                second.get("write_scope", []),
            ):
                errors.append(
                    "concurrent write scopes may overlap: "
                    f"{first_id}, {second_id}"
                )

    join = packet.get("join")
    if exact_fields(
        join,
        {"integration_order", "verification", "review_boundary"},
        "packet.join",
        errors,
        optional=set(),
    ):
        order = unique_strings(
            join.get("integration_order"),
            "packet.join.integration_order",
            errors,
            portable_ids=True,
            allow_empty=False,
        )
        if set(order) != set(assignments) or len(order) != len(assignments):
            errors.append(
                "packet join integration_order must contain every assignment"
            )
        positions = {assignment_id: index for index, assignment_id in enumerate(order)}
        for assignment_id, assignment in assignments.items():
            for dependency in assignment.get("depends_on", []):
                if (
                    assignment_id in positions
                    and dependency in positions
                    and positions[dependency] >= positions[assignment_id]
                ):
                    errors.append(
                        "packet join order violates dependency: "
                        f"{dependency} -> {assignment_id}"
                    )
        unique_strings(
            join.get("verification"),
            "packet.join.verification",
            errors,
            portable_ids=True,
            allow_empty=False,
        )
        if join.get("review_boundary") != "integrated_frozen_snapshot":
            errors.append("packet join review_boundary is invalid")
        same_workspace_order = [
            assignment_id
            for assignment_id in order
            if assignments.get(assignment_id, {}).get("mode")
            == "same_workspace_sequential_write"
        ]
        same_workspace_bindings = {
            assignments[assignment_id].get("workspace_binding_sha256")
            for assignment_id in same_workspace_order
        }
        if len(same_workspace_bindings) > 1:
            errors.append(
                "same-workspace assignments must share one workspace binding"
            )
        for index, assignment_id in enumerate(same_workspace_order):
            selected = assignments[assignment_id]
            if index == 0:
                if selected.get("baseline_binding") != {
                    "kind": "packet",
                    "assignment_id": None,
                }:
                    errors.append(
                        "first same-workspace assignment must bind the packet "
                        "baseline: " + assignment_id
                    )
                continue
            predecessor = same_workspace_order[index - 1]
            if predecessor not in closures.get(assignment_id, set()):
                errors.append(
                    "same-workspace assignment must depend on its write "
                    f"predecessor: {predecessor} -> {assignment_id}"
                )
            if selected.get("baseline_binding") != {
                "kind": "assignment_final",
                "assignment_id": predecessor,
            }:
                errors.append(
                    "same-workspace assignment baseline must bind its write "
                    f"predecessor: {predecessor} -> {assignment_id}"
                )
    packet_created_at = parse_time(packet.get("created_at"))
    if packet_created_at is None:
        errors.append("packet created_at must be timezone-aware ISO-8601")
    elif is_implausibly_future(packet_created_at):
        errors.append("packet created_at exceeds allowed future clock skew")
    resolved_project_root: Path | None = None
    if project_root is not None:
        expanded_project_root = project_root.expanduser()
        if expanded_project_root.is_symlink():
            errors.append("packet project root must not be a symbolic link")
        else:
            try:
                resolved_project_root = expanded_project_root.resolve(strict=True)
                if not resolved_project_root.is_dir():
                    raise ValueError("packet project root must be a directory")
                if project_binding(resolved_project_root).get(
                    "identity_sha256"
                ) != packet.get("project_binding_sha256"):
                    errors.append(
                        "packet project binding does not match project root"
                    )
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
                resolved_project_root = None
    resolved_workspace_root: Path | None = None
    if workspace_root is not None:
        expanded_workspace_root = workspace_root.expanduser()
        if expanded_workspace_root.is_symlink():
            errors.append("packet workspace root must not be a symbolic link")
        else:
            try:
                resolved_workspace_root = expanded_workspace_root.resolve(
                    strict=True
                )
                if not resolved_workspace_root.is_dir():
                    raise ValueError(
                        "packet workspace root must be a directory"
                    )
                selected_excluded_root = excluded_root_path(
                    resolved_workspace_root,
                    excluded_root,
                    "packet snapshot_policy excluded_root",
                    errors,
                )
                issuance_snapshot = workspace_snapshot(
                    resolved_workspace_root,
                    selected_excluded_root,
                    protected_patterns,
                    snapshot_version=2,
                )
                if issuance_snapshot.get("sha256") != baseline.get(
                    "workspace_sha256"
                ):
                    errors.append(
                        "packet baseline does not match workspace root"
                    )
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
                resolved_workspace_root = None
    live_worker_roots = normalize_live_worker_roots(worker_roots, errors)
    if live_worker_roots or require_worker_preflight:
        validate_worker_preflight(
            packet,
            assignments,
            live_worker_roots,
            project_root=resolved_project_root,
            workspace_root=resolved_workspace_root,
            excluded_root=excluded_root,
            protected_patterns=protected_patterns,
            required=require_worker_preflight,
            errors=errors,
        )
    if packet.get("packet_sha256") != packet_hash(packet):
        errors.append("packet SHA-256 is invalid")
    errors.extend(f"packet policy: {issue}" for issue in policy_violations(packet))
    return list(dict.fromkeys(errors))


def safe_artifact_path(
    artifact_root: Path,
    reference: str,
    label: str,
    errors: list[str],
) -> Path | None:
    if not valid_changed_path(reference):
        errors.append(f"{label} must be a portable artifact-relative path")
        return None
    expanded_root = artifact_root.expanduser()
    if expanded_root.is_symlink():
        errors.append("artifact root must not be a symbolic link")
        return None
    try:
        root = expanded_root.resolve(strict=True)
    except OSError:
        errors.append("artifact root is missing")
        return None
    if not root.is_dir():
        errors.append("artifact root must be a directory")
        return None
    candidate = root / reference
    current = root
    for segment in PurePosixPath(reference).parts:
        current = current / segment
        if current.is_symlink():
            errors.append(f"{label} must not traverse a symbolic link")
            return None
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        errors.append(f"{label} is missing or escapes the artifact root")
        return None
    if not resolved.is_file():
        errors.append(f"{label} must reference a regular file")
        return None
    return resolved


def validate_evidence_items(
    value: Any,
    label: str,
    artifact_ids: set[str],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return {}
    result: dict[str, dict[str, Any]] = {}
    fields = {"id", "kind", "status", "summary", "artifact_ids"}
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not exact_fields(item, fields, item_label, errors, optional=set()):
            continue
        evidence_id = item.get("id")
        if not is_portable_id(evidence_id):
            errors.append(f"{item_label}.id must be a portable ID")
            continue
        if evidence_id in result:
            errors.append(f"{label} reuses evidence ID: {evidence_id}")
            continue
        if item.get("kind") not in {"command", "inspection", "artifact"}:
            errors.append(f"{item_label}.kind is invalid")
        if item.get("status") not in {"passed", "failed", "unverified"}:
            errors.append(f"{item_label}.status is invalid")
        if (
            not isinstance(item.get("summary"), str)
            or not item["summary"].strip()
        ):
            errors.append(f"{item_label}.summary must be non-empty")
        references = unique_strings(
            item.get("artifact_ids"),
            f"{item_label}.artifact_ids",
            errors,
            portable_ids=True,
        )
        unknown = sorted(set(references) - artifact_ids)
        if unknown:
            errors.append(
                f"{item_label} references unknown artifacts: "
                + ", ".join(unknown)
            )
        result[evidence_id] = item
    return result


def validate_claims(
    value: Any,
    label: str,
    allowed_acceptance: set[str],
    evidence_ids: set[str],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return {}
    result: dict[str, dict[str, Any]] = {}
    fields = {"acceptance_id", "status", "evidence_ids"}
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not exact_fields(item, fields, item_label, errors, optional=set()):
            continue
        acceptance_id = item.get("acceptance_id")
        if not is_portable_id(acceptance_id):
            errors.append(f"{item_label}.acceptance_id is invalid")
            continue
        if acceptance_id in result:
            errors.append(f"{label} reuses acceptance ID: {acceptance_id}")
            continue
        if acceptance_id not in allowed_acceptance:
            errors.append(
                f"{item_label} references unknown acceptance ID: "
                f"{acceptance_id}"
            )
        if item.get("status") not in {"passed", "failed", "unverified"}:
            errors.append(f"{item_label}.status is invalid")
        references = unique_strings(
            item.get("evidence_ids"),
            f"{item_label}.evidence_ids",
            errors,
            portable_ids=True,
            allow_empty=False,
        )
        unknown = sorted(set(references) - evidence_ids)
        if unknown:
            errors.append(
                f"{item_label} references unknown evidence: "
                + ", ".join(unknown)
            )
        result[acceptance_id] = item
    return result


def validate_delivery(
    packet: dict[str, Any],
    delivery: dict[str, Any],
    *,
    artifact_root: Path | None = None,
    worker_root: Path | None = None,
    structural_only: bool = False,
) -> list[str]:
    errors = [f"packet: {issue}" for issue in validate_packet(packet)]
    exact_fields(delivery, DELIVERY_FIELDS, "delivery", errors)
    if delivery.get("document_type") != "quant_worker_delivery_receipt":
        errors.append("delivery document_type is invalid")
    if delivery.get("schema_version") != 1:
        errors.append("delivery schema_version must equal 1")
    if delivery.get("team_run_id") != packet.get("team_run_id"):
        errors.append("delivery team_run_id mismatch")
    if delivery.get("packet_sha256") != packet.get("packet_sha256"):
        errors.append("delivery packet_sha256 mismatch")
    assignment_id = delivery.get("assignment_id")
    assignments = {
        item.get("id"): item
        for item in packet.get("assignments", [])
        if isinstance(item, dict) and is_portable_id(item.get("id"))
    }
    assignment = assignments.get(assignment_id)
    if not isinstance(assignment, dict):
        errors.append("delivery references unknown assignment")
        assignment = {}
    status = delivery.get("status")
    if status not in DELIVERY_STATUSES:
        errors.append("delivery status is invalid")
    source = delivery.get("source")
    if exact_fields(
        source,
        {
            "project_binding_sha256",
            "workspace_binding_sha256",
            "baseline_workspace_sha256",
            "final_workspace_sha256",
        },
        "delivery.source",
        errors,
        optional=set(),
    ):
        for field in (
            "project_binding_sha256",
            "workspace_binding_sha256",
            "baseline_workspace_sha256",
            "final_workspace_sha256",
        ):
            if not is_sha256(source.get(field)):
                errors.append(f"delivery source {field} is invalid")
        if source.get("project_binding_sha256") != packet.get(
            "project_binding_sha256"
        ):
            errors.append(
                "delivery project binding does not match packet project binding"
            )
        if source.get("workspace_binding_sha256") != assignment.get(
            "workspace_binding_sha256"
        ):
            errors.append(
                "delivery workspace binding does not match assignment"
            )
        baseline_binding = assignment.get("baseline_binding", {})
        if (
            baseline_binding.get("kind") == "packet"
            and source.get("baseline_workspace_sha256")
            != packet.get("baseline", {}).get("workspace_sha256")
        ):
            errors.append(
                "delivery baseline does not match packet-bound assignment"
            )

    delivery_snapshots: dict[str, dict[str, Any]] = {}
    policy = packet.get("snapshot_policy", {})
    protected_patterns = (
        policy.get("protected_patterns", [])
        if isinstance(policy, dict)
        else []
    )
    for field, source_field in (
        ("baseline_snapshot", "baseline_workspace_sha256"),
        ("final_snapshot", "final_workspace_sha256"),
    ):
        snapshot_value = delivery.get(field)
        if not isinstance(snapshot_value, dict):
            errors.append(f"delivery {field} must be an object")
            continue
        delivery_snapshots[field] = snapshot_value
        if not verify_workspace_snapshot(snapshot_value):
            errors.append(f"delivery {field} hash is invalid")
        if snapshot_value.get("snapshot_version") != 2:
            errors.append(f"delivery {field} must use snapshot version 2")
        if snapshot_value.get("protected_patterns") != protected_patterns:
            errors.append(
                f"delivery {field} protected patterns do not match packet policy"
            )
        if snapshot_value.get("sha256") != (
            source.get(source_field) if isinstance(source, dict) else None
        ):
            errors.append(
                f"delivery {field} does not match source {source_field}"
            )

    paths = changed_paths(
        delivery.get("changed_paths"), "delivery.changed_paths", errors
    )
    mode = assignment.get("mode")
    write_scope = assignment.get("write_scope", [])
    protected_scope = assignment.get("protected_scope", [])
    if mode == "read_only" and paths:
        errors.append("read-only delivery changed paths")
    if status == "ready_for_integration" and mode != "read_only" and not paths:
        errors.append("ready write delivery must contain changed paths")
    outside = sorted(path for path in paths if not path_matches(path, write_scope))
    protected = sorted(
        path for path in paths if path_matches(path, protected_scope)
    )
    if outside:
        errors.append(
            "delivery changes outside assignment write scope: "
            + ", ".join(outside)
        )
    if protected:
        errors.append(
            "delivery changes protected scope: " + ", ".join(protected)
        )
    if {
        "baseline_snapshot",
        "final_snapshot",
    }.issubset(delivery_snapshots):
        observed_delivery_delta = snapshot_delta_paths(
            delivery_snapshots["baseline_snapshot"],
            delivery_snapshots["final_snapshot"],
        )
        if observed_delivery_delta != paths:
            errors.append(
                "delivery changed paths do not match its baseline-to-final delta"
            )

    raw_artifacts = delivery.get("delivery_artifacts")
    artifacts: dict[str, dict[str, Any]] = {}
    artifact_text_scannable: dict[str, bool] = {}
    external_scan_evidence: dict[str, str] = {}
    if not isinstance(raw_artifacts, list):
        errors.append("delivery.delivery_artifacts must be an array")
    else:
        fields = {"id", "kind", "ref", "sha256", "secret_scan"}
        for index, artifact in enumerate(raw_artifacts):
            label = f"delivery.delivery_artifacts[{index}]"
            if not exact_fields(
                artifact, fields, label, errors, optional=set()
            ):
                continue
            artifact_id = artifact.get("id")
            if not is_portable_id(artifact_id):
                errors.append(f"{label}.id must be a portable ID")
                continue
            if artifact_id in artifacts:
                errors.append(
                    "delivery reuses artifact ID: " + artifact_id
                )
                continue
            if artifact.get("kind") not in {
                "patch",
                "commit_bundle",
                "artifact",
                "report",
            }:
                errors.append(f"{label}.kind is invalid")
            reference = artifact.get("ref")
            if not isinstance(reference, str) or not reference:
                errors.append(f"{label}.ref must be non-empty")
            elif not valid_changed_path(reference):
                errors.append(
                    f"{label}.ref must be a portable artifact-relative path"
                )
            if not is_sha256(artifact.get("sha256")):
                errors.append(f"{label}.sha256 is invalid")
            secret_scan = artifact.get("secret_scan")
            if exact_fields(
                secret_scan,
                {"mode", "evidence_id"},
                f"{label}.secret_scan",
                errors,
                optional=set(),
            ):
                scan_mode = secret_scan.get("mode")
                scan_evidence_id = secret_scan.get("evidence_id")
                if scan_mode == "validated_text":
                    if scan_evidence_id is not None:
                        errors.append(
                            f"{label}.secret_scan validated_text must have "
                            "null evidence_id"
                        )
                elif scan_mode == "external_scan":
                    if not is_portable_id(scan_evidence_id):
                        errors.append(
                            f"{label}.secret_scan evidence_id is invalid"
                        )
                    elif is_portable_id(artifact_id):
                        external_scan_evidence[artifact_id] = scan_evidence_id
                else:
                    errors.append(f"{label}.secret_scan mode is invalid")
            if artifact_root is not None and isinstance(reference, str):
                artifact_path = safe_artifact_path(
                    artifact_root,
                    reference,
                    f"{label}.ref",
                    errors,
                )
                if (
                    artifact_path is not None
                    and artifact.get("sha256") != file_digest(artifact_path)
                ):
                    errors.append(f"{label}.sha256 does not match artifact bytes")
                if artifact_path is not None:
                    payload = artifact_path.read_bytes()
                    decoded: str | None = None
                    if artifact.get("kind") != "commit_bundle":
                        try:
                            decoded = payload.decode("utf-8")
                        except UnicodeDecodeError:
                            decoded = None
                    scannable = decoded is not None
                    if is_portable_id(artifact_id):
                        artifact_text_scannable[artifact_id] = scannable
                    expected_mode = (
                        "validated_text" if scannable else "external_scan"
                    )
                    if isinstance(secret_scan, dict) and secret_scan.get(
                        "mode"
                    ) != expected_mode:
                        errors.append(
                            f"{label}.secret_scan mode does not match "
                            "artifact bytes"
                        )
                    if decoded is not None:
                        for issue in literal_secret_reasons(decoded):
                            errors.append(
                                f"{label} artifact bytes {issue}"
                            )
            artifacts[artifact_id] = artifact
    if status == "ready_for_integration":
        if not artifacts:
            errors.append("ready delivery requires a delivery artifact")
        if artifact_root is None:
            errors.append(
                "ready delivery requires artifact-root byte verification"
            )
        if worker_root is None and not structural_only:
            errors.append(
                "ready delivery requires worker-root final snapshot verification"
            )
        elif worker_root is not None:
            expanded_worker_root = worker_root.expanduser()
            if expanded_worker_root.is_symlink():
                errors.append("worker root must not be a symbolic link")
            else:
                try:
                    resolved_worker_root = expanded_worker_root.resolve(
                        strict=True
                    )
                    if not resolved_worker_root.is_dir():
                        raise ValueError("worker root must be a directory")
                    if project_binding(resolved_worker_root).get(
                        "identity_sha256"
                    ) != assignment.get("workspace_binding_sha256"):
                        errors.append(
                            "worker root binding does not match assignment"
                        )
                    selected_excluded_root = excluded_root_path(
                        resolved_worker_root,
                        policy.get("excluded_root")
                        if isinstance(policy, dict)
                        else None,
                        "packet snapshot_policy excluded_root",
                        errors,
                    )
                    observed_final = workspace_snapshot(
                        resolved_worker_root,
                        selected_excluded_root,
                        protected_patterns,
                        snapshot_version=2,
                    )
                    if observed_final.get("sha256") != delivery_snapshots.get(
                        "final_snapshot", {}
                    ).get("sha256"):
                        errors.append(
                            "worker root snapshot does not match delivery final"
                        )
                except (OSError, ValueError) as exc:
                    errors.append(str(exc))

    evidence = validate_evidence_items(
        delivery.get("evidence"),
        "delivery.evidence",
        set(artifacts),
        errors,
    )
    if status == "ready_for_integration":
        for artifact_id, artifact in artifacts.items():
            if artifact_text_scannable.get(artifact_id) is not False:
                continue
            evidence_id = external_scan_evidence.get(artifact_id)
            scan_evidence = evidence.get(evidence_id, {})
            references = set(scan_evidence.get("artifact_ids", []))
            report_ids = {
                reference
                for reference in references
                if reference != artifact_id
                and artifacts.get(reference, {}).get("kind") == "report"
                and artifact_text_scannable.get(reference) is True
            }
            if (
                scan_evidence.get("status") != "passed"
                or artifact_id not in references
                or not report_ids
            ):
                errors.append(
                    "ready delivery unscannable artifact lacks passed "
                    "external secret-scan evidence and a validated text "
                    "report: " + artifact_id
                )
    claims = validate_claims(
        delivery.get("claims"),
        "delivery.claims",
        set(assignment.get("acceptance_ids", [])),
        set(evidence),
        errors,
    )
    raw_checks = delivery.get("checks")
    checks: list[dict[str, Any]] = []
    check_ids: set[str] = set()
    if not isinstance(raw_checks, list):
        errors.append("delivery.checks must be an array")
    else:
        fields = {"id", "summary", "status", "evidence_ids"}
        seen: set[str] = set()
        for index, check in enumerate(raw_checks):
            label = f"delivery.checks[{index}]"
            if not exact_fields(check, fields, label, errors, optional=set()):
                continue
            check_id = check.get("id")
            if not is_portable_id(check_id):
                errors.append(f"{label}.id must be a portable ID")
            elif check_id in seen:
                errors.append(f"delivery reuses check ID: {check_id}")
            else:
                seen.add(check_id)
                check_ids.add(check_id)
            if (
                not isinstance(check.get("summary"), str)
                or not check["summary"].strip()
            ):
                errors.append(f"{label}.summary must be non-empty")
            if check.get("status") not in {"passed", "failed", "unverified"}:
                errors.append(f"{label}.status is invalid")
            references = unique_strings(
                check.get("evidence_ids"),
                f"{label}.evidence_ids",
                errors,
                portable_ids=True,
                allow_empty=False,
            )
            unknown = sorted(set(references) - set(evidence))
            if unknown:
                errors.append(
                    f"{label} references unknown evidence: "
                    + ", ".join(unknown)
                )
            checks.append(check)

    cleanup = delivery.get("cleanup")
    if exact_fields(
        cleanup,
        {"status", "summary"},
        "delivery.cleanup",
        errors,
        optional=set(),
    ):
        if cleanup.get("status") not in {"passed", "blocked", "not_run"}:
            errors.append("delivery cleanup status is invalid")
        if (
            not isinstance(cleanup.get("summary"), str)
            or not cleanup["summary"].strip()
        ):
            errors.append("delivery cleanup summary must be non-empty")
    unverified = unique_strings(
        delivery.get("unverified"), "delivery.unverified", errors
    )
    blockers = unique_strings(
        delivery.get("blockers"), "delivery.blockers", errors
    )

    if status == "ready_for_integration":
        expected_acceptance = set(assignment.get("acceptance_ids", []))
        expected_evidence = set(assignment.get("expected_evidence", []))
        expected_checks = set(assignment.get("expected_checks", []))
        if set(claims) != expected_acceptance:
            errors.append(
                "ready delivery claims must cover every assignment acceptance ID"
            )
        missing_evidence = sorted(expected_evidence - set(evidence))
        if missing_evidence:
            errors.append(
                "ready delivery is missing expected evidence IDs: "
                + ", ".join(missing_evidence)
            )
        missing_checks = sorted(expected_checks - check_ids)
        if missing_checks:
            errors.append(
                "ready delivery is missing expected check IDs: "
                + ", ".join(missing_checks)
            )
        unbound_evidence = sorted(
            evidence_id
            for evidence_id in expected_evidence
            if not evidence.get(evidence_id, {}).get("artifact_ids")
        )
        if unbound_evidence:
            errors.append(
                "ready delivery expected evidence is not artifact-bound: "
                + ", ".join(unbound_evidence)
            )
        if any(item.get("status") != "passed" for item in claims.values()):
            errors.append("ready delivery claims must all pass")
        if not evidence or any(
            item.get("status") != "passed" for item in evidence.values()
        ):
            errors.append("ready delivery evidence must all pass")
        if not checks or any(
            item.get("status") != "passed" for item in checks
        ):
            errors.append("ready delivery checks must all pass")
        if not isinstance(cleanup, dict) or cleanup.get("status") != "passed":
            errors.append("ready delivery cleanup must pass")
        if unverified or blockers:
            errors.append(
                "ready delivery cannot retain unverified items or blockers"
            )
    elif status in {"blocked", "failed"} and not blockers:
        errors.append("blocked or failed delivery requires a blocker")
    for item in evidence.values():
        if isinstance(item, dict):
            errors.extend(
                paid_data_prose_issues(
                    "delivery proof prose",
                    [item.get("summary")],
                    allow_reported_violation=item.get("status")
                    in {"failed", "unverified"},
                )
            )
    for item in checks:
        if isinstance(item, dict):
            errors.extend(
                paid_data_prose_issues(
                    "delivery proof prose",
                    [item.get("summary")],
                    allow_reported_violation=item.get("status")
                    in {"failed", "unverified"},
                )
            )
    if isinstance(cleanup, dict):
        errors.extend(
            paid_data_prose_issues(
                "delivery proof prose",
                [cleanup.get("summary")],
                allow_reported_violation=cleanup.get("status")
                in {"blocked", "not_run"},
            )
        )
    errors.extend(
        paid_data_prose_issues(
            "delivery proof prose",
            [*unverified, *blockers],
            allow_reported_violation=True,
        )
    )
    delivery_completed_at = parse_time(delivery.get("completed_at"))
    if delivery_completed_at is None:
        errors.append("delivery completed_at must be timezone-aware ISO-8601")
    elif is_implausibly_future(delivery_completed_at):
        errors.append(
            "delivery completed_at exceeds allowed future clock skew"
        )
    packet_created_at = parse_time(packet.get("created_at"))
    if (
        packet_created_at is not None
        and delivery_completed_at is not None
        and delivery_completed_at < packet_created_at
    ):
        errors.append("delivery completion predates packet creation")
    if delivery.get("receipt_sha256") != receipt_hash(delivery):
        errors.append("delivery receipt SHA-256 is invalid")
    errors.extend(
        f"delivery policy: {issue}" for issue in policy_violations(delivery)
    )
    return list(dict.fromkeys(errors))


def validate_integration(
    packet: dict[str, Any],
    deliveries: list[dict[str, Any]],
    integration: dict[str, Any],
    *,
    artifact_root: Path | None = None,
    workspace_root: Path | None = None,
    project_root: Path | None = None,
    baseline_root: Path | None = None,
    worker_roots: dict[str, Path] | None = None,
    require_live_handoff: bool = False,
) -> list[str]:
    selected_project_root = (
        Path(project_root) if project_root is not None else None
    )
    selected_baseline_root = (
        Path(baseline_root) if baseline_root is not None else None
    )
    live_worker_roots: dict[str, Path] = {}
    worker_root_issues: list[str] = []
    if worker_roots is not None:
        if not isinstance(worker_roots, dict):
            worker_root_issues.append(
                "live worker roots must be an assignment-to-path mapping"
            )
        else:
            for assignment_id, root_value in worker_roots.items():
                if not is_portable_id(assignment_id):
                    worker_root_issues.append(
                        "live worker root mapping contains an invalid "
                        f"assignment ID: {assignment_id!r}"
                    )
                    continue
                try:
                    live_worker_roots[assignment_id] = Path(root_value)
                except TypeError:
                    worker_root_issues.append(
                        "live worker root mapping contains an invalid path for "
                        + assignment_id
                    )
    packet_issues = validate_packet(
        packet,
        project_root=(
            selected_project_root if require_live_handoff else None
        ),
        workspace_root=(
            selected_baseline_root if require_live_handoff else None
        ),
    )
    errors = [f"packet: {issue}" for issue in packet_issues]
    errors.extend(worker_root_issues)
    if require_live_handoff:
        if selected_project_root is None:
            errors.append(
                "live handoff validation requires an exact project root"
            )
        if selected_baseline_root is None:
            errors.append(
                "live handoff validation requires an issuance baseline root"
            )
    delivery_map: dict[str, dict[str, Any]] = {}
    for index, delivery in enumerate(deliveries):
        assignment_id = delivery.get("assignment_id")
        ready_delivery = delivery.get("status") == "ready_for_integration"
        selected_worker_root = (
            live_worker_roots.get(assignment_id)
            if is_portable_id(assignment_id)
            else None
        )
        delivery_errors = validate_delivery(
            packet,
            delivery,
            artifact_root=artifact_root,
            worker_root=(
                selected_worker_root
                if require_live_handoff and ready_delivery
                else None
            ),
            structural_only=not (
                require_live_handoff
                and ready_delivery
                and selected_worker_root is not None
            ),
        )
        errors.extend(
            f"deliveries[{index}]: {issue}" for issue in delivery_errors
        )
        if not is_portable_id(assignment_id):
            continue
        if assignment_id in delivery_map:
            errors.append("delivery assignment ID is reused: " + assignment_id)
            continue
        delivery_map[assignment_id] = delivery
    if require_live_handoff:
        ready_delivery_ids = {
            assignment_id
            for assignment_id, delivery in delivery_map.items()
            if delivery.get("status") == "ready_for_integration"
        }
        missing_worker_roots = sorted(
            ready_delivery_ids - set(live_worker_roots)
        )
        extra_worker_roots = sorted(
            set(live_worker_roots) - ready_delivery_ids
        )
        if missing_worker_roots:
            errors.append(
                "live handoff validation is missing worker roots for ready "
                "deliveries: " + ", ".join(missing_worker_roots)
            )
        if extra_worker_roots:
            errors.append(
                "live handoff validation has unknown or non-ready worker "
                "roots: " + ", ".join(extra_worker_roots)
            )
        ready_same_workspace_ids = sorted(
            assignment_id
            for assignment_id in ready_delivery_ids
            if next(
                (
                    assignment
                    for assignment in packet.get("assignments", [])
                    if isinstance(assignment, dict)
                    and assignment.get("id") == assignment_id
                ),
                {},
            ).get("mode")
            == "same_workspace_sequential_write"
        )
        if len(ready_same_workspace_ids) > 1:
            errors.append(
                "completion-eligible live handoff cannot preserve multiple "
                "sequential final snapshots from one shared workspace; use "
                "one compound shared-workspace assignment or isolated writer "
                "roots: " + ", ".join(ready_same_workspace_ids)
            )

    exact_fields(integration, INTEGRATION_FIELDS, "integration", errors)
    if integration.get("document_type") != "quant_team_integration_receipt":
        errors.append("integration document_type is invalid")
    if integration.get("schema_version") != 1:
        errors.append("integration schema_version must equal 1")
    if integration.get("team_run_id") != packet.get("team_run_id"):
        errors.append("integration team_run_id mismatch")
    if integration.get("packet_sha256") != packet.get("packet_sha256"):
        errors.append("integration packet_sha256 mismatch")
    if integration.get("integration_owner") != packet.get(
        "integration_owner"
    ):
        errors.append("integration owner does not match packet")
    status = integration.get("status")
    if status not in INTEGRATION_STATUSES:
        errors.append("integration status is invalid")

    assignments = {
        item.get("id"): item
        for item in packet.get("assignments", [])
        if isinstance(item, dict) and is_portable_id(item.get("id"))
    }
    raw_results = integration.get("delivery_results")
    results: dict[str, dict[str, Any]] = {}
    if not isinstance(raw_results, list):
        errors.append("integration.delivery_results must be an array")
    else:
        fields = {
            "assignment_id",
            "delivery_receipt_sha256",
            "disposition",
            "reason",
            "integrated_paths",
            "evidence_ids",
        }
        for index, result in enumerate(raw_results):
            label = f"integration.delivery_results[{index}]"
            if not exact_fields(
                result, fields, label, errors, optional=set()
            ):
                continue
            assignment_id = result.get("assignment_id")
            if not is_portable_id(assignment_id):
                errors.append(f"{label}.assignment_id is invalid")
                continue
            if assignment_id in results:
                errors.append(
                    "integration result assignment ID is reused: "
                    + assignment_id
                )
                continue
            if assignment_id not in assignments:
                errors.append(
                    f"{label} references unknown assignment: {assignment_id}"
                )
            delivery = delivery_map.get(assignment_id)
            if delivery is None:
                errors.append(
                    f"{label} has no matching worker delivery receipt"
                )
            elif result.get("delivery_receipt_sha256") != delivery.get(
                "receipt_sha256"
            ):
                errors.append(f"{label} delivery receipt hash mismatch")
            if not is_sha256(result.get("delivery_receipt_sha256")):
                errors.append(f"{label}.delivery_receipt_sha256 is invalid")
            disposition = result.get("disposition")
            if disposition not in ALL_DISPOSITIONS:
                errors.append(f"{label}.disposition is invalid")
            if (
                not isinstance(result.get("reason"), str)
                or not result["reason"].strip()
            ):
                errors.append(f"{label}.reason must be non-empty")
            integrated = changed_paths(
                result.get("integrated_paths"),
                f"{label}.integrated_paths",
                errors,
            )
            unique_strings(
                result.get("evidence_ids"),
                f"{label}.evidence_ids",
                errors,
                portable_ids=True,
                allow_empty=disposition not in ACCEPTED_DISPOSITIONS,
            )
            assignment = assignments.get(assignment_id, {})
            if disposition == "integrated":
                if assignment.get("mode") == "read_only":
                    errors.append(
                        f"{label} read-only assignment cannot be integrated"
                    )
                if delivery is not None and delivery.get(
                    "status"
                ) != "ready_for_integration":
                    errors.append(
                        f"{label} cannot integrate a non-ready delivery"
                    )
                delivery_paths = (
                    delivery.get("changed_paths", [])
                    if isinstance(delivery, dict)
                    else []
                )
                if integrated != delivery_paths:
                    errors.append(
                        f"{label} integrated paths must equal delivery paths"
                    )
                outside = sorted(
                    path
                    for path in integrated
                    if not path_matches(
                        path, assignment.get("write_scope", [])
                    )
                )
                protected = sorted(
                    path
                    for path in integrated
                    if path_matches(
                        path, assignment.get("protected_scope", [])
                    )
                )
                if outside:
                    errors.append(
                        f"{label} integrates paths outside write scope: "
                        + ", ".join(outside)
                    )
                if protected:
                    errors.append(
                        f"{label} integrates protected paths: "
                        + ", ".join(protected)
                    )
            elif disposition == "accepted_read_only":
                if assignment.get("mode") != "read_only":
                    errors.append(
                        f"{label} write assignment cannot be accepted read-only"
                    )
                if integrated:
                    errors.append(
                        f"{label} accepted read-only result has integrated paths"
                    )
                if delivery is not None and delivery.get(
                    "status"
                ) != "ready_for_integration":
                    errors.append(
                        f"{label} cannot accept a non-ready delivery"
                    )
            elif integrated:
                errors.append(
                    f"{label} rejected or superseded result has integrated paths"
                )
            results[assignment_id] = result
    if set(results) != set(assignments):
        missing = sorted(set(assignments) - set(results))
        extra = sorted(set(results) - set(assignments))
        if missing:
            errors.append(
                "integration is missing assignment results: "
                + ", ".join(missing)
            )
        if extra:
            errors.append(
                "integration has extra assignment results: "
                + ", ".join(extra)
            )

    raw_evidence = integration.get("evidence")
    evidence: dict[str, dict[str, Any]] = {}
    if not isinstance(raw_evidence, list):
        errors.append("integration.evidence must be an array")
    else:
        fields = {"id", "kind", "status", "summary", "source_sha256"}
        for index, item in enumerate(raw_evidence):
            label = f"integration.evidence[{index}]"
            if not exact_fields(item, fields, label, errors, optional=set()):
                continue
            evidence_id = item.get("id")
            if not is_portable_id(evidence_id):
                errors.append(f"{label}.id must be a portable ID")
                continue
            if evidence_id in evidence:
                errors.append(
                    "integration reuses evidence ID: " + evidence_id
                )
                continue
            if item.get("kind") not in {
                "integration",
                "verification",
                "inspection",
            }:
                errors.append(f"{label}.kind is invalid")
            if item.get("status") not in {"passed", "failed", "unverified"}:
                errors.append(f"{label}.status is invalid")
            if (
                not isinstance(item.get("summary"), str)
                or not item["summary"].strip()
            ):
                errors.append(f"{label}.summary must be non-empty")
            if not is_sha256(item.get("source_sha256")):
                errors.append(f"{label}.source_sha256 is invalid")
            evidence[evidence_id] = item
    snapshot_candidate = integration.get("canonical_snapshot")
    known_source_hashes = {
        packet.get("packet_sha256"),
        *(
            delivery.get("receipt_sha256")
            for delivery in delivery_map.values()
        ),
    }
    if isinstance(snapshot_candidate, dict):
        known_source_hashes.update(
            {
                snapshot_candidate.get("pre_workspace_sha256"),
                snapshot_candidate.get("post_workspace_sha256"),
            }
        )
    for evidence_id, item in evidence.items():
        if item.get("source_sha256") not in known_source_hashes:
            errors.append(
                "integration evidence has an unknown source anchor: "
                + evidence_id
            )
    for assignment_id, result in results.items():
        unknown = sorted(
            set(result.get("evidence_ids", [])) - set(evidence)
        )
        if unknown:
            errors.append(
                f"integration result {assignment_id} references unknown "
                "evidence: " + ", ".join(unknown)
            )

    packet_assignments = packet.get("assignments", [])
    assignment_by_id = {
        item.get("id"): item
        for item in packet_assignments
        if isinstance(item, dict) and is_portable_id(item.get("id"))
    }
    for assignment_id, selected in assignment_by_id.items():
        delivery = delivery_map.get(assignment_id)
        if delivery is None:
            continue
        completed_at = parse_time(delivery.get("completed_at"))
        for dependency_id in selected.get("depends_on", []):
            dependency = delivery_map.get(dependency_id)
            dependency_completed_at = (
                parse_time(dependency.get("completed_at"))
                if isinstance(dependency, dict)
                else None
            )
            if (
                completed_at is not None
                and dependency_completed_at is not None
                and completed_at < dependency_completed_at
            ):
                errors.append(
                    "assignment delivery predates dependency delivery: "
                    f"{dependency_id} -> {assignment_id}"
                )

    for assignment_id, selected in assignment_by_id.items():
        delivery = delivery_map.get(assignment_id)
        if delivery is None:
            continue
        observed_baseline = delivery.get("source", {}).get(
            "baseline_workspace_sha256"
        )
        baseline_binding = selected.get("baseline_binding", {})
        if baseline_binding.get("kind") == "packet":
            expected_baseline = packet.get("baseline", {}).get(
                "workspace_sha256"
            )
            expected_baseline_snapshot = packet.get("baseline_snapshot")
        else:
            predecessor_delivery = delivery_map.get(
                baseline_binding.get("assignment_id"), {}
            )
            expected_baseline = predecessor_delivery.get("source", {}).get(
                "final_workspace_sha256"
            )
            expected_baseline_snapshot = predecessor_delivery.get(
                "final_snapshot"
            )
        if observed_baseline != expected_baseline:
            errors.append(
                "delivery baseline does not match its hash-bound baseline "
                "reference: " + assignment_id
            )
        if delivery.get("baseline_snapshot") != expected_baseline_snapshot:
            errors.append(
                "delivery baseline snapshot does not match its hash-bound "
                "baseline reference: " + assignment_id
            )

    required_acceptance = {
        acceptance_id
        for assignment in assignments.values()
        if (
            assignment.get("required") is True
            or assignment.get("validation_group") is not None
        )
        for acceptance_id in assignment.get("acceptance_ids", [])
    }
    all_acceptance = {
        acceptance_id
        for assignment in assignments.values()
        for acceptance_id in assignment.get("acceptance_ids", [])
    }
    claims = validate_claims(
        integration.get("acceptance_claims"),
        "integration.acceptance_claims",
        all_acceptance,
        set(evidence),
        errors,
    )

    snapshot = integration.get("canonical_snapshot")
    canonical_paths: list[str] = []
    if exact_fields(
        snapshot,
        {
            "pre_workspace_sha256",
            "post_workspace_sha256",
            "changed_paths",
        },
        "integration.canonical_snapshot",
        errors,
        optional=set(),
    ):
        for field in ("pre_workspace_sha256", "post_workspace_sha256"):
            if not is_sha256(snapshot.get(field)):
                errors.append(
                    f"integration canonical snapshot {field} is invalid"
                )
        canonical_paths = changed_paths(
            snapshot.get("changed_paths"),
            "integration.canonical_snapshot.changed_paths",
            errors,
        )
        if snapshot.get("pre_workspace_sha256") != packet.get(
            "baseline", {}
        ).get("workspace_sha256"):
            errors.append(
                "integration canonical pre snapshot does not match packet baseline"
            )
    integrated_union = sorted(
        {
            path
            for result in results.values()
            if result.get("disposition") == "integrated"
            for path in result.get("integrated_paths", [])
        }
    )
    if canonical_paths != integrated_union:
        errors.append(
            "integration canonical changed paths must equal integrated paths"
        )
    if not integrated_union and isinstance(snapshot, dict) and (
        snapshot.get("pre_workspace_sha256")
        != snapshot.get("post_workspace_sha256")
    ):
        errors.append(
            "read-only or rejected-only integration changed canonical snapshot"
        )
    if (
        require_live_handoff
        and canonical_paths
        and selected_baseline_root is not None
        and workspace_root is not None
    ):
        try:
            same_live_root = selected_baseline_root.expanduser().samefile(
                Path(workspace_root).expanduser()
            )
        except OSError as exc:
            errors.append(
                "live handoff could not prove distinct baseline and canonical "
                f"workspace roots: {exc}"
            )
        else:
            if same_live_root:
                errors.append(
                    "changed live handoff requires distinct physical baseline "
                    "and canonical workspace roots"
                )

    raw_conflicts = integration.get("conflicts")
    conflicts: list[dict[str, Any]] = []
    if not isinstance(raw_conflicts, list):
        errors.append("integration.conflicts must be an array")
    else:
        fields = {"id", "status", "summary", "evidence_ids"}
        seen_conflicts: set[str] = set()
        for index, conflict in enumerate(raw_conflicts):
            label = f"integration.conflicts[{index}]"
            if not exact_fields(
                conflict, fields, label, errors, optional=set()
            ):
                continue
            conflict_id = conflict.get("id")
            if not is_portable_id(conflict_id):
                errors.append(f"{label}.id must be a portable ID")
            elif conflict_id in seen_conflicts:
                errors.append(
                    "integration reuses conflict ID: " + conflict_id
                )
            else:
                seen_conflicts.add(conflict_id)
            if conflict.get("status") not in {"resolved", "open"}:
                errors.append(f"{label}.status is invalid")
            if (
                not isinstance(conflict.get("summary"), str)
                or not conflict["summary"].strip()
            ):
                errors.append(f"{label}.summary must be non-empty")
            references = unique_strings(
                conflict.get("evidence_ids"),
                f"{label}.evidence_ids",
                errors,
                portable_ids=True,
                allow_empty=False,
            )
            unknown = sorted(set(references) - set(evidence))
            if unknown:
                errors.append(
                    f"{label} references unknown evidence: "
                    + ", ".join(unknown)
                )
            conflicts.append(conflict)
    unverified = unique_strings(
        integration.get("unverified"),
        "integration.unverified",
        errors,
    )
    blockers = unique_strings(
        integration.get("blockers"),
        "integration.blockers",
        errors,
    )

    if status == "ready_for_review":
        if workspace_root is None:
            errors.append(
                "ready integration requires canonical workspace-root verification"
            )
        else:
            expanded_workspace_root = workspace_root.expanduser()
            if expanded_workspace_root.is_symlink():
                errors.append("canonical workspace root must not be a symbolic link")
            else:
                try:
                    canonical_root = expanded_workspace_root.resolve(strict=True)
                    if not canonical_root.is_dir():
                        raise ValueError(
                            "canonical workspace root must be a directory"
                        )
                    observed_binding = project_binding(canonical_root).get(
                        "identity_sha256"
                    )
                    if observed_binding != packet.get(
                        "project_binding_sha256"
                    ):
                        errors.append(
                            "canonical workspace project binding does not "
                            "match packet"
                        )
                    policy = packet.get("snapshot_policy", {})
                    selected_excluded_root = excluded_root_path(
                        canonical_root,
                        policy.get("excluded_root")
                        if isinstance(policy, dict)
                        else None,
                        "packet snapshot_policy excluded_root",
                        errors,
                    )
                    observed_snapshot = workspace_snapshot(
                        canonical_root,
                        selected_excluded_root,
                        policy.get("protected_patterns", [])
                        if isinstance(policy, dict)
                        else [],
                        snapshot_version=2,
                    )
                    expected_post_sha256 = (
                        snapshot.get("post_workspace_sha256")
                        if isinstance(snapshot, dict)
                        else None
                    )
                    if (
                        observed_snapshot.get("sha256")
                        != expected_post_sha256
                    ):
                        errors.append(
                            "canonical workspace snapshot does not match "
                            "integration post snapshot"
                        )
                    baseline_snapshot = packet.get("baseline_snapshot")
                    if isinstance(baseline_snapshot, dict):
                        observed_delta = snapshot_delta_paths(
                            baseline_snapshot,
                            observed_snapshot,
                        )
                        if observed_delta != canonical_paths:
                            errors.append(
                                "canonical changed paths do not match the "
                                "observed baseline-to-post delta"
                            )
                except (OSError, ValueError) as exc:
                    errors.append(str(exc))
        for assignment_id, assignment in assignments.items():
            validation_coupled = assignment.get("validation_group") is not None
            if assignment.get("required") is not True and not validation_coupled:
                continue
            expected = (
                "accepted_read_only"
                if assignment.get("mode") == "read_only"
                else "integrated"
            )
            if results.get(assignment_id, {}).get("disposition") != expected:
                errors.append(
                    "required or validation-coupled assignment is not "
                    "accepted for review: "
                    + assignment_id
                )
        post_snapshot_sha256 = (
            snapshot.get("post_workspace_sha256")
            if isinstance(snapshot, dict)
            else None
        )
        packet_join = packet.get("join")
        raw_join_verification = (
            packet_join.get("verification", [])
            if isinstance(packet_join, dict)
            else []
        )
        join_verification_ids = (
            [
                check_id
                for check_id in raw_join_verification
                if is_portable_id(check_id)
            ]
            if isinstance(raw_join_verification, list)
            else []
        )
        missing_join_verification = sorted(
            set(join_verification_ids) - set(evidence)
        )
        if missing_join_verification:
            errors.append(
                "ready integration is missing join verification evidence: "
                + ", ".join(missing_join_verification)
            )
        for check_id in join_verification_ids:
            item = evidence.get(check_id)
            if item is None:
                continue
            if (
                item.get("kind") != "verification"
                or item.get("status") != "passed"
                or item.get("source_sha256") != post_snapshot_sha256
            ):
                errors.append(
                    "join verification evidence must pass on the current "
                    "integration snapshot: " + check_id
                )
        for assignment_id, result_item in results.items():
            if result_item.get("disposition") not in ACCEPTED_DISPOSITIONS:
                continue
            if not any(
                evidence.get(evidence_id, {}).get("source_sha256")
                == post_snapshot_sha256
                for evidence_id in result_item.get("evidence_ids", [])
            ):
                errors.append(
                    "accepted assignment lacks integrated frozen-snapshot "
                    "evidence: " + assignment_id
                )
        if not required_acceptance.issubset(set(claims)):
            errors.append(
                "integration claims do not cover required acceptance IDs"
            )
        if any(
            claims.get(acceptance_id, {}).get("status") != "passed"
            for acceptance_id in required_acceptance
        ):
            errors.append("required integration acceptance claims must pass")
        for acceptance_id in required_acceptance:
            if not any(
                evidence.get(evidence_id, {}).get("source_sha256")
                == post_snapshot_sha256
                for evidence_id in claims.get(
                    acceptance_id, {}
                ).get("evidence_ids", [])
            ):
                errors.append(
                    "required integration acceptance lacks frozen-snapshot "
                    "evidence: " + acceptance_id
                )
        if not evidence or any(
            item.get("status") != "passed" for item in evidence.values()
        ):
            errors.append("ready integration evidence must all pass")
        if any(conflict.get("status") == "open" for conflict in conflicts):
            errors.append("ready integration has an open conflict")
        if unverified:
            errors.append("ready integration cannot retain unverified items")
        if blockers:
            errors.append("ready integration cannot retain blockers")
    elif status in {"blocked", "failed"} and not blockers:
        errors.append("blocked or failed integration requires a blocker")
    for item in results.values():
        if isinstance(item, dict):
            errors.extend(
                paid_data_prose_issues(
                    "integration proof prose",
                    [item.get("reason")],
                    allow_reported_violation=item.get("disposition")
                    not in ACCEPTED_DISPOSITIONS,
                )
            )
    for item in evidence.values():
        if isinstance(item, dict):
            errors.extend(
                paid_data_prose_issues(
                    "integration proof prose",
                    [item.get("summary")],
                    allow_reported_violation=item.get("status")
                    in {"failed", "unverified"},
                )
            )
    errors.extend(
        paid_data_prose_issues(
            "integration proof prose",
            [
                *unverified,
                *blockers,
            ],
            allow_reported_violation=True,
        )
    )
    for item in conflicts:
        if isinstance(item, dict):
            errors.extend(
                paid_data_prose_issues(
                    "integration proof prose",
                    [item.get("summary")],
                    allow_reported_violation=item.get("status") == "open",
                )
            )
    integration_completed_at = parse_time(integration.get("completed_at"))
    if integration_completed_at is None:
        errors.append(
            "integration completed_at must be timezone-aware ISO-8601"
        )
    elif is_implausibly_future(integration_completed_at):
        errors.append(
            "integration completed_at exceeds allowed future clock skew"
        )
    elif any(
        completed_at is not None and integration_completed_at < completed_at
        for completed_at in (
            parse_time(delivery.get("completed_at"))
            for delivery in delivery_map.values()
        )
    ):
        errors.append("integration completion predates a worker delivery")
    if integration.get("receipt_sha256") != receipt_hash(integration):
        errors.append("integration receipt SHA-256 is invalid")
    errors.extend(
        f"integration policy: {issue}"
        for issue in policy_violations(integration)
    )
    return list(dict.fromkeys(errors))


def result(ok: bool, issues: list[str]) -> dict[str, Any]:
    return {
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "issues": issues,
    }


def emit(value: dict[str, Any]) -> int:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0 if value["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate optional structured agent-team evidence."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    packet = subparsers.add_parser("packet")
    packet.add_argument("--packet", required=True)
    packet.add_argument("--project-root")
    packet.add_argument("--workspace-root")
    packet.add_argument(
        "--worker-root",
        action="append",
        default=[],
        metavar="ASSIGNMENT_ID=PATH",
    )
    packet.add_argument("--structural-only", action="store_true")

    delivery = subparsers.add_parser("delivery")
    delivery.add_argument("--packet", required=True)
    delivery.add_argument("--delivery", required=True)
    delivery.add_argument("--artifact-root")
    delivery.add_argument("--worker-root")

    integration = subparsers.add_parser("integration")
    integration.add_argument("--packet", required=True)
    integration.add_argument("--delivery", action="append", default=[])
    integration.add_argument("--integration", required=True)
    integration.add_argument("--artifact-root")
    integration.add_argument("--workspace-root")
    integration.add_argument("--project-root")
    integration.add_argument("--baseline-root")
    integration.add_argument(
        "--worker-root",
        action="append",
        default=[],
        metavar="ASSIGNMENT_ID=PATH",
    )
    integration.add_argument("--require-live-handoff", action="store_true")
    return parser


def load(path_value: str) -> dict[str, Any]:
    path = Path(path_value).expanduser()
    if path.is_symlink():
        raise ValueError(f"{path.name} must not be a symbolic link")
    return strict_json(path.resolve())


def parse_worker_root_mappings(
    values: Any,
) -> tuple[dict[str, Path], list[str]]:
    """Parse repeatable ``assignment-id=path`` live handoff bindings."""

    if not isinstance(values, list):
        return {}, ["--worker-root must be a repeatable string argument"]
    mappings: dict[str, Path] = {}
    issues: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or "=" not in value:
            issues.append(
                f"--worker-root[{index}] must use ASSIGNMENT_ID=PATH"
            )
            continue
        assignment_id, path_value = value.split("=", 1)
        if not is_portable_id(assignment_id):
            issues.append(
                f"--worker-root[{index}] has an invalid assignment ID"
            )
            continue
        if not path_value.strip():
            issues.append(f"--worker-root[{index}] path must be non-empty")
            continue
        if assignment_id in mappings:
            issues.append(
                "duplicate --worker-root assignment ID: " + assignment_id
            )
            continue
        mappings[assignment_id] = Path(path_value).expanduser()
    return mappings, issues


def main() -> int:
    args = build_parser().parse_args()
    try:
        packet = load(args.packet)
        if args.command == "packet":
            project_root = (
                Path(args.project_root).expanduser()
                if args.project_root
                else None
            )
            workspace_root = (
                Path(args.workspace_root).expanduser()
                if args.workspace_root
                else None
            )
            worker_roots, mapping_issues = parse_worker_root_mappings(
                args.worker_root
            )
            if args.structural_only and (
                project_root is not None
                or workspace_root is not None
                or bool(args.worker_root)
            ):
                issues = [
                    "packet --structural-only cannot be combined with live roots"
                ]
            elif not args.structural_only and (
                project_root is None or workspace_root is None
            ):
                issues = [
                    "packet execution validation requires --project-root and "
                    "--workspace-root; use --structural-only for non-completion "
                    "inspection"
                ]
            else:
                issues = [
                    *mapping_issues,
                    *validate_packet(
                        packet,
                        project_root=project_root,
                        workspace_root=workspace_root,
                        worker_roots=worker_roots,
                        require_worker_preflight=not args.structural_only,
                    ),
                ]
        elif args.command == "delivery":
            delivery = load(args.delivery)
            artifact_root = (
                Path(args.artifact_root).expanduser()
                if args.artifact_root
                else None
            )
            issues = validate_delivery(
                packet,
                delivery,
                artifact_root=artifact_root,
                worker_root=(
                    Path(args.worker_root).expanduser()
                    if args.worker_root
                    else None
                ),
            )
        else:
            deliveries = [load(path) for path in args.delivery]
            integration = load(args.integration)
            artifact_root = (
                Path(args.artifact_root).expanduser()
                if args.artifact_root
                else None
            )
            workspace_root = (
                Path(args.workspace_root).expanduser()
                if args.workspace_root
                else None
            )
            project_root = (
                Path(args.project_root).expanduser()
                if args.project_root
                else None
            )
            baseline_root = (
                Path(args.baseline_root).expanduser()
                if args.baseline_root
                else None
            )
            worker_roots, mapping_issues = parse_worker_root_mappings(
                args.worker_root
            )
            live_arguments_supplied = any(
                (
                    project_root is not None,
                    baseline_root is not None,
                    bool(args.worker_root),
                )
            )
            if live_arguments_supplied and not args.require_live_handoff:
                mapping_issues.append(
                    "integration live handoff roots require "
                    "--require-live-handoff"
                )
            issues = [
                *mapping_issues,
                *validate_integration(
                    packet,
                    deliveries,
                    integration,
                    artifact_root=artifact_root,
                    workspace_root=workspace_root,
                    project_root=project_root,
                    baseline_root=baseline_root,
                    worker_roots=worker_roots,
                    require_live_handoff=args.require_live_handoff,
                ),
            ]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        issues = [str(exc)]
    payload = result(not issues, issues)
    if (
        args.command == "packet"
        and getattr(args, "structural_only", False)
        and not issues
    ):
        payload["status"] = "structural_only"
        payload["completion_eligible"] = False
    return emit(payload)


if __name__ == "__main__":
    raise SystemExit(main())
