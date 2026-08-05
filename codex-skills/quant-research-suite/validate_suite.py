#!/usr/bin/env python3
"""Validate the small public surface and preserved compatibility source.

The validator protects structural and semantic boundaries. It intentionally
does not treat headings, prose order, worker counts, or report templates as an
API. Runtime and schema behavior is exercised by the unittest suite.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INSTALLED_VALIDATOR = runpy.run_path(
    str(ROOT / "shared" / "scripts" / "validate_installed.py")
)
BASE_SHARED_FILES = INSTALLED_VALIDATOR["BASE_SHARED_FILES"]
parse_skill_frontmatter = INSTALLED_VALIDATOR["parse_skill_frontmatter"]
parse_agent_metadata = INSTALLED_VALIDATOR["parse_agent_metadata"]
validate_public_metadata = INSTALLED_VALIDATOR["validate_public_metadata"]
validate_public_body = INSTALLED_VALIDATOR["validate_public_body"]
validate_public_routes = INSTALLED_VALIDATOR["validate_public_routes"]
policy_segments = INSTALLED_VALIDATOR["policy_segments"]
has_unsafe_plan_probe_expansion = INSTALLED_VALIDATOR[
    "has_unsafe_plan_probe_expansion"
]
has_unsafe_developer_expansion = INSTALLED_VALIDATOR[
    "has_unsafe_developer_expansion"
]
has_self_expanding_quality_loop = INSTALLED_VALIDATOR[
    "has_self_expanding_quality_loop"
]
has_unsafe_plan_target_cleanup = INSTALLED_VALIDATOR[
    "has_unsafe_plan_target_cleanup"
]
has_unsafe_remote_authority_expansion = INSTALLED_VALIDATOR[
    "has_unsafe_remote_authority_expansion"
]
has_goal_scope_steering_contract = INSTALLED_VALIDATOR[
    "has_goal_scope_steering_contract"
]
validate_kernel_body = INSTALLED_VALIDATOR["validate_kernel_body"]
validate_recovery_body = INSTALLED_VALIDATOR["validate_recovery_body"]
has_unsafe_local_scm_authority_expansion = INSTALLED_VALIDATOR[
    "has_unsafe_local_scm_authority_expansion"
]
validate_repo_mutation_body = INSTALLED_VALIDATOR[
    "validate_repo_mutation_body"
]
SKILLS = ("quant-plan", "quant-goal", "quant-developer")

ORDINARY_CAPABILITY_FILES = tuple(
    Path(relative).name
    for relative in sorted(BASE_SHARED_FILES)
    if Path(relative).parent == Path("capabilities")
)

EXPECTED_WEB_DESIGN_SHA = (
    "dee11da0061b943ef04a8516ffb9811735571ff464c9a81bd8950cb3b6ee516e"
)

CANONICAL_ZERO_SPEND_GUARD = (
    "the default is zero spend and cost-unknown is blocked. a non-data paid "
    "action requires a direct prior user request naming the provider, action "
    "or resource, one-time or recurring nature, ceiling, duration, and stop "
    "condition."
)
CANONICAL_PAID_DATA_GUARD = (
    "paid data must not be proposed as a fallback, requested for approval, "
    "accessed, purchased, renewed, or used."
)

REQUIRED_SOURCE_FILES = frozenset(
    {
        ".gitignore",
        "README.md",
        "install.py",
        "validate_suite.py",
        *(
            f"skills/{skill}/{relative}"
            for skill in SKILLS
            for relative in ("SKILL.md", "agents/openai.yaml")
        ),
        "shared/core/authority.md",
        "shared/core/context-routing.md",
        "shared/references/adaptive-workflow.md",
        "shared/references/data-automation.md",
        "shared/capabilities/analysis.md",
        "shared/capabilities/external-data.md",
        "shared/capabilities/analysis-input-flow.md",
        "shared/capabilities/analysis-input-binding.md",
        "shared/capabilities/web-ui.md",
        "shared/capabilities/interactive-chart.md",
        "shared/capabilities/long-running-recovery.md",
        "shared/capabilities/backend.md",
        "shared/capabilities/scheduled-automation.md",
        "shared/capabilities/publication.md",
        "shared/capabilities/public-web.md",
        "shared/capabilities/remote-release.md",
        "shared/scripts/validate_installed.py",
        "shared/scripts/recovery_checkpoint.py",
        # Compatibility payload remains versioned in source.
        "shared/scripts/goal_ledger.py",
        "shared/scripts/goal_runtime.py",
        "shared/scripts/team_protocol.py",
        "shared/scripts/validate_project.py",
        "shared/scripts/validate_project_v2.py",
        "shared/scripts/validate_evidence.py",
        "shared/scripts/validate_evidence_v3.py",
        "shared/schemas/analysis-input-binding-capture.schema.json",
        "shared/schemas/analysis-invocation.schema.json",
        "shared/templates/analysis-input-binding-capture.example.json",
        "shared/templates/analysis-invocation.example.json",
        "shared/templates/team-run-packet.example.json",
        "shared/templates/worker-delivery-receipt.example.json",
        "shared/templates/team-integration-receipt.example.json",
    }
)

SECRET_ARTIFACT_NAMES = frozenset(
    {
        ".env",
        ".netrc",
        ".npmrc",
        ".pypirc",
        "credentials.json",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
        "secret.json",
        "secrets.json",
        "service-account.json",
        "service_account.json",
        "token",
        "token.txt",
    }
)
SECRET_ARTIFACT_SUFFIXES = (
    ".jks",
    ".kdbx",
    ".key",
    ".keystore",
    ".p12",
    ".pem",
    ".pfx",
)
OBVIOUS_SECRET_CONTENT_PATTERNS = (
    (
        "private key block",
        re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    ("AWS access key", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    (
        "GitHub token",
        re.compile(
            rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|"
            rb"github_pat_[A-Za-z0-9_]{20,})\b"
        ),
    ),
    ("Slack token", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("OpenAI-style secret key", re.compile(rb"\bsk-[A-Za-z0-9]{20,}\b")),
)


def normalized_policy_text(text: str) -> str:
    return " ".join(text.lower().split())


def frontmatter(text: str) -> dict[str, str]:
    return parse_skill_frontmatter(text) or {}


def agent_metadata(text: str) -> dict[str, str | bool] | None:
    return parse_agent_metadata(text)


def has_selector_metadata_clause(text: str, name: str) -> bool:
    clauses = re.split(r"(?<=[.!?;])\s+", normalized_policy_text(text))
    producer = r"(?:generated|derived|produced|emitted|issued)"
    selector_identity = (
        rf"(?:that\s+selector|the\s+current[- ]user(?:'s)?\s+selector|"
        rf"\${re.escape(name)}(?:\s+selector)?)"
    )
    for clause in clauses:
        positive_relation = re.search(
            rf"\bmetadata\b.{{0,100}}\b{producer}\b"
            rf".{{0,40}}\b(?:by|from)\b.{{0,60}}\b{selector_identity}\b"
            rf"|\bmetadata\b.{{0,40}}\bthat\b.{{0,30}}"
            rf"\b{selector_identity}\b.{{0,40}}\b{producer}\b"
            rf"|\b{selector_identity}\b.{{0,40}}\b{producer}\b"
            rf".{{0,40}}\bmetadata\b",
            clause,
        )
        if not (
            f"${name}" in clause
            and re.search(r"\btrusted\b", clause)
            and re.search(r"\bcurrent[- ]user(?:'s)?\b", clause)
            and re.search(r"\bsame[- ]request\b", clause)
            and positive_relation
        ):
            continue
        if re.search(
            r"\buntrusted\b|\bnot[- ]current[- ]user\b"
            r"|\bnot[- ]same[- ]request\b"
            r"|\b(?:not|never)(?:\s+\w+){0,3}\s+"
            r"(?:trusted|generated|derived|produced)\b"
            r"|\b(?:different|other)(?:\s+\w+){0,2}\s+selector\b"
            r"|\bother\s+than(?:\s+\w+){0,2}\s+selector\b"
            r"|\bselector\s+other\s+than\b"
            r"|\b(?:any|no|arbitrary)(?:\s+\w+){0,2}\s+selector\b"
            r"|\b(?:another|unrelated|second|additional|alternate)\s+selector\b"
            r"|\b(?:or|and)\s+(?:an?\s+)?"
            r"(?:another|unrelated|second|additional|alternate)\s+selector\b"
            r"|\bone\s+of\b.{0,30}\bselectors\b"
            r"|\bindependent(?:ly)?\s+of(?:\s+\w+){0,2}\s+selector\b"
            r"|\b(?:prior|previous|earlier)[- ]request\b|\bstale\b",
            clause,
        ):
            continue
        return True
    return False


def has_trusted_same_task_continuation(text: str) -> bool:
    clauses = re.split(r"(?<=[.!?;])\s+", normalized_policy_text(text))
    for clause in clauses:
        if not (
            re.search(r"\bcontinu\w*\b", clause)
            and re.search(r"\bwithout\b.{0,40}\bselector\b", clause)
            and re.search(r"\bonly when\b", clause)
            and re.search(r"\btrusted host metadata\b", clause)
            and re.search(r"\bcurrent[- ]user(?:'s)?\b", clause)
            and re.search(r"\b(?:clarification|steering)\b", clause)
            and re.search(
                r"\bsame\b.{0,40}\bunfinished\b.{0,40}"
                r"\balready[- ]active\b.{0,40}\btask\b",
                clause,
            )
        ):
            continue
        if re.search(
            r"\buntrusted\b|\bwithout trusted\b|\beven without\b"
            r"|\bany (?:prior )?task\b|\bcompleted task\b"
            r"|\bnot unfinished\b",
            clause,
        ):
            continue
        return True
    return False


def has_bounded_continuation_exclusion(text: str) -> bool:
    clauses = re.split(r"(?<=[.!?;])\s+", normalized_policy_text(text))
    for clause in clauses:
        if not all(term in clause for term in ("completed", "unrelated", "worker")):
            continue
        if (
            re.search(r"\bdoes not activate or continue\b", clause)
            or re.search(r"\bnever creates goal state\b", clause)
        ):
            return True
    return False


def has_unsafe_continuation_expansion(text: str) -> bool:
    clauses = policy_segments(text)
    for clause in clauses:
        if not (
            re.search(r"\bcontinu\w*\b", clause)
            and re.search(
                r"\b(?:any prior|completed|unrelated|worker) task\b",
                clause,
            )
            and re.search(
                r"\b(?:may|can|allow\w*|permit\w*)\b"
                r"|\bwithout\b.{0,40}\bselector\b",
                clause,
            )
        ):
            continue
        if re.search(
            r"\b(?:not|never|does not|do not|cannot|must not)\b",
            clause,
        ):
            continue
        return True
    return False


def has_guarded_kernel_skip(text: str) -> bool:
    clauses = re.split(r"(?<=[.!?;])\s+", normalized_policy_text(text))
    consult = r"(?:read|inspect|consult|check)"
    for clause in clauses:
        if not (
            re.search(r"\b(?:uncertain|unsure|unclear|in doubt)\b", clause)
            and re.search(r"\b(?:routing|router|kernel)\b", clause)
            and re.search(rf"\b{consult}\w*\b", clause)
            and re.search(r"\bskip\w*\b", clause)
        ):
            continue
        safe_double_negative = re.search(
            rf"\bdo\s+not\s+skip\w*\b.{{0,100}}\bwithout\b"
            rf".{{0,80}}\b{consult}\w*\b",
            clause,
        )
        if safe_double_negative:
            return True
        if re.search(
            rf"\b(?:do\s+not|never|avoid)\s+{consult}\w*\b"
            rf"|\brefrain\s+from\s+{consult}\w*\b"
            rf"|\brefuse\s+to\s+{consult}\w*\b",
            clause,
        ):
            continue
        if re.search(
            rf"\bskip\w*\b.{{0,100}}\bwithout\b"
            rf".{{0,80}}\b{consult}\w*\b",
            clause,
        ):
            continue
        consult_match = re.search(rf"\b{consult}\w*\b", clause)
        skip_match = re.search(r"\bskip\w*\b", clause)
        if (
            consult_match
            and skip_match
            and consult_match.start() < skip_match.start()
        ):
            return True
        if re.search(
            rf"\bskip\w*\b.{{0,80}}\bafter\b"
            rf".{{0,80}}\b{consult}\w*\b",
            clause,
        ):
            return True
    return False


def _has_direct_condition_id_relation(clause: str) -> bool:
    return bool(
        re.search(
            r"\b(?:stable\s+)?(?:condition|completion|success)[- ]+"
            r"(?:ids?|identifiers?)\b"
            r"|\b(?:ids?|identifiers?)\b.{0,50}\b(?:for|on|to|of)\b"
            r".{0,40}\b(?:completion|success)?\s*conditions?\b"
            r"|\b(?:completion|success)?\s*conditions?\b.{0,70}"
            r"\b(?:ids?|identifiers?)\b",
            clause,
        )
    )


def _has_condition_evidence_map_relation(clause: str) -> bool:
    return bool(
        re.search(r"\b(?:map|mapping)\b", clause)
        and re.search(r"\bconditions?\b", clause)
        and re.search(r"\bevidence\b", clause)
    )


def has_optional_condition_id_policy(text: str) -> bool:
    clauses = re.split(r"(?<=[.!?;])\s+", normalized_policy_text(text))
    return any(
        _has_direct_condition_id_relation(clause)
        and not re.search(r"\b(?:map|mapping|evidence)\b", clause)
        and (
            re.search(r"\boptional\b|\bselective(?:ly)?\b", clause)
            or re.search(r"\bonly\s+(?:when|if)\b", clause)
            or re.search(
                r"\b(?:may|can)\b.{0,60}\b(?:use|assign|attach|carry)\w*\b",
                clause,
            )
            or re.search(
                r"\b(?:not\s+(?:always\s+)?"
                r"(?:required|mandatory|compulsory)"
                r"|need\s+not)\b",
                clause,
            )
            or re.search(
                r"\b(?:when|if)\b.{0,80}\b(?:useful|needed)\b",
                clause,
            )
        )
        for clause in clauses
    )


def _has_map_use_prohibition_clause(clause: str) -> bool:
    action = r"(?:use(?:s|d)?|using|creat\w*|maintain\w*|map\w*)"
    return bool(
        re.search(
            rf"\b(?:do|does)\s+not(?:\s+ever)?\s+{action}\b"
            rf"|\bnever\s+{action}\b"
            rf"|\bavoid\s+{action}\b"
            rf"|\brefrain\s+from\s+{action}\b"
            rf"|\brefuse\s+to\s+{action}\b"
            rf"|\b(?:may|can)\s+not\s+be\s+{action}\b"
            r"|\b(?:forbidden|prohibited)\b",
            clause,
        )
    )


def _is_positive_conditional_map_clause(clause: str) -> bool:
    if not _has_condition_evidence_map_relation(clause):
        return False
    if _has_map_use_prohibition_clause(clause):
        return False
    if re.search(
        r"\b(?:do|does)\s+not\s+(?:use|create|maintain|map)\b"
        r"|\bnever\s+(?:use|create|maintain|map)\b",
        clause,
    ):
        return False
    if re.search(
        r"\bno\s+ambigui\w*\b"
        r"|\bambigui\w*\b.{0,40}\b(?:absent|none|without)\b",
        clause,
    ):
        return False
    trigger = re.search(
        r"\b(?:ambigui\w*|multiple|several|partial|machine[- ]audit|"
        r"useful|needed)\b",
        clause,
    )
    conditional = re.search(
        r"\b(?:optional|selective(?:ly)?|may|can|when|if)\b",
        clause,
    )
    return bool(trigger and conditional)


def has_conditional_condition_evidence_map(text: str) -> bool:
    clauses = re.split(r"(?<=[.!?;])\s+", normalized_policy_text(text))
    return any(_is_positive_conditional_map_clause(clause) for clause in clauses)


def has_universal_condition_id_mandate(text: str) -> bool:
    explicit_negation = re.compile(
        r"\b(?:do|does)\s+not\s+(?:require|need|assign|use|create)\b"
        r"|\bnever\s+(?:require|assign|use|create)\b"
        r"|\bnot\s+(?:required|mandatory|compulsory|assigned|used|needed)\b"
        r"|\bneed\s+not\b|\bnot\s+(?:all|every|each)\b"
        r"|\bno\s+(?:id|identifier)\b.{0,60}"
        r"\b(?:mandatory|required|compulsory)\b"
        r"|\bit\s+is\s+false\s+that\b"
    )
    clauses = re.split(r"(?<=[.!?;])\s+", normalized_policy_text(text))
    for clause in clauses:
        identifier = re.search(r"\b(?:ids?|identifiers?|sc-\*)\b", clause)
        universal = re.search(r"\b(?:all|every|each)\b", clause)
        condition_target = re.search(r"\bconditions?\b", clause)
        goal_target = (
            re.search(r"\bgoals?\b", clause)
            and _has_direct_condition_id_relation(clause)
        )
        direct_relation = _has_direct_condition_id_relation(clause)
        if not identifier or not (
            direct_relation
            or (universal and (condition_target or goal_target))
        ):
            continue
        if explicit_negation.search(clause):
            continue
        hard_mandate = re.search(
            r"\b(?:must|required|requires?|mandatory|compulsory|obligatory|"
            r"shall|needs?)\b"
            r"|\b(?:ids?|identifiers?)\b.{0,30}\b(?:is|are)\s+needed\b",
            clause,
        )
        action_mandate = re.search(
            r"\b(?:assign(?:s|ed)?|use[sd]?|gets?|carr(?:y|ies)|"
            r"create[sd]?)\b",
            clause,
        )
        conditional_permission = re.search(
            r"\b(?:optional|selective(?:ly)?|may|can)\b"
            r"|\bonly\s+(?:when|if)\b"
            r"|\b(?:when|if)\b.{0,80}\b(?:useful|needed)\b",
            clause,
        )
        if hard_mandate:
            return True
        if (
            universal
            and (condition_target or goal_target)
            and action_mandate
            and not conditional_permission
        ):
            return True
    return False


def has_unconditional_condition_evidence_map_mandate(text: str) -> bool:
    clauses = re.split(r"(?<=[.!?;])\s+", normalized_policy_text(text))
    for clause in clauses:
        if not _has_condition_evidence_map_relation(clause):
            continue
        if re.search(
            r"\b(?:do|does)\s+not\s+(?:require|maintain|create|use|map)\b"
            r"|\bnot\s+(?:required|mandatory|compulsory|obligatory)\b",
            clause,
        ):
            continue
        if _is_positive_conditional_map_clause(clause) and not re.search(
            r"\balways\b|\bevery\s+turn\b",
            clause,
        ):
            continue
        if (
            re.search(r"\balways\b|\bevery\s+turn\b", clause)
            or re.search(r"\bby\s+default\b", clause)
            or re.search(
                r"\b(?:required|mandatory|compulsory|obligatory|must|shall)\b",
                clause,
            )
            or re.search(
                r"^(?:map|maintain|create|update)\b.{0,120}"
                r"\b(?:all|every|each)\b",
                clause,
            )
            or (
                re.search(r"\b(?:all|every|each)\s+goals?\b", clause)
                and re.search(
                    r"\b(?:gets?|uses?|maintains?|creates?|maps?)\b",
                    clause,
                )
            )
            or (
                re.search(r"\bgoals?\b", clause)
                and re.search(r"\breceive[sd]?\b", clause)
            )
        ):
            return True
    return False


def has_condition_evidence_map_prohibition(text: str) -> bool:
    clauses = re.split(r"(?<=[.!?;])\s+", normalized_policy_text(text))
    return any(
        _has_condition_evidence_map_relation(clause)
        and _has_map_use_prohibition_clause(clause)
        and re.search(
            r"\b(?:ambigui\w*|multiple|several|partial|machine[- ]audit|"
            r"useful|needed)\b",
            clause,
        )
        for clause in clauses
    )


def has_canonical_zero_spend_guard(text: str) -> bool:
    normalized = normalized_policy_text(text)
    return (
        CANONICAL_ZERO_SPEND_GUARD in normalized
        and "does not require a direct prior user request" not in normalized
        and "cost-unknown is allowed" not in normalized
    )


def has_canonical_paid_data_guard(text: str) -> bool:
    normalized = normalized_policy_text(text)
    return (
        CANONICAL_PAID_DATA_GUARD in normalized
        and "paid data may" not in normalized
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def unsigned_document_sha256(
    value: dict[str, object],
    hash_field: str,
) -> str:
    unsigned = dict(value)
    unsigned.pop("$schema", None)
    unsigned.pop(hash_field, None)
    return canonical_json_sha256(unsigned)


def is_secret_artifact(relative: Path) -> bool:
    name = relative.name.lower()
    return (
        name in SECRET_ARTIFACT_NAMES
        or name.startswith(".env.")
        or name.endswith(SECRET_ARTIFACT_SUFFIXES)
    )


def is_ignored_bytecode(relative: Path) -> bool:
    return relative.suffix == ".pyc" and "__pycache__" in relative.parts


def is_allowed_package_file(relative: Path) -> bool:
    display = relative.as_posix()
    if display in {".gitignore", "README.md", "install.py", "validate_suite.py"}:
        return True
    if relative.name.startswith("."):
        return False
    if (
        len(relative.parts) == 4
        and relative.parts[0] == "skills"
        and relative.parts[1] in SKILLS
        and relative.parts[2] == "agents"
        and relative.parts[3] == "openai.yaml"
    ):
        return True
    if (
        len(relative.parts) == 3
        and relative.parts[0] == "skills"
        and relative.parts[1] in SKILLS
        and relative.parts[2] == "SKILL.md"
    ):
        return True
    if relative.parts[:1] == ("shared",):
        if len(relative.parts) < 3:
            return False
        section = relative.parts[1]
        if section in {
            "adapters",
            "advisory",
            "capabilities",
            "core",
            "profiles",
            "references",
        }:
            return relative.suffix == ".md"
        if section == "schemas":
            return relative.name.endswith(".schema.json")
        if section == "templates":
            return relative.suffix in {".json", ".md"}
        if section == "scripts":
            return relative.suffix == ".py" or relative.name == "github_preflight.sh"
        return False
    return (
        len(relative.parts) == 2
        and relative.parts[0] == "tests"
        and relative.name.startswith("test_")
        and relative.suffix == ".py"
    )


def validate_package_shape() -> list[str]:
    errors: list[str] = []
    discovered: set[str] = set()
    for current, directories, files in os.walk(
        ROOT,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)
        relative_dir = current_path.relative_to(ROOT)
        for directory in tuple(directories):
            path = current_path / directory
            relative = path.relative_to(ROOT)
            if path.is_symlink():
                errors.append(f"symlink is prohibited: {relative.as_posix()}")
                directories.remove(directory)
            elif directory == "__pycache__":
                directories.remove(directory)
            elif directory.startswith(".") and relative != Path(".git"):
                # The source package has no hidden directories below root.
                errors.append(
                    f"unexpected package directory: {relative.as_posix()}"
                )
                directories.remove(directory)
        for filename in files:
            path = current_path / filename
            relative = path.relative_to(ROOT)
            display = relative.as_posix()
            if path.is_symlink():
                errors.append(f"symlink is prohibited: {display}")
                continue
            if is_ignored_bytecode(relative):
                continue
            discovered.add(display)
            if is_secret_artifact(relative):
                errors.append(f"secret-bearing artifact is prohibited: {display}")
            if not is_allowed_package_file(relative):
                errors.append(f"unexpected package file: {display}")
            try:
                payload = path.read_bytes()
            except OSError:
                continue
            for label, pattern in OBVIOUS_SECRET_CONTENT_PATTERNS:
                if pattern.search(payload):
                    errors.append(
                        f"obvious {label} content is prohibited: {display}"
                    )
    for relative in sorted(REQUIRED_SOURCE_FILES - discovered):
        errors.append(f"missing package file: {relative}")
    return errors


def _missing_terms(
    text: str,
    concepts: dict[str, tuple[str, ...]],
) -> list[str]:
    normalized = normalized_policy_text(text)
    return [
        label
        for label, alternatives in concepts.items()
        if not any(term in normalized for term in alternatives)
    ]


def _validate_public_skill(name: str, text: str) -> list[str]:
    errors: list[str] = []
    normalized = normalized_policy_text(text)
    if len(text.splitlines()) > 220:
        errors.append(f"{name}: SKILL.md is no longer concise")

    common = {
        "literal selector": (f"`$${name}`".replace("$$", "$"),),
        "no semantic activation": ("semantic match",),
        "no prior activation": ("prior-turn",),
        "no worker activation": ("worker instruction",),
        "source kernel": (
            "../../shared/references/adaptive-workflow.md",
        ),
        "installed kernel": (
            "../quant-research-shared/references/adaptive-workflow.md",
        ),
        "legacy opt-in": (
            "existing exact contract",
            "existing project depends on its exact contract",
        ),
    }
    for concept in _missing_terms(text, common):
        errors.append(f"{name}: missing public contract {concept!r}")
    if not has_selector_metadata_clause(text, name):
        errors.append(
            f"{name}: selector metadata must be trusted, current-user, "
            "same-request, and selector-derived"
        )
    if not has_trusted_same_task_continuation(text):
        errors.append(
            f"{name}: continuation must require trusted host metadata for "
            "current-user clarification or steering in the same unfinished "
            "already-active task"
        )
    if not has_bounded_continuation_exclusion(text):
        errors.append(
            f"{name}: continuation must exclude completed, unrelated, and "
            "worker tasks"
        )
    if has_unsafe_continuation_expansion(text):
        errors.append(
            f"{name}: permissive continuation of prior, completed, unrelated, "
            "or worker tasks is prohibited"
        )
    if "automatically activate" in normalized or "semantic match activates" in normalized:
        errors.append(f"{name}: implicit activation is prohibited")

    role_concepts: dict[str, dict[str, tuple[str, ...]]] = {
        "quant-plan": {
            "read-only boundary": ("this role is read-only",),
            "no edits": ("do not edit files",),
            "evidence-first loop": (
                "ground → explore → decide → plan → self-critique",
            ),
            "discover before asking": ("resolve discoverable facts",),
            "planning authority": (
                "planning does not authorize implementation",
            ),
            "adaptive output": (
                "choose the leanest communication form",
                "choose the smallest form",
            ),
        },
        "quant-goal": {
            "inspect native goal first": ("call `get_goal` before",),
            "observable completion": ("observable completion conditions",),
            "no fixed condition count": ("no fixed count",),
            "no duplicate goal": ("never create a duplicate",),
            "conditional readback": (
                "call `get_goal` again only when",
            ),
            "acceptance continuation": (
                "required completion condition is unmet",
            ),
            "verified completion": (
                'update_goal(status="complete")',
            ),
            "three-turn blocker": (
                "three consecutive goal turns",
            ),
        },
        "quant-developer": {
            "implementation loop": (
                "inspect → choose → implement → verify → adapt",
            ),
            "actual surface": ("actual consumer or rendered surface",),
            "acceptance stop": (
                "acceptance condition remains unmet",
            ),
            "material risk": ("material risk",),
            "quality debt": ("quality debt",),
            "parent integration": ("the parent owns integration",),
        },
    }
    for concept in _missing_terms(text, role_concepts[name]):
        errors.append(f"{name}: missing role contract {concept!r}")
    if not has_guarded_kernel_skip(text):
        errors.append(
            f"{name}: uncertain narrow work must consult routing before skip"
        )

    if name == "quant-goal" and any(
        phrase in normalized
        for phrase in (
            "two to six",
            "sc-1 through sc-6",
            "every current `sc-*`",
        )
    ):
        errors.append("quant-goal: fixed success-condition ceremony is prohibited")
    if name == "quant-goal" and not has_optional_condition_id_policy(text):
        errors.append("quant-goal: stable condition IDs must remain optional")
    if name == "quant-goal" and not has_conditional_condition_evidence_map(text):
        errors.append(
            "quant-goal: condition-evidence mapping must remain conditional"
        )
    if (
        name == "quant-goal"
        and has_unconditional_condition_evidence_map_mandate(text)
    ):
        errors.append(
            "quant-goal: unconditional condition-evidence mapping is prohibited"
        )
    if name == "quant-goal" and has_condition_evidence_map_prohibition(text):
        errors.append(
            "quant-goal: useful condition-evidence mapping must not be prohibited"
        )
    if name == "quant-goal" and has_universal_condition_id_mandate(text):
        errors.append(
            "quant-goal: universal completion-condition IDs are prohibited"
        )
    if name == "quant-plan" and has_unsafe_plan_probe_expansion(text):
        errors.append(
            "quant-plan: probe must not permit provider writes or unsafe "
            "dependency installation"
        )
    if name == "quant-plan" and has_unsafe_plan_target_cleanup(text):
        errors.append("quant-plan: target residue cleanup is prohibited")
    if name == "quant-goal" and not has_goal_scope_steering_contract(text):
        errors.append(
            "quant-goal: material scope and steering boundaries are required"
        )
    if name == "quant-developer" and has_unsafe_developer_expansion(text):
        errors.append("quant-developer: open-ended improvement loop is prohibited")
    if name in {"quant-goal", "quant-developer"} and (
        has_self_expanding_quality_loop(text)
    ):
        errors.append(f"{name}: self-expanding quality loop is prohibited")
    if has_unsafe_remote_authority_expansion(text):
        errors.append(f"{name}: merge without separate authority is prohibited")
    return errors


def _validate_kernel(text: str) -> list[str]:
    errors: list[str] = []
    concepts = {
        "parent boundary": ("invoking public skill's role",),
        "actual environment": ("ground in the actual environment",),
        "capability routing": ("load only the needed capability rail",),
        "analysis rail": ("`capabilities/analysis.md`",),
        "data rail": ("`capabilities/external-data.md`",),
        "binding rail": ("`capabilities/analysis-input-flow.md`",),
        "automation rail": ("`capabilities/scheduled-automation.md`",),
        "publication rail": ("`capabilities/publication.md`",),
        "public rail": ("`capabilities/public-web.md`",),
        "repository-mutation rail": ("`capabilities/repo-mutation.md`",),
        "interruption-recovery rail": (
            "`capabilities/long-running-recovery.md`",
        ),
        "ordinary data automation": (
            "compose the external-data, scheduled-automation, publication, "
            "and public-web rails",
        ),
        "data automation stays compatibility-only": (
            "does not select legacy data-automation machinery",
        ),
        "available capability": (
            "collaboration and continuation surfaces the host actually exposes",
        ),
        "bounded delegation": ("bounded subagents",),
        "team threshold": ("ongoing mutual coordination",),
        "serial fallback": ("otherwise serial work",),
        "one-off lifecycle": (
            "one-off wait for time, event, thread, ci, or external status",
        ),
        "parent integration": ("parent reconciles claims",),
        "parent evidence review": ("re-inspects returned evidence",),
        "worker claim is not proof": ("worker completion claim is not proof",),
        "quality frontier": ("strongest complete result",),
        "least churn is not least effort": ("not least effort",),
        "early useful delegation": ("early enough to influence the route",),
        "visible native coordination": ("host-native plan or status",),
        "single integrated state": ("one integrated state",),
        "conflicting findings are resolved": ("test the competing claims",),
        "safe retry classification": ("safe to repeat",),
        "established quality gap": (
            "material gap against the established quality bar",
        ),
        "proportional quality stop": ("proportional quality bar",),
        "fresh independent review": ("fresh independent reviewer",),
        "acceptance continuation": ("acceptance condition is unmet",),
        "quality-debt stop": (
            "remaining items are only quality debt",
        ),
        "data policy routing": (
            "read both `capabilities/external-data.md` and "
            "`core/authority.md`",
        ),
        "zero-billing summary": ("selected route remains zero-billing",),
        "actual proof": ("prove the real outcome",),
        "authority owner": ("core/authority.md",),
    }
    for concept in _missing_terms(text, concepts):
        errors.append(f"adaptive kernel: missing concept {concept!r}")
    normalized = normalized_policy_text(text)
    if "always use a team" in normalized or "fixed worker count" in normalized:
        errors.append("adaptive kernel: fixed orchestration is prohibited")
    errors.extend(validate_kernel_body(text))
    for label, pattern in (
        ("payment method", r"\bpayment method\b"),
        ("PAYG and overage", r"\bpayg\b.{0,30}\boverage\b"),
        ("chargeable fallback", r"\bchargeable fallback\b"),
        (
            "optional paid tiers",
            r"\bprovider\b.{0,80}\boptional paid tiers\b",
        ),
        (
            "display or redistribution rights",
            r"\bdisplay\b.{0,30}\bredistribution rights\b",
        ),
    ):
        if re.search(pattern, normalized):
            errors.append(
                "adaptive kernel: detailed data policy belongs in its "
                f"selected rails, found {label!r}"
            )
    return errors


def _validate_authority(text: str) -> list[str]:
    errors: list[str] = []
    concepts = {
        "current user authority": ("current user's request",),
        "separate dimensions": ("separate dimensions",),
        "local scm": ("local source-control mutation",),
        "remote scm": ("remote source-control mutation",),
        "provider mutation": ("provider or production mutation",),
        "secret safety": ("never put secret values",),
        "data hard stop": ("hard-stop before any charge",),
        "optional paid tiers": ("provider may also sell unrelated or optional paid tiers",),
        "paid data no approval": ("no action-approval escape hatch",),
    }
    for concept in _missing_terms(text, concepts):
        errors.append(f"authority: missing concept {concept!r}")
    if not has_canonical_zero_spend_guard(text):
        errors.append("authority: missing canonical zero-spend guard")
    if not has_canonical_paid_data_guard(text):
        errors.append("authority: missing canonical paid-data guard")
    return errors


def _validate_router(text: str) -> list[str]:
    concepts = {
        "shared no activation": ("shared resources never activate",),
        "source root": ("source: the `shared` directory",),
        "installed root": ("installed: the `quant-research-shared`",),
        "ordinary kernel": ("load `references/adaptive-workflow.md`",),
        "single capability router": ("single ordinary-path router",),
        "same-task continuation": ("same unfinished",),
        "active Goal continuation": ("already-active quant goal",),
        "native Goal lifecycle continuation": ("native lifecycle work",),
        "one-off lifecycle": (
            "host-lifecycle continuation follows a time, event, thread, ci, "
            "or external-status dependency",
        ),
        "no auto legacy": ("do not auto-load a manifest",),
        "legacy trigger": ("existing project depends on the exact contract",),
        "compat profile verification": ("`install_profile: compat`",),
        "rooted install manifest": (
            "`<quant-shared-root>/install-manifest.json`",
        ),
        "missing child boundary": (
            "missing child makes only that compatibility path unavailable",
        ),
        "light recovery is not legacy runtime": (
            "lightweight recovery rail is separate from that legacy runtime",
        ),
    }
    return [
        f"context router: missing concept {concept!r}"
        for concept in _missing_terms(text, concepts)
    ]


def _validate_external_data(text: str) -> list[str]:
    errors = [
        f"external data: missing concept {concept!r}"
        for concept in _missing_terms(
            text,
            {
                "ordinary schedule rail": ("`scheduled-automation.md`",),
                "ordinary publication rail": ("`publication.md`",),
                "compat router": ("`../core/context-routing.md`",),
                "missing compatibility is unavailable": (
                    "compatibility path as unavailable",
                ),
            },
        )
    ]
    if "access_eligibility" in text:
        errors.append(
            "external data: legacy schema fields must stay off the ordinary rail"
        )
    if "`../references/data-automation.md`" in text:
        errors.append(
            "external data: ordinary base rail must not directly load "
            "compat-only data-automation.md"
        )
    return errors


def _validate_ordinary_capability_rail(
    relative: str,
    text: str,
) -> list[str]:
    errors: list[str] = []
    if re.search(r"(?m)^Activate\b", text):
        errors.append(
            f"ordinary capability {relative}: use apply/read language, not "
            "skill activation language"
        )
    if re.search(r"(?m)^Evidence gates?:", text):
        errors.append(
            f"ordinary capability {relative}: undefined evidence-gate labels "
            "are prohibited"
        )
    if relative == "analysis.md":
        for field in ("result_identity_fields", "result_identity_pointers"):
            if field in text:
                errors.append(
                    "ordinary capability analysis.md: legacy schema field "
                    f"{field!r} is prohibited"
                )
    if (
        relative == "remote-release.md"
        and "selection adds gates" in normalized_policy_text(text)
    ):
        errors.append(
            "ordinary capability remote-release.md: legacy gate wording is "
            "prohibited"
        )
    if relative == "repo-mutation.md":
        errors.extend(validate_repo_mutation_body(text))
    return errors


def _validate_analysis_input_flow(text: str) -> list[str]:
    errors = [
        f"analysis input flow: missing concept {concept!r}"
        for concept in _missing_terms(
            text,
            {
                "ordinary path": ("ordinary-path rail",),
                "repository native first": ("repository's existing contract",),
                "invoked analysis boundary": ("invoked analysis boundary",),
                "effective parameter": ("effective parameter",),
                "consumer result": ("displayed or consumed result",),
                "observable variant": ("observable analytical effect",),
                "state separation": (
                    "draft, applied, pending, and bound state",
                ),
                "compat router": ("`../core/context-routing.md`",),
                "strict contract stays compatibility-only": (
                    "contract is compatibility-only",
                ),
                "missing strict contract is unavailable": (
                    "report that path as unavailable",
                ),
            },
        )
    ]
    normalized = normalized_policy_text(text)
    if not re.search(
        r"\b(?:do not|does not|need not)\b.{0,100}\brequire\b"
        r".{0,180}\b(?:manifest|capture|trace|hash|receipt)\b",
        normalized,
    ):
        errors.append(
            "analysis input flow: ordinary proof must not require strict artifacts"
        )
    return errors


def _validate_analysis_input_binding(text: str) -> list[str]:
    errors = [
        f"analysis input binding: missing concept {concept!r}"
        for concept in _missing_terms(
            text,
            {
                "not ordinary path": ("not an ordinary-path rail",),
                "compat router": ("`../core/context-routing.md`",),
                "compat profile": ("profile is `compat`",),
                "exact child check": ("exact children exist",),
                "missing strict contract is unavailable": (
                    "strict compatibility path unavailable",
                ),
                "rooted invocation schema": (
                    "`../schemas/analysis-invocation.schema.json`",
                ),
                "rooted capture template": (
                    "`../templates/analysis-input-binding-capture.example.json`",
                ),
                "rooted invocation template": (
                    "`../templates/analysis-invocation.example.json`",
                ),
            },
        )
    ]
    for ambiguous in ("`schemas/", "`templates/"):
        if ambiguous in text:
            errors.append(
                "analysis input binding: compatibility child reference must "
                f"be rooted, found {ambiguous}"
            )
    return errors


def validate_team_template_examples(shared: Path) -> list[str]:
    errors: list[str] = []
    examples = {
        "packet": (
            "templates/team-run-packet.example.json",
            "packet_sha256",
        ),
        "delivery": (
            "templates/worker-delivery-receipt.example.json",
            "receipt_sha256",
        ),
        "integration": (
            "templates/team-integration-receipt.example.json",
            "receipt_sha256",
        ),
    }
    for label, (relative, hash_field) in examples.items():
        path = shared / relative
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            errors.append(f"team {label} example is invalid JSON")
            continue
        if not isinstance(value, dict):
            errors.append(f"team {label} example must be a JSON object")
            continue
        if value.get(hash_field) != unsigned_document_sha256(value, hash_field):
            errors.append(f"team {label} example self-hash is invalid")
    return errors


def validate() -> list[str]:
    errors = validate_package_shape()
    skills_root = ROOT / "skills"
    shared = ROOT / "shared"
    discovered = (
        {path.name for path in skills_root.iterdir() if path.is_dir()}
        if skills_root.is_dir()
        else set()
    )
    if discovered != set(SKILLS):
        errors.append(
            "public skill set must be exactly: " + ", ".join(SKILLS)
        )

    for name in SKILLS:
        skill_path = skills_root / name / "SKILL.md"
        agent_path = skills_root / name / "agents/openai.yaml"
        skill_text = (
            skill_path.read_text(encoding="utf-8")
            if skill_path.is_file()
            else None
        )
        agent_text = (
            agent_path.read_text(encoding="utf-8")
            if agent_path.is_file()
            else None
        )
        if skill_text is not None and agent_text is not None:
            errors.extend(validate_public_metadata(name, skill_text, agent_text))
            errors.extend(validate_public_body(name, skill_text))
            errors.extend(
                validate_public_routes(
                    name,
                    skill_text,
                    shared,
                    BASE_SHARED_FILES,
                )
            )
        if skill_path.is_file():
            assert skill_text is not None
            errors.extend(_validate_public_skill(name, skill_text))
        if agent_path.is_file():
            assert agent_text is not None
            metadata = agent_metadata(agent_text)
            if metadata is None:
                errors.append(f"{name}: invalid agents/openai.yaml")
            else:
                if metadata["allow_implicit_invocation"] is not False:
                    errors.append(f"{name}: implicit invocation must be false")
                prompt = str(metadata["default_prompt"])
                if f"${name}" not in prompt:
                    errors.append(
                        f"{name}: default prompt must mention ${name}"
                    )
                if len(prompt.split()) > 50:
                    errors.append(f"{name}: default prompt is too long")
                selector_copy = normalized_policy_text(
                    f"{metadata['short_description']} {prompt}"
                )
                if not any(
                    term in selector_copy
                    for term in (
                        "adaptive",
                        "adaptively",
                        "capability-aware",
                    )
                ):
                    errors.append(
                        f"{name}: selector copy must expose adaptive behavior"
                    )

    if (shared / "SKILL.md").exists():
        errors.append("shared/SKILL.md is prohibited")

    kernel = shared / "references/adaptive-workflow.md"
    authority = shared / "core/authority.md"
    router = shared / "core/context-routing.md"
    external_data = shared / "capabilities/external-data.md"
    input_flow = shared / "capabilities/analysis-input-flow.md"
    input_binding = shared / "capabilities/analysis-input-binding.md"
    recovery = shared / "capabilities/long-running-recovery.md"
    if kernel.is_file():
        errors.extend(_validate_kernel(kernel.read_text(encoding="utf-8")))
    if authority.is_file():
        authority_text = authority.read_text(encoding="utf-8")
        errors.extend(_validate_authority(authority_text))
        for path in sorted(ROOT.rglob("*")):
            if (
                path != authority
                and path.is_file()
                and path.suffix in {".md", ".yaml"}
                and has_canonical_zero_spend_guard(
                    path.read_text(encoding="utf-8")
                )
            ):
                errors.append(
                    f"{path.relative_to(ROOT)}: duplicates canonical paid policy"
                )
    if router.is_file():
        errors.extend(_validate_router(router.read_text(encoding="utf-8")))
    if external_data.is_file():
        errors.extend(
            _validate_external_data(external_data.read_text(encoding="utf-8"))
        )
    if input_flow.is_file():
        errors.extend(
            _validate_analysis_input_flow(
                input_flow.read_text(encoding="utf-8")
            )
        )
    if input_binding.is_file():
        errors.extend(
            _validate_analysis_input_binding(
                input_binding.read_text(encoding="utf-8")
            )
        )
    if recovery.is_file():
        errors.extend(
            validate_recovery_body(recovery.read_text(encoding="utf-8"))
        )
    for relative in ORDINARY_CAPABILITY_FILES:
        path = shared / "capabilities" / relative
        if path.is_file():
            errors.extend(
                _validate_ordinary_capability_rail(
                    relative,
                    path.read_text(encoding="utf-8"),
                )
            )

    for path in sorted(shared.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            errors.append(
                f"{path.relative_to(ROOT)}: invalid JSON: {error.msg}"
            )
    errors.extend(validate_team_template_examples(shared))

    design = shared / "references/web-design-v2.4.1.md"
    design_source = shared / "references/web-design-source.md"
    if design.is_file() and sha256(design) != EXPECTED_WEB_DESIGN_SHA:
        errors.append("web-design-v2.4.1.md hash mismatch")
    if design_source.is_file() and EXPECTED_WEB_DESIGN_SHA not in (
        design_source.read_text(encoding="utf-8")
    ):
        errors.append("web-design-source.md does not bind the expected hash")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("SUITE VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
