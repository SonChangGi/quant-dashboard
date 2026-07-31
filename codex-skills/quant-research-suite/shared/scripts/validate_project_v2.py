#!/usr/bin/env python3
"""Validate the progressive, capability-based project manifest v2."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from capability_model import (
    ASSURANCE_LEVELS,
    CapabilityError,
    DELIVERY_LEVELS,
    PROJECT_CAPABILITIES,
    RUNTIME_CAPABILITIES,
    ZERO_SPEND_POLICY,
    policy_violations,
    prohibited_paid_data_reasons,
    resolve,
)


PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
REPOSITORY = re.compile(r"^[^/\s]+/[^/\s]+$")
PORTABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
CONTROL_KINDS = {"display", "result_selector", "analysis", "operation"}
SOURCE_ROLES = {"required", "optional", "benchmark", "fallback"}
FREE_DATA_ACCESS_ELIGIBILITY = "permanently-free-no-billing"
TOP_LEVEL_FIELDS = {
    "$schema",
    "schema_version",
    "project",
    "assurance",
    "delivery",
    "profiles",
    "capabilities",
    "adapters",
    "contracts",
    "capability_config",
    "authority",
    "extensions",
}
PROJECT_FIELDS = {"id", "purpose", "repository"}
CONTRACT_FIELDS = {"protected_paths", "test_commands"}
AUTHORITY_FIELDS = {
    "cost_policy",
    "paid_action_authority",
    "paid_fallback_enabled",
}
INPUT_CONTROL_FIELDS = {
    "id",
    "kind",
    "frontend_field",
    "canonical_field",
    "execution_mapping",
    "execution_binding",
    "default_source",
    "input_pointer",
    "allowed_variant_input_pointers",
    "effective_value_pointer",
    "result_paths",
    "run_id_pointer",
    "project_id_pointer",
    "runtime_binding_contract",
}
EXECUTION_BINDING_FIELDS = {"kind", "locator"}
EXECUTION_BINDING_KINDS = {
    "argv-option",
    "json-payload",
    "config-json",
}
RUNTIME_BINDING_POINTER_FIELDS = {
    "dispatch_canonical_field_pointer",
    "dispatch_entrypoint_sha256_pointer",
    "dispatch_execution_mapping_pointer",
    "dispatch_frontend_field_pointer",
    "dispatch_input_pointer",
    "view_control_field_pointer",
    "view_applied_value_pointer",
    "view_binding_status_pointer",
    "view_project_id_pointer",
    "view_run_id_pointer",
    "view_result_sha256_pointer",
    "view_result_values_pointer",
}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: Any, *, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(nonempty(item) for item in value)
    )


def valid_http_url(value: Any) -> bool:
    if not nonempty(value):
        return False
    if value != value.strip() or any(character.isspace() for character in value):
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
    )


def valid_json_pointer(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("/"):
        return False
    return not re.search(r"~(?:[^01]|$)", value)


def json_pointers_overlap(left: str, right: str) -> bool:
    return (
        left == right
        or left.startswith(right + "/")
        or right.startswith(left + "/")
    )


def project_path(
    root: Path,
    value: Any,
    label: str,
    errors: list[str],
    *,
    must_exist: bool,
) -> Path | None:
    if not nonempty(value):
        errors.append(f"{label} must be a non-empty project-relative path")
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "\\" in value:
        errors.append(f"{label} must be a portable project-relative path")
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        errors.append(f"{label} resolves outside project root")
        return None
    if must_exist and not candidate.exists():
        errors.append(f"{label} does not exist: {value}")
    return candidate


def unique_strings(
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = True,
) -> list[str]:
    if not string_list(value, allow_empty=allow_empty):
        suffix = "" if allow_empty else " non-empty"
        errors.append(f"{label} must be a{suffix} string array")
        return []
    if len(value) != len(set(value)):
        errors.append(f"{label} must not contain duplicates")
    return list(value)


def reject_unknown_keys(
    value: dict[str, Any],
    allowed: set[str],
    label: str,
    errors: list[str],
) -> None:
    unknown = sorted(str(key) for key in set(value) - allowed)
    if unknown:
        errors.append(f"unknown {label} fields: " + ", ".join(unknown))


def capability_config(
    manifest: dict[str, Any],
    capability: str,
    errors: list[str],
) -> dict[str, Any]:
    configs = manifest.get("capability_config")
    if configs is None:
        return {}
    if not isinstance(configs, dict):
        errors.append("capability_config must be an object")
        return {}
    value = configs.get(capability, {})
    if not isinstance(value, dict):
        errors.append(f"capability_config.{capability} must be an object")
        return {}
    if "status" in value:
        errors.append(
            f"capability_config.{capability}.status is not persisted in v2; "
            "declare only active capabilities"
        )
    return value


def validate_analysis(
    root: Path,
    manifest: dict[str, Any],
    effective: set[str],
    errors: list[str],
) -> None:
    if "analysis" not in effective:
        return
    config = capability_config(manifest, "analysis", errors)
    entrypoints = unique_strings(
        config.get("authoritative_entrypoints"),
        "capability_config.analysis.authoritative_entrypoints",
        errors,
        allow_empty=False,
    )
    for index, entrypoint in enumerate(entrypoints):
        project_path(
            root,
            entrypoint,
            f"capability_config.analysis.authoritative_entrypoints[{index}]",
            errors,
            must_exist=True,
        )
    # Result identity is a project-owned contract. A dashboard may use
    # project_id/run_id, while a notebook, simulation, document pipeline, or
    # non-Git research project may use a content hash, dataset revision, date,
    # scenario, or another stable key. The stronger input-binding capability
    # validates the concrete pointers it needs instead of imposing one identity
    # vocabulary on every analysis project.
    identity_fields = unique_strings(
        config.get("result_identity_fields"),
        "capability_config.analysis.result_identity_fields",
        errors,
        allow_empty=False,
    )
    raw_identity_pointers = config.get("result_identity_pointers")
    if raw_identity_pointers is None:
        if "analysis-input-binding" in effective:
            errors.append(
                "active analysis-input-binding requires "
                "capability_config.analysis.result_identity_pointers"
            )
    else:
        identity_pointers = unique_strings(
            raw_identity_pointers,
            "capability_config.analysis.result_identity_pointers",
            errors,
            allow_empty="analysis-input-binding" not in effective,
        )
        for pointer in identity_pointers:
            if not valid_json_pointer(pointer):
                errors.append(
                    "capability_config.analysis.result_identity_pointers "
                    "contains an invalid JSON Pointer"
                )
        if len(identity_pointers) != len(identity_fields):
            errors.append(
                "capability_config.analysis.result_identity_pointers must "
                "have one positional pointer for every "
                "result_identity_fields entry"
            )


def validate_input_binding(
    manifest: dict[str, Any],
    effective: set[str],
    errors: list[str],
) -> None:
    if "analysis-input-binding" not in effective:
        return
    config = capability_config(
        manifest,
        "analysis-input-binding",
        errors,
    )
    analysis_config = capability_config(manifest, "analysis", errors)
    raw_identity_pointers = analysis_config.get(
        "result_identity_pointers", []
    )
    identity_pointers = (
        raw_identity_pointers
        if string_list(raw_identity_pointers, allow_empty=False)
        else []
    )
    maximum_capture_age_seconds = config.get(
        "maximum_capture_age_seconds", 86400
    )
    if (
        not isinstance(maximum_capture_age_seconds, int)
        or isinstance(maximum_capture_age_seconds, bool)
        or maximum_capture_age_seconds < 1
    ):
        errors.append(
            "capability_config.analysis-input-binding."
            "maximum_capture_age_seconds must be a positive integer"
        )
    controls = config.get("controls")
    if not isinstance(controls, list) or not controls:
        errors.append(
            "active analysis-input-binding requires a non-empty controls array"
        )
        return
    ids: list[str] = []
    for index, control in enumerate(controls):
        prefix = f"capability_config.analysis-input-binding.controls[{index}]"
        if not isinstance(control, dict):
            errors.append(f"{prefix} must be an object")
            continue
        reject_unknown_keys(
            control,
            INPUT_CONTROL_FIELDS,
            prefix,
            errors,
        )
        for field in (
            "id",
            "frontend_field",
            "canonical_field",
            "execution_mapping",
            "default_source",
            "input_pointer",
            "effective_value_pointer",
        ):
            if not nonempty(control.get(field)):
                errors.append(f"{prefix}.{field} is required")
        execution_binding = control.get("execution_binding")
        if not isinstance(execution_binding, dict):
            errors.append(f"{prefix}.execution_binding must be an object")
        else:
            reject_unknown_keys(
                execution_binding,
                EXECUTION_BINDING_FIELDS,
                f"{prefix}.execution_binding",
                errors,
            )
            execution_kind = execution_binding.get("kind")
            execution_locator = execution_binding.get("locator")
            if execution_kind not in EXECUTION_BINDING_KINDS:
                errors.append(
                    f"{prefix}.execution_binding.kind must be one of "
                    + ", ".join(sorted(EXECUTION_BINDING_KINDS))
                )
            if not nonempty(execution_locator):
                errors.append(
                    f"{prefix}.execution_binding.locator is required"
                )
            elif execution_kind == "argv-option":
                if (
                    not execution_locator.startswith("--")
                    or execution_locator == "--"
                    or any(character.isspace() for character in execution_locator)
                    or "=" in execution_locator
                ):
                    errors.append(
                        f"{prefix}.execution_binding.locator must be one "
                        "long-form argv option without whitespace or '='"
                    )
            elif execution_kind in {"json-payload", "config-json"}:
                if not valid_json_pointer(execution_locator):
                    errors.append(
                        f"{prefix}.execution_binding.locator must be a "
                        "JSON Pointer"
                    )
            if (
                nonempty(control.get("execution_mapping"))
                and nonempty(execution_locator)
                and control.get("execution_mapping") != execution_locator
            ):
                errors.append(
                    f"{prefix}.execution_mapping must equal the structured "
                    "execution_binding.locator"
                )
        for field in ("input_pointer", "effective_value_pointer"):
            if nonempty(control.get(field)) and not valid_json_pointer(
                control[field]
            ):
                errors.append(f"{prefix}.{field} must be a JSON Pointer")
        for field in ("run_id_pointer", "project_id_pointer"):
            if field in control and not valid_json_pointer(control.get(field)):
                errors.append(f"{prefix}.{field} must be a JSON Pointer")
        allowed_variant = control.get(
            "allowed_variant_input_pointers",
            [control.get("input_pointer")],
        )
        if not string_list(allowed_variant, allow_empty=False):
            errors.append(
                f"{prefix}.allowed_variant_input_pointers must be a "
                "non-empty string array"
            )
        else:
            if len(allowed_variant) != len(set(allowed_variant)):
                errors.append(
                    f"{prefix}.allowed_variant_input_pointers must be unique"
                )
            for pointer in allowed_variant:
                if not valid_json_pointer(pointer):
                    errors.append(
                        f"{prefix}.allowed_variant_input_pointers contains "
                        "an invalid JSON Pointer"
                    )
            input_pointer = control.get("input_pointer")
            if nonempty(input_pointer) and not any(
                input_pointer == pointer
                or input_pointer.startswith(pointer + "/")
                for pointer in allowed_variant
            ):
                errors.append(
                    f"{prefix}.allowed_variant_input_pointers must cover "
                    "input_pointer"
                )
        control_id = control.get("id")
        if nonempty(control_id):
            ids.append(control_id)
        if control.get("kind") != "analysis":
            errors.append(f"{prefix}.kind must equal analysis")
        result_paths = control.get("result_paths")
        if not string_list(result_paths, allow_empty=False):
            errors.append(f"{prefix}.result_paths must be a non-empty array")
        else:
            reserved_result_pointers = {
                control.get("effective_value_pointer"),
                control.get("run_id_pointer", "/run_id"),
                control.get("project_id_pointer", "/project_id"),
                *identity_pointers,
            }
            for pointer in result_paths:
                if not valid_json_pointer(pointer):
                    errors.append(
                        f"{prefix}.result_paths contains an invalid JSON Pointer"
                    )
                elif any(
                    isinstance(reserved, str)
                    and json_pointers_overlap(pointer, reserved)
                    for reserved in reserved_result_pointers
                ):
                    errors.append(
                        f"{prefix}.result_paths must not overlap effective "
                        "configuration or result identity pointers"
                    )
        runtime_contract = control.get("runtime_binding_contract")
        if not isinstance(runtime_contract, dict):
            errors.append(
                f"{prefix}.runtime_binding_contract must be an object"
            )
        else:
            reject_unknown_keys(
                runtime_contract,
                RUNTIME_BINDING_POINTER_FIELDS,
                f"{prefix}.runtime_binding_contract",
                errors,
            )
            for field in sorted(RUNTIME_BINDING_POINTER_FIELDS):
                if not valid_json_pointer(runtime_contract.get(field)):
                    errors.append(
                        f"{prefix}.runtime_binding_contract.{field} must "
                        "be a JSON Pointer"
                    )
    if len(ids) != len(set(ids)):
        errors.append("analysis input control IDs must be unique")


def validate_external_data(
    root: Path,
    manifest: dict[str, Any],
    effective: set[str],
    errors: list[str],
) -> None:
    if "external-data" not in effective:
        return
    config = capability_config(manifest, "external-data", errors)
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("active external-data requires a non-empty sources array")
        return
    source_ids: list[str] = []
    for index, source in enumerate(sources):
        prefix = f"capability_config.external-data.sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("id", "provider", "rights_policy"):
            if not nonempty(source.get(field)):
                errors.append(f"{prefix}.{field} is required")
        if source.get("access_eligibility") != FREE_DATA_ACCESS_ELIGIBILITY:
            errors.append(
                f"{prefix}.access_eligibility must equal "
                f"{FREE_DATA_ACCESS_ELIGIBILITY}"
            )
        source_declaration = "\n".join(
            f"data source {field}: {source[field]}"
            for field in ("provider", "rights_policy")
            if nonempty(source.get(field))
        )
        errors.extend(
            f"{prefix}: {reason}"
            for reason in prohibited_paid_data_reasons(source_declaration)
        )
        if source.get("role") not in SOURCE_ROLES:
            errors.append(f"{prefix}.role is invalid")
        if nonempty(source.get("id")):
            source_ids.append(source["id"])
        collector = source.get("collector")
        if collector:
            project_path(
                root,
                collector,
                f"{prefix}.collector",
                errors,
                must_exist=True,
            )
        if source.get("paid_fallback_enabled") not in {None, False}:
            errors.append(f"{prefix}.paid_fallback_enabled must be false")
    if len(source_ids) != len(set(source_ids)):
        errors.append("external data source IDs must be unique")


def validate_web_ui(
    root: Path,
    manifest: dict[str, Any],
    effective: set[str],
    errors: list[str],
) -> None:
    if "web-ui" not in effective:
        return
    config = capability_config(manifest, "web-ui", errors)
    for field in ("root", "design_contract"):
        value = config.get(field)
        if value:
            project_path(
                root,
                value,
                f"capability_config.web-ui.{field}",
                errors,
                must_exist=True,
            )
    if "test_commands" in config:
        unique_strings(
            config.get("test_commands"),
            "capability_config.web-ui.test_commands",
            errors,
        )


def validate_backend(
    root: Path,
    manifest: dict[str, Any],
    effective: set[str],
    errors: list[str],
) -> None:
    if "backend" not in effective:
        return
    config = capability_config(manifest, "backend", errors)
    entrypoints = unique_strings(
        config.get("entrypoints"),
        "capability_config.backend.entrypoints",
        errors,
        allow_empty=False,
    )
    for index, entrypoint in enumerate(entrypoints):
        project_path(
            root,
            entrypoint,
            f"capability_config.backend.entrypoints[{index}]",
            errors,
            must_exist=True,
        )
    if config.get("secret_policy") not in {
        "server-only",
        "none-required",
    }:
        errors.append(
            "active backend secret_policy must be server-only or none-required"
        )


def validate_automation(
    root: Path,
    manifest: dict[str, Any],
    effective: set[str],
    errors: list[str],
) -> None:
    if "scheduled-automation" not in effective:
        return
    config = capability_config(
        manifest,
        "scheduled-automation",
        errors,
    )
    schedules = config.get("schedules")
    if not isinstance(schedules, list) or not schedules:
        errors.append(
            "active scheduled-automation requires a non-empty schedules array"
        )
        return
    for index, schedule in enumerate(schedules):
        prefix = f"capability_config.scheduled-automation.schedules[{index}]"
        if not isinstance(schedule, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in (
            "id",
            "entrypoint",
            "schedule",
            "timezone",
            "last_good_policy",
        ):
            if not nonempty(schedule.get(field)):
                errors.append(f"{prefix}.{field} is required")
        if nonempty(schedule.get("entrypoint")):
            project_path(
                root,
                schedule["entrypoint"],
                f"{prefix}.entrypoint",
                errors,
                must_exist=True,
            )
        for field in ("retry_ceiling", "concurrency_ceiling"):
            value = schedule.get(field)
            minimum = 0 if field == "retry_ceiling" else 1
            if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
                errors.append(f"{prefix}.{field} must be an integer >= {minimum}")
        preflight = schedule.get("cost_preflight")
        if not isinstance(preflight, dict):
            errors.append(f"{prefix}.cost_preflight must be an object")
        elif preflight.get("precedes_remote_work") is not True:
            errors.append(
                f"{prefix}.cost_preflight.precedes_remote_work must be true"
            )


def validate_publication(
    manifest: dict[str, Any],
    effective: set[str],
    errors: list[str],
) -> None:
    if "publication" not in effective:
        return
    config = capability_config(manifest, "publication", errors)
    if not nonempty(config.get("last_good_policy")):
        errors.append(
            "active publication requires capability_config.publication."
            "last_good_policy"
        )
    targets = config.get("targets")
    if not isinstance(targets, list) or not targets:
        errors.append("active publication requires a non-empty targets array")
    else:
        for index, target in enumerate(targets):
            prefix = f"capability_config.publication.targets[{index}]"
            if not isinstance(target, dict):
                errors.append(f"{prefix} must be an object")
                continue
            if not nonempty(target.get("id")):
                errors.append(f"{prefix}.id is required")
            url = target.get("public_url")
            if url and not valid_http_url(url):
                errors.append(f"{prefix}.public_url is invalid")


def validate_release(
    manifest: dict[str, Any],
    effective: set[str],
    errors: list[str],
) -> None:
    if "remote-release" not in effective:
        return
    project = manifest.get("project", {})
    adapters = manifest.get("adapters")
    config = capability_config(manifest, "remote-release", errors)
    kind = config.get("kind")
    if kind is None:
        kind = (
            "scm"
            if isinstance(adapters, dict) and adapters.get("scm")
            else "provider"
        )
    if kind not in {"scm", "provider"}:
        errors.append(
            "capability_config.remote-release.kind must be scm or provider"
        )
    elif kind == "scm":
        repository = project.get("repository")
        if not nonempty(repository) or not REPOSITORY.fullmatch(repository):
            errors.append(
                "SCM remote-release requires project.repository as "
                "owner/repository"
            )
        if not isinstance(adapters, dict) or not adapters.get("scm"):
            errors.append("SCM remote-release requires an scm adapter")
        for field in ("base_branch", "approved_account"):
            if not nonempty(config.get(field)):
                errors.append(
                    f"capability_config.remote-release.{field} is required"
                )
    elif kind == "provider":
        targets = config.get("targets")
        if not isinstance(targets, list) or not targets:
            errors.append(
                "provider remote-release requires a non-empty targets array"
            )
        else:
            for index, target in enumerate(targets):
                prefix = (
                    "capability_config.remote-release.targets"
                    f"[{index}]"
                )
                if not isinstance(target, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                for field in (
                    "id",
                    "provider",
                    "account_or_project",
                    "action",
                ):
                    if not nonempty(target.get(field)):
                        errors.append(f"{prefix}.{field} is required")
    for field in ("preview_url", "production_url"):
        value = config.get(field)
        if value and not valid_http_url(value):
            errors.append(
                f"capability_config.remote-release.{field} is invalid"
            )


def validate(
    root: Path,
    manifest: dict[str, Any],
) -> tuple[list[str], list[str]]:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    if manifest.get("schema_version") != 2:
        return ["schema_version must equal 2"], warnings
    unknown_top_level = sorted(set(manifest) - TOP_LEVEL_FIELDS)
    if unknown_top_level:
        errors.append(
            "unknown top-level manifest fields: "
            + ", ".join(unknown_top_level)
        )

    project = manifest.get("project")
    if not isinstance(project, dict):
        errors.append("project must be an object")
        project = {}
    else:
        reject_unknown_keys(project, PROJECT_FIELDS, "project", errors)
    for field in ("id", "purpose"):
        if not nonempty(project.get(field)):
            errors.append(f"project.{field} is required")
    if nonempty(project.get("id")) and not PROJECT_ID.fullmatch(project["id"]):
        errors.append("project.id must use lowercase letters, digits, and hyphens")
    repository = project.get("repository")
    if repository is not None and (
        not nonempty(repository) or not REPOSITORY.fullmatch(repository)
    ):
        errors.append("project.repository must use owner/repository")

    if manifest.get("assurance") not in ASSURANCE_LEVELS:
        errors.append(
            "assurance must be one of " + ", ".join(ASSURANCE_LEVELS)
        )
    if (
        "delivery" in manifest
        and manifest.get("delivery") not in DELIVERY_LEVELS
    ):
        errors.append(
            "delivery must be one of " + ", ".join(DELIVERY_LEVELS)
        )
    unique_strings(manifest.get("profiles", []), "profiles", errors)
    declared_capabilities = unique_strings(
        manifest.get("capabilities", []), "capabilities", errors
    )
    if declared_capabilities:
        runtime_only = sorted(
            set(declared_capabilities) & RUNTIME_CAPABILITIES
        )
        if runtime_only:
            errors.append(
                "runtime-only capabilities cannot be persisted in a project "
                "manifest: " + ", ".join(runtime_only)
            )
        unsupported = sorted(
            {
                value
                for value in declared_capabilities
                if isinstance(value, str)
                and not value.startswith("x-")
                and value not in PROJECT_CAPABILITIES
                and value not in RUNTIME_CAPABILITIES
            }
        )
        if unsupported:
            errors.append(
                "unknown project capabilities: " + ", ".join(unsupported)
            )

    contracts = manifest.get("contracts")
    if not isinstance(contracts, dict):
        errors.append("contracts must be an object")
        contracts = {}
    else:
        reject_unknown_keys(
            contracts, CONTRACT_FIELDS, "contracts", errors
        )
    protected_paths = unique_strings(
        contracts.get("protected_paths", []),
        "contracts.protected_paths",
        errors,
    )
    unique_strings(
        contracts.get("test_commands", []),
        "contracts.test_commands",
        errors,
    )
    for index, pattern in enumerate(protected_paths):
        project_path(
            root,
            pattern,
            f"contracts.protected_paths[{index}]",
            errors,
            must_exist=False,
        )

    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority must be an object")
        authority = {}
    else:
        reject_unknown_keys(
            authority, AUTHORITY_FIELDS, "authority", errors
        )
    if authority.get("cost_policy") != ZERO_SPEND_POLICY:
        errors.append("authority.cost_policy is invalid")
    if authority.get("paid_action_authority") is not None:
        errors.append("project manifests cannot grant paid-action authority")
    if authority.get("paid_fallback_enabled") is not False:
        errors.append("authority.paid_fallback_enabled must be false")

    try:
        context = resolve(manifest)
    except CapabilityError as exc:
        errors.append(str(exc))
        context = {
            "effective_capabilities": [],
            "required_gates": [],
            "required_references": [],
        }
    effective = set(context["effective_capabilities"])

    configs = manifest.get("capability_config", {})
    if not isinstance(configs, dict):
        errors.append("capability_config must be an object")
    else:
        undeclared = sorted(set(configs) - effective)
        if undeclared:
            errors.append(
                "capability_config contains undeclared capabilities: "
                + ", ".join(undeclared)
            )

    validate_analysis(root, manifest, effective, errors)
    validate_input_binding(manifest, effective, errors)
    validate_external_data(root, manifest, effective, errors)
    validate_web_ui(root, manifest, effective, errors)
    validate_backend(root, manifest, effective, errors)
    validate_automation(root, manifest, effective, errors)
    validate_publication(manifest, effective, errors)
    validate_release(manifest, effective, errors)

    extensions = manifest.get("extensions")
    if not isinstance(extensions, dict):
        errors.append("extensions must be an object")
    errors.extend(policy_violations(manifest))
    if not effective:
        warnings.append("no optional project capabilities are active")
    return errors, warnings
