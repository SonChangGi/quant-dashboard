#!/usr/bin/env python3
"""Validate the three-skill suite and its bundled resources."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SKILLS = ("quant-plan", "quant-goal", "quant-developer")
EXPECTED_SKILL_DESCRIPTIONS = {
    "quant-plan": (
        "Use only when the user explicitly invokes $quant-plan. Shape work "
        "into a reviewed, decision-complete plan with observable acceptance; "
        "never auto-activate."
    ),
    "quant-developer": (
        "Use only when the user explicitly invokes $quant-developer. "
        "Implement, clean, and verify a coherent change with snapshot-bound "
        "evidence; never auto-activate."
    ),
    "quant-goal": (
        "Use only when the user explicitly invokes $quant-goal. Drive a "
        "durable objective through checkpoints, review, repair, and "
        "evidence-backed completion; never auto-activate."
    ),
}
EXPECTED_SKILL_CONTRACTS = {
    "quant-plan": (
        "activate only when the current user request intentionally invokes "
        "this skill",
        "literal token `$quant-plan`",
        "another agent's instruction is not activation",
        "read-only",
        "does not implement",
        "create goal state",
        "default path is self-contained",
        "do not invoke implementation, goal, or another skill",
    ),
    "quant-developer": (
        "activate only when the current user request intentionally invokes "
        "this skill",
        "literal token `$quant-developer`",
        "another agent's instruction is not activation",
        "repository-native",
        "smallest coherent change",
        "never declares the overall goal complete",
        "proportional verification",
        "do not activate another quant skill to obtain a worker",
    ),
    "quant-goal": (
        "activate only when the current user request intentionally invokes "
        "this skill",
        "literal token `$quant-goal`",
        "another agent's instruction is not activation",
        "host application's goal state as canonical",
        "do not create goal state for an ordinary",
        "every later turn that should use this workflow requires a fresh "
        "explicit invocation",
        "use ordinary host implementation workers by default",
        "another quant skill may participate only when the current user "
        "request explicitly invoked it too",
    ),
}
EXPECTED_PROMPT_CONTRACTS = {
    "quant-plan": (
        "current user explicitly invoked $quant-plan",
        "decision-complete plan packet",
        "without mutating",
        "activating another skill",
    ),
    "quant-developer": (
        "current user explicitly invoked $quant-developer",
        "smallest coherent repository-native change",
        "delivery evidence bound to changed paths and checks",
        "without activating another skill",
    ),
    "quant-goal": (
        "current user explicitly invoked $quant-goal",
        "host goal as canonical",
        "ordinary workers or an isolated team",
        "without activating another skill",
        "future-turn activation",
    ),
}
EXPECTED_PACKAGE_FILES = frozenset(
    {
        ".gitignore",
        "README.md",
        "install.py",
        "validate_suite.py",
        "shared/adapters/fastapi.md",
        "shared/adapters/github-actions.md",
        "shared/adapters/github-pages.md",
        "shared/adapters/github.md",
        "shared/adapters/supabase.md",
        "shared/adapters/vercel.md",
        "shared/advisory/architecture-options.md",
        "shared/advisory/external-comparisons.md",
        "shared/advisory/research-method.md",
        "shared/advisory/technology-examples.md",
        "shared/capabilities/analysis-input-binding.md",
        "shared/capabilities/analysis.md",
        "shared/capabilities/agent-team-execution.md",
        "shared/capabilities/backend.md",
        "shared/capabilities/external-data.md",
        "shared/capabilities/interactive-chart.md",
        "shared/capabilities/multi-agent-write.md",
        "shared/capabilities/public-web.md",
        "shared/capabilities/publication.md",
        "shared/capabilities/remote-release.md",
        "shared/capabilities/repo-mutation.md",
        "shared/capabilities/scheduled-automation.md",
        "shared/capabilities/web-ui.md",
        "shared/core/authority.md",
        "shared/core/context-routing.md",
        "shared/core/evidence-semantics.md",
        "shared/core/invariants.md",
        "shared/profiles/quant-public-dashboard-strict.md",
        "shared/profiles/quant-research-web.md",
        "shared/references/cost-and-authority.md",
        "shared/references/data-automation.md",
        "shared/references/developer-runbook.md",
        "shared/references/agent-orchestration.md",
        "shared/references/durable-runtime.md",
        "shared/references/goal-and-subagents.md",
        "shared/references/operating-principles.md",
        "shared/references/research-and-planning.md",
        "shared/references/web-design-source.md",
        "shared/references/web-design-v2.4.0.md",
        "shared/schemas/analysis-input-binding-capture.schema.json",
        "shared/schemas/analysis-invocation.schema.json",
        "shared/schemas/evidence-receipt-v3.schema.json",
        "shared/schemas/goal-ledger-state.schema.json",
        "shared/schemas/goal-state-v2.schema.json",
        "shared/schemas/quant-project-v2.schema.json",
        "shared/schemas/review-receipt.schema.json",
        "shared/schemas/story-envelope.schema.json",
        "shared/schemas/story-receipt.schema.json",
        "shared/schemas/team-integration-receipt.schema.json",
        "shared/schemas/team-run-packet.schema.json",
        "shared/schemas/worker-delivery-receipt.schema.json",
        "shared/scripts/capability_model.py",
        "shared/scripts/contract_guard.py",
        "shared/scripts/github_preflight.sh",
        "shared/scripts/goal_ledger.py",
        "shared/scripts/goal_primitives.py",
        "shared/scripts/goal_runtime.py",
        "shared/scripts/project_inventory.py",
        "shared/scripts/quantctl.py",
        "shared/scripts/team_protocol.py",
        "shared/scripts/validate_evidence.py",
        "shared/scripts/validate_evidence_v3.py",
        "shared/scripts/validate_installed.py",
        "shared/scripts/validate_project.py",
        "shared/scripts/validate_project_v2.py",
        "shared/templates/approved-plan.example.md",
        "shared/templates/analysis-input-binding-capture.example.json",
        "shared/templates/analysis-invocation.example.json",
        "shared/templates/audit-report.example.md",
        "shared/templates/evidence-receipt-v3.example.json",
        "shared/templates/evidence-receipt.example.json",
        "shared/templates/goal-ledger-state.example.json",
        "shared/templates/goal-state-v2.example.json",
        "shared/templates/goal-state.example.json",
        "shared/templates/quant-project-v2.example.json",
        "shared/templates/quant-project.example.json",
        "shared/templates/quant-project.schema.json",
        "shared/templates/review-receipt.example.json",
        "shared/templates/story-envelope.example.json",
        "shared/templates/story-receipt.example.json",
        "shared/templates/team-integration-receipt.example.json",
        "shared/templates/team-run-packet.example.json",
        "shared/templates/worker-delivery-receipt.example.json",
        "skills/quant-developer/SKILL.md",
        "skills/quant-developer/agents/openai.yaml",
        "skills/quant-goal/SKILL.md",
        "skills/quant-goal/agents/openai.yaml",
        "skills/quant-plan/SKILL.md",
        "skills/quant-plan/agents/openai.yaml",
        "tests/test_capability_v2.py",
        "tests/test_evidence_v3.py",
        "tests/test_evidence_v3_redteam.py",
        "tests/test_free_data_policy.py",
        "tests/test_generic_skill_contracts.py",
        "tests/test_goal_ledger.py",
        "tests/test_goal_runtime.py",
        "tests/test_goal_runtime_redteam.py",
        "tests/test_install_provenance.py",
        "tests/test_installed_runtime_smoke.py",
        "tests/test_package_shape.py",
        "tests/test_policy_guards.py",
        "tests/test_quantctl.py",
        "tests/test_registry_consistency.py",
        "tests/test_skill_routing.py",
        "tests/test_team_evidence_v3.py",
        "tests/test_team_protocol.py",
        "tests/test_tools.py",
        "tests/test_v1_compatibility.py",
    }
)
EXPECTED_PACKAGE_DIRECTORIES = frozenset(
    parent.as_posix()
    for relative in EXPECTED_PACKAGE_FILES
    for parent in Path(relative).parents
    if parent != Path(".")
)
EXPECTED_BYTECODE_PARENTS = EXPECTED_PACKAGE_DIRECTORIES | {"."}
EXTENSIBLE_PACKAGE_RULES: dict[str, tuple[str, ...]] = {
    "shared/adapters": (".md",),
    "shared/advisory": (".md",),
    "shared/capabilities": (".md",),
    "shared/profiles": (".md",),
    "shared/references": (".md",),
    "shared/schemas": (".schema.json",),
    "shared/templates": (".json", ".md"),
}
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
        re.compile(
            rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
        ),
    ),
    ("AWS access key", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    (
        "GitHub token",
        re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    ("Slack token", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("OpenAI-style secret key", re.compile(rb"\bsk-[A-Za-z0-9]{20,}\b")),
)
REQUIRED_PAID_ACTION_GUARDS = (
    "auto-renewing or free-to-paid trials",
    "payment method registration",
    "plan upgrade",
    "paid overage",
    "paid add-on",
    "spend cap disablement",
)
CANONICAL_ZERO_SPEND_GUARD = (
    "auto-renewing or free-to-paid trials, payment method registration, "
    "plan upgrades, paid overage or pay-as-you-go use, exceeding a verified "
    "free quota, paid add-ons, and spend cap disablement are paid actions and "
    "are prohibited unless a direct prior user request names the exact bounded "
    "paid action; free-plan cost hard stops must remain enabled."
)
CANONICAL_PAID_DATA_GUARD = (
    "paid data is ineligible and must not be proposed, compared as a fallback, "
    "requested for approval, accessed, purchased, renewed, or used."
)
EXPECTED_WEB_DESIGN_SHA = (
    "831054bf048769f335d5229c71e17e90bf9bdf7cbe899641735cc7a47f78c525"
)
AGENT_METADATA_PATTERN = re.compile(
    r"\Ainterface:\n"
    r'  display_name: (?P<display_name>"(?:[^"\\\n]|\\.)*")\n'
    r'  short_description: (?P<short_description>"(?:[^"\\\n]|\\.)*")\n'
    r'  default_prompt: (?P<default_prompt>"(?:[^"\\\n]|\\.)*")\n'
    r"policy:\n"
    r"  allow_implicit_invocation: "
    r"(?P<allow_implicit_invocation>true|false)\n?"
    r"\Z"
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


def validate_team_template_examples(shared: Path) -> list[str]:
    """Validate the sealed examples without requiring live worker roots."""

    errors: list[str] = []
    templates = shared / "templates"
    paths = {
        "packet": templates / "team-run-packet.example.json",
        "delivery": templates / "worker-delivery-receipt.example.json",
        "integration": templates / "team-integration-receipt.example.json",
    }
    if not all(path.is_file() for path in paths.values()):
        return errors
    try:
        values = {
            label: json.loads(path.read_text(encoding="utf-8"))
            for label, path in paths.items()
        }
    except (json.JSONDecodeError, OSError):
        return errors
    if not all(isinstance(value, dict) for value in values.values()):
        errors.append("team protocol examples must be JSON objects")
        return errors

    packet = values["packet"]
    delivery = values["delivery"]
    integration = values["integration"]
    expected_types = {
        "packet": "quant_team_run_packet",
        "delivery": "quant_worker_delivery_receipt",
        "integration": "quant_team_integration_receipt",
    }
    expected_schema_versions = {
        "packet": 2,
        "delivery": 1,
        "integration": 1,
    }
    for label, value in values.items():
        if value.get("document_type") != expected_types[label]:
            errors.append(
                f"team {label} example has invalid document_type"
            )
        if value.get("schema_version") != expected_schema_versions[label]:
            errors.append(
                f"team {label} example must use schema_version "
                f"{expected_schema_versions[label]}"
            )

    packet_sha = packet.get("packet_sha256")
    if packet_sha != unsigned_document_sha256(packet, "packet_sha256"):
        errors.append("team packet example self-hash is invalid")
    objective_sha = packet.get("objective_sha256")
    if not (
        isinstance(objective_sha, str)
        and len(objective_sha) == 64
        and all(character in "0123456789abcdef" for character in objective_sha)
    ):
        errors.append("team packet example objective hash is invalid")
    delivery_sha = delivery.get("receipt_sha256")
    if delivery_sha != unsigned_document_sha256(delivery, "receipt_sha256"):
        errors.append("team delivery example self-hash is invalid")
    integration_sha = integration.get("receipt_sha256")
    if integration_sha != unsigned_document_sha256(
        integration,
        "receipt_sha256",
    ):
        errors.append("team integration example self-hash is invalid")

    for label, value in (
        ("delivery", delivery),
        ("integration", integration),
    ):
        if value.get("team_run_id") != packet.get("team_run_id"):
            errors.append(f"team {label} example run binding is invalid")
        if value.get("packet_sha256") != packet_sha:
            errors.append(f"team {label} example packet binding is invalid")
    if integration.get("integration_owner") != packet.get(
        "integration_owner"
    ):
        errors.append("team integration example owner binding is invalid")

    baseline_snapshot = packet.get("baseline_snapshot")
    if isinstance(baseline_snapshot, dict):
        unsigned_snapshot = dict(baseline_snapshot)
        recorded_snapshot_sha = unsigned_snapshot.pop("sha256", None)
        if recorded_snapshot_sha != canonical_json_sha256(unsigned_snapshot):
            errors.append("team packet example baseline snapshot is invalid")
        if recorded_snapshot_sha != packet.get("baseline", {}).get(
            "workspace_sha256"
        ):
            errors.append(
                "team packet example baseline identity is inconsistent"
            )
    else:
        errors.append("team packet example baseline snapshot is missing")

    assignments = packet.get("assignments")
    assignment_ids = {
        item.get("id")
        for item in assignments
        if isinstance(item, dict)
    } if isinstance(assignments, list) else set()
    delivery_assignment = delivery.get("assignment_id")
    if delivery_assignment not in assignment_ids:
        errors.append("team delivery example assignment binding is invalid")
    delivery_results = integration.get("delivery_results")
    matching_results = [
        item
        for item in delivery_results
        if isinstance(item, dict)
        and item.get("assignment_id") == delivery_assignment
    ] if isinstance(delivery_results, list) else []
    if len(matching_results) != 1:
        errors.append(
            "team integration example must bind the delivery exactly once"
        )
    elif matching_results[0].get("delivery_receipt_sha256") != delivery_sha:
        errors.append(
            "team integration example delivery receipt binding is invalid"
        )

    canonical_snapshot = integration.get("canonical_snapshot")
    source = delivery.get("source")
    if not isinstance(canonical_snapshot, dict) or not isinstance(source, dict):
        errors.append("team integration example snapshot binding is missing")
    else:
        if canonical_snapshot.get(
            "pre_workspace_sha256"
        ) != packet.get("baseline", {}).get("workspace_sha256"):
            errors.append(
                "team integration example pre-snapshot binding is invalid"
            )
        if canonical_snapshot.get(
            "post_workspace_sha256"
        ) != source.get("final_workspace_sha256"):
            errors.append(
                "team integration example post-snapshot binding is invalid"
            )
        if canonical_snapshot.get("changed_paths") != delivery.get(
            "changed_paths"
        ):
            errors.append(
                "team integration example changed-path binding is invalid"
            )
    return errors


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        return {}
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def agent_metadata(text: str) -> dict[str, str | bool] | None:
    normalized = text.replace("\r\n", "\n")
    match = AGENT_METADATA_PATTERN.fullmatch(normalized)
    if not match:
        return None
    try:
        values: dict[str, str | bool] = {
            key: json.loads(match.group(key))
            for key in (
                "display_name",
                "short_description",
                "default_prompt",
            )
        }
        values["allow_implicit_invocation"] = json.loads(
            match.group("allow_implicit_invocation")
        )
    except json.JSONDecodeError:
        return None
    if not all(
        isinstance(values[key], str) and values[key].strip()
        for key in ("display_name", "short_description", "default_prompt")
    ):
        return None
    if not isinstance(values["allow_implicit_invocation"], bool):
        return None
    return values


def normalized_policy_text(text: str) -> str:
    return " ".join(text.lower().split())


def has_canonical_zero_spend_guard(text: str) -> bool:
    return CANONICAL_ZERO_SPEND_GUARD in normalized_policy_text(text)


def has_canonical_paid_data_guard(text: str) -> bool:
    return CANONICAL_PAID_DATA_GUARD in normalized_policy_text(text)


def is_secret_artifact(relative: Path) -> bool:
    name = relative.name.lower()
    return (
        name in SECRET_ARTIFACT_NAMES
        or name.startswith(".env.")
        or name.endswith(SECRET_ARTIFACT_SUFFIXES)
    )


def is_ignored_bytecode(relative: Path) -> bool:
    return (
        relative.suffix == ".pyc"
        and relative.parent.name == "__pycache__"
        and relative.parent.parent.as_posix() in EXPECTED_BYTECODE_PARENTS
    )


def is_allowed_package_file(relative: Path) -> bool:
    display = relative.as_posix()
    if display in EXPECTED_PACKAGE_FILES:
        return True
    if relative.name.startswith("."):
        return False
    suffixes = EXTENSIBLE_PACKAGE_RULES.get(relative.parent.as_posix())
    if suffixes and relative.name.endswith(suffixes):
        return True
    return (
        relative.parent == Path("tests")
        and relative.name.startswith("test_")
        and relative.suffix == ".py"
    )


def validate_package_shape() -> list[str]:
    errors: list[str] = []
    discovered_files: set[str] = set()

    for current, directory_names, file_names in os.walk(
        ROOT,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)
        current_relative = current_path.relative_to(ROOT)

        for name in sorted(directory_names):
            path = current_path / name
            relative = current_relative / name
            display = relative.as_posix()
            if path.is_symlink():
                errors.append(f"symlink is prohibited: {display}")
                directory_names.remove(name)
                continue
            if (
                display not in EXPECTED_PACKAGE_DIRECTORIES
                and not (
                    name == "__pycache__"
                    and current_relative.as_posix()
                    in EXPECTED_BYTECODE_PARENTS
                )
            ):
                errors.append(f"unexpected package directory: {display}")

        for name in sorted(file_names):
            path = current_path / name
            relative = current_relative / name
            display = relative.as_posix()
            if path.is_symlink():
                errors.append(f"symlink is prohibited: {display}")
                continue
            if not path.is_file():
                errors.append(f"unsupported package entry: {display}")
                continue
            if is_secret_artifact(relative):
                errors.append(f"secret-bearing artifact is prohibited: {display}")
            if is_ignored_bytecode(relative):
                continue
            if not is_allowed_package_file(relative):
                errors.append(f"unexpected package file: {display}")
                continue
            discovered_files.add(display)
            content = path.read_bytes()
            for label, pattern in OBVIOUS_SECRET_CONTENT_PATTERNS:
                if pattern.search(content):
                    errors.append(
                        f"obvious {label} content is prohibited: {display}"
                    )

    for missing in sorted(EXPECTED_PACKAGE_FILES - discovered_files):
        errors.append(f"missing intended package file: {missing}")
    return errors


def validate() -> list[str]:
    errors = validate_package_shape()
    discovered_skills = {
        path.parent.name
        for path in (ROOT / "skills").glob("*/SKILL.md")
        if path.is_file()
    }
    expected_skills = set(SKILLS)
    if discovered_skills != expected_skills:
        extra = sorted(discovered_skills - expected_skills)
        missing = sorted(expected_skills - discovered_skills)
        if extra:
            errors.append(
                "unexpected discoverable skills: " + ", ".join(extra)
            )
        if missing:
            errors.append(
                "missing discoverable skills: " + ", ".join(missing)
            )
    for name in SKILLS:
        skill_dir = ROOT / "skills" / name
        skill_file = skill_dir / "SKILL.md"
        agent_file = skill_dir / "agents" / "openai.yaml"
        if not skill_file.is_file():
            errors.append(f"missing {skill_file}")
            continue
        if not agent_file.is_file():
            errors.append(f"missing {agent_file}")
        else:
            agent_text = agent_file.read_text(encoding="utf-8")
            metadata = agent_metadata(agent_text)
            if metadata is None:
                errors.append(
                    f"{name}: agent metadata must use the exact interface and "
                    "policy structure"
                )
            else:
                raw_prompt = metadata["default_prompt"]
                assert isinstance(raw_prompt, str)
                prompt = normalized_policy_text(raw_prompt)
                if metadata["allow_implicit_invocation"] is not False:
                    errors.append(
                        f"{name}: implicit invocation must be disabled"
                    )
                word_count = len(raw_prompt.split())
                if word_count > 120:
                    errors.append(
                        f"{name}: agent prompt must stay under 120 words "
                        f"(found {word_count})"
                    )
                if len(re.findall(r"[.!?](?=\s|$)", raw_prompt)) > 3:
                    errors.append(
                        f"{name}: agent prompt must contain at most three "
                        "sentences"
                    )
                if f"${name}" not in raw_prompt:
                    errors.append(
                        f"{name}: agent prompt must name ${name}"
                    )
                other_skill_tokens = {
                    f"${candidate}"
                    for candidate in SKILLS
                    if candidate != name
                }
                present_other_tokens = sorted(
                    token for token in other_skill_tokens if token in raw_prompt
                )
                if present_other_tokens:
                    errors.append(
                        f"{name}: agent prompt must not activate another skill: "
                        + ", ".join(present_other_tokens)
                    )
                for phrase in EXPECTED_PROMPT_CONTRACTS[name]:
                    if phrase not in prompt:
                        errors.append(
                            f"{name}: agent prompt missing role contract "
                            f"{phrase!r}"
                        )
                for phrase in ("remote", "paid"):
                    if phrase not in prompt:
                        errors.append(
                            f"{name}: agent prompt missing concise authority "
                            f"marker {phrase!r}"
                        )
                for forbidden in (
                    "validate_installed",
                    "quantctl",
                    "goal_runtime",
                    "canonical_zero_spend_guard",
                ):
                    if forbidden in prompt:
                        errors.append(
                            f"{name}: agent prompt requires optional runtime "
                            f"detail {forbidden!r}"
                        )
                if has_canonical_zero_spend_guard(raw_prompt):
                    errors.append(
                        f"{name}: agent prompt duplicates canonical paid policy"
                    )
        text = skill_file.read_text(encoding="utf-8")
        metadata = frontmatter(text)
        if metadata.get("name") != name:
            errors.append(f"{name}: frontmatter name mismatch")
        if metadata.get("description") != EXPECTED_SKILL_DESCRIPTIONS[name]:
            errors.append(f"{name}: frontmatter description mismatch")
        if len(text.splitlines()) > 500:
            errors.append(f"{name}: SKILL.md exceeds 500 lines")
        normalized_skill = normalized_policy_text(text)
        for phrase in EXPECTED_SKILL_CONTRACTS[name]:
            if phrase not in normalized_skill:
                errors.append(
                    f"{name}: missing role contract {phrase!r}"
                )
        for reference in re.findall(
            r"`((?:references|templates)/[^`]+)`",
            text,
        ):
            if not (ROOT / "shared" / reference).is_file():
                errors.append(f"{name}: missing referenced shared/{reference}")
        for authority_reference in (
            "../quant-research-shared/core/authority.md",
            "../../shared/core/authority.md",
        ):
            if authority_reference not in text:
                errors.append(
                    f"{name}: missing layout-aware authority reference "
                    f"{authority_reference!r}"
                )
        source_authority = (
            skill_dir / "../../shared/core/authority.md"
        ).resolve()
        if source_authority != (ROOT / "shared/core/authority.md").resolve():
            errors.append(
                f"{name}: source authority reference resolves incorrectly"
            )
        elif not source_authority.is_file():
            errors.append(
                f"{name}: source authority reference is unreadable"
            )
        for phrase in ("remote", "paid"):
            if phrase not in normalized_skill:
                errors.append(
                    f"{name}: missing concise authority marker {phrase!r}"
                )
        if has_canonical_zero_spend_guard(text):
            errors.append(f"{name}: duplicates canonical paid policy")

    shared = ROOT / "shared"
    if (shared / "SKILL.md").exists():
        errors.append(
            "shared/SKILL.md is prohibited; the suite exposes exactly three skills"
        )
    required_shared = (
        "core/invariants.md",
        "core/authority.md",
        "core/evidence-semantics.md",
        "core/context-routing.md",
        "references/operating-principles.md",
        "references/cost-and-authority.md",
        "references/data-automation.md",
        "references/research-and-planning.md",
        "references/goal-and-subagents.md",
        "references/developer-runbook.md",
        "references/agent-orchestration.md",
        "references/durable-runtime.md",
        "references/web-design-source.md",
        "references/web-design-v2.4.0.md",
        "templates/quant-project.example.json",
        "templates/quant-project.schema.json",
        "templates/quant-project-v2.example.json",
        "schemas/quant-project-v2.schema.json",
        "templates/approved-plan.example.md",
        "templates/audit-report.example.md",
        "templates/goal-state.example.json",
        "templates/goal-state-v2.example.json",
        "schemas/goal-state-v2.schema.json",
        "templates/goal-ledger-state.example.json",
        "schemas/goal-ledger-state.schema.json",
        "templates/evidence-receipt.example.json",
        "templates/evidence-receipt-v3.example.json",
        "schemas/evidence-receipt-v3.schema.json",
        "templates/review-receipt.example.json",
        "schemas/review-receipt.schema.json",
        "templates/story-envelope.example.json",
        "templates/story-receipt.example.json",
        "schemas/story-envelope.schema.json",
        "schemas/story-receipt.schema.json",
        "templates/team-run-packet.example.json",
        "schemas/team-run-packet.schema.json",
        "templates/worker-delivery-receipt.example.json",
        "schemas/worker-delivery-receipt.schema.json",
        "templates/team-integration-receipt.example.json",
        "schemas/team-integration-receipt.schema.json",
        "capabilities/agent-team-execution.md",
        "scripts/project_inventory.py",
        "scripts/contract_guard.py",
        "scripts/github_preflight.sh",
        "scripts/capability_model.py",
        "scripts/quantctl.py",
        "scripts/goal_ledger.py",
        "scripts/goal_primitives.py",
        "scripts/goal_runtime.py",
        "scripts/team_protocol.py",
        "scripts/validate_installed.py",
        "scripts/validate_project.py",
        "scripts/validate_project_v2.py",
        "scripts/validate_evidence.py",
        "scripts/validate_evidence_v3.py",
    )
    for relative in required_shared:
        if not (shared / relative).is_file():
            errors.append(f"missing shared/{relative}")

    authority_path = shared / "core" / "authority.md"
    if authority_path.is_file():
        authority_text = authority_path.read_text(encoding="utf-8")
        normalized_authority = normalized_policy_text(authority_text)
        for guard in REQUIRED_PAID_ACTION_GUARDS:
            if guard not in normalized_authority:
                errors.append(
                    f"core/authority.md: missing paid guard {guard!r}"
                )
        if not has_canonical_zero_spend_guard(authority_text):
            errors.append(
                "core/authority.md: missing canonical zero-spend guard"
            )
        if not has_canonical_paid_data_guard(authority_text):
            errors.append(
                "core/authority.md: missing permanent paid-data guard"
            )

    policy_surfaces = (
        ROOT / "README.md",
        shared / "references" / "operating-principles.md",
        shared / "references" / "cost-and-authority.md",
    )
    for path in policy_surfaces:
        if not path.is_file():
            errors.append(
                f"missing policy surface {path.relative_to(ROOT)}"
            )
            continue
        raw_text = path.read_text(encoding="utf-8")
        normalized = normalized_policy_text(raw_text)
        if "shared/core/authority.md" not in raw_text:
            errors.append(
                f"{path.relative_to(ROOT)}: missing central authority reference"
            )
        if "paid" not in normalized:
            errors.append(
                f"{path.relative_to(ROOT)}: missing concise paid boundary"
            )
        if has_canonical_zero_spend_guard(raw_text):
            errors.append(
                f"{path.relative_to(ROOT)}: duplicates canonical paid policy"
            )

    for path in sorted(ROOT.rglob("*")):
        if path == authority_path or path.suffix not in {".md", ".yaml"}:
            continue
        if path.is_file() and has_canonical_zero_spend_guard(
            path.read_text(encoding="utf-8")
        ):
            errors.append(
                f"{path.relative_to(ROOT)}: canonical paid policy must live "
                "only in shared/core/authority.md"
            )

    for relative in (
        "templates/quant-project.example.json",
        "templates/quant-project.schema.json",
        "templates/quant-project-v2.example.json",
        "schemas/quant-project-v2.schema.json",
        "templates/goal-state.example.json",
        "templates/goal-state-v2.example.json",
        "schemas/goal-state-v2.schema.json",
        "templates/goal-ledger-state.example.json",
        "schemas/goal-ledger-state.schema.json",
        "templates/evidence-receipt.example.json",
        "templates/evidence-receipt-v3.example.json",
        "schemas/evidence-receipt-v3.schema.json",
        "templates/review-receipt.example.json",
        "schemas/review-receipt.schema.json",
        "templates/story-envelope.example.json",
        "templates/story-receipt.example.json",
        "schemas/story-envelope.schema.json",
        "schemas/story-receipt.schema.json",
        "templates/team-run-packet.example.json",
        "schemas/team-run-packet.schema.json",
        "templates/worker-delivery-receipt.example.json",
        "schemas/worker-delivery-receipt.schema.json",
        "templates/team-integration-receipt.example.json",
        "schemas/team-integration-receipt.schema.json",
    ):
        path = shared / relative
        if path.is_file():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{relative}: invalid JSON: {exc}")

    errors.extend(validate_team_template_examples(shared))

    project_example = shared / "templates" / "quant-project.example.json"
    if project_example.is_file():
        value = json.loads(project_example.read_text(encoding="utf-8"))
        if "data" not in value:
            errors.append("quant-project example is missing data registry")
        automation = value.get("automation", {})
        for field in (
            "pipeline_stages",
            "public_readback_urls",
            "cost_bounds",
        ):
            if field not in automation:
                errors.append(
                    f"quant-project example automation is missing {field}"
                )
        cost_bounds = automation.get("cost_bounds")
        if isinstance(cost_bounds, dict):
            for field in (
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
            ):
                if cost_bounds.get(field) is not False:
                    errors.append(
                        f"quant-project example cost_bounds.{field} "
                        "must be false"
                    )
            for field in ("spend_cap_enabled", "quota_hard_stop"):
                if cost_bounds.get(field) is not True:
                    errors.append(
                        f"quant-project example cost_bounds.{field} "
                        "must be true"
                    )
        release = value.get("release", {})
        if release.get("cost_policy") != (
            "zero-spend-unless-user-first-requests-specific-paid-action"
        ):
            errors.append("quant-project example has unsafe cost_policy")
        if release.get("paid_action_authority") is not None:
            errors.append(
                "quant-project manifest must not grant paid-action authority"
            )

    evidence_example = shared / "templates" / "evidence-receipt.example.json"
    if evidence_example.is_file():
        value = json.loads(evidence_example.read_text(encoding="utf-8"))
        if value.get("schema_version") != 2:
            errors.append("evidence receipt example must use schema_version 2")
        if "cost" not in value.get("required_gates", []):
            errors.append("evidence receipt example must require cost gate")
        cost = value.get("cost_authority")
        envelope = (
            cost.get("canonical_actions_envelope")
            if isinstance(cost, dict)
            else None
        )
        if not isinstance(envelope, dict) or envelope.get(
            "canonicalization"
        ) != "canonical-json-v1":
            errors.append(
                "evidence receipt example has incompatible cost canonicalization"
            )
        identity = value.get("automation_identity")
        for field in (
            "source_manifest_sha256",
            "source_manifest_size",
            "workflow_run_evidence_sha256",
            "workflow_started_at",
            "cost_preflight_completed_at",
            "entrypoint_started_at",
            "analysis_input_sha256",
            "analysis_input_size",
            "analysis_input_validation_sha256",
            "analysis_input_validation_size",
            "analysis_entrypoint_sha256",
            "analysis_request_manifest_sha256",
            "analysis_request_manifest_size",
            "result_manifest_sha256",
            "result_manifest_size",
            "result_artifact_sha256",
            "publication_state",
            "public_response_sha256",
            "frontend_response_sha256",
            "frontend_binding_evidence_sha256",
            "frontend_binding_evidence_size",
            "frontend_dom_snapshot_sha256",
            "frontend_dom_snapshot_size",
            "public_pointer_before_sha256",
            "public_pointer_before_size",
            "public_pointer_after_sha256",
            "public_pointer_after_size",
            "publication_ordering_evidence_sha256",
            "publication_ordering_evidence_size",
            "publication_ordering_test_output_sha256",
            "publication_ordering_test_output_size",
        ):
            if not isinstance(identity, dict) or field not in identity:
                errors.append(
                    f"evidence receipt automation_identity missing {field}"
                )
        release_identity = value.get("release_identity")
        for field in (
            "release_run_evidence_sha256",
            "job_id",
            "steps_completed",
            "cost_preflight_step_id",
            "cost_preflight_completed_at",
            "remote_write_step_id",
            "remote_write_started_at",
        ):
            if not isinstance(release_identity, dict) or field not in (
                release_identity
            ):
                errors.append(
                    f"evidence receipt release_identity missing {field}"
                )

    goal_example = shared / "templates" / "goal-state.example.json"
    if goal_example.is_file():
        value = json.loads(goal_example.read_text(encoding="utf-8"))
        outcomes = value.get("required_outcomes")
        if not isinstance(outcomes, dict) or set(outcomes) != {
            "automated_data_to_web",
            "remote_release",
        }:
            errors.append("goal state example must lock required outcomes")
        automation_state = value.get("automation_state")
        if not isinstance(automation_state, dict) or automation_state.get(
            "scope_status"
        ) != "explicitly-out-of-scope":
            errors.append(
                "goal state example must explicitly classify automation scope"
            )

    project_v2 = shared / "templates" / "quant-project-v2.example.json"
    if project_v2.is_file():
        value = json.loads(project_v2.read_text(encoding="utf-8"))
        if value.get("schema_version") != 2:
            errors.append("project v2 example must use schema_version 2")
        authority = value.get("authority")
        if not isinstance(authority, dict):
            errors.append("project v2 example must include authority")
        else:
            if authority.get("cost_policy") != (
                "zero-spend-unless-user-first-requests-specific-paid-action"
            ):
                errors.append("project v2 example has unsafe cost policy")
            if authority.get("paid_action_authority") is not None:
                errors.append("project v2 example cannot grant paid authority")
            if authority.get("paid_fallback_enabled") is not False:
                errors.append("project v2 paid fallback must be false")

    receipt_v3 = (
        shared / "templates" / "evidence-receipt-v3.example.json"
    )
    if receipt_v3.is_file():
        value = json.loads(receipt_v3.read_text(encoding="utf-8"))
        if value.get("schema_version") != 3:
            errors.append("evidence v3 example must use schema_version 3")
        if "cost" not in value.get("required_gates", []):
            errors.append("evidence v3 example must require cost gate")
        scope = value.get("scope")
        if not isinstance(scope, dict) or scope.get(
            "remote_actions"
        ) is not False:
            errors.append("evidence v3 example must default to local scope")

    goal_v2 = shared / "templates" / "goal-state-v2.example.json"
    if goal_v2.is_file():
        value = json.loads(goal_v2.read_text(encoding="utf-8"))
        if value.get("schema_version") != 2:
            errors.append("goal v2 example must use schema_version 2")
        forbidden = {
            "approval_gates",
            "cost_authority",
            "paid_action_authority",
        }
        present = sorted(forbidden & set(value))
        if present:
            errors.append(
                "goal v2 must not persist authority fields: "
                + ", ".join(present)
            )

    goal_ledger = (
        shared / "templates" / "goal-ledger-state.example.json"
    )
    if goal_ledger.is_file():
        value = json.loads(goal_ledger.read_text(encoding="utf-8"))
        if value.get("document_type") != "quant_goal_ledger_state":
            errors.append("goal ledger example has invalid document_type")
        if value.get("schema_version") != 1:
            errors.append("goal ledger example must use schema_version 1")
        policy = value.get("proof_policy")
        if not isinstance(policy, dict):
            errors.append("goal ledger example must include proof_policy")
        for forbidden in (
            "approval_gates",
            "cost_authority",
            "paid_action_authority",
            "secrets",
        ):
            if forbidden in value:
                errors.append(
                    f"goal ledger must not persist authority field: {forbidden}"
                )

    review_receipt = (
        shared / "templates" / "review-receipt.example.json"
    )
    if review_receipt.is_file():
        value = json.loads(review_receipt.read_text(encoding="utf-8"))
        if value.get("document_type") != "quant_review_receipt":
            errors.append("review receipt example has invalid document_type")
        if value.get("schema_version") != 1:
            errors.append("review receipt example must use schema_version 1")
        for field in (
            "plan_revision",
            "acceptance_revision",
            "acceptance_ids",
            "workspace_sha256",
            "receipt_sha256",
        ):
            if field not in value:
                errors.append(
                    f"review receipt example is missing {field}"
                )
        if (
            value.get("role") == "terminal_critic"
            and "evidence_candidate_sha256" not in value
        ):
            errors.append(
                "terminal review receipt example must bind the "
                "completion evidence candidate"
            )

    story_envelope = (
        shared / "templates" / "story-envelope.example.json"
    )
    if story_envelope.is_file():
        value = json.loads(story_envelope.read_text(encoding="utf-8"))
        if value.get("external_effects") != "none":
            errors.append("story envelope cannot grant external effects")
        if value.get("cost_class") != "no_billable_action":
            errors.append("story envelope cannot grant billable action")

    core_authority = shared / "core" / "authority.md"
    if core_authority.is_file() and not has_canonical_zero_spend_guard(
        core_authority.read_text(encoding="utf-8")
    ):
        errors.append("core/authority.md missing canonical zero-spend guard")

    python_files = {
        ROOT / relative
        for relative in EXPECTED_PACKAGE_FILES
        if relative.endswith(".py")
    }
    python_files.update((ROOT / "tests").glob("test_*.py"))
    for path in sorted(python_files):
        if not path.is_file():
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(ROOT)}: syntax error: {exc}")

    design = shared / "references" / "web-design-v2.4.0.md"
    if design.is_file() and sha256(design) != EXPECTED_WEB_DESIGN_SHA:
        errors.append("bundled web-design-v2.4.0.md SHA-256 mismatch")

    github_preflight = shared / "scripts" / "github_preflight.sh"
    if github_preflight.is_file():
        result = subprocess.run(
            ["bash", "-n", str(github_preflight)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            errors.append(
                "github_preflight.sh syntax error: " + result.stderr.strip()
            )
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("SUITE VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("SUITE VALIDATION PASSED")
    print("skills=" + ",".join(SKILLS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
