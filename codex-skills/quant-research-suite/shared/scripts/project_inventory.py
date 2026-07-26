#!/usr/bin/env python3
"""Produce a read-only, non-secret inventory for an arbitrary project."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


IGNORED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}

MANIFEST_NAMES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "pom.xml",
    "build.gradle",
    "Dockerfile",
    "docker-compose.yml",
    "vercel.json",
    "netlify.toml",
)
DEFAULT_MAX_DEPTH = 6


def run_git(root: Path, *args: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}
    output = result.stdout.strip()
    error = result.stderr.strip()
    return {
        "ok": result.returncode == 0,
        "value": output,
        "error": error if result.returncode else "",
    }


def sanitize_remote_result(result: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(result)
    value = sanitized.get("value")
    if isinstance(value, str):
        sanitized["value"] = re.sub(
            r"^(https?://)[^/@]+@",
            r"\1",
            value,
        )
    return sanitized


def scan_visible_files(
    root: Path,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> tuple[list[Path], dict[str, Any]]:
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1")
    rows: list[Path] = []
    ignored_directory_count = 0
    pruned_directory_count = 0
    deepest_included_depth = 0
    for current, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)
        relative_directory = current_path.relative_to(root)
        directory_depth = len(relative_directory.parts)

        visible_directories = []
        for name in sorted(directory_names):
            if name in IGNORED_PARTS:
                ignored_directory_count += 1
            else:
                visible_directories.append(name)
        directory_names[:] = visible_directories

        if directory_depth >= max_depth - 1:
            pruned_directory_count += len(directory_names)
            directory_names[:] = []

        for name in sorted(file_names):
            relative = (
                relative_directory / name
                if relative_directory.parts
                else Path(name)
            )
            if len(relative.parts) > max_depth:
                continue
            if any(part in IGNORED_PARTS for part in relative.parts):
                continue
            path = current_path / name
            if path.is_file():
                rows.append(relative)
                deepest_included_depth = max(
                    deepest_included_depth,
                    len(relative.parts),
                )

    ordered = sorted(rows, key=lambda item: item.as_posix())
    return ordered, {
        "max_depth": max_depth,
        "file_count": len(ordered),
        "deepest_included_depth": deepest_included_depth,
        "depth_truncated": pruned_directory_count > 0,
        "pruned_directory_count": pruned_directory_count,
        "ignored_directory_count": ignored_directory_count,
    }


def visible_files(root: Path, max_depth: int = DEFAULT_MAX_DEPTH) -> list[Path]:
    files, _ = scan_visible_files(root, max_depth=max_depth)
    return files


def upstream_status(root: Path) -> dict[str, Any]:
    upstream = run_git(
        root,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
    )
    status: dict[str, Any] = {
        "ok": False,
        "upstream": upstream.get("value", "") if upstream.get("ok") else "",
        "ahead": None,
        "behind": None,
        "error": upstream.get("error", "") if not upstream.get("ok") else "",
    }
    if not upstream.get("ok"):
        return status

    divergence = run_git(
        root,
        "rev-list",
        "--left-right",
        "--count",
        f"{upstream['value']}...HEAD",
    )
    if not divergence.get("ok"):
        status["error"] = divergence.get("error", "")
        return status
    parts = divergence.get("value", "").split()
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        status["error"] = "unexpected git rev-list output"
        return status
    behind, ahead = (int(part) for part in parts)
    status.update(
        {
            "ok": True,
            "ahead": ahead,
            "behind": behind,
            "error": "",
        }
    )
    return status


def matching(files: list[Path], predicate) -> list[str]:
    return [path.as_posix() for path in files if predicate(path)]


def workflow_hints(root: Path, workflows: list[str]) -> dict[str, Any]:
    hints: dict[str, Any] = {}
    for relative in workflows:
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            hints[relative] = {"read_error": str(exc)}
            continue
        cron = re.findall(
            r"""(?mx)^\s*-\s*cron\s*:\s*["']?([^"'#\n]+)""",
            text,
        )
        secret_names = sorted(
            set(re.findall(r"""secrets\.([A-Za-z_][A-Za-z0-9_]*)""", text))
        )
        hints[relative] = {
            "schedule_declared": bool(
                re.search(r"(?m)^\s*schedule\s*:", text)
            ),
            "cron_expressions": [value.strip() for value in cron],
            "manual_dispatch_declared": bool(
                re.search(r"(?m)^\s*workflow_dispatch\s*:", text)
            ),
            "concurrency_declared": bool(
                re.search(r"(?m)^\s*concurrency\s*:", text)
            ),
            "permissions_declared": bool(
                re.search(r"(?m)^\s*permissions\s*:", text)
            ),
            "secret_names": secret_names,
            "pages_publish_hint": (
                "actions/deploy-pages" in text
                or "peaceiris/actions-gh-pages" in text
                or "github-pages" in text
            ),
        }
    return hints


def contract_automation_summary(
    contract: dict[str, Any] | None,
) -> dict[str, Any]:
    value = contract or {}
    data = value.get("data") if isinstance(value.get("data"), dict) else {}
    automation = (
        value.get("automation")
        if isinstance(value.get("automation"), dict)
        else {}
    )
    sources = data.get("sources") if isinstance(data.get("sources"), list) else []
    schedules = (
        automation.get("schedules")
        if isinstance(automation.get("schedules"), list)
        else []
    )
    return {
        "source_ids": [
            item.get("id", "")
            for item in sources
            if isinstance(item, dict) and item.get("id")
        ],
        "required_source_ids": [
            item.get("id", "")
            for item in sources
            if isinstance(item, dict)
            and item.get("id")
            and item.get("role") == "required"
        ],
        "coherent_cutoff_policy_present": bool(
            data.get("coherent_cutoff_policy")
        ),
        "workflow_paths": automation.get("workflows", []),
        "schedule_ids": [
            item.get("id", "")
            for item in schedules
            if isinstance(item, dict) and item.get("id")
        ],
        "freshness_fields": automation.get("freshness_fields", []),
        "publication_path": automation.get("publication_path", ""),
        "public_readback_urls": automation.get("public_readback_urls", []),
        "last_good_policy_present": bool(
            automation.get("last_good_policy")
            or data.get("source_last_good_policy")
        ),
    }


def validate_contract(root: Path, manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.is_file():
        return {"checked": False, "valid": False, "errors": ["manifest missing"]}
    script = Path(__file__).resolve().with_name("validate_project.py")
    if not script.is_file():
        return {
            "checked": False,
            "valid": False,
            "errors": ["validate_project.py missing"],
        }
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--root",
                str(root),
                "--manifest",
                str(manifest_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"checked": True, "valid": False, "errors": [str(exc)]}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "checked": True,
            "valid": False,
            "errors": [result.stderr.strip() or "validator returned invalid output"],
        }
    return {
        "checked": True,
        "valid": bool(payload.get("valid")),
        "errors": payload.get("errors", []),
        "warnings": payload.get("warnings", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Project root")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Project root does not exist: {root}")

    files, scan = scan_visible_files(root)
    manifest_path = root / ".codex" / "quant-project.json"
    project_contract: dict[str, Any] | None = None
    contract_error = ""
    contract_json_valid = False
    if manifest_path.is_file():
        try:
            loaded_contract = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            contract_json_valid = True
            if isinstance(loaded_contract, dict):
                project_contract = loaded_contract
            else:
                contract_error = "manifest root must be an object"
        except (OSError, json.JSONDecodeError) as exc:
            contract_error = str(exc)

    workflow_files = matching(
        files,
        lambda p: len(p.parts) >= 3
        and p.parts[0:2] == (".github", "workflows")
        and p.suffix in {".yml", ".yaml"},
    )

    branch = run_git(root, "branch", "--show-current")
    project_section = (
        project_contract.get("project")
        if isinstance(project_contract, dict)
        and isinstance(project_contract.get("project"), dict)
        else {}
    )
    inventory = {
        "schema_version": 1,
        "root": str(root),
        "scan": scan,
        "git": {
            "top_level": run_git(root, "rev-parse", "--show-toplevel"),
            "branch": branch,
            "detached": bool(
                branch.get("ok") and not branch.get("value")
            ),
            "head": run_git(root, "rev-parse", "HEAD"),
            "status": run_git(root, "status", "--short", "--branch"),
            "remote_origin": sanitize_remote_result(
                run_git(root, "remote", "get-url", "origin")
            ),
            "remote_default_branch": run_git(
                root,
                "symbolic-ref",
                "--short",
                "refs/remotes/origin/HEAD",
            ),
            "tracking": upstream_status(root),
            "worktrees": run_git(root, "worktree", "list", "--porcelain"),
        },
        "project_contract": {
            "path": str(manifest_path),
            "present": manifest_path.is_file(),
            "valid_json": contract_json_valid,
            "valid_object": project_contract is not None,
            "project_id": project_section.get("id", ""),
            "error": contract_error,
            "semantic_validation": validate_contract(root, manifest_path),
            "automation": contract_automation_summary(project_contract),
        },
        "manifests": [
            name for name in MANIFEST_NAMES if (root / name).is_file()
        ],
        "source": {
            "python": matching(files, lambda p: p.suffix == ".py"),
            "typescript": matching(files, lambda p: p.suffix in {".ts", ".tsx"}),
            "javascript": matching(files, lambda p: p.suffix in {".js", ".mjs", ".jsx"}),
            "html": matching(files, lambda p: p.suffix == ".html"),
            "styles": matching(files, lambda p: p.suffix in {".css", ".scss", ".sass"}),
        },
        "data_and_contracts": matching(
            files,
            lambda p: p.suffix in {".json", ".csv", ".parquet", ".arrow"}
            or "schema" in p.name.lower()
            or "contract" in p.name.lower(),
        ),
        "tests": matching(
            files,
            lambda p: "test" in p.name.lower()
            or any(part in {"test", "tests", "__tests__"} for part in p.parts),
        ),
        "workflows": workflow_files,
        "workflow_hints": workflow_hints(root, workflow_files),
        "deployment": matching(
            files,
            lambda p: p.name
            in {
                "vercel.json",
                "netlify.toml",
                "Dockerfile",
                "docker-compose.yml",
                "CNAME",
                ".nojekyll",
            }
            or "deploy" in p.name.lower()
            or "pages" in p.name.lower(),
        ),
        "instructions": matching(
            files,
            lambda p: p.name
            in {
                "AGENTS.md",
                "README.md",
                "DESIGN.md",
                "web-design.md",
                "CONTRIBUTING.md",
            },
        ),
        "notes": [
            "This inventory is local and read-only.",
            "Workflow presence is not proof of a successful scheduled run.",
            "Workflow hints are static and do not prove default-branch enablement or live execution.",
            "Git upstream and divergence are local tracking state; this command does not fetch.",
            "The scan section reports whether the configured file-depth limit pruned directories.",
            "Public freshness and deployment require separate live verification.",
        ],
    }

    rendered = json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
