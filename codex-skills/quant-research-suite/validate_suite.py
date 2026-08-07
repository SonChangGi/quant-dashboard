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
EXPECTED_PACKAGE_FILES = frozenset(
    {
        ".gitignore",
        "README.md",
        "install.py",
        "validate_suite.py",
        "shared/references/cost-and-authority.md",
        "shared/references/data-automation.md",
        "shared/references/developer-runbook.md",
        "shared/references/goal-and-subagents.md",
        "shared/references/operating-principles.md",
        "shared/references/research-and-planning.md",
        "shared/references/web-design-source.md",
        "shared/references/web-design-v2.4.0.md",
        "shared/scripts/contract_guard.py",
        "shared/scripts/github_preflight.sh",
        "shared/scripts/project_inventory.py",
        "shared/scripts/validate_evidence.py",
        "shared/scripts/validate_installed.py",
        "shared/scripts/validate_project.py",
        "shared/templates/approved-plan.example.md",
        "shared/templates/evidence-receipt.example.json",
        "shared/templates/goal-state.example.json",
        "shared/templates/quant-project.example.json",
        "shared/templates/quant-project.schema.json",
        "skills/quant-developer/SKILL.md",
        "skills/quant-developer/agents/openai.yaml",
        "skills/quant-goal/SKILL.md",
        "skills/quant-goal/agents/openai.yaml",
        "skills/quant-plan/SKILL.md",
        "skills/quant-plan/agents/openai.yaml",
        "tests/test_install_provenance.py",
        "tests/test_package_shape.py",
        "tests/test_policy_guards.py",
        "tests/test_tools.py",
    }
)
EXPECTED_PACKAGE_DIRECTORIES = frozenset(
    parent.as_posix()
    for relative in EXPECTED_PACKAGE_FILES
    for parent in Path(relative).parents
    if parent != Path(".")
)
EXPECTED_BYTECODE_PARENTS = EXPECTED_PACKAGE_DIRECTORIES | {"."}
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
EXPECTED_WEB_DESIGN_SHA = (
    "08839e31be6e5136808969394c879f8ea3ade89bf5f4ab828f9d0d1f7e9d5ea8"
)
AGENT_METADATA_PATTERN = re.compile(
    r"\Ainterface:\n"
    r'  display_name: (?P<display_name>"(?:[^"\\\n]|\\.)*")\n'
    r'  short_description: (?P<short_description>"(?:[^"\\\n]|\\.)*")\n'
    r'  default_prompt: (?P<default_prompt>"(?:[^"\\\n]|\\.)*")\n?'
    r"\Z"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


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


def agent_metadata(text: str) -> dict[str, str] | None:
    normalized = text.replace("\r\n", "\n")
    match = AGENT_METADATA_PATTERN.fullmatch(normalized)
    if not match:
        return None
    try:
        values = {
            key: json.loads(match.group(key))
            for key in (
                "display_name",
                "short_description",
                "default_prompt",
            )
        }
    except json.JSONDecodeError:
        return None
    if not all(isinstance(value, str) and value.strip() for value in values.values()):
        return None
    return values


def normalized_policy_text(text: str) -> str:
    return " ".join(text.lower().split())


def has_canonical_zero_spend_guard(text: str) -> bool:
    return CANONICAL_ZERO_SPEND_GUARD in normalized_policy_text(text)


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
            if display not in EXPECTED_PACKAGE_FILES:
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
                    f"{name}: agent metadata must use the exact interface structure"
                )
            elif "paid action" not in metadata["default_prompt"].lower():
                errors.append(f"{name}: agent prompt missing paid-action guard")
            else:
                prompt = normalized_policy_text(metadata["default_prompt"])
                for guard in REQUIRED_PAID_ACTION_GUARDS:
                    if guard not in prompt:
                        errors.append(
                            f"{name}: agent prompt missing paid guard {guard!r}"
                        )
                if not has_canonical_zero_spend_guard(
                    metadata["default_prompt"]
                ):
                    errors.append(
                        f"{name}: agent prompt missing canonical zero-spend guard"
                    )
        text = skill_file.read_text(encoding="utf-8")
        metadata = frontmatter(text)
        if metadata.get("name") != name:
            errors.append(f"{name}: frontmatter name mismatch")
        if len(metadata.get("description", "")) < 80:
            errors.append(f"{name}: description is too short for reliable routing")
        if len(text.splitlines()) > 500:
            errors.append(f"{name}: SKILL.md exceeds 500 lines")
        for required_phrase in (
            "quant-research-shared",
            "project",
            "cost-and-authority.md",
            "data-automation.md",
        ):
            if required_phrase not in text:
                errors.append(f"{name}: missing required phrase {required_phrase!r}")
        for reference in re.findall(
            r"`((?:references|templates)/[^`]+)`",
            text,
        ):
            if not (ROOT / "shared" / reference).is_file():
                errors.append(f"{name}: missing referenced shared/{reference}")
        if "paid action" not in text.lower():
            errors.append(f"{name}: missing paid-action guard")
        normalized_skill = normalized_policy_text(text)
        for guard in REQUIRED_PAID_ACTION_GUARDS:
            if guard not in normalized_skill:
                errors.append(f"{name}: missing paid guard {guard!r}")
        if not has_canonical_zero_spend_guard(text):
            errors.append(f"{name}: missing canonical zero-spend guard")

    shared = ROOT / "shared"
    if (shared / "SKILL.md").exists():
        errors.append(
            "shared/SKILL.md is prohibited; the suite exposes exactly three skills"
        )
    required_shared = (
        "references/operating-principles.md",
        "references/cost-and-authority.md",
        "references/data-automation.md",
        "references/research-and-planning.md",
        "references/goal-and-subagents.md",
        "references/developer-runbook.md",
        "references/web-design-source.md",
        "references/web-design-v2.4.0.md",
        "templates/quant-project.example.json",
        "templates/quant-project.schema.json",
        "templates/approved-plan.example.md",
        "templates/goal-state.example.json",
        "templates/evidence-receipt.example.json",
        "scripts/project_inventory.py",
        "scripts/contract_guard.py",
        "scripts/github_preflight.sh",
        "scripts/validate_installed.py",
        "scripts/validate_project.py",
        "scripts/validate_evidence.py",
    )
    for relative in required_shared:
        if not (shared / relative).is_file():
            errors.append(f"missing shared/{relative}")

    for relative in (
        "references/operating-principles.md",
        "references/cost-and-authority.md",
        "../README.md",
    ):
        path = shared / relative
        if not path.is_file():
            errors.append(f"missing policy surface {relative}")
            continue
        raw_text = path.read_text(encoding="utf-8")
        text = normalized_policy_text(raw_text)
        for guard in REQUIRED_PAID_ACTION_GUARDS:
            if guard not in text:
                errors.append(f"{relative}: missing paid guard {guard!r}")
        if not has_canonical_zero_spend_guard(raw_text):
            errors.append(
                f"{relative}: missing canonical zero-spend guard"
            )

    for relative in (
        "templates/quant-project.example.json",
        "templates/quant-project.schema.json",
        "templates/goal-state.example.json",
        "templates/evidence-receipt.example.json",
    ):
        path = shared / relative
        if path.is_file():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{relative}: invalid JSON: {exc}")

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

    for relative in (
        "scripts/project_inventory.py",
        "scripts/contract_guard.py",
        "scripts/validate_installed.py",
        "scripts/validate_project.py",
        "scripts/validate_evidence.py",
        "../install.py",
    ):
        path = (
            (shared / relative).resolve()
            if not relative.startswith("..")
            else (ROOT / "install.py")
        )
        if not path.is_file():
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(ROOT)}: syntax error: {exc}")
    test_path = ROOT / "tests" / "test_tools.py"
    if test_path.is_file():
        try:
            compile(
                test_path.read_text(encoding="utf-8"),
                str(test_path),
                "exec",
            )
        except SyntaxError as exc:
            errors.append(f"tests/test_tools.py: syntax error: {exc}")

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
