#!/usr/bin/env python3
"""Snapshot and verify project-owned protected paths with SHA-256."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"Expected an object in {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def should_ignore(relative: str) -> bool:
    parts = Path(relative).parts
    return ".git" in parts or "__pycache__" in parts or "node_modules" in parts


def ensure_within_root(root: Path, path: Path, label: str) -> None:
    resolved_root = root.resolve()
    try:
        path.resolve().relative_to(resolved_root)
    except ValueError as exc:
        raise SystemExit(f"{label} escapes project root: {path}") from exc


def validate_pattern(pattern: str) -> None:
    path = Path(pattern)
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"Protected path must stay within root: {pattern}")


def files_for_pattern(root: Path, pattern: str) -> set[str]:
    validate_pattern(pattern)
    candidates: set[str] = set()
    for match in root.glob(pattern):
        ensure_within_root(root, match, "Protected match")
        if match.is_file():
            relative = match.relative_to(root).as_posix()
            if not should_ignore(relative):
                candidates.add(relative)
        elif match.is_dir():
            for nested in match.rglob("*"):
                if nested.is_file():
                    ensure_within_root(root, nested, "Protected nested match")
                    relative = nested.relative_to(root).as_posix()
                    if not should_ignore(relative):
                        candidates.add(relative)
    return candidates


def protected_files(root: Path, patterns: list[str]) -> dict[str, dict[str, Any]]:
    candidates: set[str] = set()
    for pattern in patterns:
        candidates.update(files_for_pattern(root, pattern))

    rows: dict[str, dict[str, Any]] = {}
    for relative in sorted(candidates):
        path = root / relative
        stat = path.stat()
        rows[relative] = {
            "sha256": sha256(path),
            "size": stat.st_size,
            "mode": oct(stat.st_mode & 0o777),
        }
    return rows


def manifest_patterns(manifest: dict[str, Any]) -> list[str]:
    protected = manifest.get("protected")
    if not isinstance(protected, dict):
        raise SystemExit("Manifest is missing protected object")
    patterns = protected.get("paths")
    if not isinstance(patterns, list) or not patterns:
        raise SystemExit("Manifest protected.paths must be a non-empty array")
    if not all(isinstance(item, str) and item.strip() for item in patterns):
        raise SystemExit("Each protected path must be a non-empty string")
    return patterns


def snapshot(root: Path, manifest_path: Path) -> dict[str, Any]:
    ensure_within_root(root, manifest_path, "Manifest")
    manifest = load_json(manifest_path)
    patterns = manifest_patterns(manifest)
    unmatched = [
        pattern for pattern in patterns if not files_for_pattern(root, pattern)
    ]
    if unmatched:
        raise SystemExit(
            "Protected patterns matched no files: " + ", ".join(unmatched)
        )
    return {
        "schema_version": 2,
        "project_id": manifest.get("project", {}).get("id", ""),
        "root": str(root.resolve()),
        "git_head": git_value(root, "rev-parse", "HEAD"),
        "manifest_sha256": sha256(manifest_path),
        "patterns": patterns,
        "files": protected_files(root, patterns),
    }


def verify(
    root: Path,
    baseline_path: Path,
    manifest_path: Path,
) -> tuple[dict[str, Any], bool]:
    baseline = load_json(baseline_path)
    if baseline.get("schema_version") != 2:
        raise SystemExit("Baseline schema_version must equal 2")
    if baseline.get("root") != str(root.resolve()):
        raise SystemExit("Baseline root does not match current project root")
    ensure_within_root(root, manifest_path, "Manifest")
    manifest = load_json(manifest_path)
    if baseline.get("manifest_sha256") != sha256(manifest_path):
        raise SystemExit("Project manifest changed since contract snapshot")
    if baseline.get("project_id") != manifest.get("project", {}).get("id", ""):
        raise SystemExit("Baseline project_id does not match manifest")
    patterns = baseline.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        raise SystemExit("Baseline has no protected patterns")
    before = baseline.get("files")
    if not isinstance(before, dict) or not before:
        raise SystemExit("Baseline has no protected files")
    after = protected_files(root, patterns)

    before_names = set(before)
    after_names = set(after)
    added = sorted(after_names - before_names)
    removed = sorted(before_names - after_names)
    changed = sorted(
        name
        for name in before_names & after_names
        if before[name].get("sha256") != after[name].get("sha256")
        or before[name].get("mode") != after[name].get("mode")
    )

    result = {
        "schema_version": 2,
        "project_id": baseline.get("project_id", ""),
        "baseline_head": baseline.get("git_head", ""),
        "current_head": git_value(root, "rev-parse", "HEAD"),
        "ok": not (added or removed or changed),
        "added": added,
        "removed": removed,
        "changed": changed,
        "checked_files": len(after),
    }
    return result, bool(result["ok"])


def write_json(value: dict[str, Any], output: str | None) -> None:
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if output:
        path = Path(output).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--root", required=True)
    snapshot_parser.add_argument("--manifest", required=True)
    snapshot_parser.add_argument("--output", required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--root", required=True)
    verify_parser.add_argument("--baseline", required=True)
    verify_parser.add_argument("--manifest", required=True)
    verify_parser.add_argument("--output")

    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Project root does not exist: {root}")

    if args.command == "snapshot":
        value = snapshot(root, Path(args.manifest).expanduser().resolve())
        write_json(value, args.output)
        return 0

    value, ok = verify(
        root,
        Path(args.baseline).expanduser().resolve(),
        Path(args.manifest).expanduser().resolve(),
    )
    write_json(value, args.output)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
