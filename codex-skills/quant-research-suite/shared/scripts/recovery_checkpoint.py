#!/usr/bin/env python3
"""Persist one small, non-authoritative recovery checkpoint.

The native host task/Goal, current user request, live workspace, workers, and
consumer surfaces remain canonical. This helper only makes a compact recovery
capsule crash-safe; it never activates a skill, grants authority, or proves
completion.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterator, TextIO
from urllib.parse import urlsplit, urlunsplit


DOCUMENT_TYPE = "quant_recovery_checkpoint"
SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 128 * 1024
MAX_CAPSULE_BYTES = 64 * 1024
MAX_TEXT_LENGTH = 2_000
LOCK_NAME = ".lock"
CHECKPOINT_NAME = "checkpoint.json"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _fields(names: str) -> frozenset[str]:
    return frozenset(names.split())


CAPSULE_FIELDS = _fields(
    "objective_summary phase completion_conditions workers evidence_refs blockers "
    "pending_authority next_action no_repeat"
)
CONDITION_STATES = _fields("pending in_progress verified stale blocked failed unknown")
WORKER_STATES = _fields("running returned accepted unknown cancelled blocked failed")
EVIDENCE_STATES = _fields("candidate verified stale unknown unavailable")

# name: (allowed, required, text fields, text-list fields, allowed state values)
RECORD_SPECS = {
    "completion_conditions": (
        _fields("id summary state evidence_refs"), _fields("summary state"),
        ("id", "summary"), ("evidence_refs",), CONDITION_STATES,
    ),
    "workers": (
        _fields("ref scope_summary state artifact_refs"), _fields("ref scope_summary state"),
        ("ref", "scope_summary"), ("artifact_refs",), WORKER_STATES,
    ),
    "evidence_refs": (
        _fields("ref summary state"), _fields("ref summary state"),
        ("ref", "summary"), (), EVIDENCE_STATES,
    ),
    "pending_authority": (
        _fields("action target"), _fields("action target"),
        ("action", "target"), (), None,
    ),
}
CHECKPOINT_FIELDS = _fields(
    "document_type schema_version recovery_id sequence recorded_at project workspace "
    "capsule checkpoint_sha256"
)
PROJECT_FIELDS = _fields(
    "root_realpath root_device root_inode git_common_dir_realpath "
    "origin_fingerprint_sha256 "
    "locator_sha256 identity_sha256"
)
WORKSPACE_FIELDS = _fields("kind verification head branch dirty status_sha256")

FORBIDDEN_CONTENT = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b(?:gh[opusr]_|github_pat_)[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:api[_-]?key|password|passwd|secret|token|authorization)"
               r"\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"https?://[^\s/@:]+:[^\s/@]+@", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9_.-])(?:\.env|\.netrc|credentials\.json|id_rsa|"
               r"id_ed25519|private\.pem)(?![A-Za-z0-9_.-])", re.IGNORECASE),
    re.compile(r"\bhttps?://", re.IGNORECASE),
)
AUTHORITY_CLAIM = re.compile(
    r"\b(?:approved|authorized|authorised|granted|permission received|consent received)\b|"
    r"(?:승인|허가|권한)\s*(?:됨|받음|완료|획득|있음)",
    re.IGNORECASE,
)


class RecoveryError(Exception):
    """Expected, user-correctable helper error."""


class ConflictError(RecoveryError):
    """The checkpoint generation changed."""


class OutcomeUnknownError(RecoveryError):
    """Replace completed but directory sync did not."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.details = details


def canonical_bytes(value: Any) -> bytes:
    options = dict(allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return json.dumps(value, **options).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise RecoveryError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def finite_json_bytes(raw: bytes, *, label: str) -> dict[str, Any]:
    if len(raw) > MAX_INPUT_BYTES:
        raise RecoveryError(f"{label} exceeds {MAX_INPUT_BYTES} bytes")

    def reject_constant(value: str) -> None:
        raise RecoveryError(f"non-finite JSON value is prohibited: {value}")

    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=unique_object,
        )
    except UnicodeDecodeError as exc:
        raise RecoveryError(f"{label} must be UTF-8 JSON") from exc
    except json.JSONDecodeError as exc:
        raise RecoveryError(f"invalid {label} JSON: {exc.msg}") from exc
    except (ValueError, RecursionError) as exc:
        raise RecoveryError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RecoveryError(f"{label} root must be an object")
    return value


def _read_limited(stream: BinaryIO, *, label: str) -> bytes:
    raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise RecoveryError(f"{label} exceeds {MAX_INPUT_BYTES} bytes")
    return raw


def open_regular_nofollow(
    path: Path, flags: int, *, mode: int = 0o600, require_private: bool = False
) -> int:
    if path.is_symlink():
        raise RecoveryError(f"refusing symlink: {path}")
    try:
        descriptor = os.open(path, flags | getattr(os, "O_NOFOLLOW", 0), mode)
    except OSError as exc:
        raise RecoveryError(f"cannot open regular file {path}: {exc}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise RecoveryError(f"not a regular file: {path}")
        loose = metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) & 0o077
        if require_private and loose:
            raise RecoveryError(
                f"private file permissions are too broad or ownership is invalid: {path}"
            )
        if path.is_symlink():
            raise RecoveryError(f"refusing symlink: {path}")
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def read_json_file(
    path: Path, *, label: str, require_private: bool = False
) -> dict[str, Any]:
    descriptor = open_regular_nofollow(path, os.O_RDONLY, require_private=require_private)
    with os.fdopen(descriptor, "rb") as handle:
        return finite_json_bytes(_read_limited(handle, label=label), label=label)


def read_capsule(path_value: str, stdin: BinaryIO | None = None) -> dict[str, Any]:
    if path_value != "-":
        return read_json_file(Path(path_value).expanduser(), label="capsule")
    stream = stdin if stdin is not None else sys.stdin.buffer
    return finite_json_bytes(_read_limited(stream, label="capsule"), label="capsule")


def _exact_object(
    value: Any, *, label: str, allowed: frozenset[str], required: frozenset[str] = frozenset()
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RecoveryError(f"{label} must be an object")
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise RecoveryError(f"{label} has unexpected fields: {unexpected}")
    missing = sorted(required - set(value))
    if missing:
        raise RecoveryError(f"{label} is missing required fields: {missing}")
    return value


def _check_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise RecoveryError(f"{label} must be a string")
    if not value.strip():
        raise RecoveryError(f"{label} must not be empty")
    if len(value) > MAX_TEXT_LENGTH:
        raise RecoveryError(f"{label} exceeds {MAX_TEXT_LENGTH} characters")
    if "\n" in value or "\r" in value or "\x00" in value:
        raise RecoveryError(f"{label} must be a single-line summary or reference")
    if any(pattern.search(value) for pattern in FORBIDDEN_CONTENT):
        raise RecoveryError(f"{label} appears to contain secret-bearing content")
    if AUTHORITY_CLAIM.search(value):
        raise RecoveryError(f"{label} must not persist an authority claim")
    return value


def _string_list(value: Any, *, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RecoveryError(f"{label} must be a list")
    return [
        _check_text(item, label=f"{label}[{index}]") for index, item in enumerate(value)
    ]


def _normalize_records(value: dict[str, Any], name: str) -> list[dict[str, Any]]:
    allowed, required, text_fields, list_fields, states = RECORD_SPECS[name]
    raw_items = value.get(name, [])
    if not isinstance(raw_items, list):
        raise RecoveryError(f"capsule.{name} must be a list")
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items):
        label = f"capsule.{name}[{index}]"
        item = _exact_object(raw, label=label, allowed=allowed, required=required)
        record = {
            field: _check_text(item[field], label=f"{label}.{field}")
            for field in text_fields
            if field in item
        }
        for field in list_fields:
            record[field] = _string_list(item.get(field), label=f"{label}.{field}")
        if states is not None:
            state = item["state"]
            if not isinstance(state, str) or state not in states:
                raise RecoveryError(f"{label}.state is invalid")
            record["state"] = state
        normalized.append(record)
    return normalized


def validate_capsule(value: dict[str, Any]) -> dict[str, Any]:
    value = _exact_object(
        value,
        label="capsule",
        allowed=CAPSULE_FIELDS,
        required=frozenset({"objective_summary", "phase", "next_action"}),
    )
    normalized = {
        "objective_summary": _check_text(value["objective_summary"], label="capsule.objective_summary"),
        "phase": _check_text(value["phase"], label="capsule.phase"),
        "completion_conditions": _normalize_records(value, "completion_conditions"),
        "workers": _normalize_records(value, "workers"),
        "evidence_refs": _normalize_records(value, "evidence_refs"),
        "blockers": _string_list(value.get("blockers"), label="capsule.blockers"),
        "pending_authority": _normalize_records(value, "pending_authority"),
        "next_action": _check_text(value["next_action"], label="capsule.next_action"),
        "no_repeat": _string_list(value.get("no_repeat"), label="capsule.no_repeat"),
    }
    if len(canonical_bytes(normalized)) > MAX_CAPSULE_BYTES:
        raise RecoveryError(f"normalized capsule exceeds {MAX_CAPSULE_BYTES} bytes")
    return normalized


def normalize_recovery_id(value: str) -> str:
    try:
        normalized = str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise RecoveryError("recovery-id must be a canonical UUID") from exc
    if value.lower() != normalized:
        raise RecoveryError("recovery-id must use canonical UUID form")
    return normalized


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sanitize_origin(value: str) -> str:
    origin = value.strip()
    if not origin:
        return ""
    if "://" in origin:
        parsed = urlsplit(origin)
        hostname = parsed.hostname or ""
        host = f"[{hostname}]" if ":" in hostname else hostname
        try:
            port = parsed.port
        except ValueError:
            port = None
        if port is not None:
            host = f"{host}:{port}"
        return urlunsplit((parsed.scheme, host, parsed.path, "", ""))
    scp_like = re.fullmatch(r"[^@/\s]+@([^:\s]+):(.+)", origin)
    if scp_like:
        return f"{scp_like.group(1)}:{scp_like.group(2)}"
    return origin.split("?", 1)[0].split("#", 1)[0]


def git_run(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    try:
        return subprocess.run(
            ["git", "--no-optional-locks", "-C", str(root), *args],
            capture_output=True,
            check=False,
            timeout=30,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RecoveryError(f"cannot inspect Git workspace: {exc}") from exc


def git_text(root: Path, *args: str) -> str | None:
    result = git_run(root, *args)
    if result.returncode:
        return None
    try:
        return result.stdout.decode("utf-8").strip()
    except UnicodeDecodeError:
        return None


def resolve_project_root(value: str) -> Path:
    path = Path(value).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise RecoveryError(f"project root is unavailable: {path}") from exc
    if not resolved.is_dir():
        raise RecoveryError(f"project root is not a directory: {resolved}")
    return resolved


def capture_project(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root_stat = root.stat(follow_symlinks=False)
    inside = git_text(root, "rev-parse", "--is-inside-work-tree") == "true"
    common_dir = (
        git_text(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if inside
        else None
    )
    if common_dir:
        common_dir = str(Path(common_dir).resolve())
    sanitized = sanitize_origin(
        (git_text(root, "remote", "get-url", "origin") if inside else None) or ""
    )
    identity = {
        "root_realpath": str(root),
        "root_device": root_stat.st_dev,
        "root_inode": root_stat.st_ino,
        "git_common_dir_realpath": common_dir,
        "origin_fingerprint_sha256": (
            hashlib.sha256(sanitized.encode("utf-8")).hexdigest() if sanitized else None
        ),
    }
    project = {
        **identity,
        "locator_sha256": hashlib.sha256(str(root).encode("utf-8")).hexdigest(),
        "identity_sha256": digest(identity),
    }
    if not inside:
        return project, {
            "kind": "non_git",
            "verification": "unavailable",
            "head": None,
            "branch": None,
            "dirty": None,
            "status_sha256": None,
        }
    status = git_run(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    available = status.returncode == 0
    return project, {
        "kind": "git",
        "verification": "available" if available else "partial",
        "head": git_text(root, "rev-parse", "HEAD"),
        "branch": git_text(root, "symbolic-ref", "--quiet", "--short", "HEAD"),
        "dirty": bool(status.stdout) if available else None,
        "status_sha256": hashlib.sha256(status.stdout).hexdigest() if available else None,
    }


def state_root() -> Path:
    configured = os.environ.get("CODEX_HOME")
    home = Path(configured).expanduser() if configured else Path.home() / ".codex"
    if not home.is_absolute():
        home = (Path.cwd() / home).absolute()
    return home / "state" / "quant-recovery"


def reject_symlink(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise RecoveryError(f"{label} must not be a symlink: {path}")


def _check_directory(
    path: Path,
    *,
    label: str,
    required: bool = False,
    private: bool = False,
    create: bool = False,
) -> None:
    reject_symlink(path, label=label)
    if create:
        try:
            path.mkdir(parents=True, mode=0o700, exist_ok=True)
        except OSError as exc:
            raise RecoveryError(f"cannot create recovery directory {path}: {exc}") from exc
    reject_symlink(path, label=label)
    if not path.exists():
        if required:
            raise RecoveryError(f"{label} is unavailable: {path}")
        return
    if not path.is_dir():
        raise RecoveryError(f"{label} is not a directory: {path}")
    metadata = path.stat(follow_symlinks=False)
    if metadata.st_uid != os.geteuid():
        raise RecoveryError(f"{label} ownership or write permissions are unsafe: {path}")
    if create:
        os.chmod(path, 0o700)
        metadata = path.stat(follow_symlinks=False)
    mask = 0o077 if private else 0o022
    if stat.S_IMODE(metadata.st_mode) & mask:
        detail = "permissions are too broad" if private else "ownership or write permissions are unsafe"
        raise RecoveryError(f"{label} {detail}: {path}")


def validate_state_ancestors(*, require_root: bool) -> None:
    root = state_root()
    for label, path in (
        ("CODEX_HOME", root.parent.parent),
        ("CODEX_HOME state directory", root.parent),
        ("recovery root", root),
    ):
        _check_directory(path, label=label)
    if require_root and not root.is_dir():
        raise RecoveryError("recovery state does not exist")


def ensure_state_outside_project(root: Path, state: Path) -> None:
    try:
        state.resolve(strict=False).relative_to(root)
    except ValueError:
        return
    raise RecoveryError("recovery state must stay outside the project root")


def ensure_private_dir(path: Path) -> None:
    _check_directory(path, label="recovery directory", create=True, private=True)


def validate_existing_state_path(path: Path) -> None:
    validate_state_ancestors(require_root=True)
    for directory in (state_root(), path.parent.parent, path.parent):
        _check_directory(
            directory, label="recovery directory", required=True, private=True
        )
    reject_symlink(path, label="recovery state component")


def checkpoint_path(project: dict[str, Any], recovery_id: str) -> Path:
    return state_root() / project["locator_sha256"] / recovery_id / CHECKPOINT_NAME


def fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid():
            raise RecoveryError(f"unsafe recovery directory: {path}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def recovery_lock(*, create: bool) -> Iterator[None]:
    root = state_root()
    if create:
        validate_state_ancestors(require_root=False)
        ensure_private_dir(root)
    validate_state_ancestors(require_root=True)
    lock_path = root / LOCK_NAME
    if not create and not lock_path.is_file():
        raise RecoveryError("recovery lock is missing")
    descriptor = open_regular_nofollow(
        lock_path, os.O_RDWR | (os.O_CREAT if create else 0)
    )
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        if create:
            fsync_directory(root)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    encoded = (
        json.dumps(value, allow_nan=False, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    if len(encoded) > MAX_INPUT_BYTES:
        raise RecoveryError(f"checkpoint exceeds {MAX_INPUT_BYTES} bytes")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    replaced = False
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        replaced = True
        try:
            fsync_directory(path.parent)
        except (OSError, RecoveryError) as exc:
            raise OutcomeUnknownError(
                "checkpoint replacement completed but durable readback is required",
                recovery_id=value.get("recovery_id"),
                attempted_sequence=value.get("sequence"),
                checkpoint_path=str(path),
            ) from exc
    finally:
        if not replaced and os.path.exists(temporary):
            os.unlink(temporary)


def _check_sha(value: Any, *, label: str, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise RecoveryError(f"{label} is invalid")


def _validate_project(value: Any, *, locator: str) -> dict[str, Any]:
    project = _exact_object(
        value, label="checkpoint project", allowed=PROJECT_FIELDS, required=PROJECT_FIELDS
    )
    if project.get("locator_sha256") != locator:
        raise RecoveryError("checkpoint project binding mismatch")
    if not isinstance(project["root_realpath"], str) or not project["root_realpath"]:
        raise RecoveryError("checkpoint project identity is invalid")
    if type(project["root_device"]) is not int or project["root_device"] < 0:
        raise RecoveryError("checkpoint project identity is invalid")
    if type(project["root_inode"]) is not int or project["root_inode"] <= 0:
        raise RecoveryError("checkpoint project identity is invalid")
    common_dir = project["git_common_dir_realpath"]
    if common_dir is not None and not isinstance(common_dir, str):
        raise RecoveryError("checkpoint project identity is invalid")
    _check_sha(
        project["origin_fingerprint_sha256"],
        label="checkpoint origin fingerprint",
        optional=True,
    )
    _check_sha(project["locator_sha256"], label="checkpoint project locator digest")
    _check_sha(project["identity_sha256"], label="checkpoint project identity digest")
    identity = {
        "root_realpath": project["root_realpath"],
        "root_device": project["root_device"],
        "root_inode": project["root_inode"],
        "git_common_dir_realpath": common_dir,
        "origin_fingerprint_sha256": project["origin_fingerprint_sha256"],
    }
    if project["identity_sha256"] != digest(identity):
        raise RecoveryError("checkpoint project identity hash mismatch")
    expected_locator = hashlib.sha256(project["root_realpath"].encode("utf-8")).hexdigest()
    if project["locator_sha256"] != expected_locator:
        raise RecoveryError("checkpoint project locator hash mismatch")
    return project


def _validate_workspace(value: Any) -> dict[str, Any]:
    workspace = _exact_object(
        value,
        label="checkpoint workspace",
        allowed=WORKSPACE_FIELDS,
        required=WORKSPACE_FIELDS,
    )
    if workspace["kind"] not in {"git", "non_git"}:
        raise RecoveryError("checkpoint workspace kind is invalid")
    if workspace["verification"] not in {"available", "partial", "unavailable"}:
        raise RecoveryError("checkpoint workspace verification is invalid")
    if type(workspace["dirty"]) not in {bool, type(None)}:
        raise RecoveryError("checkpoint workspace dirty state is invalid")
    for field in ("head", "branch"):
        if workspace[field] is not None and not isinstance(workspace[field], str):
            raise RecoveryError(f"checkpoint workspace {field} is invalid")
    _check_sha(
        workspace["status_sha256"],
        label="checkpoint workspace status digest",
        optional=True,
    )
    return workspace


def validate_checkpoint(
    value: dict[str, Any], *, recovery_id: str, project_locator: str
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != CHECKPOINT_FIELDS:
        raise RecoveryError("checkpoint fields do not match schema v1")
    if value.get("document_type") != DOCUMENT_TYPE or value.get("schema_version") != 1:
        raise RecoveryError("unsupported recovery checkpoint")
    if value.get("recovery_id") != recovery_id:
        raise RecoveryError("checkpoint recovery-id mismatch")
    sequence = value.get("sequence")
    if type(sequence) is not int or sequence <= 0:
        raise RecoveryError("checkpoint sequence must be a positive integer")
    recorded_at = value.get("recorded_at")
    if not isinstance(recorded_at, str) or not recorded_at.endswith("Z"):
        raise RecoveryError("checkpoint recorded_at is invalid")
    try:
        datetime.fromisoformat(recorded_at[:-1] + "+00:00")
    except ValueError as exc:
        raise RecoveryError("checkpoint recorded_at is invalid") from exc
    _validate_project(value.get("project"), locator=project_locator)
    _validate_workspace(value.get("workspace"))
    capsule = value.get("capsule")
    if not isinstance(capsule, dict):
        raise RecoveryError("checkpoint capsule is invalid")
    if validate_capsule(capsule) != capsule:
        raise RecoveryError("checkpoint capsule is not canonical")
    unsigned = dict(value)
    recorded_digest = unsigned.pop("checkpoint_sha256")
    if not isinstance(recorded_digest, str) or recorded_digest != digest(unsigned):
        raise RecoveryError("checkpoint hash mismatch")
    return value


def read_checkpoint(
    path: Path, *, recovery_id: str, project_locator: str
) -> dict[str, Any]:
    validate_existing_state_path(path)
    if not path.is_file():
        raise RecoveryError("recovery checkpoint not found")
    value = read_json_file(path, label="checkpoint", require_private=True)
    return validate_checkpoint(
        value, recovery_id=recovery_id, project_locator=project_locator
    )


def save_checkpoint(
    *,
    root: Path,
    capsule: dict[str, Any],
    recovery_id: str | None,
    expected_sequence: int | None,
) -> dict[str, Any]:
    capsule = validate_capsule(capsule)
    project, workspace = capture_project(root)
    recovery_root = state_root()
    ensure_state_outside_project(root, recovery_root)
    generated = recovery_id is None
    if generated:
        if expected_sequence is not None:
            raise RecoveryError("expected-sequence requires an explicit recovery-id")
        recovery_id = str(uuid.uuid4())
    else:
        recovery_id = normalize_recovery_id(recovery_id)
        if expected_sequence is None:
            raise RecoveryError(
                "checkpoint with an explicit recovery-id requires expected-sequence"
            )
        if expected_sequence < 0:
            raise RecoveryError("expected-sequence must be zero or greater")

    path = checkpoint_path(project, recovery_id)
    with recovery_lock(create=True):
        ensure_private_dir(path.parent.parent)
        ensure_private_dir(path.parent)
        existing = None
        if os.path.lexists(path):
            if generated:
                raise ConflictError("generated recovery-id collision; retry checkpoint")
            existing = read_checkpoint(
                path,
                recovery_id=recovery_id,
                project_locator=project["locator_sha256"],
            )
            if existing["project"]["identity_sha256"] != project["identity_sha256"]:
                raise RecoveryError("checkpoint is bound to a different project identity")
        current_sequence = existing["sequence"] if existing is not None else 0
        if expected_sequence is not None and current_sequence != expected_sequence:
            raise ConflictError(
                f"checkpoint sequence conflict: expected {expected_sequence}, "
                f"found {current_sequence}"
            )
        sequence = current_sequence + 1
        body = {
            "document_type": DOCUMENT_TYPE,
            "schema_version": SCHEMA_VERSION,
            "recovery_id": recovery_id,
            "sequence": sequence,
            "recorded_at": utc_now(),
            "project": project,
            "workspace": workspace,
            "capsule": capsule,
        }
        checkpoint = {**body, "checkpoint_sha256": digest(body)}
        atomic_json(path, checkpoint)
    return {
        "status": "checkpointed",
        "recovery_id": recovery_id,
        "sequence": sequence,
        "recorded_at": checkpoint["recorded_at"],
        "checkpoint_path": str(path),
        "authority": {"status": "not_recorded"},
    }


def _workspace_reconciliation(
    stored_project: dict[str, Any],
    stored_workspace: dict[str, Any],
    current_project: dict[str, Any],
    current_workspace: dict[str, Any],
) -> dict[str, Any]:
    project_match = stored_project.get("identity_sha256") == current_project.get(
        "identity_sha256"
    )
    fields = ("kind", "verification", "head", "branch", "dirty", "status_sha256")
    changed = [
        field for field in fields if stored_workspace.get(field) != current_workspace.get(field)
    ]
    if not project_match:
        state = "project_mismatch"
    elif stored_workspace.get("kind") != "git" or current_workspace.get("kind") != "git":
        state = "unverifiable"
    elif {
        stored_workspace.get("verification"), current_workspace.get("verification")
    } != {"available"}:
        state = "unverifiable"
    else:
        state = "drifted" if changed else "snapshot_metadata_unchanged"
    return {
        "state": state,
        "project_match": project_match,
        "changed_fields": changed,
        "stored": stored_workspace,
        "current": current_workspace,
    }


def _worker_reconciliation(capsule: dict[str, Any]) -> list[dict[str, str]]:
    def resume_state(saved: str) -> str:
        if saved in {"running", "unknown", "blocked"}:
            return "unknown"
        if saved in {"returned", "accepted"}:
            return "requires_live_artifact_and_host_reinspection"
        return "requires_host_confirmation"

    return [
        {
            "ref": worker["ref"],
            "saved_state": worker["state"],
            "resume_state": resume_state(worker["state"]),
        }
        for worker in capsule["workers"]
    ]


def build_resume_result(
    checkpoint: dict[str, Any],
    *,
    current_project: dict[str, Any],
    current_workspace: dict[str, Any],
    path: Path,
) -> dict[str, Any]:
    workspace = _workspace_reconciliation(
        checkpoint["project"], checkpoint["workspace"], current_project, current_workspace
    )
    evidence_state = {
        "snapshot_metadata_unchanged": "requires_live_revalidation",
        "drifted": "stale_due_to_live_drift",
        "project_mismatch": "stale_due_to_project_mismatch",
        "unverifiable": "unverified",
    }[workspace["state"]]
    capsule = checkpoint["capsule"]
    condition_state = (
        "stale_due_to_live_drift"
        if workspace["state"] == "drifted"
        else "requires_live_reconciliation"
    )
    reconciliation = {
        "goal": "requires_native_readback",
        "workspace": workspace,
        "workers": _worker_reconciliation(capsule),
        "conditions": [
            {
                **({"id": item["id"]} if "id" in item else {}),
                "saved_state": item["state"],
                "resume_state": condition_state,
            }
            for item in capsule["completion_conditions"]
        ],
        "evidence_refs": [
            {
                "ref": item["ref"],
                "saved_state": item["state"],
                "resume_state": evidence_state,
            }
            for item in capsule["evidence_refs"]
        ],
        "evidence": evidence_state,
        "authority": {
            "status": "not_recorded",
            "rule": "obtain fresh current-user authority for any gated action",
        },
        "saved_next_action": {
            "status": "advisory_only",
            "summary": capsule["next_action"],
        },
        "no_repeat": {
            "status": "check_live_state_before_replay",
            "actions": capsule["no_repeat"],
        },
        "remote_and_public_results": "require_live_readback",
    }
    return {
        "status": "recovery_candidate",
        "recovery_id": checkpoint["recovery_id"],
        "sequence": checkpoint["sequence"],
        "recorded_at": checkpoint["recorded_at"],
        "checkpoint_path": str(path),
        "saved_capsule": capsule,
        "reconciliation": reconciliation,
    }


def candidate_ids(project: dict[str, Any]) -> list[str]:
    root = state_root()
    validate_state_ancestors(require_root=False)
    if not root.is_dir():
        return []
    project_dir = root / project["locator_sha256"]
    reject_symlink(project_dir, label="recovery project directory")
    if not project_dir.is_dir():
        return []
    candidates = []
    for child in project_dir.iterdir():
        if child.is_symlink() or not child.is_dir():
            continue
        try:
            recovery_id = normalize_recovery_id(child.name)
        except RecoveryError:
            continue
        checkpoint = child / CHECKPOINT_NAME
        if checkpoint.is_file() and not checkpoint.is_symlink():
            candidates.append(recovery_id)
    return sorted(candidates)


def resume_checkpoint(*, root: Path, recovery_id: str | None) -> tuple[int, dict[str, Any]]:
    project, workspace = capture_project(root)
    ensure_state_outside_project(root, state_root())
    if recovery_id is None:
        candidates = candidate_ids(project)
        if not candidates:
            return 2, {"status": "not_found", "candidates": []}
        if len(candidates) > 1:
            return 2, {"status": "ambiguous", "candidates": candidates}
        recovery_id = candidates[0]
    else:
        recovery_id = normalize_recovery_id(recovery_id)
    path = checkpoint_path(project, recovery_id)
    checkpoint = read_checkpoint(
        path, recovery_id=recovery_id, project_locator=project["locator_sha256"]
    )
    if checkpoint["project"]["identity_sha256"] != project["identity_sha256"]:
        raise RecoveryError("checkpoint is bound to a different project identity")
    return 0, build_resume_result(
        checkpoint,
        current_project=project,
        current_workspace=workspace,
        path=path,
    )


def retire_checkpoint(
    *, root: Path, recovery_id: str, expected_sequence: int
) -> dict[str, Any]:
    recovery_id = normalize_recovery_id(recovery_id)
    if expected_sequence <= 0:
        raise RecoveryError("expected-sequence must be a positive integer")
    project, _workspace = capture_project(root)
    recovery_root = state_root()
    ensure_state_outside_project(root, recovery_root)
    path = checkpoint_path(project, recovery_id)
    validate_state_ancestors(require_root=False)
    if not recovery_root.is_dir():
        return {"status": "already_absent", "recovery_id": recovery_id}
    with recovery_lock(create=False):
        if not os.path.lexists(path):
            return {"status": "already_absent", "recovery_id": recovery_id}
        checkpoint = read_checkpoint(
            path,
            recovery_id=recovery_id,
            project_locator=project["locator_sha256"],
        )
        if checkpoint["project"]["identity_sha256"] != project["identity_sha256"]:
            raise RecoveryError("checkpoint is bound to a different project identity")
        if checkpoint["sequence"] != expected_sequence:
            raise ConflictError(
                f"checkpoint sequence conflict: expected {expected_sequence}, "
                f"found {checkpoint['sequence']}"
            )
        path.unlink()
        fsync_directory(path.parent)
        try:
            path.parent.rmdir()
            fsync_directory(path.parent.parent)
        except OSError:
            pass
        project_dir = recovery_root / project["locator_sha256"]
        try:
            project_dir.rmdir()
            fsync_directory(recovery_root)
        except OSError:
            pass
    return {"status": "retired", "recovery_id": recovery_id}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage an optional non-authoritative Quant recovery checkpoint."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    checkpoint = commands.add_parser("checkpoint")
    checkpoint.add_argument("--root", required=True, help="Project root to bind")
    checkpoint.add_argument("--capsule", required=True, help="Capsule JSON file, or - for stdin")
    checkpoint.add_argument("--recovery-id")
    checkpoint.add_argument("--expected-sequence", type=int)
    resume = commands.add_parser("resume")
    resume.add_argument("--root", required=True, help="Project root to reconcile")
    resume.add_argument("--recovery-id")
    retire = commands.add_parser("retire")
    retire.add_argument("--root", required=True, help="Bound project root")
    retire.add_argument("--recovery-id", required=True)
    retire.add_argument("--expected-sequence", required=True, type=int)
    return parser


def emit(value: dict[str, Any], *, stream: TextIO = sys.stdout) -> None:
    print(
        json.dumps(value, allow_nan=False, ensure_ascii=False, sort_keys=True),
        file=stream,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = resolve_project_root(args.root)
        if args.command == "checkpoint":
            result = save_checkpoint(
                root=root,
                capsule=read_capsule(args.capsule),
                recovery_id=args.recovery_id,
                expected_sequence=args.expected_sequence,
            )
            emit(result)
            return 0
        if args.command == "resume":
            code, result = resume_checkpoint(root=root, recovery_id=args.recovery_id)
            emit(result)
            return code
        result = retire_checkpoint(
            root=root,
            recovery_id=args.recovery_id,
            expected_sequence=args.expected_sequence,
        )
        emit(result)
        return 0
    except ConflictError as exc:
        emit({"status": "conflict", "error": str(exc)}, stream=sys.stderr)
        return 3
    except OutcomeUnknownError as exc:
        emit(
            {"status": "outcome_unknown", "error": str(exc), **exc.details},
            stream=sys.stderr,
        )
        return 4
    except (RecoveryError, OSError) as exc:
        emit({"status": "error", "error": str(exc)}, stream=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
