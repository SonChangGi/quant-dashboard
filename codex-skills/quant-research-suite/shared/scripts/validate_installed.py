#!/usr/bin/env python3
"""Verify the installed Quant Research suite against its install manifest."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit


SCRIPT = Path(__file__).absolute()
SHARED = SCRIPT.parents[1]
INSTALL_ROOT = SHARED.parent
MANIFEST = SHARED / "install-manifest.json"
INSTALL_ITEMS = (
    "quant-plan",
    "quant-goal",
    "quant-developer",
    "quant-research-shared",
)
PUBLIC_SKILLS = INSTALL_ITEMS[:3]
PUBLIC_ITEM_FILES = frozenset({"SKILL.md", "agents/openai.yaml"})
BASE_SHARED_FILES = frozenset(
    {
        "capabilities/analysis-input-flow.md",
        "capabilities/analysis.md",
        "capabilities/backend.md",
        "capabilities/external-data.md",
        "capabilities/interactive-chart.md",
        "capabilities/public-web.md",
        "capabilities/publication.md",
        "capabilities/remote-release.md",
        "capabilities/scheduled-automation.md",
        "capabilities/web-ui.md",
        "core/authority.md",
        "core/context-routing.md",
        "references/adaptive-workflow.md",
        "scripts/validate_installed.py",
    }
)
COMPAT_SHARED_FILES = frozenset(
    {
        "adapters/fastapi.md",
        "adapters/github-actions.md",
        "adapters/github-pages.md",
        "adapters/github.md",
        "adapters/supabase.md",
        "adapters/vercel.md",
        "advisory/architecture-options.md",
        "advisory/external-comparisons.md",
        "advisory/research-method.md",
        "advisory/technology-examples.md",
        "capabilities/agent-team-execution.md",
        "capabilities/analysis-input-binding.md",
        "capabilities/analysis-input-flow.md",
        "capabilities/analysis.md",
        "capabilities/backend.md",
        "capabilities/external-data.md",
        "capabilities/interactive-chart.md",
        "capabilities/multi-agent-write.md",
        "capabilities/public-web.md",
        "capabilities/publication.md",
        "capabilities/remote-release.md",
        "capabilities/repo-mutation.md",
        "capabilities/scheduled-automation.md",
        "capabilities/web-ui.md",
        "core/authority.md",
        "core/context-routing.md",
        "core/evidence-semantics.md",
        "core/invariants.md",
        "profiles/quant-public-dashboard-strict.md",
        "profiles/quant-research-web.md",
        "references/adaptive-workflow.md",
        "references/agent-orchestration.md",
        "references/cost-and-authority.md",
        "references/data-automation.md",
        "references/developer-runbook.md",
        "references/durable-runtime.md",
        "references/goal-and-subagents.md",
        "references/operating-principles.md",
        "references/research-and-planning.md",
        "references/web-design-source.md",
        "references/web-design-v2.4.1.md",
        "schemas/analysis-input-binding-capture.schema.json",
        "schemas/analysis-invocation.schema.json",
        "schemas/evidence-receipt-v3.schema.json",
        "schemas/goal-ledger-state.schema.json",
        "schemas/goal-state-v2.schema.json",
        "schemas/quant-project-v2.schema.json",
        "schemas/review-receipt.schema.json",
        "schemas/story-envelope.schema.json",
        "schemas/story-receipt.schema.json",
        "schemas/team-integration-receipt.schema.json",
        "schemas/team-run-packet.schema.json",
        "schemas/worker-delivery-receipt.schema.json",
        "scripts/capability_model.py",
        "scripts/contract_guard.py",
        "scripts/github_preflight.sh",
        "scripts/goal_ledger.py",
        "scripts/goal_primitives.py",
        "scripts/goal_runtime.py",
        "scripts/project_inventory.py",
        "scripts/quantctl.py",
        "scripts/team_protocol.py",
        "scripts/validate_evidence.py",
        "scripts/validate_evidence_v3.py",
        "scripts/validate_installed.py",
        "scripts/validate_project.py",
        "scripts/validate_project_v2.py",
        "templates/analysis-input-binding-capture.example.json",
        "templates/analysis-invocation.example.json",
        "templates/approved-plan.example.md",
        "templates/audit-report.example.md",
        "templates/evidence-receipt-v3.example.json",
        "templates/evidence-receipt.example.json",
        "templates/goal-ledger-state.example.json",
        "templates/goal-state-v2.example.json",
        "templates/goal-state.example.json",
        "templates/quant-project-v2.example.json",
        "templates/quant-project.example.json",
        "templates/quant-project.schema.json",
        "templates/review-receipt.example.json",
        "templates/story-envelope.example.json",
        "templates/story-receipt.example.json",
        "templates/team-integration-receipt.example.json",
        "templates/team-run-packet.example.json",
        "templates/worker-delivery-receipt.example.json",
    }
)
INSTALL_PROFILES = frozenset({"base", "compat"})
INSTALL_MANIFEST_SCHEMA_VERSION = 3
INSTALL_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "install_profile",
        "canonicalization",
        "suite_content_sha256",
        "source_git",
        "items",
    }
)
CANONICALIZATION = "canonical-json-v1"
FULL_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
FRONTMATTER_BLOCK = re.compile(
    r"\A---\n(?P<body>.*?)\n---(?:\n|\Z)",
    re.DOTALL,
)
PUBLIC_ROUTE = re.compile(
    r"`(?P<prefix>\.\./\.\./shared|\.\./quant-research-shared)/"
    r"(?P<suffix>[^`]+\.md)`"
)
REQUIRED_PUBLIC_ROUTES = frozenset(
    {
        "core/context-routing.md",
        "references/adaptive-workflow.md",
    }
)
ROLE_DESCRIPTION_PATTERNS = {
    "quant-plan": (r"\b(?:audit|plan)\b", r"\bread-only\b", r"\badapt\w*"),
    "quant-goal": (
        r"\bnative goal\b",
        r"\b(?:complete|completion|blocker|blocked)\b",
        r"\badapt\w*",
    ),
    "quant-developer": (
        r"\b(?:implementation|change|deliver)\b",
        r"\b(?:verify|verification|surface)\b",
        r"\badapt\w*",
    ),
}
ROLE_PROMPT_PATTERNS = {
    "quant-plan": (
        r"\b(?:audit|inspect|plan)\b",
        r"\b(?:read-only|non-mutating|without changing)\b",
    ),
    "quant-goal": (
        r"\b(?:one|single)\b.{0,30}\bnative goal\b",
        r"\bnative goal\b",
        r"\b(?:evidence|blocker|complete|transition)\b",
    ),
    "quant-developer": (
        r"\b(?:implementation|deliver)\b",
        r"\brequested (?:outcome|change|result)\b",
        r"\b(?:verify|verification|surface)\b",
    ),
}


def _strip_yaml_comment(value: str) -> str:
    quote: str | None = None
    index = 0
    while index < len(value):
        character = value[index]
        if quote == '"' and character == "\\":
            index += 2
            continue
        if quote == "'" and character == "'":
            if index + 1 < len(value) and value[index + 1] == "'":
                index += 2
                continue
            quote = None
        elif quote == '"' and character == '"':
            quote = None
        elif quote is None and character in {'"', "'"}:
            quote = character
        elif (
            quote is None
            and character == "#"
            and (index == 0 or value[index - 1].isspace())
        ):
            return value[:index].rstrip()
        index += 1
    return value.strip()


def _yaml_scalar(value: str) -> str | bool | int | float | None:
    candidate = _strip_yaml_comment(value)
    if not candidate:
        return None
    if candidate.startswith('"'):
        try:
            parsed: Any = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, (str, bool, int, float)) else None
    if candidate.startswith("'"):
        if len(candidate) < 2 or not candidate.endswith("'"):
            return None
        return candidate[1:-1].replace("''", "'")
    if candidate in {"true", "false"}:
        return candidate == "true"
    if re.fullmatch(r"-?(?:0|[1-9]\d*)(?:\.\d+)?", candidate):
        return float(candidate) if "." in candidate else int(candidate)
    unsupported = ("!", "&", "*", "|", ">", "[", "]", "{", "}")
    if any(token in candidate for token in unsupported):
        return None
    return candidate


def normalized_policy_text(text: str) -> str:
    return " ".join(text.lower().split())


def policy_segments(text: str) -> list[str]:
    normalized = normalized_policy_text(text)
    return [
        segment.strip()
        for segment in re.split(
            r"(?<=[.!?;])\s+|\b(?:but|however|although|though|whereas)\b",
            normalized,
        )
        if segment.strip()
    ]


def _prohibits_write(clause: str) -> bool:
    action = r"(?:allow\w*|permit\w*|edit\w*|mutat\w*|writ\w*)"
    return bool(
        re.search(
            rf"\b(?:do not|never|must not|cannot)\b.{{0,35}}\b{action}\b",
            clause,
        )
        or re.search(r"\bno\b.{0,40}\b(?:writes?|edits?|mutations?)\b", clause)
        or re.search(
            r"\b(?:writes?|edits?|mutations?)\b.{0,35}"
            r"\b(?:not allowed|not permitted|prohibited)\b",
            clause,
        )
        or re.search(
            r"\b(?:may|can|should|must) not (?:be )?"
            r"(?:allowed|permitted|written|edited)\b",
            clause,
        )
    )


def has_unsafe_plan_probe_expansion(text: str) -> bool:
    for clause in policy_segments(text):
        provider_write = (
            re.search(r"\b(?:provider|remote)\b", clause)
            and re.search(r"\bwrit\w*\b", clause)
            and re.search(r"\b(?:may|can|allow\w*|permit\w*)\b", clause)
        )
        unsafe_dependency = (
            re.search(r"\bdependenc(?:y|ies)\b", clause)
            and re.search(r"\binstall\w*\b", clause)
            and re.search(
                r"\b(?:unlocked|target environment|global environment)\b",
                clause,
            )
            and re.search(r"\b(?:may|can|allow\w*|permit\w*)\b", clause)
        )
        target_write = (
            re.search(
                r"\b(?:project|target(?:[- ]tree| directory| files?| state)?)\b",
                clause,
            )
            and re.search(r"\b(?:edit|mutat\w*|writ(?:e|es|ten|ing))\b", clause)
            and re.search(r"\b(?:may|can|allow\w*|permit\w*)\b", clause)
        )
        if (provider_write or unsafe_dependency or target_write) and not (
            _prohibits_write(clause)
            or re.search(r"\bonly inside\b", clause)
        ):
            return True
    return False


def has_unsafe_developer_expansion(text: str) -> bool:
    clauses = policy_segments(text)
    for index, clause in enumerate(clauses):
        if not re.search(r"\bcontinu\w*\b", clause):
            continue
        continuation_prohibited = re.search(
            r"\b(?:do not|never|must not|cannot)\s+continu\w*\b"
            r"|\bcontinu\w*\b.{0,35}"
            r"\b(?:not allowed|not permitted|prohibited)\b",
            clause,
        )
        if continuation_prohibited:
            continue
        after_acceptance = re.search(r"\bafter acceptance\b", clause) and not (
            re.search(r"\bmaterial risks?\b|\binvalidat\w*\b", clause)
        )
        open_ended = re.search(
            r"\bwhile\b.{0,80}"
            r"\b(?:any improvement|optional (?:polish|improvement))s?\b"
            r"|\b(?:hypothetical risks?|non-required polish)\b",
            clause,
        )
        if after_acceptance or open_ended:
            return True
        if (
            index > 0
            and re.search(r"\bafter acceptance\b", clauses[index - 1])
            and not re.search(
                r"\bmaterial risks?\b|\binvalidat\w*\b",
                f"{clauses[index - 1]} {clause}",
            )
            and not re.search(
                r"\b(?:do not|never|must not|cannot)\s+continu\w*\b",
                f"{clauses[index - 1]} {clause}",
            )
        ):
            return True
    return False


def has_unsafe_goal_terminal_expansion(text: str) -> bool:
    for clause in policy_segments(text):
        if _has_goal_terminal_guard(clause):
            continue
        terminal = re.search(r"\b(?:complete|blocked)\b", clause)
        replacement = re.search(
            r"\b(?:clear|free|release|replace)\w*\b",
            clause,
        )
        action = re.search(
            r"\b(?:mark|use|may|can|allow\w*|permit\w*)\b",
            clause,
        )
        if terminal and replacement and action:
            return True
    return False


def parse_skill_frontmatter(text: str) -> dict[str, str] | None:
    match = FRONTMATTER_BLOCK.match(text.replace("\r\n", "\n"))
    if not match:
        return None
    values: dict[str, str] = {}
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line != stripped or ":" not in line:
            return None
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[a-z][a-z0-9-]*", key) or key in values:
            return None
        value = _yaml_scalar(raw_value)
        if not isinstance(value, str):
            return None
        values[key] = value
    return values


def parse_agent_metadata(text: str) -> dict[str, str | bool] | None:
    sections: dict[str, dict[str, str | bool | int | float]] = {}
    current: str | None = None
    for raw_line in text.replace("\r\n", "\n").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        top = re.fullmatch(r"([a-z][a-z0-9_-]*):", raw_line)
        if top:
            current = top.group(1)
            if current in sections:
                return None
            sections[current] = {}
            continue
        field = re.fullmatch(
            r" {2,}([a-z][a-z0-9_-]*):\s*(.+)",
            raw_line,
        )
        if field and current is not None:
            key = field.group(1)
            if key in sections[current]:
                return None
            value = _yaml_scalar(field.group(2))
            if value is None:
                return None
            sections[current][key] = value
            continue
        if current in {"interface", "policy"}:
            return None

    interface = sections.get("interface", {})
    policy = sections.get("policy", {})
    required_strings = ("display_name", "short_description", "default_prompt")
    if not all(
        isinstance(interface.get(key), str) and str(interface[key]).strip()
        for key in required_strings
    ):
        return None
    if not isinstance(policy.get("allow_implicit_invocation"), bool):
        return None
    return {
        **{key: str(interface[key]) for key in required_strings},
        "allow_implicit_invocation": bool(
            policy["allow_implicit_invocation"]
        ),
    }


def _has_all_patterns(text: str, patterns: tuple[str, ...]) -> bool:
    return all(re.search(pattern, text) for pattern in patterns)


def has_relation(
    text: str,
    *concept_groups: tuple[str, ...],
    span: int = 2,
) -> bool:
    units = policy_segments(text)
    for index in range(len(units)):
        candidate = " ".join(units[index : index + span])
        if all(
            any(re.search(pattern, candidate) for pattern in group)
            for group in concept_groups
        ):
            return True
    return False


def _has_goal_terminal_guard(text: str) -> bool:
    for clause in policy_segments(text):
        if re.search(
            r"\b(?:never|do not|must not|cannot)\s+"
            r"(?:mark|use|misuse)\w*\b.{0,70}\bcomplete\b"
            r".{0,50}\bblocked\b.{0,70}"
            r"\b(?:clear|free|release)\w*\b.{0,40}\bslot\b",
            clause,
        ):
            return True
    return False


def validate_public_body(name: str, skill_text: str) -> list[str]:
    match = FRONTMATTER_BLOCK.match(skill_text.replace("\r\n", "\n"))
    if not match:
        return []
    body = normalized_policy_text(skill_text[match.end() :])
    errors: list[str] = []
    if name == "quant-plan":
        read_only = has_relation(
            body,
            (r"\b(?:target|project)\b",),
            (r"\b(?:remote|provider)\b",),
            (r"\b(?:read-only|non-mutating|unchanged|untouched)\b",),
            span=3,
        )
        direct_check = has_relation(
            body,
            (r"\b(?:check|probe)\b",),
            (r"\b(?:known|proven|verified)\b",),
            (r"\b(?:non-writing|non-mutating)\b",),
        )
        write_isolation = has_relation(
            body,
            (
                r"\b(?:may write|writing|cache|dependenc(?:y|ies)|build|"
                r"snapshot|output)\b",
            ),
            (
                r"\b(?:isolat\w*|sandbox\w*|disposable|redirect\w*|"
                r"temporary)\b",
            ),
            span=3,
        )
        if not (read_only and direct_check and write_isolation):
            errors.append(f"{name}: body must preserve the read-only probe boundary")
        if re.search(
            r"\b(?:target|project|role)\b.{0,50}\bnot read-only\b",
            body,
        ):
            errors.append(f"{name}: body contradicts the read-only boundary")
        if re.search(r"\bdisposable copy\b.{0,30}\bor\b.{0,30}\bredirect\b", body):
            errors.append(f"{name}: disposable copies must isolate external writes")
        if has_unsafe_plan_probe_expansion(body):
            errors.append(f"{name}: body permits unsafe target or remote writes")
    elif name == "quant-goal":
        tools = (
            r"\bnative goal\b",
            r"`create_goal`",
            r"`get_goal`",
            r"`update_goal`",
        )
        empty_slot = has_relation(
            body,
            (r"`get_goal`",),
            (r"\bfresh\b",),
            (r"\b(?:no unfinished goal|empty (?:native )?slot)\b",),
            span=3,
        )
        if not (_has_all_patterns(body, tools) and empty_slot):
            errors.append(f"{name}: body must preserve the native Goal lifecycle")
        if not _has_goal_terminal_guard(body):
            errors.append(f"{name}: body must prohibit fake terminal replacement")
        if has_unsafe_goal_terminal_expansion(body):
            errors.append(f"{name}: body permits fake terminal replacement")
    elif name == "quant-developer":
        bounded_change = has_relation(
            body,
            (r"\b(?:smallest|minimal|bounded)\b",),
            (r"\b(?:change|implementation|scope)\b",),
        )
        bounded_continuation = has_relation(
            body,
            (r"\bcontinu\w*\b",),
            (
                r"\bacceptance\b.{0,60}\bunmet\b",
                r"\bunmet\b.{0,60}\bacceptance\b",
                r"\bmaterial risk\b.{0,80}\binvalidat\w*\b",
            ),
            span=3,
        )
        finish_condition = has_relation(
            body,
            (r"\b(?:finish|stop|end)\w*\b",),
            (r"\brequested (?:outcome|change|result)\b",),
            (r"\b(?:no required work|working|acceptance (?:is )?met)\b",),
            span=3,
        )
        evidence_gated_scope = has_relation(
            body,
            (r"\b(?:new|extra|optional|expansion|redesign)\w*\b",),
            (r"\b(?:request(?:ed)?|target evidence)\b",),
            (r"\b(?:only|unless|require\w*)\b",),
            span=3,
        )
        if not all(
            (
                bounded_change,
                bounded_continuation,
                finish_condition,
                evidence_gated_scope,
            )
        ):
            errors.append(f"{name}: body must preserve proportional delivery")
        if re.search(
            r"\b(?:do not|never|must not|cannot)\b.{0,35}"
            r"\b(?:prefer|make|use)\b.{0,60}"
            r"\b(?:smallest|minimal|bounded)\b",
            body,
        ):
            errors.append(f"{name}: body contradicts proportional delivery")
        if has_unsafe_developer_expansion(body):
            errors.append(f"{name}: body permits open-ended improvement")
    return errors


def validate_public_metadata(
    name: str,
    skill_text: str,
    agent_text: str,
) -> list[str]:
    errors: list[str] = []
    metadata = parse_skill_frontmatter(skill_text)
    if metadata is None:
        errors.append(f"{name}: invalid SKILL.md frontmatter")
    else:
        if set(metadata) != {"name", "description"}:
            errors.append(
                f"{name}: frontmatter must contain only name and description"
            )
        if metadata.get("name") != name:
            errors.append(f"{name}: frontmatter name mismatch")
        description = metadata.get("description", "")
        if (
            not description
            or len(description) > 1024
            or re.search(r"[<>]", description)
        ):
            errors.append(f"{name}: invalid frontmatter description")
        normalized = " ".join(description.lower().split())
        selectors = set(re.findall(r"\$(quant-[a-z0-9-]+)", normalized))
        if selectors != {name}:
            errors.append(f"{name}: description must name only ${name}")
        if not re.search(r"\b(?:explicit|only when|use only)\b", normalized):
            errors.append(f"{name}: description must require explicit selection")
        for pattern in ROLE_DESCRIPTION_PATTERNS[name]:
            if not re.search(pattern, normalized):
                errors.append(f"{name}: description is missing a role concept")
                break

    agent = parse_agent_metadata(agent_text)
    if agent is None:
        errors.append(f"{name}: invalid agents/openai.yaml")
        return errors
    if agent["allow_implicit_invocation"] is not False:
        errors.append(f"{name}: implicit invocation must be false")
    short_description = str(agent["short_description"])
    if not 25 <= len(short_description) <= 64:
        errors.append(f"{name}: short_description must be 25-64 characters")
    prompt = str(agent["default_prompt"])
    prompt_selectors = set(re.findall(r"\$(quant-[a-z0-9-]+)", prompt))
    if prompt_selectors != {name}:
        errors.append(f"{name}: default prompt must name only ${name}")
    normalized_prompt = normalized_policy_text(prompt)
    if not _has_all_patterns(normalized_prompt, ROLE_PROMPT_PATTERNS[name]):
        errors.append(f"{name}: default prompt is missing a role concept")
    prompt_contradictions = {
        "quant-plan": r"\bnot read-only\b",
        "quant-goal": r"\bnot (?:one|a|single) native goal\b",
        "quant-developer": (
            r"\b(?:do not|never|must not|cannot)\b.{0,35}"
            r"\b(?:implement|deliver|verify)\w*\b"
        ),
    }
    if re.search(prompt_contradictions[name], normalized_prompt):
        errors.append(f"{name}: default prompt contradicts its role")
    return errors


def extract_public_shared_routes(
    text: str,
) -> tuple[frozenset[str], frozenset[str]]:
    source: set[str] = set()
    installed: set[str] = set()
    for match in PUBLIC_ROUTE.finditer(text):
        destination = (
            source
            if match.group("prefix") == "../../shared"
            else installed
        )
        destination.add(match.group("suffix"))
    return frozenset(source), frozenset(installed)


def validate_public_routes(
    name: str,
    skill_text: str,
    shared_root: Path,
    available_files: frozenset[str],
) -> list[str]:
    errors: list[str] = []
    source, installed = extract_public_shared_routes(skill_text)
    if source != installed:
        errors.append(f"{name}: source and installed shared routes must match")
    routes = source | installed
    missing_required = REQUIRED_PUBLIC_ROUTES - routes
    if missing_required:
        errors.append(
            f"{name}: missing required shared routes {sorted(missing_required)}"
        )
    for suffix in sorted(routes):
        relative = PurePosixPath(suffix)
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"{name}: unsafe shared route {suffix}")
            continue
        if suffix not in available_files or not (shared_root / suffix).is_file():
            errors.append(f"{name}: unavailable shared route {suffix}")
    return errors


def tree_hashes(root: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if (
            "__pycache__" in relative.parts
            or path.suffix == ".pyc"
            or relative.as_posix() == "install-manifest.json"
        ):
            continue
        values[relative.as_posix()] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return values


def symlink_entries(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_symlink()
    )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def suite_content_sha256(items: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(items)).hexdigest()


def valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None


def sanitized_origin(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str) or not value.strip():
        return False
    origin = value.strip()
    if "://" in origin:
        parsed = urlsplit(origin)
        return (
            parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
        )
    return re.fullmatch(r"[^@/\s]+@[^:\s]+:.+", origin) is None


def validate_source_git(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["source_git provenance missing"]
    expected_fields = {
        "available",
        "origin",
        "branch",
        "commit",
        "tree",
        "dirty",
        "captured_at",
    }
    if set(value) != expected_fields:
        errors.append("source_git provenance fields mismatch")
    if not valid_timestamp(value.get("captured_at")):
        errors.append("source_git captured_at must be a UTC timestamp")
    available = value.get("available")
    if not isinstance(available, bool):
        errors.append("source_git available must be boolean")
        return errors
    if available:
        if not sanitized_origin(value.get("origin")):
            errors.append("source_git origin is not sanitized")
        branch = value.get("branch")
        if branch is not None and (
            not isinstance(branch, str) or not branch.strip()
        ):
            errors.append("source_git branch must be null or a nonempty string")
        for field in ("commit", "tree"):
            candidate = value.get(field)
            if not isinstance(candidate, str) or not FULL_GIT_SHA.fullmatch(
                candidate
            ):
                errors.append(f"source_git {field} must be a full Git SHA")
        if not isinstance(value.get("dirty"), bool):
            errors.append("source_git dirty must be boolean when available")
    else:
        for field in ("origin", "branch", "commit", "tree", "dirty"):
            if value.get(field) is not None:
                errors.append(
                    f"source_git {field} must be null when provenance is unavailable"
                )
    return errors


def valid_item_hashes(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    for path, digest in value.items():
        if not isinstance(path, str) or not path:
            return False
        relative = PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts:
            return False
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            return False
    return True


def validate_profile_shared_files(
    profile: Any,
    shared_hashes: Any,
) -> list[str]:
    if not isinstance(profile, str) or profile not in INSTALL_PROFILES:
        return ["install_profile must be base or compat"]
    if not valid_item_hashes(shared_hashes):
        return []
    paths = frozenset(shared_hashes)
    if profile == "base":
        missing = sorted(BASE_SHARED_FILES - paths)
        unexpected = sorted(paths - BASE_SHARED_FILES)
        if missing or unexpected:
            return [
                "base profile shared files mismatch "
                f"missing={missing} unexpected={unexpected}"
            ]
        return []

    missing = sorted(COMPAT_SHARED_FILES - paths)
    unexpected = sorted(paths - COMPAT_SHARED_FILES)
    if missing or unexpected:
        return [
            "compat profile shared files mismatch "
            f"missing={missing} unexpected={unexpected}"
        ]
    return []


def main() -> int:
    try:
        value: Any = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INSTALLED SUITE INVALID: {exc}")
        return 1
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != INSTALL_MANIFEST_SCHEMA_VERSION
    ):
        print("INSTALLED SUITE INVALID: unsupported install manifest")
        return 1
    errors: list[str] = []
    manifest_fields = frozenset(value)
    if manifest_fields != INSTALL_MANIFEST_FIELDS:
        errors.append(
            "install-manifest fields mismatch "
            f"missing={sorted(INSTALL_MANIFEST_FIELDS - manifest_fields)} "
            f"unexpected={sorted(manifest_fields - INSTALL_MANIFEST_FIELDS)}"
        )
    if value.get("canonicalization") != CANONICALIZATION:
        errors.append("unsupported install-manifest canonicalization")
    install_profile = value.get("install_profile")
    errors.extend(validate_source_git(value.get("source_git")))
    expected = value.get("items")
    if not isinstance(expected, dict):
        print("INSTALLED SUITE INVALID: manifest items missing")
        return 1
    item_names_valid = set(expected) == set(INSTALL_ITEMS)
    if not item_names_valid:
        errors.append("manifest item names mismatch")
    item_shapes_valid = item_names_valid and all(
        valid_item_hashes(expected.get(name))
        for name in INSTALL_ITEMS
    )
    for name in PUBLIC_SKILLS:
        item = expected.get(name)
        if not valid_item_hashes(item):
            continue
        paths = frozenset(item)
        missing = sorted(PUBLIC_ITEM_FILES - paths)
        unexpected = sorted(paths - PUBLIC_ITEM_FILES)
        if missing or unexpected:
            errors.append(
                f"{name} manifest files mismatch "
                f"missing={missing} unexpected={unexpected}"
            )
    errors.extend(
        validate_profile_shared_files(
            install_profile,
            expected.get("quant-research-shared"),
        )
    )
    manifest_suite_hash = value.get("suite_content_sha256")
    if (
        not isinstance(manifest_suite_hash, str)
        or not SHA256.fullmatch(manifest_suite_hash)
    ):
        errors.append("suite_content_sha256 must be SHA-256")
    elif (
        item_shapes_valid
        and manifest_suite_hash != suite_content_sha256(expected)
    ):
        errors.append("suite_content_sha256 does not match manifest items")
    actual_items: dict[str, dict[str, str]] = {}
    for name in INSTALL_ITEMS:
        item = expected.get(name)
        if not valid_item_hashes(item):
            errors.append(f"invalid or missing manifest item {name}")
            continue
        destination = INSTALL_ROOT / name
        if destination.is_symlink():
            errors.append(f"{name} installed item is a symlink")
            continue
        if not destination.is_dir():
            errors.append(f"missing installed item {name}")
            continue
        symlinks = symlink_entries(destination)
        if symlinks:
            errors.append(f"{name} contains symlinks: {symlinks}")
            continue
        actual = tree_hashes(destination)
        actual_items[name] = actual
        if actual != item:
            missing = sorted(set(item) - set(actual))
            unexpected = sorted(set(actual) - set(item))
            changed = sorted(
                path
                for path in set(item) & set(actual)
                if item[path] != actual[path]
            )
            errors.append(
                f"{name} mismatch "
                f"missing={missing} unexpected={unexpected} changed={changed}"
            )
    shared_files = frozenset(actual_items.get("quant-research-shared", {}))
    shared_root = INSTALL_ROOT / "quant-research-shared"
    if shared_files:
        for name in PUBLIC_SKILLS:
            skill_root = INSTALL_ROOT / name
            try:
                skill_text = (skill_root / "SKILL.md").read_text(
                    encoding="utf-8"
                )
                agent_text = (skill_root / "agents/openai.yaml").read_text(
                    encoding="utf-8"
                )
            except OSError as exc:
                errors.append(f"{name}: cannot read public metadata: {exc}")
                continue
            errors.extend(validate_public_metadata(name, skill_text, agent_text))
            errors.extend(validate_public_body(name, skill_text))
            errors.extend(
                validate_public_routes(
                    name,
                    skill_text,
                    shared_root,
                    shared_files,
                )
            )
    if (
        len(actual_items) == len(INSTALL_ITEMS)
        and isinstance(manifest_suite_hash, str)
        and SHA256.fullmatch(manifest_suite_hash)
        and suite_content_sha256(actual_items) != manifest_suite_hash
    ):
        errors.append("installed canonical suite content hash mismatch")
    if errors:
        print("INSTALLED SUITE INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("INSTALLED SUITE VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
