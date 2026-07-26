#!/usr/bin/env python3
"""Validate a project-owned Quant Research contract without extra packages."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CONTROL_KINDS = {"display", "result_selector", "analysis", "operation"}
SOURCE_ROLES = {"required", "optional", "benchmark", "fallback"}
SOURCE_FALLBACK_POLICIES = {
    "fail-closed",
    "explicit-degraded",
    "last-good-explicit-degraded",
}
SOURCE_FRESHNESS_FIELDS = {
    "source_as_of",
    "collected_at",
    "artifact_sha256",
}
SOURCE_PROVENANCE_FIELDS = SOURCE_FRESHNESS_FIELDS | {"source_id"}
RESULT_IDENTITY_FIELDS = {
    "project_id",
    "run_id",
    "data_as_of",
    "code_version",
    "data_manifest_sha256",
    "analysis_input_sha256",
    "analysis_input_validation_sha256",
    "analysis_entrypoint_sha256",
    "config_hash",
    "effective_config_hash",
    "input_schema_version",
    "data_schema_version",
    "result_schema_version",
    "artifact_sha256",
}
AUTOMATION_FRESHNESS_FIELDS = {
    "source_as_of",
    "collected_at",
    "data_as_of",
    "calculated_at",
    "published_at",
    "verified_at",
}
REPOSITORY = re.compile(r"^[^/\s]+/[^/\s]+$")
COST_POLICY = (
    "zero-spend-unless-user-first-requests-specific-paid-action"
)
PIPELINE = (
    "collect",
    "validate",
    "normalize",
    "coherent_cutoff",
    "analyze",
    "validate_result",
    "stage",
    "publish",
    "deploy",
    "public_readback",
)
SECRET_VALUE_KEYS = {
    "token",
    "password",
    "api_key",
    "secret_value",
    "service_role",
    "private_key",
}
PAID_FALLBACK_TERMS = {
    "paid",
    "billable",
    "metered",
    "overage",
    "upgrade",
    "trial",
}
MONTH_NAMES = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}
DAY_NAMES = {
    "SUN": 0,
    "MON": 1,
    "TUE": 2,
    "WED": 3,
    "THU": 4,
    "FRI": 5,
    "SAT": 6,
}
TRUSTED_GITHUB_HOSTED_RUNNERS = {
    "ubuntu-latest",
    "ubuntu-24.04",
    "ubuntu-22.04",
    "windows-latest",
    "windows-2025",
    "windows-2022",
    "macos-latest",
    "macos-15",
    "macos-14",
    "macos-13",
}
DANGEROUS_WORKFLOW_ENVIRONMENT = {
    "BASH_ENV",
    "DYLD_INSERT_LIBRARIES",
    "ENV",
    "GITHUB_ENV",
    "GITHUB_PATH",
    "GITHUB_WORKSPACE",
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "NODE_OPTIONS",
    "PATH",
    "PERL5OPT",
    "PYTHONHOME",
    "PYTHONPATH",
    "RUBYOPT",
    "SHELLOPTS",
}


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("Manifest root must be an object")
    return value


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def require_strings(
    value: dict[str, Any],
    fields: tuple[str, ...],
    prefix: str,
    errors: list[str],
) -> None:
    for field in fields:
        if not nonempty_string(value.get(field)):
            errors.append(f"{prefix}.{field} must be a non-empty string")


def string_list(value: Any, *, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(nonempty_string(item) for item in value)
    )


def integer_between(value: Any, minimum: int, maximum: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    )


def project_path(
    root: Path,
    value: Any,
    prefix: str,
    errors: list[str],
    *,
    must_exist: bool,
    kind: str = "file",
) -> Path | None:
    if not nonempty_string(value):
        return None
    if "\x00" in value or "\\" in value:
        errors.append(f"{prefix} must be a portable project-relative path")
        return None
    path = Path(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value)
    ):
        errors.append(f"{prefix} must stay within project root: {value}")
        return None
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        errors.append(f"{prefix} resolves outside project root: {value}")
        return None
    if must_exist:
        if kind == "directory" and not resolved.is_dir():
            errors.append(f"{prefix} directory does not exist: {value}")
        elif kind == "file" and not resolved.is_file():
            errors.append(f"{prefix} file does not exist: {value}")
    return resolved


def valid_http_url(value: Any) -> bool:
    if not nonempty_string(value) or any(character.isspace() for character in value):
        return False
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme.lower() in {"http", "https"}
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
    )


def validate_optional_url(
    value: Any,
    prefix: str,
    errors: list[str],
) -> None:
    if value in (None, ""):
        return
    if not valid_http_url(value):
        errors.append(f"{prefix} must be an HTTP(S) URL without credentials")


def cron_value(
    token: str,
    *,
    minimum: int,
    maximum: int,
    names: dict[str, int] | None,
) -> int | None:
    upper = token.upper()
    if names and upper in names:
        return names[upper]
    if not token.isdigit():
        return None
    value = int(token)
    return value if minimum <= value <= maximum else None


def valid_cron_field(
    field: str,
    *,
    minimum: int,
    maximum: int,
    names: dict[str, int] | None = None,
) -> bool:
    if not field:
        return False
    for item in field.split(","):
        if not item:
            return False
        base, separator, step = item.partition("/")
        if separator and (not step.isdigit() or int(step) < 1):
            return False
        if base == "*":
            continue
        if "-" in base:
            start, marker, end = base.partition("-")
            if not marker or "-" in end:
                return False
            start_value = cron_value(
                start,
                minimum=minimum,
                maximum=maximum,
                names=names,
            )
            end_value = cron_value(
                end,
                minimum=minimum,
                maximum=maximum,
                names=names,
            )
            if (
                start_value is None
                or end_value is None
                or start_value > end_value
            ):
                return False
            continue
        if cron_value(
            base,
            minimum=minimum,
            maximum=maximum,
            names=names,
        ) is None:
            return False
    return True


def valid_cron(expression: Any) -> bool:
    if not nonempty_string(expression):
        return False
    fields = expression.split()
    if len(fields) != 5:
        return False
    rules = (
        (0, 59, None),
        (0, 23, None),
        (1, 31, None),
        (1, 12, MONTH_NAMES),
        (0, 7, DAY_NAMES),
    )
    return all(
        valid_cron_field(
            field,
            minimum=minimum,
            maximum=maximum,
            names=names,
        )
        for field, (minimum, maximum, names) in zip(fields, rules)
    )


def workflow_schedule_crons(text: str) -> tuple[bool, list[str]]:
    lines = text.splitlines()
    on_index: int | None = None
    on_indent = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0 and re.match(
            r"^(?:on|['\"]on['\"])\s*:\s*(?:#.*)?$",
            stripped,
        ):
            on_index = index
            break
    if on_index is None:
        return False, []

    schedule_index: int | None = None
    schedule_indent = 0
    for index in range(on_index + 1, len(lines)):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= on_indent:
            break
        if re.match(r"^schedule\s*:\s*(?:#.*)?$", stripped):
            schedule_index = index
            schedule_indent = indent
            break
    if schedule_index is None:
        return False, []

    values: list[str] = []
    pattern = re.compile(r"^-\s*cron\s*:\s*(.*?)\s*(?:#.*)?$")
    for line in lines[schedule_index + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= schedule_indent:
            break
        match = pattern.match(stripped)
        if match is None:
            continue
        value = match.group(1).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values.append(" ".join(value.split()))
    return True, values


def simple_yaml_mapping_key(text: str) -> str | None:
    logical = re.sub(r"^-\s*", "", text.strip())
    match = re.match(
        r"^(?:\"([A-Za-z0-9_-]+)\"|'([A-Za-z0-9_-]+)'|"
        r"([A-Za-z0-9_-]+))\s*:",
        logical,
    )
    if match is None:
        return None
    return next(value for value in match.groups() if value is not None)


def duplicated(values: list[str]) -> list[str]:
    return sorted(
        value for value in set(values) if values.count(value) > 1
    )


def workflow_trigger_keys(text: str) -> tuple[int, list[str]]:
    lines = text.splitlines()
    on_indices = [
        index
        for index, line in enumerate(lines)
        if (
            len(line) == len(line.lstrip(" "))
            and re.match(
                r"^(?:on|['\"]on['\"])\s*:\s*(?:#.*)?$",
                line.strip(),
            )
        )
    ]
    if len(on_indices) != 1:
        return len(on_indices), []
    start = on_indices[0]
    children: list[tuple[int, str]] = []
    for line in lines[start + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            break
        children.append((indent, line.strip()))
    if not children:
        return 1, []
    event_indent = min(indent for indent, _ in children)
    events: list[str] = []
    for indent, stripped in children:
        if indent != event_indent:
            continue
        key = simple_yaml_mapping_key(stripped)
        if key is not None:
            events.append(key)
    return 1, events


def workflow_concurrency(text: str) -> tuple[int, dict[str, list[str]]]:
    lines = text.splitlines()
    indices = [
        index
        for index, line in enumerate(lines)
        if (
            len(line) == len(line.lstrip(" "))
            and re.match(
                r"^(?:concurrency|['\"]concurrency['\"])\s*:"
                r"\s*(?:#.*)?$",
                line.strip(),
            )
        )
    ]
    if len(indices) != 1:
        return len(indices), {}
    start = indices[0]
    children: list[tuple[int, str]] = []
    for line in lines[start + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            break
        children.append((indent, line.strip()))
    if not children:
        return 1, {}
    field_indent = min(indent for indent, _ in children)
    fields: dict[str, list[str]] = {}
    for indent, stripped in children:
        if indent != field_indent:
            continue
        match = re.match(
            r"^(?:\"([A-Za-z0-9_-]+)\"|'([A-Za-z0-9_-]+)'|"
            r"([A-Za-z0-9_-]+))\s*:\s*(.*?)\s*$",
            stripped,
        )
        if match is None:
            continue
        key = next(
            value for value in match.groups()[:3] if value is not None
        )
        fields.setdefault(key, []).append(match.group(4))
    return 1, fields


def yaml_scalar(value: str) -> str | None:
    stripped = value.strip()
    if (
        len(stripped) >= 2
        and stripped[0] == stripped[-1]
        and stripped[0] in {"'", '"'}
    ):
        stripped = stripped[1:-1]
    if (
        not stripped
        or stripped.startswith(("[", "{", "*", "&", "${{"))
        or any(character.isspace() for character in stripped)
    ):
        return None
    return stripped


def environment_overrides(
    lines: list[str],
    *,
    exact_indent: int,
) -> tuple[set[str], bool, bool]:
    dangerous: set[str] = set()
    ambiguous = False
    declared = False
    for index, line in enumerate(lines):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent != exact_indent:
            continue
        match = re.match(
            r"^(?:env|['\"]env['\"])\s*:\s*(.*?)\s*$",
            line.strip(),
        )
        if match is None:
            continue
        declared = True
        inline = match.group(1)
        if inline and not inline.startswith("#"):
            ambiguous = True
            continue
        for nested in lines[index + 1 :]:
            if not nested.strip() or nested.lstrip().startswith("#"):
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= exact_indent:
                break
            stripped = nested.strip()
            if re.match(r"^(?:<<|['\"]<<['\"])\s*:", stripped):
                ambiguous = True
                continue
            key_match = re.match(
                r"^(?:\"([^\"]+)\"|'([^']+)'|"
                r"([A-Za-z_][A-Za-z0-9_]*))\s*:",
                stripped,
            )
            if key_match is None:
                continue
            key = next(
                value for value in key_match.groups() if value is not None
            ).upper()
            if key in DANGEROUS_WORKFLOW_ENVIRONMENT:
                dangerous.add(key)
    return dangerous, ambiguous, declared


def ambiguous_yaml_mapping_keys(text: str) -> list[str]:
    findings: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        logical = re.sub(r"^-\s*", "", stripped)
        if not logical or logical.startswith("#"):
            continue
        if logical.startswith("?"):
            findings.append(f"line {number}: explicit mapping key")
        if logical.startswith("%"):
            findings.append(f"line {number}: YAML directive")
        if re.match(r"^(?:<<|['\"]<<['\"])\s*:", logical):
            findings.append(f"line {number}: merged mapping key")
        if (
            re.match(
                r"^(?:!!|!<|![A-Za-z]|&[A-Za-z0-9_-]+\s+|"
                r"\*[A-Za-z0-9_-]+\s*:)",
                logical,
            )
            or re.search(
                r"[{,]\s*(?:!!|!<|![A-Za-z]|"
                r"&[A-Za-z0-9_-]+\s+|\*[A-Za-z0-9_-]+\s*:)",
                logical,
            )
        ):
            findings.append(
                f"line {number}: tagged, anchored, or aliased mapping key"
            )
        if (
            re.match(r'^"[^"\n]*\\', logical)
            or re.search(r'[{,]\s*"[^"\n]*\\', logical)
        ):
            findings.append(f"line {number}: escaped mapping key")
    return findings


def validate_workflow_schedule(
    workflow: Path,
    *,
    workflow_label: str,
    cron: str,
    expected_crons: set[str],
    concurrency_group: str,
    cancel_in_progress: bool,
    job_id: str,
    cost_preflight_step_id: str,
    entrypoint_step_id: str,
    entrypoint_command: str,
    cost_preflight_command: str,
    errors: list[str],
) -> None:
    try:
        text = workflow.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{workflow_label} cannot be read as UTF-8: {exc}")
        return
    ambiguous_keys = ambiguous_yaml_mapping_keys(text)
    if ambiguous_keys:
        errors.append(
            f"{workflow_label} must use simple literal YAML mapping keys; "
            + "; ".join(ambiguous_keys)
        )
    has_schedule, declared_crons = workflow_schedule_crons(text)
    on_count, trigger_keys = workflow_trigger_keys(text)
    concurrency_count, concurrency_fields = workflow_concurrency(text)
    if not re.search(r"(?m)^(?:on|['\"]on['\"])\s*:\s*(?:#.*)?$", text):
        errors.append(f"{workflow_label} must declare an on block")
    if not has_schedule:
        errors.append(f"{workflow_label} must declare an on.schedule block")
    if on_count != 1:
        errors.append(f"{workflow_label} must declare exactly one on block")
    trigger_key_set = set(trigger_keys)
    if not trigger_keys or not trigger_key_set.issubset(
        {"schedule", "workflow_dispatch"}
    ):
        errors.append(
            f"{workflow_label} triggers must be limited to schedule and "
            "optional workflow_dispatch"
        )
    if duplicated(trigger_keys):
        errors.append(
            f"{workflow_label} trigger mapping keys must be unique: "
            + ", ".join(duplicated(trigger_keys))
        )
    if concurrency_count != 1:
        errors.append(
            f"{workflow_label} must declare exactly one workflow-level "
            "concurrency block"
        )
    if set(concurrency_fields) != {"group", "cancel-in-progress"} or any(
        len(values) != 1 for values in concurrency_fields.values()
    ):
        errors.append(
            f"{workflow_label} concurrency must declare only one group and "
            "one cancel-in-progress value"
        )
    else:
        declared_group = yaml_scalar(concurrency_fields["group"][0])
        if declared_group != concurrency_group:
            errors.append(
                f"{workflow_label} concurrency group must exactly match "
                "the project manifest"
            )
        declared_cancel = concurrency_fields["cancel-in-progress"][0].strip()
        if cancel_in_progress is not False or declared_cancel != "false":
            errors.append(
                f"{workflow_label} concurrency cancel-in-progress must be "
                "the literal false value"
            )
    if not re.search(r"(?m)^jobs\s*:\s*(?:#.*)?$", text):
        errors.append(f"{workflow_label} must declare jobs")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        defaults_match = re.match(
            r"^(?:defaults|['\"]defaults['\"])\s*:\s*(.*?)\s*$",
            stripped,
        )
        if defaults_match is None:
            continue
        defaults_indent = len(line) - len(line.lstrip(" "))
        inline_defaults = defaults_match.group(1)
        defaults_block: list[str] = []
        if inline_defaults and not inline_defaults.startswith("#"):
            defaults_block.append(inline_defaults)
        for nested in lines[index + 1 :]:
            if not nested.strip() or nested.lstrip().startswith("#"):
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= defaults_indent:
                break
            defaults_block.append(nested.strip())
        if any(
            re.search(
                r"(?:^|[,{]\s*)(?:shell|['\"]shell['\"]|"
                r"working-directory|['\"]working-directory['\"])\s*:",
                nested,
            )
            for nested in defaults_block
        ):
            errors.append(
                f"{workflow_label} must not override shell or "
                "working-directory through defaults.run"
            )
        elif inline_defaults and not inline_defaults.startswith("#"):
            errors.append(
                f"{workflow_label} must not use inline or aliased defaults "
                "for a required job"
            )
    (
        workflow_environment,
        workflow_environment_ambiguous,
        workflow_environment_declared,
    ) = (
        environment_overrides(lines, exact_indent=0)
    )
    if workflow_environment_declared:
        errors.append(
            f"{workflow_label} workflow must not declare env because it "
            "changes the required cost-check execution context"
        )
    if workflow_environment:
        errors.append(
            f"{workflow_label} workflow env overrides execution context: "
            + ", ".join(sorted(workflow_environment))
        )
    if workflow_environment_ambiguous:
        errors.append(
            f"{workflow_label} workflow env must not use inline or aliased "
            "configuration"
        )
    normalized_cron = " ".join(cron.split())
    if normalized_cron not in declared_crons:
        errors.append(
            f"{workflow_label} does not declare schedule cron {cron!r}"
        )
    if (
        len(declared_crons) != len(expected_crons)
        or set(declared_crons) != expected_crons
    ):
        errors.append(
            f"{workflow_label} schedule crons must exactly match the "
            "project manifest"
        )
    top_level_keys = [
        key
        for line in lines
        if len(line) == len(line.lstrip(" "))
        and (key := simple_yaml_mapping_key(line)) is not None
    ]
    if duplicated(top_level_keys):
        errors.append(
            f"{workflow_label} top-level mapping keys must be unique: "
            + ", ".join(duplicated(top_level_keys))
        )
    jobs_indices = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^jobs\s*:\s*(?:#.*)?$", line.strip())
        and len(line) == len(line.lstrip(" "))
    ]
    jobs_index = jobs_indices[0] if len(jobs_indices) == 1 else None
    if len(jobs_indices) != 1:
        errors.append(f"{workflow_label} must declare exactly one jobs block")
    job_start: int | None = None
    job_indent: int | None = None
    declared_job_id_list: list[str] = []
    if jobs_index is not None:
        job_candidates: list[tuple[int, int, str]] = []
        for index in range(jobs_index + 1, len(lines)):
            line = lines[index]
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent == 0:
                break
            match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(?:#.*)?$", line.strip())
            if match:
                job_candidates.append((indent, index, match.group(1)))
        if job_candidates:
            first_level_indent = min(
                indent for indent, _, _ in job_candidates
            )
            declared_job_id_list = [
                candidate
                for indent, _, candidate in job_candidates
                if indent == first_level_indent
            ]
            for indent, index, candidate in job_candidates:
                if indent == first_level_indent and candidate == job_id:
                    job_start = index
                    job_indent = indent
                    break
    if duplicated(declared_job_id_list):
        errors.append(
            f"{workflow_label} job IDs must be unique: "
            + ", ".join(duplicated(declared_job_id_list))
        )
    if set(declared_job_id_list) != {job_id}:
        errors.append(
            f"{workflow_label} jobs must contain only the declared required "
            f"job {job_id!r}"
        )
    if job_start is None or job_indent is None:
        errors.append(f"{workflow_label} does not declare required job {job_id!r}")
        return
    job_end = len(lines)
    for index in range(job_start + 1, len(lines)):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent < job_indent:
            job_end = index
            break
        if indent == job_indent and re.match(
            r"^[A-Za-z0-9_-]+\s*:\s*(?:#.*)?$",
            line.strip(),
        ):
            job_end = index
            break
    job_lines = lines[job_start + 1 : job_end]
    job_property_keys = [
        key
        for line in job_lines
        if len(line) - len(line.lstrip(" ")) == job_indent + 2
        and (key := simple_yaml_mapping_key(line)) is not None
    ]
    if duplicated(job_property_keys):
        errors.append(
            f"{workflow_label} required job mapping keys must be unique: "
            + ", ".join(duplicated(job_property_keys))
        )
    runs_on_values: list[str | None] = []
    container_declared = False
    strategy_declared = False
    for line in job_lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent != job_indent + 2:
            continue
        stripped = line.strip()
        runs_on_match = re.match(
            r"^(?:runs-on|['\"]runs-on['\"])\s*:\s*(.*?)\s*$",
            stripped,
        )
        if runs_on_match is not None:
            runs_on_values.append(yaml_scalar(runs_on_match.group(1)))
        if re.match(
            r"^(?:container|['\"]container['\"])\s*:",
            stripped,
        ):
            container_declared = True
        if re.match(
            r"^(?:strategy|['\"]strategy['\"])\s*:",
            stripped,
        ):
            strategy_declared = True
    if (
        len(runs_on_values) != 1
        or runs_on_values[0] not in TRUSTED_GITHUB_HOSTED_RUNNERS
    ):
        errors.append(
            f"{workflow_label} required job must use one literal trusted "
            "GitHub-hosted runner"
        )
    if container_declared:
        errors.append(
            f"{workflow_label} required job must not use a container"
        )
    if strategy_declared:
        errors.append(
            f"{workflow_label} required job must not use strategy or matrix"
        )
    (
        job_environment,
        job_environment_ambiguous,
        job_environment_declared,
    ) = environment_overrides(
        job_lines,
        exact_indent=job_indent + 2,
    )
    if job_environment_declared:
        errors.append(
            f"{workflow_label} required job must not declare env"
        )
    if job_environment:
        errors.append(
            f"{workflow_label} required job env overrides execution context: "
            + ", ".join(sorted(job_environment))
        )
    if job_environment_ambiguous:
        errors.append(
            f"{workflow_label} required job env must not use inline or "
            "aliased configuration"
        )
    if any(
        len(line) - len(line.lstrip(" ")) == job_indent + 2
        and re.match(r"^(?:if|['\"]if['\"])\s*:", line.strip())
        for line in job_lines
    ):
        errors.append(f"{workflow_label} required job must not be conditional")
    if any(
        len(line) - len(line.lstrip(" ")) == job_indent + 2
        and re.match(
            r"^(?:continue-on-error|['\"]continue-on-error['\"])\s*:",
            line.strip(),
            re.I,
        )
        for line in job_lines
    ):
        errors.append(
            f"{workflow_label} required job must not declare continue-on-error"
        )

    steps_line_index = next(
        (
            index
            for index, line in enumerate(job_lines)
            if re.match(r"^steps\s*:\s*(?:#.*)?$", line.strip())
        ),
        None,
    )
    if steps_line_index is None:
        errors.append(f"{workflow_label} required job has no steps")
        return
    steps_indent = len(job_lines[steps_line_index]) - len(
        job_lines[steps_line_index].lstrip(" ")
    )
    step_lines = job_lines[steps_line_index + 1 :]
    step_starts = [
        index
        for index, line in enumerate(step_lines)
        if (
            len(line) - len(line.lstrip(" ")) == steps_indent + 2
            and re.match(r"^\s*-\s+", line)
        )
    ]
    steps: dict[str, dict[str, Any]] = {}
    step_order: list[str] = []
    all_steps: list[dict[str, Any]] = []
    for position, start in enumerate(step_starts):
        end = (
            step_starts[position + 1]
            if position + 1 < len(step_starts)
            else len(step_lines)
        )
        block = step_lines[start:end]
        step_id = ""
        commands: list[str] = []
        conditional = False
        continue_on_error = False
        shell_declared = False
        working_directory_declared = False
        inherited_configuration = False
        uses: list[str] = []
        with_declared = False
        step_indent = len(block[0]) - len(block[0].lstrip(" "))
        (
            step_environment,
            step_environment_ambiguous,
            step_environment_declared,
        ) = environment_overrides(block, exact_indent=step_indent + 2)
        step_property_keys: list[str] = []
        index = 0
        while index < len(block):
            line_indent = len(block[index]) - len(block[index].lstrip(" "))
            stripped = block[index].strip()
            stripped = re.sub(r"^-\s*", "", stripped)
            if line_indent in {step_indent, step_indent + 2}:
                key = simple_yaml_mapping_key(block[index])
                if key is not None:
                    step_property_keys.append(key)
            id_match = re.match(
                r"^(?:id|['\"]id['\"])\s*:\s*([A-Za-z0-9_-]+)\s*$",
                stripped,
            )
            if id_match:
                step_id = id_match.group(1)
            if re.match(r"^(?:if|['\"]if['\"])\s*:", stripped):
                conditional = True
            if re.match(
                r"^(?:continue-on-error|['\"]continue-on-error['\"])"
                r"\s*:",
                stripped,
                re.I,
            ):
                continue_on_error = True
            if re.match(
                r"^(?:shell|['\"]shell['\"])\s*:",
                stripped,
            ):
                shell_declared = True
            if re.match(
                r"^(?:working-directory|['\"]working-directory['\"])\s*:",
                stripped,
            ):
                working_directory_declared = True
            if re.match(r"^(?:<<|['\"]<<['\"])\s*:", stripped):
                inherited_configuration = True
            if (
                line_indent == step_indent + 2
                and re.match(r"^(?:with|['\"]with['\"])\s*:", stripped)
            ):
                with_declared = True
            uses_match = re.match(
                r"^(?:uses|['\"]uses['\"])\s*:\s*(.*?)\s*$",
                stripped,
            )
            if line_indent in {step_indent, step_indent + 2} and uses_match:
                uses.append(uses_match.group(1).strip().strip("'\""))
            run_match = re.match(
                r"^(?:run|['\"]run['\"])\s*:\s*(.*?)\s*$",
                stripped,
            )
            if run_match:
                value = run_match.group(1)
                if value not in {"|", ">", "|-", ">-", "|+", ">+"}:
                    commands.append(" ".join(value.split()))
                else:
                    run_indent = len(block[index]) - len(
                        block[index].lstrip(" ")
                    )
                    cursor = index + 1
                    while cursor < len(block):
                        nested = block[cursor]
                        nested_indent = len(nested) - len(nested.lstrip(" "))
                        if nested.strip() and nested_indent <= run_indent:
                            break
                        if nested.strip() and not nested.lstrip().startswith("#"):
                            commands.append(" ".join(nested.strip().split()))
                        cursor += 1
            index += 1
        if duplicated(step_property_keys):
            errors.append(
                f"{workflow_label} step mapping keys must be unique: "
                + ", ".join(duplicated(step_property_keys))
            )
        if step_id:
            if step_id in steps:
                errors.append(f"{workflow_label} step ID {step_id!r} is duplicated")
            steps[step_id] = {
                "commands": commands,
                "conditional": conditional,
                "continue_on_error": continue_on_error,
                "shell_declared": shell_declared,
                "working_directory_declared": working_directory_declared,
                "inherited_configuration": inherited_configuration,
                "uses": uses,
                "with_declared": with_declared,
                "dangerous_environment": step_environment,
                "ambiguous_environment": step_environment_ambiguous,
                "environment_declared": step_environment_declared,
            }
            step_order.append(step_id)
        all_steps.append(
            {
                "id": step_id,
                "commands": commands,
                "conditional": conditional,
                "continue_on_error": continue_on_error,
                "shell_declared": shell_declared,
                "working_directory_declared": working_directory_declared,
                "inherited_configuration": inherited_configuration,
                "uses": uses,
                "with_declared": with_declared,
                "dangerous_environment": step_environment,
                "ambiguous_environment": step_environment_ambiguous,
                "environment_declared": step_environment_declared,
            }
        )

    normalized_entrypoint = " ".join(entrypoint_command.split())
    normalized_cost_preflight = " ".join(cost_preflight_command.split())
    entry_step = steps.get(entrypoint_step_id)
    cost_step = steps.get(cost_preflight_step_id)
    if not isinstance(entry_step, dict):
        errors.append(
            f"{workflow_label} missing entrypoint step {entrypoint_step_id!r}"
        )
    elif entry_step["commands"] != [normalized_entrypoint]:
        errors.append(
            f"{workflow_label} entrypoint step must contain only the exact "
            f"command {entrypoint_command!r}"
        )
    if not isinstance(cost_step, dict):
        errors.append(
            f"{workflow_label} missing cost step {cost_preflight_step_id!r}"
        )
    elif cost_step["commands"] != [normalized_cost_preflight]:
        errors.append(
            f"{workflow_label} cost step must contain only the exact "
            f"preflight command {cost_preflight_command!r}"
        )
    for step_id, step in (
        (cost_preflight_step_id, cost_step),
        (entrypoint_step_id, entry_step),
    ):
        if isinstance(step, dict) and (
            step["conditional"] or step["continue_on_error"]
        ):
            errors.append(
                f"{workflow_label} required step {step_id!r} must be "
                "unconditional and fail-closed"
            )
        if isinstance(step, dict) and step["shell_declared"]:
            errors.append(
                f"{workflow_label} required step {step_id!r} must not "
                "override its shell"
            )
        if isinstance(step, dict) and step["working_directory_declared"]:
            errors.append(
                f"{workflow_label} required step {step_id!r} must not "
                "override its working-directory"
            )
        if isinstance(step, dict) and step["inherited_configuration"]:
            errors.append(
                f"{workflow_label} required step {step_id!r} must not "
                "inherit aliased configuration"
            )
        if isinstance(step, dict) and step["dangerous_environment"]:
            errors.append(
                f"{workflow_label} required step {step_id!r} env overrides "
                "execution context: "
                + ", ".join(sorted(step["dangerous_environment"]))
            )
        if isinstance(step, dict) and step["ambiguous_environment"]:
            errors.append(
                f"{workflow_label} required step {step_id!r} env must not "
                "use inline or aliased configuration"
            )
        if isinstance(step, dict) and step["environment_declared"]:
            errors.append(
                f"{workflow_label} required step {step_id!r} must not "
                "declare env"
            )
        if isinstance(step, dict) and (
            step["uses"] or step["with_declared"]
        ):
            errors.append(
                f"{workflow_label} required step {step_id!r} must use only "
                "its exact run command"
            )
    if (
        cost_preflight_step_id in step_order
        and entrypoint_step_id in step_order
        and step_order.index(cost_preflight_step_id)
        > step_order.index(entrypoint_step_id)
    ):
        errors.append(
            f"{workflow_label} must run cost preflight before the entrypoint"
        )
    def is_pinned_checkout_step(step: dict[str, Any]) -> bool:
        return (
            len(step["uses"]) == 1
            and re.fullmatch(
                r"actions/checkout@[0-9a-fA-F]{40}",
                step["uses"][0],
            )
            is not None
            and not step["with_declared"]
            and not step["commands"]
            and not step["conditional"]
            and not step["continue_on_error"]
            and not step["shell_declared"]
            and not step["working_directory_declared"]
            and not step["inherited_configuration"]
            and not step["dangerous_environment"]
            and not step["ambiguous_environment"]
            and not step["environment_declared"]
        )

    cost_positions = [
        index
        for index, step in enumerate(all_steps)
        if step["id"] == cost_preflight_step_id
    ]
    if len(cost_positions) == 1:
        prior_steps = all_steps[: cost_positions[0]]
        if len(prior_steps) > 1:
            errors.append(
                f"{workflow_label} at most one pinned actions/checkout step "
                "may precede cost preflight"
            )
        for prior in prior_steps:
            if not is_pinned_checkout_step(prior):
                errors.append(
                    f"{workflow_label} only one pinned actions/checkout step "
                    "without overrides may precede cost preflight"
                )
                break
    executable_steps = all_steps
    if executable_steps and is_pinned_checkout_step(executable_steps[0]):
        executable_steps = executable_steps[1:]
    if (
        len(executable_steps) != 2
        or [step["id"] for step in executable_steps]
        != [cost_preflight_step_id, entrypoint_step_id]
    ):
        errors.append(
            f"{workflow_label} steps must be an optional pinned checkout "
            "followed only by cost preflight and the declared entrypoint"
        )


def contains_paid_fallback_language(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    words = set(re.findall(r"[a-z]+", value.lower()))
    return bool(words & PAID_FALLBACK_TERMS)


def validate_cost_bounds(value: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("automation.cost_bounds must be an object")
        return
    false_flags = (
        "overage_enabled",
        "paid_fallback_enabled",
        "trial_credit_or_overage_possible",
        "auto_renewing_trial_enabled",
        "automatic_upgrade_enabled",
        "payment_method_change_required",
        "payment_method_registration_required",
        "plan_upgrade_required",
        "pay_as_you_go_enabled",
        "free_quota_exceedance_allowed",
        "paid_add_on_enabled",
        "spend_cap_disabled",
    )
    integer_fields = (
        "retry_ceiling",
        "concurrency_ceiling",
        "retention_ceiling",
    )
    allowed_fields = {
        "policy",
        *false_flags,
        "spend_cap_enabled",
        "quota_hard_stop",
        *integer_fields,
    }
    unexpected_fields = sorted(set(value) - allowed_fields)
    if unexpected_fields:
        errors.append(
            "automation.cost_bounds has unexpected fields: "
            + ", ".join(unexpected_fields)
        )
    if value.get("policy") != "zero-spend":
        errors.append("automation.cost_bounds.policy must be zero-spend")
    for field in false_flags:
        if value.get(field) is not False:
            errors.append(
                f"automation.cost_bounds.{field} must be false"
            )
    if value.get("spend_cap_enabled") is not True:
        errors.append(
            "automation.cost_bounds.spend_cap_enabled must be true"
        )
    if value.get("quota_hard_stop") is not True:
        errors.append("automation.cost_bounds.quota_hard_stop must be true")
    for field, minimum, maximum in (
        ("retry_ceiling", 0, 10),
        ("concurrency_ceiling", 1, 10),
        ("retention_ceiling", 0, 3650),
    ):
        if not integer_between(value.get(field), minimum, maximum):
            errors.append(
                f"automation.cost_bounds.{field} must be an integer "
                f"{minimum}..{maximum}"
            )


def find_secret_values(
    value: Any,
    path: str = "",
) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            current = f"{path}.{key}" if path else key
            if key.lower() in SECRET_VALUE_KEYS and nested not in ("", None, []):
                errors.append(
                    f"{current} may contain a secret value; store secret names only"
                )
            errors.extend(find_secret_values(nested, current))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            errors.extend(find_secret_values(nested, f"{path}[{index}]"))
    return errors


def find_paid_fallback_values(
    value: Any,
    path: str = "",
) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            current = f"{path}.{key}" if path else key
            normalized = re.sub(r"[^a-z]", "", key.lower())
            if "paid" in normalized and "fallback" in normalized:
                allowed = (
                    nested is False
                    or nested is None
                    or (
                        isinstance(nested, str)
                        and nested
                        in {
                            "",
                            "prohibited",
                            "blocked",
                            "disabled",
                            "none",
                        }
                    )
                )
                if not allowed:
                    errors.append(
                        f"{current} cannot enable or authorize a paid fallback"
                    )
            errors.extend(find_paid_fallback_values(nested, current))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            errors.extend(
                find_paid_fallback_values(nested, f"{path}[{index}]")
            )
    return errors


def ordered_contains(values: list[str], expected: tuple[str, ...]) -> bool:
    cursor = 0
    for value in values:
        if cursor < len(expected) and value == expected[cursor]:
            cursor += 1
    return cursor == len(expected)


def validate(root: Path, manifest: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest root must be an object"], warnings
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must equal 1")

    project = manifest.get("project")
    if not isinstance(project, dict):
        errors.append("project must be an object")
        project = {}
    require_strings(
        project,
        ("id", "name", "purpose", "repository"),
        "project",
        errors,
    )
    if nonempty_string(project.get("id")) and not PROJECT_ID.fullmatch(
        project["id"]
    ):
        errors.append("project.id must use lowercase letters, digits, and hyphens")
    if nonempty_string(project.get("repository")) and not REPOSITORY.fullmatch(
        project["repository"]
    ):
        errors.append("project.repository must use owner/repository")
    for field in ("public_url", "fallback_url"):
        validate_optional_url(
            project.get(field),
            f"project.{field}",
            errors,
        )

    protected = manifest.get("protected")
    if not isinstance(protected, dict):
        errors.append("protected must be an object")
        protected = {}
    if not string_list(protected.get("paths"), allow_empty=False):
        errors.append("protected.paths must contain non-empty relative patterns")
    else:
        if len(protected["paths"]) != len(set(protected["paths"])):
            errors.append("protected.paths must contain unique patterns")
        for pattern in protected["paths"]:
            path = Path(pattern)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in pattern
                or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", pattern)
            ):
                errors.append(
                    f"protected path must stay within project root: {pattern}"
                )
    result_fixtures = protected.get("result_fixtures", [])
    if not string_list(result_fixtures):
        errors.append("protected.result_fixtures must be a string array")
    else:
        for index, fixture in enumerate(result_fixtures):
            project_path(
                root,
                fixture,
                f"protected.result_fixtures[{index}]",
                errors,
                must_exist=True,
            )

    data = manifest.get("data")
    if not isinstance(data, dict):
        errors.append("data must be an object")
        data = {}
    sources = data.get("sources")
    if not isinstance(sources, list):
        errors.append("data.sources must be an array")
        sources = []
    require_strings(
        data,
        ("coherent_cutoff_policy", "source_last_good_policy"),
        "data",
        errors,
    )
    source_ids: list[str] = []
    source_string_fields = (
        "id",
        "provider",
        "collector_entrypoint",
        "rights_policy",
        "provider_timezone",
        "session_calendar",
        "expected_release_window",
        "allowed_lag",
        "rate_limit_policy",
        "retry_policy",
        "cache_policy",
        "raw_artifact",
        "normalized_artifact",
        "schema_contract",
        "fallback_policy",
    )
    for index, source in enumerate(sources):
        prefix = f"data.sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        require_strings(source, source_string_fields, prefix, errors)
        source_id = source.get("id")
        if nonempty_string(source_id):
            source_ids.append(source_id)
        if source.get("role") not in SOURCE_ROLES:
            errors.append(f"{prefix}.role is invalid")
        allowed_lag_seconds = source.get("allowed_lag_seconds")
        if (
            isinstance(allowed_lag_seconds, bool)
            or not isinstance(allowed_lag_seconds, int)
            or allowed_lag_seconds < 0
        ):
            errors.append(
                f"{prefix}.allowed_lag_seconds must be a nonnegative integer"
            )
        maximum_source_age_seconds = source.get(
            "maximum_source_age_seconds"
        )
        if (
            isinstance(maximum_source_age_seconds, bool)
            or not isinstance(maximum_source_age_seconds, int)
            or maximum_source_age_seconds < 0
        ):
            errors.append(
                f"{prefix}.maximum_source_age_seconds must be a "
                "nonnegative integer"
            )
        elif (
            isinstance(allowed_lag_seconds, int)
            and not isinstance(allowed_lag_seconds, bool)
            and maximum_source_age_seconds < allowed_lag_seconds
        ):
            errors.append(
                f"{prefix}.maximum_source_age_seconds must be at least "
                "allowed_lag_seconds"
            )
        if not string_list(source.get("secret_names")):
            errors.append(f"{prefix}.secret_names must be an array of names")
        if not string_list(source.get("freshness_fields"), allow_empty=False):
            errors.append(f"{prefix}.freshness_fields must not be empty")
        else:
            if len(source["freshness_fields"]) != len(
                set(source["freshness_fields"])
            ):
                errors.append(f"{prefix}.freshness_fields must be unique")
            missing_freshness = sorted(
                SOURCE_FRESHNESS_FIELDS - set(source["freshness_fields"])
            )
            if missing_freshness:
                errors.append(
                    f"{prefix}.freshness_fields missing: "
                    + ", ".join(missing_freshness)
                )
        if source.get("paid_fallback_enabled") is not False:
            errors.append(f"{prefix}.paid_fallback_enabled must be false")
        if source.get("fallback_policy") not in SOURCE_FALLBACK_POLICIES:
            errors.append(
                f"{prefix}.fallback_policy must be fail-closed or an "
                "explicit degraded policy"
            )
        if (
            source.get("role") == "required"
            and source.get("fallback_policy") != "fail-closed"
        ):
            errors.append(
                f"{prefix} required sources must use fallback_policy=fail-closed"
            )
        if contains_paid_fallback_language(source.get("fallback_policy")):
            errors.append(
                f"{prefix}.fallback_policy cannot select a paid fallback"
            )
        for field, must_exist in (
            ("collector_entrypoint", True),
            ("raw_artifact", False),
            ("normalized_artifact", False),
            ("schema_contract", True),
        ):
            project_path(
                root,
                source.get(field),
                f"{prefix}.{field}",
                errors,
                must_exist=must_exist,
            )
    if len(source_ids) != len(set(source_ids)):
        errors.append("data source IDs must be unique")
    if sources:
        require_strings(
            data,
            ("data_manifest_path",),
            "data",
            errors,
        )
        project_path(
            root,
            data.get("data_manifest_path"),
            "data.data_manifest_path",
            errors,
            must_exist=False,
        )
        provenance_fields = data.get("provenance_fields")
        if not string_list(provenance_fields, allow_empty=False):
            errors.append("data.provenance_fields must not be empty")
        else:
            if len(provenance_fields) != len(set(provenance_fields)):
                errors.append("data.provenance_fields must be unique")
            missing_provenance = sorted(
                SOURCE_PROVENANCE_FIELDS - set(provenance_fields)
            )
            if missing_provenance:
                errors.append(
                    "data.provenance_fields missing: "
                    + ", ".join(missing_provenance)
                )

    analysis = manifest.get("analysis")
    if not isinstance(analysis, dict):
        errors.append("analysis must be an object")
        analysis = {}
    entrypoints = analysis.get("authoritative_entrypoints")
    if not string_list(entrypoints):
        errors.append("analysis.authoritative_entrypoints must be a string array")
        entrypoints = []
    else:
        for index, entrypoint in enumerate(entrypoints):
            project_path(
                root,
                entrypoint,
                f"analysis.authoritative_entrypoints[{index}]",
                errors,
                must_exist=True,
            )
    if entrypoints:
        require_strings(
            analysis,
            ("input_schema_contract",),
            "analysis",
            errors,
        )
        project_path(
            root,
            analysis.get("input_schema_contract"),
            "analysis.input_schema_contract",
            errors,
            must_exist=True,
        )
        assertions = analysis.get("result_artifact_identity")
        if not isinstance(assertions, list) or not assertions:
            errors.append(
                "authoritative analysis requires result_artifact_identity"
            )
        else:
            assertion_ids: list[str] = []
            assertion_pointers: list[str] = []
            identity_fields: list[str] = []
            for index, assertion in enumerate(assertions):
                prefix = f"analysis.result_artifact_identity[{index}]"
                if not isinstance(assertion, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                require_strings(
                    assertion,
                    ("id", "json_pointer", "identity_field"),
                    prefix,
                    errors,
                )
                if nonempty_string(assertion.get("id")):
                    assertion_ids.append(assertion["id"])
                pointer = assertion.get("json_pointer")
                if nonempty_string(pointer):
                    assertion_pointers.append(pointer)
                    if not pointer.startswith("/"):
                        errors.append(
                            f"{prefix}.json_pointer must start with /"
                        )
                identity_field = assertion.get("identity_field")
                if nonempty_string(identity_field):
                    identity_fields.append(identity_field)
                    if identity_field not in RESULT_IDENTITY_FIELDS:
                        errors.append(
                            f"{prefix}.identity_field is not a result identity"
                        )
            if len(assertion_ids) != len(set(assertion_ids)):
                errors.append("result artifact assertion IDs must be unique")
            if len(assertion_pointers) != len(set(assertion_pointers)):
                errors.append("result artifact JSON pointers must be unique")
            missing_artifact_identity = {
                "project_id",
                "run_id",
            } - set(identity_fields)
            if missing_artifact_identity:
                errors.append(
                    "result_artifact_identity must bind both project_id and "
                    "run_id; missing "
                    + ", ".join(sorted(missing_artifact_identity))
                )
    controls = analysis.get("controls")
    if not isinstance(controls, list):
        errors.append("analysis.controls must be an array")
        controls = []
    control_ids: list[str] = []
    has_analysis_control = False
    for index, control in enumerate(controls):
        prefix = f"analysis.controls[{index}]"
        if not isinstance(control, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not nonempty_string(control.get("id")):
            errors.append(f"{prefix}.id must be non-empty")
        else:
            control_ids.append(control["id"])
        if control.get("kind") not in CONTROL_KINDS:
            errors.append(f"{prefix}.kind is invalid")
        if control.get("kind") == "analysis":
            has_analysis_control = True
            for field in (
                "frontend_field",
                "canonical_field",
                "validation",
                "execution_mapping",
            ):
                if not nonempty_string(control.get(field)):
                    errors.append(f"{prefix}.{field} is required for analysis")
            if not string_list(control.get("result_paths"), allow_empty=False):
                errors.append(
                    f"{prefix}.result_paths is required for analysis"
                )
    if len(control_ids) != len(set(control_ids)):
        errors.append("analysis control IDs must be unique")
    if has_analysis_control and not entrypoints:
        errors.append("analysis controls require authoritative_entrypoints")
    if has_analysis_control and not string_list(
        analysis.get("result_identity_fields"),
        allow_empty=False,
    ):
        errors.append("analysis controls require result_identity_fields")
    result_identity_fields = analysis.get("result_identity_fields")
    if entrypoints:
        if not string_list(result_identity_fields, allow_empty=False):
            errors.append(
                "authoritative analysis requires result_identity_fields"
            )
        else:
            if len(result_identity_fields) != len(set(result_identity_fields)):
                errors.append(
                    "analysis.result_identity_fields must be unique"
                )
            missing_identity = sorted(
                RESULT_IDENTITY_FIELDS - set(result_identity_fields)
            )
            if missing_identity:
                errors.append(
                    "analysis.result_identity_fields missing: "
                    + ", ".join(missing_identity)
                )

    for section_name in ("frontend", "backend"):
        section = manifest.get(section_name)
        if not isinstance(section, dict):
            errors.append(f"{section_name} must be an object")
            continue
        if not string_list(section.get("test_commands")):
            errors.append(f"{section_name}.test_commands must be a string array")
        if section_name == "frontend":
            if not nonempty_string(section.get("type")):
                errors.append("frontend.type must be a non-empty string")
            if section.get("root") not in (None, ""):
                project_path(
                    root,
                    section.get("root"),
                    "frontend.root",
                    errors,
                    must_exist=True,
                    kind="directory",
                )
            if section.get("design_contract") not in (None, ""):
                project_path(
                    root,
                    section.get("design_contract"),
                    "frontend.design_contract",
                    errors,
                    must_exist=True,
                )
        elif not isinstance(section.get("required"), bool):
            errors.append("backend.required must be boolean")

    automation = manifest.get("automation")
    if not isinstance(automation, dict):
        errors.append("automation must be an object")
        automation = {}
    mode = automation.get("mode")
    if mode not in {"none", "manual", "scheduled"}:
        errors.append("automation.mode is invalid")
    workflows = automation.get("workflows")
    if not string_list(workflows):
        errors.append("automation.workflows must be a string array")
        workflows = []
    elif len(workflows) != len(set(workflows)):
        errors.append("automation.workflows must contain unique paths")
    for workflow in workflows:
        project_path(
            root,
            workflow,
            f"automation.workflows[{workflows.index(workflow)}]",
            errors,
            must_exist=True,
        )
    schedules = automation.get("schedules")
    if not isinstance(schedules, list):
        errors.append("automation.schedules must be an array")
        schedules = []
    schedule_ids: list[str] = []
    expected_crons_by_workflow: dict[str, set[str]] = {}
    schedule_pairs: list[tuple[str, str]] = []
    for schedule in schedules:
        if not isinstance(schedule, dict):
            continue
        workflow_value = schedule.get("workflow")
        cron_value = schedule.get("cron")
        if nonempty_string(workflow_value) and nonempty_string(cron_value):
            normalized = " ".join(cron_value.split())
            expected_crons_by_workflow.setdefault(
                workflow_value,
                set(),
            ).add(normalized)
            schedule_pairs.append((workflow_value, normalized))
    if len(schedule_pairs) != len(set(schedule_pairs)):
        errors.append(
            "automation.schedules must not duplicate a workflow cron"
        )
    schedule_fields = (
        "id",
        "workflow",
        "entrypoint",
        "entrypoint_command",
        "job_id",
        "cost_preflight_step_id",
        "entrypoint_step_id",
        "cost_preflight_entrypoint",
        "cost_preflight_command",
        "cron",
        "cron_timezone",
        "business_timezone",
        "calendar",
        "availability_lag",
        "idempotency_key",
        "concurrency_policy",
        "concurrency_group",
        "timeout",
        "retry_policy",
        "manual_dispatch_mode",
        "retention_policy",
    )
    for index, schedule in enumerate(schedules):
        prefix = f"automation.schedules[{index}]"
        if not isinstance(schedule, dict):
            errors.append(f"{prefix} must be an object")
            continue
        require_strings(schedule, schedule_fields, prefix, errors)
        if nonempty_string(schedule.get("id")):
            schedule_ids.append(schedule["id"])
        if schedule.get("workflow") not in workflows:
            errors.append(f"{prefix}.workflow must be listed in workflows")
        if not isinstance(schedule.get("enabled_on_default_branch"), bool):
            errors.append(f"{prefix}.enabled_on_default_branch must be boolean")
        elif mode == "scheduled" and schedule["enabled_on_default_branch"] is not True:
            errors.append(
                f"{prefix}.enabled_on_default_branch must be true in scheduled mode"
            )
        if schedule.get("cancel_in_progress") is not False:
            errors.append(f"{prefix}.cancel_in_progress must be false")
        if (
            nonempty_string(schedule.get("concurrency_group"))
            and re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]*",
                schedule["concurrency_group"],
            )
            is None
        ):
            errors.append(
                f"{prefix}.concurrency_group must be a literal portable ID"
            )
        if nonempty_string(schedule.get("cron")) and not valid_cron(
            schedule["cron"]
        ):
            errors.append(f"{prefix}.cron must be a valid five-field cron")
        workflow_path = project_path(
            root,
            schedule.get("workflow"),
            f"{prefix}.workflow",
            errors,
            must_exist=True,
        )
        entrypoint_path = project_path(
            root,
            schedule.get("entrypoint"),
            f"{prefix}.entrypoint",
            errors,
            must_exist=True,
        )
        if schedule.get("entrypoint") not in entrypoints:
            errors.append(
                f"{prefix}.entrypoint must be an authoritative analysis "
                "pipeline entrypoint"
            )
        cost_preflight_path = project_path(
            root,
            schedule.get("cost_preflight_entrypoint"),
            f"{prefix}.cost_preflight_entrypoint",
            errors,
            must_exist=True,
        )
        if (
            workflow_path is not None
            and workflow_path.is_file()
            and entrypoint_path is not None
            and entrypoint_path.is_file()
            and cost_preflight_path is not None
            and cost_preflight_path.is_file()
            and nonempty_string(schedule.get("cron"))
            and nonempty_string(schedule.get("entrypoint_command"))
            and nonempty_string(schedule.get("cost_preflight_command"))
        ):
            validate_workflow_schedule(
                workflow_path,
                workflow_label=f"{prefix}.workflow",
                cron=schedule["cron"],
                expected_crons=expected_crons_by_workflow.get(
                    schedule["workflow"],
                    set(),
                ),
                concurrency_group=schedule["concurrency_group"],
                cancel_in_progress=schedule.get("cancel_in_progress"),
                job_id=schedule["job_id"],
                cost_preflight_step_id=schedule["cost_preflight_step_id"],
                entrypoint_step_id=schedule["entrypoint_step_id"],
                entrypoint_command=schedule["entrypoint_command"],
                cost_preflight_command=schedule["cost_preflight_command"],
                errors=errors,
            )
    if len(schedule_ids) != len(set(schedule_ids)):
        errors.append("automation schedule IDs must be unique")

    active_automation = mode in {"manual", "scheduled"} or bool(
        workflows or schedules
    )
    cost_bounds = automation.get("cost_bounds")
    validate_cost_bounds(cost_bounds, errors)
    if mode == "none" and active_automation:
        errors.append("automation.mode=none cannot declare workflows or schedules")
    if mode == "scheduled" and (not workflows or not schedules):
        errors.append("automation.mode=scheduled requires workflows and schedules")
    if active_automation:
        if not sources:
            errors.append("active automation requires a data source registry")
        elif not any(
            isinstance(source, dict) and source.get("role") == "required"
            for source in sources
        ):
            errors.append("active automation requires at least one required source")
        if not entrypoints:
            errors.append(
                "active automation requires authoritative analysis entrypoints"
            )
        pipeline = automation.get("pipeline_stages")
        if not string_list(pipeline, allow_empty=False) or not ordered_contains(
            pipeline,
            PIPELINE,
        ):
            errors.append(
                "automation.pipeline_stages must include the full ordered chain"
            )
        require_strings(
            automation,
            ("publication_path", "last_good_policy", "failure_policy"),
            "automation",
            errors,
        )
        project_path(
            root,
            automation.get("publication_path"),
            "automation.publication_path",
            errors,
            must_exist=False,
        )
        if not string_list(
            automation.get("public_readback_urls"),
            allow_empty=False,
        ):
            errors.append(
                "active automation requires automation.public_readback_urls"
            )
        else:
            public_readback_urls = automation["public_readback_urls"]
            if len(public_readback_urls) != len(set(public_readback_urls)):
                errors.append(
                    "automation.public_readback_urls must be unique"
                )
            for index, url in enumerate(public_readback_urls):
                if not valid_http_url(url):
                    errors.append(
                        "automation.public_readback_urls"
                        f"[{index}] must be an HTTP(S) URL without credentials"
                    )
        if not valid_http_url(project.get("public_url")):
            errors.append(
                "active automation requires a valid project.public_url"
            )
        freshness_fields = automation.get("freshness_fields")
        if not string_list(freshness_fields, allow_empty=False):
            errors.append(
                "active automation requires automation.freshness_fields"
            )
        else:
            if len(freshness_fields) != len(set(freshness_fields)):
                errors.append("automation.freshness_fields must be unique")
            missing_freshness = sorted(
                AUTOMATION_FRESHNESS_FIELDS - set(freshness_fields)
            )
            if missing_freshness:
                errors.append(
                    "automation.freshness_fields missing: "
                    + ", ".join(missing_freshness)
                )

    release = manifest.get("release")
    if not isinstance(release, dict):
        errors.append("release must be an object")
        release = {}
    require_strings(
        release,
        ("base_branch", "approved_account"),
        "release",
        errors,
    )
    if release.get("cost_policy") != COST_POLICY:
        errors.append("release.cost_policy is invalid")
    if release.get("paid_action_authority") is not None:
        errors.append("repository manifest cannot grant paid-action authority")
    if release.get("paid_fallback_policy") != "prohibited":
        errors.append("release.paid_fallback_policy must be prohibited")
    for field in ("preview", "production"):
        validate_optional_url(
            release.get(field),
            f"release.{field}",
            errors,
        )

    quality = manifest.get("quality")
    if not isinstance(quality, dict):
        errors.append("quality must be an object")
    elif not string_list(quality.get("commands")):
        errors.append("quality.commands must be a string array")

    errors.extend(find_secret_values(manifest))
    errors.extend(find_paid_fallback_values(manifest))
    if not active_automation:
        warnings.append("automation is not active in this contract")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--manifest",
        default=".codex/quant-project.json",
    )
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Project root does not exist: {root}")
    manifest_path = Path(args.manifest).expanduser()
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    manifest_path = manifest_path.resolve()
    try:
        manifest_path.relative_to(root)
    except ValueError:
        parser.error("Manifest must stay within project root")
    manifest = load_object(manifest_path)
    errors, warnings = validate(root, manifest)
    result = {
        "schema_version": 1,
        "valid": not errors,
        "manifest": str(manifest_path),
        "project_id": manifest.get("project", {}).get("id", ""),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
