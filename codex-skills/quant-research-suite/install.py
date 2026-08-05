#!/usr/bin/env python3
"""Install the validated suite into a Codex user skills directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent
CANONICAL_BASE_SHARED_FILES = runpy.run_path(
    str(ROOT / "shared" / "scripts" / "validate_installed.py")
)["BASE_SHARED_FILES"]
INSTALL_ITEMS = {
    "quant-plan": ROOT / "skills" / "quant-plan",
    "quant-goal": ROOT / "skills" / "quant-goal",
    "quant-developer": ROOT / "skills" / "quant-developer",
    "quant-research-shared": ROOT / "shared",
}
BASE_SHARED_FILES = tuple(sorted(CANONICAL_BASE_SHARED_FILES))
INSTALL_MANIFEST_SCHEMA_VERSION = 3
CANONICALIZATION = "canonical-json-v1"
FULL_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
BASE_TEST_TARGETS = (
    "tests.test_free_data_policy",
    "tests.test_generic_skill_contracts",
    "tests.test_install_provenance",
    (
        "tests.test_installed_runtime_smoke.InstalledRuntimeSmokeTests."
        "test_default_install_contains_only_lean_shared_runtime"
    ),
    (
        "tests.test_installed_runtime_smoke.InstalledRuntimeSmokeTests."
        "test_base_update_removes_previous_compatibility_overlay"
    ),
    (
        "tests.test_installed_runtime_smoke.InstalledRuntimeSmokeTests."
        "test_installed_base_recovery_helper_round_trip_from_unrelated_cwd"
    ),
    "tests.test_package_shape",
    "tests.test_policy_guards",
    "tests.test_recovery_checkpoint",
    "tests.test_skill_routing",
)


def tree_hashes(root: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
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
        rows[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return rows


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def suite_content_sha256(items: dict[str, dict[str, str]]) -> str:
    return hashlib.sha256(canonical_json_bytes(items)).hexdigest()


def sanitize_git_origin(value: str | None) -> str | None:
    if value is None:
        return None
    origin = value.strip()
    if not origin:
        return None
    if "://" in origin:
        parsed = urlsplit(origin)
        hostname = parsed.hostname
        if hostname is None:
            if parsed.netloc:
                return None
            return urlunsplit((parsed.scheme, "", parsed.path, "", ""))
        host = f"[{hostname}]" if ":" in hostname else hostname
        try:
            port = parsed.port
        except ValueError:
            return None
        if port is not None:
            host = f"{host}:{port}"
        return urlunsplit((parsed.scheme, host, parsed.path, "", ""))
    scp_like = re.fullmatch(r"([^@/\s]+)@([^:\s]+):(.+)", origin)
    if scp_like:
        return f"{scp_like.group(2)}:{scp_like.group(3)}"
    return origin.split("#", 1)[0].split("?", 1)[0]


def git_output(root: Path, *args: str) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return 127, ""
    return result.returncode, result.stdout.strip()


def capture_source_git_provenance(root: Path) -> dict[str, Any]:
    captured_at = (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00",
            "Z",
        )
    )
    unavailable = {
        "available": False,
        "origin": None,
        "branch": None,
        "commit": None,
        "tree": None,
        "dirty": None,
        "captured_at": captured_at,
    }
    root_status, repository_root = git_output(root, "rev-parse", "--show-toplevel")
    if root_status or not repository_root:
        return unavailable
    repository = Path(repository_root)
    commit_status, commit = git_output(repository, "rev-parse", "HEAD")
    tree_status, tree = git_output(repository, "rev-parse", "HEAD^{tree}")
    dirty_status, dirty_output = git_output(
        repository,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if (
        commit_status
        or tree_status
        or dirty_status
        or not FULL_GIT_SHA.fullmatch(commit)
        or not FULL_GIT_SHA.fullmatch(tree)
    ):
        return unavailable
    branch_status, branch = git_output(
        repository,
        "symbolic-ref",
        "--quiet",
        "--short",
        "HEAD",
    )
    origin_status, origin = git_output(
        repository,
        "config",
        "--get",
        "remote.origin.url",
    )
    return {
        "available": True,
        "origin": sanitize_git_origin(origin if origin_status == 0 else None),
        "branch": branch if branch_status == 0 and branch else None,
        "commit": commit,
        "tree": tree,
        "dirty": bool(dirty_output),
        "captured_at": captured_at,
    }


def require_clean_source(provenance: dict[str, Any]) -> None:
    if provenance.get("available") is not True:
        raise SystemExit(
            "--require-clean-source refused installation because source Git "
            "provenance is unavailable"
        )
    if provenance.get("dirty") is not False:
        raise SystemExit(
            "--require-clean-source refused installation from a dirty source"
        )


def install_manifest(
    staging_root: Path,
    source_git: dict[str, Any],
    install_profile: str,
) -> dict[str, Any]:
    items = {
        name: tree_hashes(staging_root / name)
        for name in INSTALL_ITEMS
    }
    return {
        "schema_version": INSTALL_MANIFEST_SCHEMA_VERSION,
        "install_profile": install_profile,
        "canonicalization": CANONICALIZATION,
        "suite_content_sha256": suite_content_sha256(items),
        "source_git": source_git,
        "items": items,
    }


def stage_shared(
    staging_root: Path,
    *,
    include_legacy: bool,
) -> None:
    source = INSTALL_ITEMS["quant-research-shared"]
    destination = staging_root / "quant-research-shared"
    if include_legacy:
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "install-manifest.json",
            ),
        )
        return

    destination.mkdir(parents=True)
    for relative_value in BASE_SHARED_FILES:
        relative = Path(relative_value)
        source_file = source / relative
        if not source_file.is_file():
            raise RuntimeError(f"Missing base shared resource: {relative_value}")
        destination_file = destination / relative
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination_file)


def verify_installed(
    target: Path,
    expected_items: dict[str, dict[str, str]],
) -> None:
    mismatches = [
        name
        for name in INSTALL_ITEMS
        if expected_items.get(name) != tree_hashes(target / name)
    ]
    if mismatches:
        raise RuntimeError(
            "Installed content hash mismatch: " + ", ".join(mismatches)
        )
    result = subprocess.run(
        [
            sys.executable,
            str(
                target
                / "quant-research-shared"
                / "scripts"
                / "validate_installed.py"
            ),
        ],
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Installed runtime integrity validation failed")


def validate_source(*, run_tests: bool, include_legacy: bool) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "validate_suite.py")],
        check=False,
    )
    if result.returncode:
        raise SystemExit("Refusing to install an invalid skill suite")
    if run_tests:
        test_command = (
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(ROOT / "tests"),
                "-v",
            ]
            if include_legacy
            else [
                sys.executable,
                "-m",
                "unittest",
                *BASE_TEST_TARGETS,
                "-v",
            ]
        )
        result = subprocess.run(
            test_command,
            check=False,
            cwd=ROOT,
        )
        if result.returncode:
            raise SystemExit("Refusing to install a skill suite with failed tests")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        default=str(Path.home() / ".codex" / "skills"),
        help="Codex skills directory",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Back up and replace existing suite directories",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip unit tests; static suite validation still runs",
    )
    parser.add_argument(
        "--require-clean-source",
        action="store_true",
        help=(
            "Fail closed unless source Git provenance is available and the "
            "repository is clean"
        ),
    )
    parser.add_argument(
        "--include-legacy",
        action="store_true",
        help=(
            "Overlay the preserved manifest, ledger, receipt, schema, and "
            "team compatibility resources at their established shared paths"
        ),
    )
    args = parser.parse_args()

    if args.skip_tests and not args.dry_run:
        raise SystemExit("--skip-tests is permitted only with --dry-run")
    install_profile = "compat" if args.include_legacy else "base"
    validate_source(
        run_tests=not args.skip_tests,
        include_legacy=args.include_legacy,
    )
    source_git = capture_source_git_provenance(ROOT)
    if args.require_clean_source:
        require_clean_source(source_git)
    target = Path(args.target).expanduser().resolve()
    existing = [name for name in INSTALL_ITEMS if (target / name).exists()]
    if existing and not args.update:
        raise SystemExit(
            "Existing targets found; rerun with --update after review: "
            + ", ".join(existing)
        )

    if args.dry_run:
        print(f"would install profile {install_profile}")
        for name, source in INSTALL_ITEMS.items():
            suffix = (
                " (lean shared selection)"
                if name == "quant-research-shared" and not args.include_legacy
                else ""
            )
            print(f"would install {source} -> {target / name}{suffix}")
        return 0

    target.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    staging_root = Path(tempfile.mkdtemp(prefix=".quant-skills-", dir=target))
    backup_root: Path | None = None
    backups: list[tuple[Path, Path, Path]] = []
    installed: list[Path] = []

    try:
        for name, source in INSTALL_ITEMS.items():
            if name == "quant-research-shared":
                continue
            shutil.copytree(
                source,
                staging_root / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        stage_shared(staging_root, include_legacy=args.include_legacy)
        manifest_value = install_manifest(
            staging_root,
            source_git,
            install_profile,
        )
        (
            staging_root
            / "quant-research-shared"
            / "install-manifest.json"
        ).write_text(
            json.dumps(
                manifest_value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        for name in INSTALL_ITEMS:
            destination = target / name
            staged = staging_root / name
            if destination.exists():
                if backup_root is None:
                    backup_parent = target.parent / "skill-backups"
                    backup_parent.mkdir(parents=True, exist_ok=True)
                    backup_root = Path(
                        tempfile.mkdtemp(
                            prefix=f"quant-research-suite-{timestamp}-",
                            dir=backup_parent,
                        )
                    )
                backup = backup_root / name
                destination.rename(backup)
                marker = target / f".{name}.backup-pointer-{backup_root.name}"
                backups.append((destination, backup, marker))
                marker.write_text(str(backup) + "\n", encoding="utf-8")
            staged.rename(destination)
            installed.append(destination)
            print(f"installed {destination}")
        verify_installed(target, manifest_value["items"])
    except Exception as exc:
        rollback_errors: list[str] = []
        for destination in reversed(installed):
            if not destination.exists():
                continue
            failed = staging_root / f".failed-{destination.name}"
            try:
                destination.rename(failed)
            except OSError as rollback_exc:
                rollback_errors.append(
                    f"remove new {destination}: {rollback_exc}"
                )
        for destination, backup, marker in reversed(backups):
            if backup.exists() and not destination.exists():
                try:
                    backup.rename(destination)
                except OSError as rollback_exc:
                    rollback_errors.append(
                        f"restore {destination}: {rollback_exc}"
                    )
            if marker.exists():
                try:
                    marker.unlink()
                except OSError as rollback_exc:
                    rollback_errors.append(
                        f"remove backup pointer {marker}: {rollback_exc}"
                    )
        if backup_root is not None and backup_root.exists():
            try:
                backup_root.rmdir()
            except OSError as rollback_exc:
                rollback_errors.append(
                    f"remove empty backup directory {backup_root}: {rollback_exc}"
                )
        if rollback_errors:
            raise RuntimeError(
                "Install failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from exc
        raise
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)
    for _, backup, marker in backups:
        print(f"backup retained {backup}")
        print(f"backup pointer {marker}")
    print("installed suite hash verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
