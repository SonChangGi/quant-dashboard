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
