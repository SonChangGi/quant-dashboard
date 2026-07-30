#!/usr/bin/env python3
"""Shared durable-goal filesystem, hashing, and workspace primitives.

This module contains mechanics that are independent of the legacy Goal CLI and
its schema. Callers retain ownership of lifecycle, event vocabulary, receipt
validation, and user-facing policy.
"""

from __future__ import annotations

import fcntl
import fnmatch
import hashlib
import json
import os
import stat
import subprocess
import tempfile
from collections.abc import Callable, Collection, Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit, urlunsplit


GENESIS = "0" * 64
DEFAULT_CORE_STATE_ARTIFACTS = (
    ".lock",
    "goal-state.json",
    "ledger.jsonl",
    "pending-event.json",
)


def canonical_bytes(value: Any) -> bytes:
    """Return the suite's canonical UTF-8 JSON representation."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    """Hash one value using the suite's canonical JSON representation."""

    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique_json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    """Build a JSON object while rejecting ambiguous duplicate keys."""

    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def strict_json(path: Path) -> dict[str, Any]:
    """Read a finite-JSON object from ``path``."""

    def reject(value: str) -> None:
        raise ValueError(f"non-finite JSON value is prohibited: {value}")

    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject,
        object_pairs_hook=unique_json_object,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} root must be an object")
    return value


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def sanitize_origin(value: str) -> str:
    value = value.strip()
    if "://" not in value:
        return value.split("?", 1)[0].split("#", 1)[0]
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port is not None:
        host = f"{host}:{port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def git_value(root: Path, *args: str) -> str | None:
    completed = git(root, *args)
    if completed.returncode:
        return None
    return completed.stdout.strip()


def project_binding(root: Path) -> dict[str, Any]:
    """Bind a project to its real path, Git common dir, and sanitized origin."""

    root = root.resolve()
    inside = git_value(root, "rev-parse", "--is-inside-work-tree")
    git_common = (
        git_value(
            root,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        )
        if inside == "true"
        else None
    )
    origin = (
        sanitize_origin(git_value(root, "remote", "get-url", "origin") or "")
        if inside == "true"
        else ""
    )
    identity = {
        "root_realpath": str(root),
        "git_common_dir_realpath": git_common,
        "origin_fingerprint_sha256": (
            hashlib.sha256(origin.encode("utf-8")).hexdigest()
            if origin
            else None
        ),
    }
    return {
        **identity,
        "identity_sha256": digest(identity),
    }


def portable_relative(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        bool(value)
        and bool(path.parts)
        and not path.is_absolute()
        and ".." not in path.parts
        and value == path.as_posix()
    )


def scope_pattern_selects_git_metadata(pattern: str) -> bool:
    """Return whether a non-generic glob segment can select ``.git``.

    Generic ``*`` and ``**`` scopes may describe a whole project, but Git
    metadata remains an implicit reserved exclusion. More specific wildcard
    spellings such as ``.git*`` or ``[.]git`` are treated as explicit attempts
    to select that reserved namespace.
    """

    if not portable_relative(pattern):
        return False
    return any(
        segment.casefold() not in {"*", "**"}
        and fnmatch.fnmatchcase(".git", segment.casefold())
        for segment in PurePosixPath(pattern).parts
    )


def _casefold_segment_glob_matches(path: str, pattern: str) -> bool:
    path_segments = tuple(
        segment.casefold() for segment in path.rstrip("/").split("/")
    )
    pattern_segments = tuple(
        segment.casefold() for segment in pattern.rstrip("/").split("/")
    )
    memo: dict[tuple[int, int], bool] = {}

    def visit(pattern_index: int, path_index: int) -> bool:
        key = (pattern_index, path_index)
        if key in memo:
            return memo[key]
        if pattern_index == len(pattern_segments):
            result = path_index == len(path_segments)
        elif pattern_segments[pattern_index] == "**":
            result = visit(pattern_index + 1, path_index) or (
                path_index < len(path_segments)
                and visit(pattern_index, path_index + 1)
            )
        else:
            result = (
                path_index < len(path_segments)
                and fnmatch.fnmatchcase(
                    path_segments[path_index],
                    pattern_segments[pattern_index],
                )
                and visit(pattern_index + 1, path_index + 1)
            )
        memo[key] = result
        return result

    return visit(0, 0)


def casefold_glob(root: Path, pattern: str) -> list[Path]:
    """Expand a project glob conservatively across filesystem case modes."""

    try:
        return list(root.glob(pattern, case_sensitive=False))
    except TypeError:
        candidates: list[Path] = []
        for current, directories, files in os.walk(
            root, topdown=True, followlinks=False
        ):
            current_path = Path(current)
            retained: list[str] = []
            for name in sorted(directories):
                candidate = current_path / name
                candidates.append(candidate)
                if (
                    not candidate.is_symlink()
                    and name.casefold() != ".git"
                ):
                    retained.append(name)
            directories[:] = retained
            candidates.extend(
                current_path / name for name in sorted(files)
            )
        return [
            candidate
            for candidate in candidates
            if _casefold_segment_glob_matches(
                candidate.relative_to(root).as_posix(),
                pattern,
            )
        ]


def path_state(
    root: Path,
    relative: str,
    *,
    snapshot_version: int = 1,
) -> dict[str, Any]:
    path = root / relative
    if snapshot_version not in {1, 2}:
        raise ValueError("workspace snapshot version must be 1 or 2")
    mode = None
    if snapshot_version == 2 and (path.exists() or path.is_symlink()):
        mode = stat.S_IMODE(path.lstat().st_mode)
    if path.is_symlink():
        value = {
            "kind": "symlink",
            "target": os.readlink(path),
        }
        return {**value, "mode": mode} if snapshot_version == 2 else value
    if path.is_file():
        value = {
            "kind": "file",
            "sha256": file_digest(path),
            "size": path.stat().st_size,
        }
        return {**value, "mode": mode} if snapshot_version == 2 else value
    if snapshot_version == 2 and path.is_dir():
        return {"kind": "directory", "mode": mode}
    if path.exists():
        value = {"kind": "other"}
        return {**value, "mode": mode} if snapshot_version == 2 else value
    return {"kind": "missing"}


def non_git_snapshot(
    root: Path,
    excluded: Path | None,
    *,
    snapshot_version: int = 1,
) -> dict[str, Any]:
    if snapshot_version not in {1, 2}:
        raise ValueError("workspace snapshot version must be 1 or 2")
    paths: dict[str, Any] = {}
    for current, directories, files in os.walk(
        root, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        if snapshot_version == 1:
            directories[:] = sorted(
                name
                for name in directories
                if name.casefold() not in {
                    ".git",
                    "__pycache__",
                    "node_modules",
                }
                and (
                    excluded is None
                    or (current_path / name).resolve() != excluded
                )
            )
            for name in sorted(files):
                path = current_path / name
                if excluded is not None:
                    try:
                        path.resolve().relative_to(excluded)
                        continue
                    except ValueError:
                        pass
                relative = path.relative_to(root).as_posix()
                paths[relative] = path_state(root, relative)
            continue
        retained_directories: list[str] = []
        for name in sorted(directories):
            if name.casefold() in {".git", "__pycache__", "node_modules"}:
                continue
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                paths[relative] = path_state(
                    root, relative, snapshot_version=2
                )
                continue
            if excluded is not None and path.resolve() == excluded:
                continue
            paths[relative] = path_state(
                root, relative, snapshot_version=2
            )
            retained_directories.append(name)
        directories[:] = retained_directories
        for name in sorted(files):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                paths[relative] = path_state(
                    root, relative, snapshot_version=2
                )
                continue
            if excluded is not None:
                try:
                    path.resolve().relative_to(excluded)
                    continue
                except ValueError:
                    pass
            paths[relative] = path_state(
                root, relative, snapshot_version=2
            )
    body = {
        "kind": "directory",
        "head": None,
        "branch": None,
        "diff_sha256": None,
        "paths": paths,
    }
    if snapshot_version == 2:
        body["snapshot_version"] = 2
    return {**body, "sha256": digest(body)}


def protected_path_snapshot(
    root: Path,
    patterns: list[str],
    excluded: Path | None,
    *,
    snapshot_version: int = 1,
) -> dict[str, Any]:
    """Capture protected paths even when Git intentionally ignores them."""

    root = root.resolve()
    excluded_relative: str | None = None
    if excluded is not None:
        try:
            excluded_relative = (
                excluded.resolve(strict=False)
                .relative_to(root)
                .as_posix()
            )
        except ValueError:
            excluded_relative = None
    captured: dict[str, Any] = {}
    for pattern in sorted(set(patterns)):
        if not portable_relative(pattern):
            raise ValueError(
                f"protected pattern must stay within project root: {pattern}"
            )
        if scope_pattern_selects_git_metadata(pattern):
            raise ValueError(
                f"protected pattern selects Git metadata: {pattern}"
            )
        if excluded_relative is not None and (
            pattern == excluded_relative
            or pattern.startswith(excluded_relative + "/")
        ):
            raise ValueError(
                f"protected pattern selects goal state: {pattern}"
            )
        matches_for_pattern = casefold_glob(root, pattern)
        if not matches_for_pattern and not any(
            character in pattern for character in "*?["
        ):
            matches_for_pattern = [root / pattern]
        captured_for_pattern = 0
        selected_reserved_path = False
        for path in matches_for_pattern:
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError as exc:
                raise ValueError(
                    f"protected pattern escaped project root: {pattern}"
                ) from exc
            if relative == ".":
                continue
            if not portable_relative(relative):
                continue
            if ".git" in {
                segment.casefold()
                for segment in PurePosixPath(relative).parts
            }:
                selected_reserved_path = True
                continue
            if path != root:
                ancestor = path.parent
                while ancestor != root:
                    if ancestor.is_symlink():
                        raise ValueError(
                            "protected pattern traverses project symbolic link: "
                            f"{relative}"
                        )
                    ancestor = ancestor.parent
            if excluded is not None:
                try:
                    path.resolve(strict=False).relative_to(
                        excluded.resolve(strict=False)
                    )
                    selected_reserved_path = True
                    continue
                except ValueError:
                    pass
            captured[relative] = path_state(
                root,
                relative,
                snapshot_version=snapshot_version,
            )
            captured_for_pattern += 1
        if (
            selected_reserved_path
            and captured_for_pattern == 0
            and pattern not in {"*", "**", "**/*"}
        ):
            raise ValueError(
                "protected pattern selects only reserved project metadata: "
                f"{pattern}"
            )
    return dict(sorted(captured.items()))


def workspace_snapshot(
    root: Path,
    state_dir: Path | None = None,
    protected_patterns: list[str] | None = None,
    *,
    snapshot_version: int = 1,
) -> dict[str, Any]:
    """Capture a deterministic Git or directory workspace identity."""

    if snapshot_version not in {1, 2}:
        raise ValueError("workspace snapshot version must be 1 or 2")
    root = root.resolve()
    protected = protected_path_snapshot(
        root,
        protected_patterns or [],
        state_dir,
        snapshot_version=snapshot_version,
    )
    if git_value(root, "rev-parse", "--is-inside-work-tree") != "true":
        snapshot = non_git_snapshot(
            root,
            state_dir,
            snapshot_version=snapshot_version,
        )
        body = {
            key: value for key, value in snapshot.items() if key != "sha256"
        }
        body["protected_patterns"] = sorted(set(protected_patterns or []))
        body["protected_paths"] = protected
        return {**body, "sha256": digest(body)}
    head = git_value(root, "rev-parse", "HEAD")
    baseline_args = ("HEAD",) if head is not None else ()
    staged_names = git(
        root, "diff", "--name-only", "-z", "--cached", *baseline_args
    )
    unstaged_names = git(root, "diff", "--name-only", "-z")
    untracked_names = git(
        root, "ls-files", "--others", "--exclude-standard", "-z"
    )
    for completed in (staged_names, unstaged_names, untracked_names):
        if completed.returncode:
            raise ValueError(
                completed.stderr.strip() or "git path scan failed"
            )
    changed = sorted(
        {
            value
            for completed in (
                staged_names,
                unstaged_names,
                untracked_names,
            )
            for value in completed.stdout.split("\0")
            if value and portable_relative(value)
        }
    )
    staged = git(root, "diff", "--binary", "--cached", *baseline_args)
    unstaged = git(root, "diff", "--binary")
    if staged.returncode or unstaged.returncode:
        raise ValueError(
            staged.stderr.strip()
            or unstaged.stderr.strip()
            or "git diff failed"
        )
    diff_bytes = (staged.stdout + unstaged.stdout).encode("utf-8")
    body = {
        "kind": "git",
        "head": head,
        "branch": git_value(root, "branch", "--show-current"),
        "diff_sha256": hashlib.sha256(diff_bytes).hexdigest(),
        "paths": {
            relative: path_state(
                root,
                relative,
                snapshot_version=snapshot_version,
            )
            for relative in changed
        },
        "protected_patterns": sorted(set(protected_patterns or [])),
        "protected_paths": protected,
    }
    if snapshot_version == 2:
        body["snapshot_version"] = 2
    return {**body, "sha256": digest(body)}


def verify_workspace_snapshot(snapshot: Any) -> bool:
    if not isinstance(snapshot, dict):
        return False
    recorded = snapshot.get("sha256")
    unsigned = dict(snapshot)
    unsigned.pop("sha256", None)
    return isinstance(recorded, str) and recorded == digest(unsigned)


def snapshot_paths(snapshot: dict[str, Any]) -> dict[str, Any]:
    paths = snapshot.get("paths")
    protected = snapshot.get("protected_paths")
    merged = dict(paths) if isinstance(paths, dict) else {}
    if isinstance(protected, dict):
        merged.update(protected)
    return merged


def ensure_state_location(
    root: Path,
    state_dir: Path,
    *,
    artifact_names: Collection[str] = DEFAULT_CORE_STATE_ARTIFACTS,
    nested_artifacts: Collection[str] = (
        "stories/story.json",
        "receipts/receipt.json",
    ),
) -> None:
    """Require in-project state to be inside an existing Git ignore boundary."""

    try:
        relative = state_dir.resolve().relative_to(root.resolve())
    except ValueError:
        return
    if relative == Path("."):
        raise ValueError("state directory must not be the project root")
    if git_value(root, "rev-parse", "--is-inside-work-tree") != "true":
        raise ValueError(
            "state directory must stay outside a non-Git project root"
        )
    candidates = [
        (relative / name).as_posix()
        for name in (*artifact_names, *nested_artifacts)
    ]
    if not candidates or not all(
        git(root, "check-ignore", "-q", candidate).returncode == 0
        for candidate in candidates
    ):
        raise ValueError(
            "state directory inside the project must already be gitignored"
        )


def ensure_core_state_artifacts(
    state_dir: Path,
    *,
    artifact_names: Collection[str] = DEFAULT_CORE_STATE_ARTIFACTS,
) -> None:
    """Reject link or non-file substitutions for fixed runtime artifacts."""

    for name in artifact_names:
        path = state_dir / name
        if path.is_symlink():
            raise ValueError(f"goal state artifact must not be a symlink: {name}")
        if path.exists() and not path.is_file():
            raise ValueError(f"goal state artifact must be a regular file: {name}")


def open_regular_nofollow(
    path: Path,
    flags: int,
    *,
    mode: int = 0o600,
) -> int:
    """Open one regular file without following its final symlink component."""

    if path.is_symlink():
        raise ValueError(
            f"goal state artifact must not be a symlink: {path.name}"
        )
    descriptor = os.open(
        path,
        flags | getattr(os, "O_NOFOLLOW", 0),
        mode,
    )
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(
                f"goal state artifact must be a regular file: {path.name}"
            )
        # O_NOFOLLOW is not available on every supported Python platform.
        # Recheck before returning; callers do not write until this succeeds.
        if path.is_symlink():
            raise ValueError(
                f"goal state artifact must not be a symlink: {path.name}"
            )
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


@contextmanager
def state_lock(
    state_dir: Path,
    *,
    create: bool = False,
    artifact_names: Collection[str] = DEFAULT_CORE_STATE_ARTIFACTS,
) -> Iterator[None]:
    """Lock a state directory after rejecting fixed-artifact substitutions."""

    if create:
        state_dir.mkdir(parents=True, exist_ok=True)
    if not state_dir.is_dir():
        raise ValueError(f"state directory does not exist: {state_dir}")
    ensure_core_state_artifacts(
        state_dir,
        artifact_names=artifact_names,
    )
    lock_path = state_dir / ".lock"
    if not create and not lock_path.is_file():
        raise ValueError("goal state lock is missing")
    flags = os.O_RDWR | (os.O_CREAT if create else 0)
    descriptor = open_regular_nofollow(lock_path, flags)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    """Durably replace one JSON object without exposing partial bytes."""

    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                value,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_bytes(path: Path, value: bytes) -> None:
    """Durably replace one byte artifact without exposing partial bytes."""

    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_event(path: Path, event: dict[str, Any]) -> None:
    """Durably append one canonical JSON event without following a symlink."""

    encoded = canonical_bytes(event) + b"\n"
    descriptor = open_regular_nofollow(
        path,
        os.O_WRONLY | os.O_APPEND | os.O_CREAT,
    )
    with os.fdopen(descriptor, "ab") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(path.parent)


def seal_hash_chain_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of an event with its canonical ``event_sha256``."""

    sealed = dict(event)
    sealed.pop("event_sha256", None)
    sealed["event_sha256"] = digest(sealed)
    return sealed


def parse_hash_chain_text(
    text: str,
    *,
    allowed_event_types: Collection[str],
    label: str = "ledger",
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate an append-only event chain while preserving every parsed event."""

    errors: list[str] = []
    events: list[dict[str, Any]] = []
    previous = GENESIS
    for number, line in enumerate(text.splitlines(), start=1):
        try:
            event = json.loads(
                line,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-finite JSON value: {value}")
                ),
                object_pairs_hook=unique_json_object,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{label} line {number} is invalid: {exc}")
            continue
        if not isinstance(event, dict):
            errors.append(f"{label} line {number} must be an object")
            continue
        recorded_hash = event.get("event_sha256")
        unsigned = dict(event)
        unsigned.pop("event_sha256", None)
        expected_hash = digest(unsigned)
        if type(event.get("seq")) is not int or event["seq"] != number:
            errors.append(f"{label} line {number} has invalid sequence")
        if (
            type(event.get("schema_version")) is not int
            or event["schema_version"] != 1
        ):
            errors.append(
                f"{label} line {number} has invalid schema version"
            )
        if event.get("previous_sha256") != previous:
            errors.append(f"{label} line {number} has a broken previous hash")
        if recorded_hash != expected_hash:
            errors.append(f"{label} line {number} has an invalid event hash")
        if event.get("type") not in allowed_event_types:
            errors.append(f"{label} line {number} has an invalid event type")
        if not isinstance(event.get("payload"), dict):
            errors.append(f"{label} line {number} payload must be an object")
        if not isinstance(event.get("workspace"), dict):
            errors.append(f"{label} line {number} workspace must be an object")
        previous = recorded_hash if isinstance(recorded_hash, str) else ""
        events.append(event)
    return events, errors


def read_hash_chain(
    path: Path,
    *,
    allowed_event_types: Collection[str],
    label: str = "ledger",
    missing_error: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Read and validate an append-only canonical JSON event chain."""

    if not path.is_file():
        return [], [missing_error or f"{path.name} is missing"]
    return parse_hash_chain_text(
        path.read_text(encoding="utf-8"),
        allowed_event_types=allowed_event_types,
        label=label,
    )


def pending_transaction(
    event: dict[str, Any],
    updated_state: dict[str, Any],
    *,
    document_type: str = "quant_goal_pending_event",
    schema_version: int = 1,
) -> dict[str, Any]:
    """Journal one event plus its post-event state before either is committed."""

    body = {
        "document_type": document_type,
        "schema_version": schema_version,
        "event": event,
        "event_sha256": event.get("event_sha256"),
        "updated_state": updated_state,
        "updated_state_sha256": digest(updated_state),
    }
    return {**body, "transaction_sha256": digest(body)}


def clear_pending_transaction(
    state_dir: Path,
    *,
    pending_name: str = "pending-event.json",
) -> None:
    path = state_dir / pending_name
    if path.exists():
        path.unlink()
        fsync_directory(state_dir)


def recover_pending_transaction(
    state_dir: Path,
    *,
    allowed_event_types: Collection[str],
    state_name: str = "goal-state.json",
    ledger_name: str = "ledger.jsonl",
    pending_name: str = "pending-event.json",
    pending_document_type: str = "quant_goal_pending_event",
    pending_schema_version: int = 1,
    artifact_names: Collection[str] = DEFAULT_CORE_STATE_ARTIFACTS,
    atomic_json_writer: Callable[[Path, dict[str, Any]], None] = atomic_json,
    atomic_bytes_writer: Callable[[Path, bytes], None] = atomic_bytes,
    append_event_writer: Callable[[Path, dict[str, Any]], None] = append_event,
) -> bool:
    """Finish a journalled event/state write after an interrupted process.

    The caller must hold ``state_lock`` for the same directory.
    The state cache must expose ``ledger.event_count`` and
    ``ledger.tail_sha256``. Recovery repairs only an exact canonical prefix of
    the journalled event at the physical tail; unrelated corruption remains
    blocked.
    """

    ensure_core_state_artifacts(
        state_dir,
        artifact_names=artifact_names,
    )
    path = state_dir / pending_name
    if not path.is_file():
        return False
    pending = strict_json(path)
    unsigned = dict(pending)
    transaction_hash = unsigned.pop("transaction_sha256", None)
    if (
        pending.get("document_type") != pending_document_type
        or type(pending.get("schema_version")) is not int
        or pending["schema_version"] != pending_schema_version
        or transaction_hash != digest(unsigned)
    ):
        raise ValueError("pending goal transaction is invalid")
    event = pending.get("event")
    updated_state = pending.get("updated_state")
    if not isinstance(event, dict) or not isinstance(updated_state, dict):
        raise ValueError("pending goal transaction payload is invalid")
    if pending.get("event_sha256") != event.get("event_sha256"):
        raise ValueError("pending goal event binding is invalid")
    if pending.get("updated_state_sha256") != digest(updated_state):
        raise ValueError("pending goal state binding is invalid")
    unsigned_event = dict(event)
    recorded_event_hash = unsigned_event.pop("event_sha256", None)
    if recorded_event_hash != digest(unsigned_event):
        raise ValueError("pending goal event hash is invalid")
    sequence = event.get("seq")
    if type(sequence) is not int or sequence < 1:
        raise ValueError("pending goal event sequence is invalid")
    ledger_path = state_dir / ledger_name
    missing_separator = False
    if ledger_path.exists():
        ledger_bytes = ledger_path.read_bytes()
        events, errors = read_hash_chain(
            ledger_path,
            allowed_event_types=allowed_event_types,
            label="ledger",
            missing_error=f"{ledger_name} is missing",
        )
        missing_separator = bool(
            ledger_bytes and not ledger_bytes.endswith(b"\n")
        )
        if errors:
            # append_event writes exactly one canonical JSON line. A process
            # interruption may leave only a prefix of the pending event at the
            # physical tail. Repair only that exact, journal-proven case; any
            # earlier corruption or unrelated trailing bytes remain blocked.
            last_newline = ledger_bytes.rfind(b"\n")
            complete_bytes = (
                ledger_bytes[: last_newline + 1]
                if last_newline >= 0
                else b""
            )
            torn_tail = ledger_bytes[last_newline + 1 :]
            expected_line = canonical_bytes(event)
            try:
                prefix_events, prefix_errors = parse_hash_chain_text(
                    complete_bytes.decode("utf-8"),
                    allowed_event_types=allowed_event_types,
                    label="ledger",
                )
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"cannot recover pending transaction: {exc}"
                ) from exc
            expected_previous = (
                prefix_events[-1]["event_sha256"]
                if prefix_events
                else GENESIS
            )
            recoverable_tail = (
                bool(torn_tail)
                and expected_line.startswith(torn_tail)
                and not prefix_errors
                and len(prefix_events) == sequence - 1
                and event.get("previous_sha256") == expected_previous
            )
            if not recoverable_tail:
                raise ValueError(
                    "cannot recover pending transaction: "
                    + "; ".join(errors)
                )
            atomic_bytes_writer(ledger_path, complete_bytes)
            ledger_bytes = complete_bytes
            events = prefix_events
            missing_separator = False
    else:
        ledger_bytes = b""
        events = []
    if len(events) == sequence - 1:
        previous = events[-1]["event_sha256"] if events else GENESIS
        if event.get("previous_sha256") != previous:
            raise ValueError("pending goal event previous hash is invalid")
        if missing_separator:
            # Validate the pending event against the existing ledger before
            # making any separator repair. Replace the complete byte sequence
            # atomically so a second interruption cannot leave a separator-only
            # mutation.
            atomic_bytes_writer(
                ledger_path,
                ledger_bytes + b"\n" + canonical_bytes(event) + b"\n",
            )
        else:
            append_event_writer(ledger_path, event)
    elif len(events) >= sequence:
        if events[sequence - 1].get("event_sha256") != recorded_event_hash:
            raise ValueError("pending goal event conflicts with ledger")
        if len(events) != sequence:
            raise ValueError("pending goal transaction is stale")
        if missing_separator:
            # The no-newline event is the exact journalled event. Normalize it
            # only after identity, sequence, and stale checks all pass.
            atomic_bytes_writer(ledger_path, ledger_bytes + b"\n")
    else:
        raise ValueError("pending goal transaction skips ledger events")
    ledger = updated_state.get("ledger")
    if (
        not isinstance(ledger, dict)
        or type(ledger.get("event_count")) is not int
        or ledger["event_count"] != sequence
        or ledger.get("tail_sha256") != recorded_event_hash
    ):
        raise ValueError("pending goal state ledger cache is invalid")
    atomic_json_writer(state_dir / state_name, updated_state)
    clear_pending_transaction(
        state_dir,
        pending_name=pending_name,
    )
    return True


__all__ = [
    "DEFAULT_CORE_STATE_ARTIFACTS",
    "GENESIS",
    "append_event",
    "atomic_bytes",
    "atomic_json",
    "canonical_bytes",
    "casefold_glob",
    "clear_pending_transaction",
    "digest",
    "ensure_core_state_artifacts",
    "ensure_state_location",
    "file_digest",
    "fsync_directory",
    "git",
    "git_value",
    "non_git_snapshot",
    "open_regular_nofollow",
    "parse_hash_chain_text",
    "path_state",
    "pending_transaction",
    "portable_relative",
    "project_binding",
    "protected_path_snapshot",
    "read_hash_chain",
    "recover_pending_transaction",
    "sanitize_origin",
    "scope_pattern_selects_git_metadata",
    "seal_hash_chain_event",
    "snapshot_paths",
    "state_lock",
    "strict_json",
    "verify_workspace_snapshot",
    "workspace_snapshot",
]
