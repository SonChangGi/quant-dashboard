#!/usr/bin/env python3
"""Host-aligned durable Goal evidence ledger.

The host Goal owns lifecycle state. This runtime records append-only revisions,
stories, snapshot-bound reviews, checkpoints, and completion readiness without
mutating the host or granting repository/provider/payment authority.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .goal_primitives import (
        GENESIS,
        append_event,
        atomic_bytes,
        atomic_json,
        canonical_bytes,
        clear_pending_transaction,
        digest,
        ensure_core_state_artifacts,
        ensure_state_location,
        file_digest,
        fsync_directory,
        pending_transaction,
        portable_relative,
        protected_path_snapshot,
        project_binding,
        read_hash_chain,
        recover_pending_transaction,
        seal_hash_chain_event,
        snapshot_paths,
        state_lock,
        strict_json,
        verify_workspace_snapshot,
        workspace_snapshot as primitive_workspace_snapshot,
    )
except ImportError:
    from goal_primitives import (
        GENESIS,
        append_event,
        atomic_bytes,
        atomic_json,
        canonical_bytes,
        clear_pending_transaction,
        digest,
        ensure_core_state_artifacts,
        ensure_state_location,
        file_digest,
        fsync_directory,
        pending_transaction,
        portable_relative,
        protected_path_snapshot,
        project_binding,
        read_hash_chain,
        recover_pending_transaction,
        seal_hash_chain_event,
        snapshot_paths,
        state_lock,
        strict_json,
        verify_workspace_snapshot,
        workspace_snapshot as primitive_workspace_snapshot,
    )


STATE_NAME = "goal-ledger-state.json"
LEDGER_NAME = "goal-ledger.jsonl"
PENDING_NAME = "goal-ledger-pending.json"
LOCK_NAME = ".lock"
CORE_ARTIFACTS = (LOCK_NAME, STATE_NAME, LEDGER_NAME, PENDING_NAME)
STATE_SCHEMA = (
    "https://example.invalid/quant-research-suite/"
    "goal-ledger-state.schema.json"
)
PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PORTABLE_ID = re.compile(r"^[a-z0-9_-]{1,128}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ASSURANCE_LEVELS = ("light", "standard", "strict", "release")
DELIVERY_LEVELS = ("local", "release")
STEERING_OPS = frozenset(
    {
        "clarify",
        "add",
        "retire",
        "split",
        "merge",
        "reorder",
        "replace",
    }
)
HOST_STATES = frozenset(
    {
        "active",
        "waiting",
        "paused",
        "blocked",
        "completed",
        "cancelled",
        "superseded",
    }
)
TERMINAL_HOST_STATES = frozenset(
    {"completed", "cancelled", "superseded"}
)
REVIEW_ROLES = frozenset(
    {
        "integration_review",
        "architecture_review",
        "adversarial_qa",
        "terminal_critic",
    }
)
EVENT_TYPES = frozenset(
    {
        "goal_bound",
        "plan_bound",
        "acceptance_revised",
        "checkpoint_recorded",
        "continuation_capsule_recorded",
        "story_issued",
        "story_returned",
        "story_accepted",
        "review_recorded",
        "blocker_classified",
        "completion_ready",
        "host_state_observed",
        "goal_cancelled",
        "goal_superseded",
    }
)
ASSURANCE_GATES: dict[str, frozenset[str]] = {
    "light": frozenset({"contract", "verification", "self_review"}),
    "standard": frozenset(
        {
            "contract",
            "verification",
            "self_review",
            "cleanup",
            "integration",
            "integration_review",
        }
    ),
    "strict": frozenset(
        {
            "contract",
            "verification",
            "self_review",
            "cleanup",
            "integration",
            "integration_review",
            "baseline",
            "failure_mode",
            "architecture_review",
            "adversarial_qa",
            "terminal_critic",
        }
    ),
    "release": frozenset(
        {
            "contract",
            "verification",
            "self_review",
            "cleanup",
            "integration",
            "integration_review",
            "baseline",
            "failure_mode",
            "architecture_review",
            "adversarial_qa",
            "terminal_critic",
            "release",
        }
    ),
}
ASSURANCE_REVIEW_ROLES: dict[str, tuple[str, ...]] = {
    "light": (),
    "standard": ("integration_review",),
    "strict": (
        "architecture_review",
        "adversarial_qa",
        "terminal_critic",
    ),
    "release": (
        "architecture_review",
        "adversarial_qa",
        "terminal_critic",
    ),
}
STALE_COMPLETION_EVENTS = frozenset(
    {
        "plan_bound",
        "acceptance_revised",
        "checkpoint_recorded",
        "story_issued",
        "story_returned",
        "story_accepted",
        "review_recorded",
        "blocker_classified",
        "goal_cancelled",
        "goal_superseded",
    }
)
TERMINAL_CONTEXT_EVENTS = frozenset(
    {
        "goal_bound",
        "plan_bound",
        "acceptance_revised",
        "checkpoint_recorded",
        "story_issued",
        "story_returned",
        "story_accepted",
        "blocker_classified",
        "host_state_observed",
        "goal_cancelled",
        "goal_superseded",
    }
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def workspace_snapshot(
    root: Path,
    state_dir: Path | None = None,
    protected_patterns: list[str] | None = None,
) -> dict[str, Any]:
    """Capture the stronger v2 identity used only by the host ledger."""

    selected_patterns = protected_patterns
    if (
        selected_patterns is None
        and state_dir is not None
        and (state_dir / STATE_NAME).is_file()
        and not (state_dir / STATE_NAME).is_symlink()
    ):
        selected_patterns = workspace_patterns(
            strict_json(state_dir / STATE_NAME)
        )
    return primitive_workspace_snapshot(
        root,
        state_dir,
        selected_patterns,
        snapshot_version=2,
    )


def stable_result(
    ok: bool,
    status: str,
    *,
    issues: list[str] | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "status": status,
        "issues": issues or [],
        "result": result or {},
    }


def emit(value: dict[str, Any]) -> int:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )
    if value["ok"]:
        return 0
    return 2 if value["status"] == "review_required" else 1


def is_portable_id(value: Any) -> bool:
    return isinstance(value, str) and PORTABLE_ID.fullmatch(value) is not None


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def validate_acceptance(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ValueError("acceptance must be a non-empty array")
    result: list[dict[str, str]] = []
    for item in value:
        if (
            not isinstance(item, dict)
            or set(item) != {"id", "text"}
            or not is_portable_id(item.get("id"))
            or not isinstance(item.get("text"), str)
            or not item["text"].strip()
        ):
            raise ValueError(
                "acceptance items require portable id and non-empty text"
            )
        result.append({"id": item["id"], "text": item["text"].strip()})
    identifiers = [item["id"] for item in result]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("acceptance IDs must be unique")
    return result


def acceptance_artifact(path_value: str) -> list[dict[str, str]]:
    artifact = strict_json(Path(path_value).expanduser().resolve())
    if set(artifact) - {"acceptance", "reason"}:
        raise ValueError("acceptance artifact contains unknown fields")
    return validate_acceptance(artifact.get("acceptance"))


def input_policy_issues(value: Any, label: str) -> list[str]:
    try:
        import goal_runtime
    except ImportError:
        from . import goal_runtime
    return goal_runtime.untrusted_policy_issues(value, label)


try:
    from capability_model import prohibited_paid_data_reasons
except ImportError:
    from .capability_model import prohibited_paid_data_reasons


def validated_plan_artifact(path: Path) -> tuple[str, bytes]:
    """Read a text Plan Packet only after secret/authority policy checks."""

    suffix = path.suffix.lower()
    if suffix not in {".json", ".md", ".txt"}:
        raise ValueError(
            "plan artifact must be UTF-8 JSON, Markdown, or text"
        )
    content = path.read_bytes()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("plan artifact must be valid UTF-8 text") from exc
    if "\x00" in text:
        raise ValueError("plan artifact must not contain NUL bytes")
    if suffix == ".json":
        def reject_non_finite(value: str) -> None:
            raise ValueError(
                f"plan artifact contains non-finite JSON: {value}"
            )

        def reject_duplicate_keys(
            pairs: list[tuple[str, Any]],
        ) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(
                        f"plan artifact contains duplicate JSON key: {key}"
                    )
                result[key] = value
            return result

        policy_value = json.loads(
            text,
            parse_constant=reject_non_finite,
            object_pairs_hook=reject_duplicate_keys,
        )
    else:
        policy_value = text
    issues = input_policy_issues(policy_value, "plan artifact")
    try:
        from capability_model import paid_approval_text_reasons
    except ImportError:
        from .capability_model import paid_approval_text_reasons
    issues.extend(
        f"plan artifact policy: {issue}"
        for issue in paid_approval_text_reasons(text)
    )
    issues.extend(
        f"plan artifact policy: {issue}"
        for issue in prohibited_paid_data_reasons(text)
    )
    if issues:
        raise ValueError("; ".join(dict.fromkeys(issues)))
    return suffix, content


def acceptance_revision(
    revision: int,
    acceptance: list[dict[str, str]],
    *,
    reason: str,
    recorded_at: str,
    steering: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    body = {
        "revision": revision,
        "reason": reason,
        "recorded_at": recorded_at,
        "acceptance": acceptance,
    }
    if steering is not None:
        body["steering"] = steering
    return {**body, "sha256": digest(body)}


def normalize_steering(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("steering must be a non-empty array")
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {
            "op",
            "source_ids",
            "target_ids",
        }:
            raise ValueError(
                "steering entries require only op, source_ids, and target_ids"
            )
        op = item.get("op")
        source_ids = item.get("source_ids")
        target_ids = item.get("target_ids")
        if not isinstance(op, str) or op not in STEERING_OPS:
            raise ValueError(f"unknown steering operation: {op!r}")
        for label, identifiers in (
            ("source_ids", source_ids),
            ("target_ids", target_ids),
        ):
            if (
                not isinstance(identifiers, list)
                or not all(is_portable_id(identifier) for identifier in identifiers)
                or len(identifiers) != len(set(identifiers))
            ):
                raise ValueError(
                    f"steering {label} must contain unique portable IDs"
                )
        normalized.append(
            {
                "op": op,
                "source_ids": list(source_ids),
                "target_ids": list(target_ids),
            }
        )
    if len({digest(item) for item in normalized}) != len(normalized):
        raise ValueError("steering entries must be unique")
    return normalized


def validate_steering(
    value: Any,
    previous: list[dict[str, str]],
    current: list[dict[str, str]],
) -> list[dict[str, Any]]:
    steering = normalize_steering(value)
    previous_by_id = {item["id"]: item["text"] for item in previous}
    current_by_id = {item["id"]: item["text"] for item in current}
    previous_ids = [item["id"] for item in previous]
    current_ids = [item["id"] for item in current]
    previous_set = set(previous_ids)
    current_set = set(current_ids)
    added = current_set - previous_set
    retired = previous_set - current_set
    common = previous_set & current_set
    clarified = {
        identifier
        for identifier in common
        if previous_by_id[identifier] != current_by_id[identifier]
    }
    previous_common_order = [
        identifier for identifier in previous_ids if identifier in common
    ]
    current_common_order = [
        identifier for identifier in current_ids if identifier in common
    ]
    order_changed = previous_common_order != current_common_order
    if not (added or retired or clarified or order_changed):
        raise ValueError("steering requires an acceptance change")

    covered_added: set[str] = set()
    covered_retired: set[str] = set()
    covered_clarified: set[str] = set()
    reorder_covers_change = False

    def claim(
        covered: set[str],
        identifiers: set[str],
        change_kind: str,
    ) -> None:
        overlap = covered & identifiers
        if overlap:
            raise ValueError(
                "steering explains the same "
                f"{change_kind} acceptance ID more than once: "
                + ", ".join(sorted(overlap))
            )
        covered.update(identifiers)

    for entry in steering:
        op = entry["op"]
        sources = entry["source_ids"]
        targets = entry["target_ids"]
        source_set = set(sources)
        target_set = set(targets)
        if not source_set.issubset(previous_set):
            raise ValueError("steering source_ids must exist in the prior revision")
        if not target_set.issubset(current_set):
            raise ValueError("steering target_ids must exist in the new revision")

        if op == "clarify":
            if (
                not sources
                or sources != targets
                or not source_set.issubset(clarified)
            ):
                raise ValueError(
                    "clarify must map text-changed IDs to themselves"
                )
            claim(covered_clarified, source_set, "clarified")
        elif op == "add":
            if sources or not targets or not target_set.issubset(added):
                raise ValueError("add must map no sources to newly added IDs")
            claim(covered_added, target_set, "added")
        elif op == "retire":
            if targets or not sources or not source_set.issubset(retired):
                raise ValueError(
                    "retire must map retired IDs to no targets"
                )
            claim(covered_retired, source_set, "retired")
        elif op == "split":
            if (
                len(sources) != 1
                or len(targets) < 2
                or not source_set.issubset(retired)
                or not target_set.issubset(added)
            ):
                raise ValueError(
                    "split must map one retired ID to at least two added IDs"
                )
            claim(covered_retired, source_set, "retired")
            claim(covered_added, target_set, "added")
        elif op == "merge":
            if (
                len(sources) < 2
                or len(targets) != 1
                or not source_set.issubset(retired)
                or not target_set.issubset(added)
            ):
                raise ValueError(
                    "merge must map at least two retired IDs to one added ID"
                )
            claim(covered_retired, source_set, "retired")
            claim(covered_added, target_set, "added")
        elif op == "replace":
            if (
                not sources
                or not targets
                or not source_set.issubset(retired)
                or not target_set.issubset(added)
            ):
                raise ValueError(
                    "replace must map retired IDs to explicit added IDs"
                )
            claim(covered_retired, source_set, "retired")
            claim(covered_added, target_set, "added")
        elif op == "reorder":
            if (
                len(sources) < 2
                or set(sources) != set(targets)
                or sources == targets
                or sources != previous_common_order
                or targets != current_common_order
            ):
                raise ValueError(
                    "reorder must map the full prior common order to the "
                    "full new common order"
                )
            reorder_covers_change = True

    if covered_added != added:
        raise ValueError("steering does not explain every added acceptance ID")
    if covered_retired != retired:
        raise ValueError("steering does not explain every retired acceptance ID")
    if covered_clarified != clarified:
        raise ValueError("steering does not explain every clarified acceptance ID")
    if reorder_covers_change != order_changed:
        raise ValueError("steering does not explain the acceptance order change")
    return steering


def current_plan_revision(state: dict[str, Any]) -> int:
    plan = state.get("plan")
    return (
        int(plan.get("revision", 0))
        if isinstance(plan, dict)
        else 0
    )


def goal_delivery(state: dict[str, Any]) -> str:
    """Return explicit delivery or infer it for pre-axis ledger state."""

    delivery = state.get("delivery")
    if delivery in DELIVERY_LEVELS:
        return delivery
    policy = state.get("proof_policy")
    capabilities = (
        policy.get("required_capabilities", [])
        if isinstance(policy, dict)
        else []
    )
    if (
        state.get("assurance") == "release"
        or (
            isinstance(capabilities, list)
            and "remote-release" in capabilities
        )
    ):
        return "release"
    return "local"


def current_plan_binding_issues(state: dict[str, Any]) -> list[str]:
    """Require strict/release work to use the current acceptance-bound Plan."""

    if state.get("assurance") not in {"strict", "release"}:
        return []
    plan = state.get("plan")
    acceptance_revision_value = state.get("acceptance_revision")
    if not isinstance(plan, dict):
        return ["strict/release Goal lacks a current reviewed Plan"]
    if plan.get("acceptance_revision") != acceptance_revision_value:
        return [
            "strict/release current reviewed Plan does not bind the current "
            "acceptance revision"
        ]
    return []


def required_review_roles(assurance: str) -> list[str]:
    if assurance not in ASSURANCE_REVIEW_ROLES:
        raise ValueError(f"unknown assurance: {assurance}")
    return list(ASSURANCE_REVIEW_ROLES[assurance])


def required_gates(
    assurance: str,
    capabilities: list[str],
    *,
    custom_gates: list[str] | None = None,
) -> list[str]:
    if assurance not in ASSURANCE_GATES:
        raise ValueError(f"unknown assurance: {assurance}")
    try:
        from capability_model import CAPABILITY_GATES
    except ImportError:
        from .capability_model import CAPABILITY_GATES
    gates = set(ASSURANCE_GATES[assurance])
    for capability in capabilities:
        gates.update(CAPABILITY_GATES.get(capability, ()))
    gates.update(custom_gates or [])
    return sorted(gates)


def default_state_dir(root: Path, goal_id: str) -> Path:
    binding = project_binding(root)
    codex_root = Path(
        os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
    ).expanduser()
    return Path(
        os.path.abspath(
            codex_root
            / "state"
            / "quant-goals"
            / binding["identity_sha256"][:24]
            / goal_id
        )
    )


def unresolved_absolute_path(path_value: str | Path) -> Path:
    """Normalize a declared path without following its final component."""

    return Path(os.path.abspath(Path(path_value).expanduser()))


def checked_state_root(path_value: str | Path) -> Path:
    """Reject a declared state-root substitution before resolving it."""

    declared = unresolved_absolute_path(path_value)
    try:
        metadata = os.lstat(declared)
    except FileNotFoundError as exc:
        raise ValueError(
            f"state directory does not exist: {declared}"
        ) from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError("declared state directory must not be a symlink")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("declared state directory must be a directory")
    return declared.resolve(strict=True)


def state_root_binding(state_dir: Path) -> dict[str, Any]:
    """Bind the real state root, including replacement-sensitive identity."""

    metadata = os.lstat(state_dir)
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("state directory binding requires a real directory")
    unsigned = {
        "path_realpath": str(state_dir.resolve(strict=True)),
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
    }
    return {**unsigned, "binding_sha256": digest(unsigned)}


def state_root_binding_issues(
    state_dir: Path,
    state: dict[str, Any],
) -> list[str]:
    recorded = state.get("state_root")
    if not isinstance(recorded, dict):
        return ["goal ledger state-root binding is missing"]
    unsigned = {
        key: recorded.get(key)
        for key in ("path_realpath", "device", "inode")
    }
    if recorded.get("binding_sha256") != digest(unsigned):
        return ["goal ledger state-root binding hash mismatch"]
    try:
        current = state_root_binding(state_dir)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    if current != recorded:
        return ["goal ledger state-root binding changed"]
    return []


def command_state_dir(path_value: str | Path) -> Path:
    """Resolve an existing command state root after a pre-lock binding check."""

    state_dir = checked_state_root(path_value)
    ensure_core_state_artifacts(
        state_dir,
        artifact_names=CORE_ARTIFACTS,
    )
    state_path = state_dir / STATE_NAME
    if not state_path.is_file():
        raise ValueError("goal ledger state cache is missing")
    state = strict_json(state_path)
    issues = state_root_binding_issues(state_dir, state)
    if issues:
        raise ValueError("; ".join(issues))
    return state_dir


def resolve_state_dir(
    root: Path,
    goal_id: str,
    path_value: str | None,
    *,
    project_local: bool,
) -> Path:
    raw = (
        unresolved_absolute_path(path_value)
        if path_value
        else default_state_dir(root, goal_id)
    )
    if raw.is_symlink():
        raise ValueError("state directory must not be a symbolic link")
    state_dir = raw.resolve()
    try:
        state_dir.relative_to(root)
        inside = True
    except ValueError:
        inside = False
    if inside and not project_local:
        raise ValueError(
            "project-local state requires explicit --project-local"
        )
    if project_local and not inside:
        raise ValueError(
            "--project-local requires --state-dir inside the project root"
        )
    ensure_state_location(
        root,
        state_dir,
        artifact_names=CORE_ARTIFACTS,
        nested_artifacts=(
            "plans/plan.md",
            "stories/story.json",
            "reviews/review.json",
            "receipts/receipt.json",
            "orphaned/artifact.orphan",
        ),
    )
    return state_dir


def state_artifact_dir(
    state_dir: Path,
    *parts: str,
    create: bool = False,
) -> Path:
    current = state_dir
    for part in parts:
        if not is_portable_id(part):
            raise ValueError(f"invalid state artifact directory: {part}")
        current = current / part
        if current.is_symlink():
            raise ValueError(
                f"state artifact directory must not be a symlink: {part}"
            )
        if create:
            current.mkdir(exist_ok=True)
        if not current.is_dir():
            raise ValueError(
                f"state artifact directory is missing: {current}"
            )
    return current


def state_artifact_path(
    state_dir: Path,
    directories: tuple[str, ...],
    artifact_id: str,
    *,
    suffix: str = ".json",
    create_parent: bool = False,
) -> Path:
    if not is_portable_id(artifact_id):
        raise ValueError("artifact ID must be portable")
    parent = state_artifact_dir(
        state_dir,
        *directories,
        create=create_parent,
    )
    candidate = parent / f"{artifact_id}{suffix}"
    if candidate.is_symlink():
        raise ValueError(
            f"state artifact must not be a symlink: {candidate.name}"
        )
    return candidate


def stored_artifact_path(state_dir: Path, relative: str) -> Path:
    """Resolve a ledger-bound artifact without following directory symlinks."""
    if not portable_relative(relative):
        raise ValueError("stored artifact path is invalid")
    parts = Path(relative).parts
    if not parts:
        raise ValueError("stored artifact path is invalid")
    parent = state_artifact_dir(state_dir, *parts[:-1])
    candidate = parent / parts[-1]
    if candidate.is_symlink():
        raise ValueError(
            f"state artifact must not be a symlink: {candidate.name}"
        )
    return candidate


def preserve_unbound_artifact(state_dir: Path, path: Path) -> Path:
    """Move a pre-journal orphan aside without rewriting immutable history."""

    if path.is_symlink() or not path.is_file():
        raise ValueError("unbound artifact must be a regular file")
    try:
        path.relative_to(state_dir)
    except ValueError as exc:
        raise ValueError("unbound artifact escapes state directory") from exc
    content_sha256 = file_digest(path)
    archive_dir = state_artifact_dir(state_dir, "orphaned", create=True)
    archive = archive_dir / (
        f"{path.name}-{content_sha256}.orphan"
    )
    if archive.is_symlink():
        raise ValueError("orphan archive must not be a symbolic link")
    if archive.exists():
        if not archive.is_file() or archive.read_bytes() != path.read_bytes():
            raise ValueError("orphan archive hash collision")
        path.unlink()
        fsync_directory(path.parent)
        return archive
    os.replace(path, archive)
    fsync_directory(path.parent)
    if archive_dir != path.parent:
        fsync_directory(archive_dir)
    return archive


def write_unbound_immutable(
    state_dir: Path,
    path: Path,
    payload: bytes,
) -> None:
    """Write the next unbound artifact, adopting or preserving crash debris."""

    if path.is_symlink():
        raise ValueError("immutable artifact must not be a symbolic link")
    if path.exists():
        if not path.is_file():
            raise ValueError("immutable artifact path is not a regular file")
        if path.read_bytes() == payload:
            return
        preserve_unbound_artifact(state_dir, path)
    atomic_bytes(path, payload)


def protected_patterns(state: dict[str, Any]) -> list[str]:
    policy = state.get("proof_policy")
    manifest_binding = (
        policy.get("manifest") if isinstance(policy, dict) else None
    )
    if not isinstance(manifest_binding, dict):
        return []
    path = Path(manifest_binding.get("path_realpath", ""))
    manifest = strict_json(path)
    try:
        import goal_runtime
    except ImportError:
        from . import goal_runtime
    return goal_runtime.protected_patterns_from_manifest(manifest)


def workspace_patterns(state: dict[str, Any]) -> list[str]:
    """Track manifest contracts and every issued Story scope, including ignored paths."""

    patterns = set(protected_patterns(state))
    for story in state.get("stories", {}).values():
        if not isinstance(story, dict):
            continue
        for field in ("write_scope", "protected_scope"):
            values = story.get(field)
            if isinstance(values, list):
                patterns.update(
                    value
                    for value in values
                    if isinstance(value, str) and portable_relative(value)
                )
    return sorted(patterns)


def review_scope_binding(
    root: Path,
    state_dir: Path,
    patterns: Any,
) -> dict[str, Any]:
    if (
        not isinstance(patterns, list)
        or len(patterns) != len(set(patterns))
        or not all(
            isinstance(value, str) and portable_relative(value)
            for value in patterns
        )
    ):
        raise ValueError(
            "review scope patterns must be unique portable paths"
        )
    normalized = sorted(patterns)
    try:
        import goal_runtime
    except ImportError:
        from . import goal_runtime
    symlink_issues = goal_runtime.project_scope_symlink_issues(
        root,
        state_dir,
        normalized,
        scope_label="review",
    )
    state_issues = goal_runtime.project_scope_state_issues(
        root,
        state_dir,
        normalized,
        scope_label="review",
    )
    if symlink_issues or state_issues:
        raise ValueError("; ".join([*symlink_issues, *state_issues]))
    captured = protected_path_snapshot(
        root.resolve(),
        normalized,
        state_dir.resolve(),
        snapshot_version=2,
    )
    visible = {
        path: value
        for path, value in captured.items()
        if ".git" not in {
            segment.casefold()
            for segment in Path(path).parts
        }
    }
    body = {"patterns": normalized, "paths": visible}
    return {
        "patterns": normalized,
        "sha256": digest(body),
    }


def snapshot_identity(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "sha256": snapshot["sha256"],
        "head": snapshot.get("head"),
        "branch": snapshot.get("branch"),
        "changed_paths": sorted(snapshot_paths(snapshot)),
    }


def make_event(
    state: dict[str, Any] | None,
    *,
    goal_id: str,
    event_type: str,
    payload: dict[str, Any],
    workspace: dict[str, Any],
) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unsupported event type: {event_type}")
    ledger = state.get("ledger", {}) if isinstance(state, dict) else {}
    event = {
        "document_type": "quant_goal_ledger_event",
        "schema_version": 1,
        "goal_id": goal_id,
        "seq": int(ledger.get("event_count", 0)) + 1,
        "type": event_type,
        "at": now(),
        "payload": payload,
        "workspace": snapshot_identity(workspace),
        "previous_sha256": ledger.get("tail_sha256", GENESIS),
    }
    return seal_hash_chain_event(event)


def read_ledger(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    return read_hash_chain(
        path,
        allowed_event_types=EVENT_TYPES,
        label="goal ledger",
        missing_error=f"{LEDGER_NAME} is missing",
    )


def event_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def reduce_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events or events[0].get("type") != "goal_bound":
        raise ValueError("goal ledger must begin with goal_bound")
    genesis = event_payload(events[0])
    created_at = events[0].get("at")
    initial_revision = genesis.get("acceptance_revision")
    if not isinstance(initial_revision, dict):
        raise ValueError("goal_bound acceptance revision is invalid")
    state: dict[str, Any] = {
        "$schema": STATE_SCHEMA,
        "document_type": "quant_goal_ledger_state",
        "schema_version": 1,
        "goal_id": events[0].get("goal_id"),
        "project_id": genesis.get("project_id"),
        "project_binding": genesis.get("project_binding"),
        "state_root": genesis.get("state_root"),
        "host": genesis.get("host"),
        "objective": genesis.get("objective"),
        "objective_sha256": genesis.get("objective_sha256"),
        "acceptance": initial_revision.get("acceptance"),
        "acceptance_revision": initial_revision.get("revision"),
        "acceptance_revisions": [initial_revision],
        "plan": None,
        "plan_revisions": [],
        "assurance": genesis.get("assurance"),
        "proof_policy": genesis.get("proof_policy"),
        "checkpoint": None,
        "blockers": {},
        "next_action": None,
        "stories": {},
        "reviews": [],
        "review_context": {"terminal_after_event_seq": 0},
        "completion_ready": None,
        "completion_history": [],
        "ledger": {
            "path": LEDGER_NAME,
            "event_count": 0,
            "tail_sha256": GENESIS,
        },
        "workspace": {
            "project_fingerprint": genesis.get("project_fingerprint"),
            "last_event_workspace_sha256": events[0]
            .get("workspace", {})
            .get("sha256"),
        },
        "created_at": created_at,
        "updated_at": created_at,
    }
    if "delivery" in genesis:
        state["delivery"] = genesis.get("delivery")
    for event in events:
        payload = event_payload(event)
        event_type = event.get("type")
        previous_host_state = state["host"]["last_observed_state"]
        completion_was_ready = state["completion_ready"] is not None
        if event_type in STALE_COMPLETION_EVENTS:
            state["completion_ready"] = None
        if event_type == "plan_bound":
            plan = payload.get("plan")
            if not isinstance(plan, dict):
                raise ValueError("plan_bound payload is invalid")
            state["plan"] = plan
            state["plan_revisions"].append(plan)
        elif event_type == "acceptance_revised":
            revision = payload.get("acceptance_revision")
            if not isinstance(revision, dict):
                raise ValueError("acceptance_revised payload is invalid")
            for story in state["stories"].values():
                if (
                    isinstance(story, dict)
                    and story.get("status") in {"open", "returned"}
                ):
                    story["status"] = "superseded"
                    story["superseded_by_acceptance_revision"] = (
                        revision.get("revision")
                    )
            state["acceptance"] = revision.get("acceptance")
            state["acceptance_revision"] = revision.get("revision")
            state["acceptance_revisions"].append(revision)
        elif event_type == "blocker_classified":
            blocker = payload.get("blocker")
            if not isinstance(blocker, dict):
                raise ValueError("blocker_classified payload is invalid")
            state["blockers"][blocker.get("id")] = blocker
        elif event_type == "checkpoint_recorded":
            checkpoint = payload.get("checkpoint")
            if not isinstance(checkpoint, dict):
                raise ValueError("checkpoint_recorded payload is invalid")
            state["checkpoint"] = checkpoint
            state["next_action"] = checkpoint.get("next_action")
        elif event_type == "continuation_capsule_recorded":
            capsule = payload.get("continuation_capsule")
            if not isinstance(capsule, dict):
                raise ValueError(
                    "continuation_capsule_recorded payload is invalid"
                )
            state["continuation_capsule"] = capsule
            state["next_action"] = capsule.get("next_action")
        elif event_type == "story_issued":
            story_id = payload.get("story_id")
            state["stories"][story_id] = {
                "status": "open",
                "mode": payload.get("mode"),
                "envelope_sha256": payload.get("envelope_sha256"),
                "baseline_workspace_sha256": payload.get(
                    "baseline_workspace_sha256"
                ),
                "plan_revision": payload.get("plan_revision"),
                "acceptance_revision": payload.get("acceptance_revision"),
                "acceptance_ids": payload.get("acceptance_ids"),
                "write_scope": payload.get("write_scope"),
                "protected_scope": payload.get("protected_scope"),
                "superseded_by_acceptance_revision": None,
                "receipt_sha256": None,
                "receipt_path": None,
                "return_count": 0,
                "returns": [],
                "returned_workspace_sha256": None,
            }
        elif event_type == "story_returned":
            story_id = payload.get("story_id")
            story = state["stories"].get(story_id)
            if not isinstance(story, dict):
                raise ValueError("story_returned references unknown story")
            returned = {
                "receipt_sha256": payload.get("receipt_sha256"),
                "receipt_path": payload.get("receipt_path"),
                "return_count": payload.get("return_count"),
                "workspace_sha256": payload.get("workspace_sha256"),
            }
            story["returns"].append(returned)
            story.update(
                {
                    "status": "returned",
                    **returned,
                    "returned_workspace_sha256": returned[
                        "workspace_sha256"
                    ],
                }
            )
        elif event_type == "story_accepted":
            story_id = payload.get("story_id")
            story = state["stories"].get(story_id)
            if not isinstance(story, dict):
                raise ValueError("story_accepted references unknown story")
            story["status"] = "accepted"
        elif event_type == "review_recorded":
            review = payload.get("review")
            if not isinstance(review, dict):
                raise ValueError("review_recorded payload is invalid")
            state["reviews"].append(review)
        elif event_type == "completion_ready":
            completion = payload.get("completion")
            if not isinstance(completion, dict):
                raise ValueError("completion_ready payload is invalid")
            state["completion_ready"] = completion
            state["completion_history"].append(completion)
        elif event_type in {
            "host_state_observed",
            "goal_cancelled",
            "goal_superseded",
        }:
            host = payload.get("host")
            if not isinstance(host, dict):
                raise ValueError("host observation payload is invalid")
            state["host"] = host
        if event_type in TERMINAL_CONTEXT_EVENTS:
            host_readback_after_completion = (
                event_type == "host_state_observed"
                and completion_was_ready
                and state["completion_ready"] is not None
            )
            same_semantic_host_refresh = (
                event_type == "host_state_observed"
                and state["host"]["last_observed_state"]
                == previous_host_state
            )
            if (
                not host_readback_after_completion
                and not same_semantic_host_refresh
            ):
                state["review_context"][
                    "terminal_after_event_seq"
                ] = event.get("seq")
        elif event_type == "review_recorded":
            review = payload.get("review")
            if (
                isinstance(review, dict)
                and review.get("role") != "terminal_critic"
            ):
                state["review_context"][
                    "terminal_after_event_seq"
                ] = event.get("seq")
        state["ledger"] = {
            "path": LEDGER_NAME,
            "event_count": event.get("seq"),
            "tail_sha256": event.get("event_sha256"),
        }
        state["workspace"][
            "last_event_workspace_sha256"
        ] = event.get("workspace", {}).get("sha256")
        state["updated_at"] = event.get("at")
    return state


def clear_pending(state_dir: Path) -> None:
    clear_pending_transaction(state_dir, pending_name=PENDING_NAME)


def recover_pending(state_dir: Path) -> bool:
    return recover_pending_transaction(
        state_dir,
        allowed_event_types=EVENT_TYPES,
        state_name=STATE_NAME,
        ledger_name=LEDGER_NAME,
        pending_name=PENDING_NAME,
        pending_document_type="quant_goal_ledger_pending_event",
        artifact_names=CORE_ARTIFACTS,
    )


def persist_event(
    state_dir: Path,
    state: dict[str, Any] | None,
    event: dict[str, Any],
) -> dict[str, Any]:
    if (state_dir / LEDGER_NAME).exists():
        events, errors = read_ledger(state_dir / LEDGER_NAME)
        if errors:
            raise ValueError("; ".join(errors))
    else:
        events = []
    expected_previous = (
        events[-1]["event_sha256"] if events else GENESIS
    )
    if event.get("previous_sha256") != expected_previous:
        raise ValueError("event previous hash does not match ledger")
    if event.get("seq") != len(events) + 1:
        raise ValueError("event sequence does not match ledger")
    updated = reduce_events([*events, event])
    atomic_json(
        state_dir / PENDING_NAME,
        pending_transaction(
            event,
            updated,
            document_type="quant_goal_ledger_pending_event",
        ),
    )
    append_event(state_dir / LEDGER_NAME, event)
    atomic_json(state_dir / STATE_NAME, updated)
    clear_pending(state_dir)
    return updated


def artifact_file_issues(
    state_dir: Path,
    state: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    try:
        import goal_runtime
    except ImportError:
        from . import goal_runtime
    for plan in state.get("plan_revisions", []):
        if not isinstance(plan, dict):
            errors.append("plan revision cache is invalid")
            continue
        relative = plan.get("artifact_path")
        if not isinstance(relative, str) or not portable_relative(relative):
            errors.append("plan artifact path is invalid")
            continue
        try:
            path = stored_artifact_path(state_dir, relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not path.is_file():
            errors.append("plan artifact is missing or symbolic")
        elif file_digest(path) != plan.get("sha256"):
            errors.append("plan artifact hash mismatch")
        else:
            try:
                validated_plan_artifact(path)
            except (
                OSError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                errors.append(f"plan artifact policy is invalid: {exc}")
    for story_id, story in state.get("stories", {}).items():
        try:
            envelope_path = state_artifact_path(
                state_dir, ("stories",), story_id
            )
            baseline_path = state_artifact_path(
                state_dir,
                ("stories",),
                story_id,
                suffix=".baseline.json",
            )
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not envelope_path.is_file() or envelope_path.is_symlink():
            errors.append(f"story {story_id} envelope is missing or symbolic")
        else:
            try:
                envelope = strict_json(envelope_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"story {story_id} envelope is invalid: {exc}")
            else:
                if (
                    envelope.get("envelope_sha256")
                    != goal_runtime.envelope_hash(envelope)
                    or envelope.get("envelope_sha256")
                    != story.get("envelope_sha256")
                    or envelope.get("baseline_workspace_sha256")
                    != story.get("baseline_workspace_sha256")
                    or envelope.get("write_scope")
                    != story.get("write_scope")
                    or envelope.get("protected_scope")
                    != story.get("protected_scope")
                    or [
                        item.get("id")
                        for item in envelope.get("acceptance", [])
                        if isinstance(item, dict)
                    ]
                    != story.get("acceptance_ids")
                ):
                    errors.append(
                        f"story {story_id} envelope is not ledger-bound"
                    )
        if not baseline_path.is_file() or baseline_path.is_symlink():
            errors.append(f"story {story_id} baseline is missing or symbolic")
        else:
            try:
                baseline = strict_json(baseline_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"story {story_id} baseline is invalid: {exc}")
            else:
                if (
                    not verify_workspace_snapshot(baseline)
                    or baseline.get("sha256")
                    != story.get("baseline_workspace_sha256")
                ):
                    errors.append(
                        f"story {story_id} baseline is not ledger-bound"
                    )
        for returned in story.get("returns", []):
            receipt_path = (
                returned.get("receipt_path")
                if isinstance(returned, dict)
                else None
            )
            if (
                not isinstance(receipt_path, str)
                or not portable_relative(receipt_path)
            ):
                errors.append(f"story {story_id} receipt path is invalid")
                continue
            try:
                path = stored_artifact_path(state_dir, receipt_path)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if not path.is_file():
                errors.append(
                    f"story {story_id} receipt is missing or symbolic"
                )
            else:
                try:
                    receipt = strict_json(path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(
                        f"story {story_id} receipt is invalid: {exc}"
                    )
                else:
                    if (
                        receipt.get("receipt_sha256")
                        != goal_runtime.receipt_hash(receipt)
                        or receipt.get("receipt_sha256")
                        != returned.get("receipt_sha256")
                    ):
                        errors.append(
                            f"story {story_id} receipt is not ledger-bound"
                        )
    for review in state.get("reviews", []):
        review_id = review.get("review_id") if isinstance(review, dict) else None
        try:
            path = state_artifact_path(
                state_dir, ("reviews",), review_id
            )
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if path.is_symlink() or not path.is_file():
            errors.append(f"review {review_id} receipt is missing or symbolic")
            continue
        try:
            receipt = strict_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"review {review_id} receipt is invalid: {exc}")
            continue
        if (
            receipt.get("receipt_sha256") != review_receipt_hash(receipt)
            or receipt.get("receipt_sha256") != review.get("receipt_sha256")
            or receipt.get("review_scope") != review.get("review_scope")
            or receipt.get("carry_forward_from_receipt_sha256")
            != review.get("carry_forward_from_receipt_sha256")
            or sorted(
                finding.get("id")
                for finding in receipt.get("findings", [])
                if isinstance(finding, dict)
                and finding.get("severity") == "blocking"
                and finding.get("status") == "open"
            )
            != review.get("open_blocking_finding_ids")
            or sorted(
                finding.get("id")
                for finding in receipt.get("findings", [])
                if isinstance(finding, dict)
                and finding.get("severity") == "blocking"
                and finding.get("status") == "resolved"
            )
            != review.get("resolved_finding_ids")
        ):
            errors.append(f"review {review_id} receipt is not ledger-bound")
    for completion in state.get("completion_history", []):
        relative = (
            completion.get("receipt_path")
            if isinstance(completion, dict)
            else None
        )
        if not isinstance(relative, str) or not portable_relative(relative):
            errors.append("final receipt path is invalid")
            continue
        try:
            path = stored_artifact_path(state_dir, relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not path.is_file():
            errors.append("final receipt is missing or symbolic")
        else:
            try:
                receipt = strict_json(path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"final receipt is invalid: {exc}")
            else:
                if digest(receipt) != completion.get("receipt_sha256"):
                    errors.append("final receipt is not ledger-bound")
    return errors


def continuation_capsule_shape_issues(value: Any) -> list[str]:
    if value is None:
        return []
    required = {
        "kind",
        "context_sha256",
        "acceptance_revision",
        "plan_revision",
        "workspace_sha256",
        "open_work",
        "open_story_ids",
        "worker_states",
        "current_evidence_refs",
        "stale_evidence_refs",
        "blocker_ids",
        "pending_authority",
        "no_repeat",
        "next_action",
        "recorded_at",
        "sha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        return ["goal ledger continuation capsule shape is invalid"]
    errors: list[str] = []
    if value.get("kind") not in {"handoff", "suspension"}:
        errors.append("goal ledger continuation capsule kind is invalid")
    for field in ("context_sha256", "workspace_sha256"):
        if SHA256.fullmatch(str(value.get(field, ""))) is None:
            errors.append(
                f"goal ledger continuation capsule {field} is invalid"
            )
    for field, minimum in (
        ("acceptance_revision", 1),
        ("plan_revision", 0),
    ):
        field_value = value.get(field)
        if type(field_value) is not int or field_value < minimum:
            errors.append(
                f"goal ledger continuation capsule {field} is invalid"
            )
    for field in (
        "open_work",
        "open_story_ids",
        "current_evidence_refs",
        "stale_evidence_refs",
        "blocker_ids",
        "pending_authority",
        "no_repeat",
    ):
        items = value.get(field)
        if (
            not isinstance(items, list)
            or not all(
                isinstance(item, str) and item.strip()
                for item in items
            )
            or len(items) != len(set(items))
        ):
            errors.append(
                f"goal ledger continuation capsule {field} is invalid"
            )
    for field in ("open_story_ids", "blocker_ids"):
        items = value.get(field)
        if isinstance(items, list) and not all(
            is_portable_id(item) for item in items
        ):
            errors.append(
                f"goal ledger continuation capsule {field} is invalid"
            )
    workers = value.get("worker_states")
    if not isinstance(workers, list):
        errors.append(
            "goal ledger continuation capsule worker_states is invalid"
        )
    else:
        worker_ids: list[str] = []
        for worker in workers:
            if (
                not isinstance(worker, dict)
                or set(worker) != {"id", "status", "story_id"}
                or not is_portable_id(worker.get("id"))
                or not is_portable_id(worker.get("status"))
                or (
                    worker.get("story_id") is not None
                    and not is_portable_id(worker.get("story_id"))
                )
            ):
                errors.append(
                    "goal ledger continuation capsule worker_states is invalid"
                )
                break
            worker_ids.append(worker["id"])
        if len(worker_ids) != len(set(worker_ids)):
            errors.append(
                "goal ledger continuation capsule worker IDs must be unique"
            )
    current_refs = value.get("current_evidence_refs")
    stale_refs = value.get("stale_evidence_refs")
    if isinstance(current_refs, list) and isinstance(stale_refs, list):
        if set(current_refs) & set(stale_refs):
            errors.append(
                "goal ledger continuation evidence cannot be current and stale"
            )
    next_action = value.get("next_action")
    if next_action is not None and (
        not isinstance(next_action, str) or not next_action.strip()
    ):
        errors.append(
            "goal ledger continuation capsule next_action is invalid"
        )
    if parse_time(value.get("recorded_at")) is None:
        errors.append(
            "goal ledger continuation capsule recorded_at is invalid"
        )
    unsigned = {
        key: item for key, item in value.items() if key != "sha256"
    }
    if value.get("sha256") != digest(unsigned):
        errors.append("goal ledger continuation capsule hash mismatch")
    return errors


def state_shape_issues(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if state.get("document_type") != "quant_goal_ledger_state":
        errors.append("goal ledger state document_type is invalid")
    if state.get("schema_version") != 1:
        errors.append("goal ledger state schema_version must equal 1")
    if not is_portable_id(state.get("goal_id")):
        errors.append("goal ledger state goal_id is invalid")
    if not isinstance(state.get("project_id"), str) or not PROJECT_ID.fullmatch(
        state["project_id"]
    ):
        errors.append("goal ledger state project_id is invalid")
    state_root = state.get("state_root")
    if (
        not isinstance(state_root, dict)
        or set(state_root)
        != {"path_realpath", "device", "inode", "binding_sha256"}
        or not isinstance(state_root.get("path_realpath"), str)
        or not state_root["path_realpath"]
        or not isinstance(state_root.get("device"), int)
        or state_root["device"] < 0
        or not isinstance(state_root.get("inode"), int)
        or state_root["inode"] < 1
        or not SHA256.fullmatch(
            str(state_root.get("binding_sha256", ""))
        )
    ):
        errors.append("goal ledger state-root binding is invalid")
    else:
        unsigned_state_root = {
            key: state_root[key]
            for key in ("path_realpath", "device", "inode")
        }
        if state_root["binding_sha256"] != digest(unsigned_state_root):
            errors.append("goal ledger state-root binding hash mismatch")
    objective = state.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        errors.append("goal ledger objective is invalid")
    elif digest(objective) != state.get("objective_sha256"):
        errors.append("goal ledger objective hash mismatch")
    try:
        acceptance = validate_acceptance(state.get("acceptance"))
    except ValueError as exc:
        errors.append(str(exc))
        acceptance = []
    revision = state.get("acceptance_revision")
    revisions = state.get("acceptance_revisions")
    if (
        not isinstance(revision, int)
        or revision < 1
        or not isinstance(revisions, list)
        or not revisions
        or revisions[-1].get("revision") != revision
        or revisions[-1].get("acceptance") != acceptance
    ):
        errors.append("goal ledger acceptance revision cache is invalid")
    else:
        previous_acceptance: list[dict[str, str]] | None = None
        for index, item in enumerate(revisions, start=1):
            if not isinstance(item, dict) or item.get("revision") != index:
                errors.append("acceptance revisions must be contiguous")
                break
            unsigned = {
                key: item.get(key)
                for key in (
                    "revision",
                    "reason",
                    "recorded_at",
                    "acceptance",
                )
            }
            if "steering" in item:
                unsigned["steering"] = item.get("steering")
            if item.get("sha256") != digest(unsigned):
                errors.append("acceptance revision hash mismatch")
                break
            try:
                item_acceptance = validate_acceptance(item.get("acceptance"))
                if "steering" in item:
                    if previous_acceptance is None:
                        raise ValueError(
                            "initial acceptance revision cannot contain steering"
                        )
                    validate_steering(
                        item.get("steering"),
                        previous_acceptance,
                        item_acceptance,
                    )
            except ValueError as exc:
                errors.append(str(exc))
                break
            previous_acceptance = item_acceptance
    plans = state.get("plan_revisions")
    current_plan = state.get("plan")
    if not isinstance(plans, list):
        errors.append("goal ledger plan revisions are invalid")
    else:
        for index, plan in enumerate(plans, start=1):
            carried_from = (
                plan.get("carried_forward_from_revision")
                if isinstance(plan, dict)
                else None
            )
            if (
                not isinstance(plan, dict)
                or not {
                    "revision",
                    "acceptance_revision",
                    "sha256",
                    "artifact_path",
                    "recorded_at",
                }.issubset(plan)
                or set(plan)
                - {
                    "revision",
                    "acceptance_revision",
                    "sha256",
                    "artifact_path",
                    "recorded_at",
                    "carried_forward_from_revision",
                }
                or type(plan.get("revision")) is not int
                or plan.get("revision") != index
                or type(plan.get("acceptance_revision")) is not int
                or plan["acceptance_revision"] < 1
                or not isinstance(revision, int)
                or plan["acceptance_revision"] > revision
                or (
                    carried_from is not None
                    and (
                        type(carried_from) is not int
                        or carried_from < 1
                        or carried_from >= index
                    )
                )
            ):
                errors.append("goal ledger plan revisions are invalid")
                break
            if carried_from is not None:
                source = plans[carried_from - 1]
                if (
                    not isinstance(source, dict)
                    or source.get("sha256") != plan.get("sha256")
                ):
                    errors.append(
                        "goal ledger carried-forward Plan hash mismatch"
                    )
                    break
        if (plans[-1] if plans else None) != current_plan:
            errors.append("goal ledger current plan is not history-bound")
    errors.extend(
        continuation_capsule_shape_issues(
            state.get("continuation_capsule")
        )
    )
    stories = state.get("stories")
    if not isinstance(stories, dict):
        errors.append("goal ledger stories are invalid")
    else:
        for story_id, story in stories.items():
            if (
                not is_portable_id(story_id)
                or not isinstance(story, dict)
                or story.get("status")
                not in {"open", "returned", "accepted", "superseded"}
                or not isinstance(story.get("plan_revision"), int)
                or not isinstance(story.get("acceptance_revision"), int)
                or not isinstance(story.get("acceptance_ids"), list)
                or not all(
                    is_portable_id(value)
                    for value in story.get("acceptance_ids", [])
                )
                or len(story["acceptance_ids"])
                != len(set(story["acceptance_ids"]))
                or not isinstance(story.get("write_scope"), list)
                or not isinstance(story.get("protected_scope"), list)
                or not all(
                    isinstance(value, str) and portable_relative(value)
                    for value in [
                        *story.get("write_scope", []),
                        *story.get("protected_scope", []),
                    ]
                )
            ):
                errors.append("goal ledger story revision binding is invalid")
                break
    if state.get("assurance") not in ASSURANCE_LEVELS:
        errors.append("goal ledger assurance is invalid")
    if (
        "delivery" in state
        and state.get("delivery") not in DELIVERY_LEVELS
    ):
        errors.append("goal ledger delivery is invalid")
    host = state.get("host")
    if (
        not isinstance(host, dict)
        or not isinstance(host.get("goal_id"), str)
        or not host["goal_id"]
        or host.get("last_observed_state") not in HOST_STATES
        or parse_time(host.get("observed_at")) is None
        or not isinstance(host.get("source"), str)
        or not host["source"]
    ):
        errors.append("goal ledger host binding is invalid")
    policy = state.get("proof_policy")
    if not isinstance(policy, dict):
        errors.append("goal ledger proof policy is invalid")
    else:
        assurance = state.get("assurance")
        expected_roles = (
            required_review_roles(assurance)
            if assurance in ASSURANCE_LEVELS
            else []
        )
        if policy.get("required_review_roles") != expected_roles:
            errors.append("goal ledger review policy is invalid")
        if (
            not isinstance(policy.get("required_gates"), list)
            or len(policy["required_gates"])
            != len(set(policy["required_gates"]))
        ):
            errors.append("goal ledger gate policy is invalid")
        capabilities = policy.get("required_capabilities")
        has_remote_release = (
            isinstance(capabilities, list)
            and "remote-release" in capabilities
        )
        if goal_delivery(state) == "release" and not has_remote_release:
            errors.append(
                "release delivery requires remote-release capability"
            )
        if goal_delivery(state) == "local" and has_remote_release:
            errors.append(
                "local delivery conflicts with remote-release capability"
            )
    review_context = state.get("review_context")
    if (
        not isinstance(review_context, dict)
        or set(review_context) != {"terminal_after_event_seq"}
        or not isinstance(
            review_context.get("terminal_after_event_seq"), int
        )
        or review_context["terminal_after_event_seq"] < 1
    ):
        errors.append("goal ledger review context is invalid")
    completion_history = state.get("completion_history")
    if not isinstance(completion_history, list):
        errors.append("goal ledger completion history is invalid")
    else:
        for index, completion in enumerate(
            completion_history, start=1
        ):
            if (
                not isinstance(completion, dict)
                or completion.get("receipt_path")
                != f"receipts/final-r{index}.json"
                or completion.get("event_seq") is None
                or not isinstance(
                    completion.get("evidence_candidate_sha256"), str
                )
                or SHA256.fullmatch(
                    completion.get("evidence_candidate_sha256", "")
                )
                is None
            ):
                errors.append(
                    "goal ledger completion history is not contiguous"
                )
                break
            terminal_receipt = completion.get(
                "terminal_review_receipt_sha256"
            )
            expects_terminal = state.get("assurance") in {
                "strict",
                "release",
            }
            if (
                expects_terminal
                and (
                    not isinstance(terminal_receipt, str)
                    or SHA256.fullmatch(terminal_receipt) is None
                )
            ) or (
                not expects_terminal and terminal_receipt is not None
            ):
                errors.append(
                    "goal ledger completion terminal review binding "
                    "is invalid"
                )
                break
        current_completion = state.get("completion_ready")
        if (
            current_completion is not None
            and (
                not completion_history
                or current_completion != completion_history[-1]
            )
        ):
            errors.append(
                "goal ledger current completion is not history-bound"
            )
    return errors


def load_and_verify(
    root: Path,
    state_dir: Path,
    *,
    check_workspace: bool,
    recover: bool = False,
) -> tuple[
    dict[str, Any] | None,
    list[str],
    dict[str, Any] | None,
    list[dict[str, Any]],
]:
    errors: list[str] = []
    if recover:
        try:
            recover_pending(state_dir)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return (
                None,
                [f"pending transaction recovery failed: {exc}"],
                None,
                [],
            )
    elif (state_dir / PENDING_NAME).exists():
        return (
            None,
            [
                "pending transaction requires resume or a mutating command; "
                "read-only validation remains non-mutating"
            ],
            None,
            [],
        )
    try:
        ensure_core_state_artifacts(
            state_dir,
            artifact_names=CORE_ARTIFACTS,
        )
        state = strict_json(state_dir / STATE_NAME)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return None, [f"invalid goal ledger state: {exc}"], None, []
    errors.extend(state_shape_issues(state))
    events, ledger_errors = read_ledger(state_dir / LEDGER_NAME)
    errors.extend(ledger_errors)
    for event in events:
        if event.get("goal_id") != state.get("goal_id"):
            errors.append("goal ledger event goal_id mismatch")
    if not ledger_errors:
        try:
            reduced = reduce_events(events)
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"goal ledger reduction failed: {exc}")
        else:
            if state != reduced:
                errors.append("goal ledger state cache does not match ledger")
    current_binding = project_binding(root)
    stored_binding = state.get("project_binding")
    if (
        not isinstance(stored_binding, dict)
        or stored_binding.get("identity_sha256")
        != current_binding.get("identity_sha256")
    ):
        errors.append("goal ledger project binding changed")
    errors.extend(state_root_binding_issues(state_dir, state))
    policy = state.get("proof_policy")
    manifest = policy.get("manifest") if isinstance(policy, dict) else None
    if isinstance(manifest, dict):
        path = Path(manifest.get("path_realpath", ""))
        if (
            path.is_symlink()
            or not path.is_file()
            or file_digest(path) != manifest.get("sha256")
        ):
            errors.append("goal ledger manifest binding changed")
        else:
            try:
                path.resolve().relative_to(root.resolve())
            except ValueError:
                errors.append("goal ledger manifest resolves outside root")
    errors.extend(artifact_file_issues(state_dir, state))
    current: dict[str, Any] | None = None
    if check_workspace and not errors:
        current = workspace_snapshot(
            root,
            state_dir,
            workspace_patterns(state),
        )
    return state, errors, current, events


def mutation_blockers(
    state: dict[str, Any],
    *,
    allow_suspended: bool = False,
    allow_plan_repair: bool = False,
) -> list[str]:
    host = state.get("host")
    observed = (
        host.get("last_observed_state")
        if isinstance(host, dict)
        else None
    )
    if observed in TERMINAL_HOST_STATES:
        return [f"host Goal is {observed}"]
    if not allow_suspended and observed in {"waiting", "paused", "blocked"}:
        return [
            f"host Goal is {observed}; active-work mutation requires active"
        ]
    return [] if allow_plan_repair else current_plan_binding_issues(state)


def current_review_status_map(
    state: dict[str, Any],
    workspace_sha256: str,
) -> dict[str, dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    plan_revision = current_plan_revision(state)
    acceptance_revision_value = state.get("acceptance_revision")
    acceptance_ids = {
        item["id"]
        for item in state.get("acceptance", [])
        if isinstance(item, dict) and is_portable_id(item.get("id"))
    }
    review_context = state.get("review_context")
    terminal_after_event_seq = (
        review_context.get("terminal_after_event_seq", 0)
        if isinstance(review_context, dict)
        else 0
    )
    try:
        review_root = Path(
            state["project_binding"]["root_realpath"]
        )
        review_state_dir = Path(
            state["state_root"]["path_realpath"]
        )
    except (KeyError, TypeError):
        review_root = None
        review_state_dir = None
    for review in state.get("reviews", []):
        role = review.get("role") if isinstance(review, dict) else None
        bound_acceptance = (
            review.get("acceptance_ids", [])
            if isinstance(review, dict)
            else []
        )
        acceptance_subset_is_current = (
            isinstance(bound_acceptance, list)
            and bool(bound_acceptance)
            and len(bound_acceptance) == len(set(bound_acceptance))
            and set(bound_acceptance).issubset(acceptance_ids)
        )
        terminal_candidate_is_bound = (
            role != "terminal_critic"
            or (
                set(bound_acceptance) == acceptance_ids
                and isinstance(
                    review.get("evidence_candidate_sha256"), str
                )
                and SHA256.fullmatch(
                    review["evidence_candidate_sha256"]
                )
                is not None
            )
        )
        scope_is_current = False
        scope = review.get("review_scope") if isinstance(review, dict) else None
        if (
            review_root is not None
            and review_state_dir is not None
            and isinstance(scope, dict)
            and set(scope) == {"patterns", "sha256"}
        ):
            try:
                scope_is_current = scope == review_scope_binding(
                    review_root,
                    review_state_dir,
                    scope.get("patterns"),
                )
            except (OSError, TypeError, ValueError):
                scope_is_current = False
        if (
            isinstance(review, dict)
            and review.get("workspace_sha256") == workspace_sha256
            and review.get("plan_revision") == plan_revision
            and review.get("acceptance_revision")
            == acceptance_revision_value
            and acceptance_subset_is_current
            and terminal_candidate_is_bound
            and scope_is_current
        ):
            if (
                role == "terminal_critic"
                and review.get("event_seq", 0)
                <= terminal_after_event_seq
            ):
                continue
            current[role] = review
    return current


def current_review_map(
    state: dict[str, Any],
    workspace_sha256: str,
) -> dict[str, dict[str, Any]]:
    return {
        role: review
        for role, review in current_review_status_map(
            state,
            workspace_sha256,
        ).items()
        if review.get("status") == "passed"
    }


def review_completion_time_issues(
    receipt: dict[str, Any],
    state: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    """Require the final receipt to follow every current Review Verdict.

    ``completed_at`` is deliberately absent from the cycle-free terminal
    candidate digest. The final completion path must therefore enforce this
    causal ordering directly after the terminal verdict exists.
    """

    completed_at = parse_time(receipt.get("completed_at"))
    if completed_at is None:
        # The candidate validator reports the malformed final timestamp.
        return []
    issues: list[str] = []
    current_reviews = current_review_status_map(
        state,
        current.get("sha256"),
    )
    for role, review in sorted(current_reviews.items()):
        recorded_at = parse_time(review.get("recorded_at"))
        if recorded_at is None:
            issues.append(
                f"current Review Verdict {role!r} has invalid recorded_at"
            )
        elif recorded_at > completed_at:
            issues.append(
                f"current Review Verdict {role!r} was recorded after "
                "receipt completed_at"
            )
    return issues


def terminal_review_chronology_issues(
    terminal_checked_at: Any,
    state: dict[str, Any],
    current: dict[str, Any],
    *,
    candidate_completed_at: Any = None,
) -> list[str]:
    """Require a terminal verdict to follow its candidate and prerequisites."""

    checked_at = parse_time(terminal_checked_at)
    if checked_at is None:
        return []
    issues: list[str] = []
    if candidate_completed_at is not None:
        candidate_at = parse_time(candidate_completed_at)
        if candidate_at is not None and checked_at < candidate_at:
            issues.append(
                "terminal critic checked_at precedes Completion Evidence "
                "Candidate completed_at"
            )
    review_map = current_review_map(state, current.get("sha256"))
    required_roles = state.get("proof_policy", {}).get(
        "required_review_roles",
        [],
    )
    for role in sorted(
        value
        for value in required_roles
        if value != "terminal_critic"
    ):
        review = review_map.get(role)
        if not isinstance(review, dict):
            continue
        prerequisite_at = parse_time(review.get("recorded_at"))
        if prerequisite_at is not None and checked_at < prerequisite_at:
            issues.append(
                "terminal critic checked_at precedes current Review "
                f"Verdict {role!r} recorded_at"
            )
    return issues


def outstanding_review_blocking_findings(
    state: dict[str, Any],
    *,
    role: str | None = None,
) -> dict[tuple[str, str], set[str]]:
    """Reduce unresolved blocking findings for the current review contract."""

    outstanding: dict[tuple[str, str], set[str]] = {}
    plan_revision = current_plan_revision(state)
    acceptance_revision_value = state.get("acceptance_revision")
    for review in state.get("reviews", []):
        if (
            not isinstance(review, dict)
            or review.get("plan_revision") != plan_revision
            or review.get("acceptance_revision")
            != acceptance_revision_value
        ):
            continue
        review_role = review.get("role")
        if not isinstance(review_role, str) or (
            role is not None and review_role != role
        ):
            continue
        review_acceptance = {
            value
            for value in review.get("acceptance_ids", [])
            if isinstance(value, str)
        }
        for finding_id in review.get(
            "open_blocking_finding_ids",
            [],
        ):
            if isinstance(finding_id, str):
                outstanding.setdefault(
                    (review_role, finding_id),
                    set(),
                ).update(review_acceptance)
        for finding_id in review.get("resolved_finding_ids", []):
            key = (review_role, finding_id)
            required_ids = outstanding.get(key)
            if (
                isinstance(finding_id, str)
                and isinstance(required_ids, set)
                and required_ids.issubset(review_acceptance)
            ):
                outstanding.pop(key, None)
    return outstanding


def completion_context_issues(
    state: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    host_state = state.get("host", {}).get("last_observed_state")
    completed_with_receipt = (
        host_state == "completed"
        and isinstance(state.get("completion_ready"), dict)
    )
    if host_state != "active" and not completed_with_receipt:
        errors.append(
            f"completion requires an active host Goal, observed {host_state}"
        )
    open_stories = sorted(
        story_id
        for story_id, story in state.get("stories", {}).items()
        if isinstance(story, dict)
        and story.get("status") in {"open", "returned"}
    )
    if open_stories:
        errors.append(
            "completion has open or review-blocked stories: "
            + ", ".join(open_stories)
        )
    unresolved = sorted(
        blocker_id
        for blocker_id, blocker in state.get("blockers", {}).items()
        if isinstance(blocker, dict)
        and blocker.get("required") is True
        and blocker.get("status") != "resolved"
    )
    if unresolved:
        errors.append(
            "completion has unresolved required blockers: "
            + ", ".join(unresolved)
        )
    unresolved_reviews = outstanding_review_blocking_findings(state)
    if unresolved_reviews:
        errors.append(
            "completion has unresolved review blocking findings: "
            + ", ".join(
                f"{role}:{finding_id}"
                for role, finding_id in sorted(unresolved_reviews)
            )
        )
    review_map = current_review_map(state, current["sha256"])
    roles = state.get("proof_policy", {}).get("required_review_roles", [])
    missing = sorted(set(roles) - set(review_map))
    if missing:
        errors.append(
            "completion is missing current snapshot reviews: "
            + ", ".join(missing)
        )
    if "terminal_critic" in roles and "terminal_critic" in review_map:
        prerequisite_sequences = [
            review_map[role]["event_seq"]
            for role in roles
            if role != "terminal_critic"
            if role in review_map
        ]
        if prerequisite_sequences and review_map["terminal_critic"][
            "event_seq"
        ] <= max(prerequisite_sequences):
            errors.append(
                "terminal critic must follow all current prerequisite "
                "reviews"
            )
        errors.extend(
            terminal_review_chronology_issues(
                review_map["terminal_critic"].get("recorded_at"),
                state,
                current,
            )
        )
    return errors


def current_completion_consistency_issues(
    state: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    """Check that the current completion still proves the current Goal."""

    completion = state.get("completion_ready")
    if not isinstance(completion, dict):
        return []
    issues = completion_context_issues(state, current)
    if completion.get("workspace_sha256") != current.get("sha256"):
        issues.append("completion_ready workspace snapshot is stale")
    if completion.get("plan_revision") != current_plan_revision(state):
        issues.append("completion_ready plan revision is stale")
    if (
        completion.get("acceptance_revision")
        != state.get("acceptance_revision")
    ):
        issues.append("completion_ready acceptance revision is stale")
    return list(dict.fromkeys(issues))


def host_ledger_divergence(
    state: dict[str, Any],
    current: dict[str, Any] | None = None,
) -> list[str]:
    host_state = state.get("host", {}).get("last_observed_state")
    completion = state.get("completion_ready")
    divergence: list[str] = []
    if host_state == "completed" and completion is None:
        divergence.append(
            "host_completed_without_completion_ready: reopen the same host "
            "Goal or create a new Goal before continuing"
        )
    elif host_state != "completed" and completion is not None:
        divergence.append("completion_ready_host_not_completed")
    if host_state in {"cancelled", "superseded"} and completion is not None:
        divergence.append(f"completion_ready_host_{host_state}")
    if current is not None and isinstance(completion, dict):
        divergence.extend(
            f"completion_ready_inconsistent: {issue}"
            for issue in current_completion_consistency_issues(
                state, current
            )
        )
    return divergence


def plan_binding(
    state_dir: Path,
    source_path: Path,
    *,
    revision: int,
    acceptance_revision: int,
    recorded_at: str,
    carried_forward_from_revision: int | None = None,
) -> dict[str, Any]:
    if source_path.is_symlink() or not source_path.is_file():
        raise ValueError("plan artifact must be a regular file")
    suffix, content = validated_plan_artifact(source_path)
    relative = f"plans/plan-r{revision}{suffix}"
    destination = state_artifact_path(
        state_dir,
        ("plans",),
        f"plan-r{revision}",
        suffix=suffix,
        create_parent=True,
    )
    write_unbound_immutable(state_dir, destination, content)
    binding = {
        "revision": revision,
        "acceptance_revision": acceptance_revision,
        "sha256": file_digest(destination),
        "artifact_path": relative,
        "recorded_at": recorded_at,
    }
    if carried_forward_from_revision is not None:
        binding["carried_forward_from_revision"] = (
            carried_forward_from_revision
        )
    return binding


def init_command(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        return stable_result(False, "blocked", issues=["project root missing"])
    if not is_portable_id(args.goal_id):
        return stable_result(False, "blocked", issues=["goal_id is invalid"])
    if not isinstance(args.project_id, str) or not PROJECT_ID.fullmatch(
        args.project_id
    ):
        return stable_result(False, "blocked", issues=["project_id is invalid"])
    if not args.objective.strip():
        return stable_result(False, "blocked", issues=["objective is required"])
    if not args.host_goal_id.strip():
        return stable_result(
            False, "blocked", issues=["host_goal_id is required"]
        )
    host_goal_id = args.host_goal_id.strip()
    if not isinstance(args.host_source, str) or not args.host_source.strip():
        return stable_result(
            False, "blocked", issues=["host_source is required"]
        )
    host_source = args.host_source.strip()
    try:
        acceptance = acceptance_artifact(args.acceptance)
        state_dir = resolve_state_dir(
            root,
            args.goal_id,
            args.state_dir,
            project_local=args.project_local,
        )
        try:
            import goal_runtime
            from capability_model import resolve
        except ImportError:
            from . import goal_runtime
            from .capability_model import resolve
        policy_issues = input_policy_issues(
            {
                "objective": args.objective.strip(),
                "acceptance": acceptance,
                "host_goal_id": host_goal_id,
                "host_source": host_source,
            },
            "goal ledger init",
        )
        policy_issues.extend(
            prohibited_paid_data_reasons(
                "\n".join(
                    [
                        args.objective.strip(),
                        *(item["text"] for item in acceptance),
                    ]
                )
            )
        )
        if policy_issues:
            raise ValueError("; ".join(policy_issues))
        manifest_binding, manifest = goal_runtime.validated_manifest_binding(
            root, args.manifest, args.project_id
        )
        context = resolve(
            manifest,
            capabilities=args.require_capability,
            assurance=args.assurance,
            delivery=args.delivery,
        )
        assurance = context["assurance"]
        delivery = context["delivery"]
        capabilities = list(context["effective_capabilities"])
        if assurance == "release" and "remote-release" not in capabilities:
            capabilities.append("remote-release")
        activation_reasons = list(dict.fromkeys(args.activation_reason))
        automatic_reason = (
            f"assurance-{assurance}"
            if assurance in {"strict", "release"}
            else None
        )
        if automatic_reason and automatic_reason not in activation_reasons:
            activation_reasons.append(automatic_reason)
        if not activation_reasons:
            raise ValueError(
                "light/standard ledger requires an explicit activation reason"
            )
        plan_source = (
            unresolved_absolute_path(args.plan) if args.plan else None
        )
        if assurance in {"strict", "release"} and plan_source is None:
            raise ValueError("strict/release ledger requires a reviewed plan")
        if plan_source is not None and (
            plan_source.is_symlink() or not plan_source.is_file()
        ):
            raise ValueError("plan artifact must be a regular file")
        gates = required_gates(
            assurance,
            capabilities,
            custom_gates=context.get("custom_required_gates", []),
        )
        binding = project_binding(root)
        observed_at = now()
        workspace = workspace_snapshot(
            root,
            state_dir,
            goal_runtime.protected_patterns_from_manifest(manifest),
        )
        revision = acceptance_revision(
            1,
            acceptance,
            reason="Initial accepted objective.",
            recorded_at=observed_at,
        )
        proof_policy = {
            "activation_reasons": activation_reasons,
            "required_capabilities": capabilities,
            "required_review_roles": required_review_roles(assurance),
            "required_gates": gates,
            "manifest": manifest_binding,
        }
        with state_lock(
            state_dir,
            create=True,
            artifact_names=CORE_ARTIFACTS,
        ):
            staged_plan: dict[str, Any] | None = None
            existing = any(
                (state_dir / name).exists()
                for name in (STATE_NAME, LEDGER_NAME, PENDING_NAME)
            )
            if existing:
                state, errors, current, _events = load_and_verify(
                    root,
                    state_dir,
                    check_workspace=True,
                    recover=True,
                )
                if errors or state is None or current is None:
                    raise ValueError(
                        "existing goal ledger is invalid: "
                        + "; ".join(errors)
                    )
                expected = {
                    "goal_id": args.goal_id,
                    "project_id": args.project_id,
                    "objective": args.objective.strip(),
                    "acceptance": acceptance,
                    "assurance": assurance,
                    "delivery": delivery,
                    "host_goal_id": host_goal_id,
                    "project_binding_sha256": binding["identity_sha256"],
                    "proof_policy": proof_policy,
                }
                observed = {
                    "goal_id": state.get("goal_id"),
                    "project_id": state.get("project_id"),
                    "objective": state.get("objective"),
                    "acceptance": state.get("acceptance"),
                    "assurance": state.get("assurance"),
                    "delivery": goal_delivery(state),
                    "host_goal_id": state.get("host", {}).get("goal_id"),
                    "project_binding_sha256": state.get(
                        "project_binding", {}
                    ).get("identity_sha256"),
                    "proof_policy": state.get("proof_policy"),
                }
                if observed != expected or state.get(
                    "acceptance_revision"
                ) != 1:
                    raise ValueError(
                        "goal ledger state already exists for different intent"
                    )
                workspace = current
            else:
                if plan_source is not None:
                    staged_plan = plan_binding(
                        state_dir,
                        plan_source,
                        revision=1,
                        acceptance_revision=1,
                        recorded_at=now(),
                    )
                event = make_event(
                    None,
                    goal_id=args.goal_id,
                    event_type="goal_bound",
                    payload={
                        "project_id": args.project_id,
                        "project_binding": binding,
                        "state_root": state_root_binding(state_dir),
                        "project_fingerprint": binding["identity_sha256"],
                        "host": {
                            "goal_id": host_goal_id,
                            "last_observed_state": args.host_state,
                            "observed_at": observed_at,
                            "source": host_source,
                        },
                        "objective": args.objective.strip(),
                        "objective_sha256": digest(args.objective.strip()),
                        "acceptance_revision": revision,
                        "assurance": assurance,
                        "delivery": delivery,
                        "proof_policy": proof_policy,
                    },
                    workspace=workspace,
                )
                state = persist_event(state_dir, None, event)
            if plan_source is not None:
                plan = state.get("plan")
                if isinstance(plan, dict):
                    if file_digest(plan_source) != plan.get("sha256"):
                        raise ValueError(
                            "goal ledger already binds a different plan"
                        )
                else:
                    bound = staged_plan or plan_binding(
                        state_dir,
                        plan_source,
                        revision=1,
                        acceptance_revision=1,
                        recorded_at=now(),
                    )
                    plan_event = make_event(
                        state,
                        goal_id=args.goal_id,
                        event_type="plan_bound",
                        payload={"plan": bound},
                        workspace=workspace,
                    )
                    state = persist_event(state_dir, state, plan_event)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        return stable_result(False, "blocked", issues=[str(exc)])
    divergence = host_ledger_divergence(state, workspace)
    status = (
        "review_required"
        if divergence
        else state["host"]["last_observed_state"]
    )
    return stable_result(
        not divergence,
        status,
        issues=divergence,
        result={
            "goal_id": state["goal_id"],
            "host_goal_id": state["host"]["goal_id"],
            "state_dir": str(state_dir),
            "assurance": state["assurance"],
            "delivery": goal_delivery(state),
            "required_gates": state["proof_policy"]["required_gates"],
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
            "workspace_sha256": workspace["sha256"],
        },
    )


def resume_command(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).expanduser().resolve()
    try:
        state_dir = command_state_dir(args.state_dir)
        with state_lock(
            state_dir,
            artifact_names=CORE_ARTIFACTS,
        ):
            state, errors, current, events = load_and_verify(
                root,
                state_dir,
                check_workspace=True,
                recover=True,
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return stable_result(False, "blocked", issues=[str(exc)])
    if errors or state is None or current is None:
        return stable_result(False, "blocked", issues=errors)
    review_map = current_review_map(state, current["sha256"])
    required_roles = state["proof_policy"]["required_review_roles"]
    stale_roles = sorted(
        set(required_roles)
        - set(review_map)
        & {
            review.get("role")
            for review in state.get("reviews", [])
            if isinstance(review, dict)
        }
    )
    completion = state.get("completion_ready")
    divergence = host_ledger_divergence(state, current)
    workspace_drift = (
        current["sha256"]
        != state["workspace"]["last_event_workspace_sha256"]
    )
    host_state = state["host"]["last_observed_state"]
    plan_issues = (
        []
        if host_state in TERMINAL_HOST_STATES
        else current_plan_binding_issues(state)
    )
    terminal_without_completion = host_state in {
        "cancelled",
        "superseded",
    }
    needs_review = bool(
        not terminal_without_completion
        and (workspace_drift or stale_roles or divergence)
    )
    status = (
        "blocked"
        if plan_issues
        else ("review_required" if needs_review else host_state)
    )
    stories_by_status = {
        story_status: sorted(
            story_id
            for story_id, story in state["stories"].items()
            if story.get("status") == story_status
        )
        for story_status in ("open", "returned", "accepted", "superseded")
    }
    current_blockers = [
        state["blockers"][blocker_id]
        for blocker_id in sorted(state["blockers"])
        if state["blockers"][blocker_id].get("status") == "open"
    ]
    capsule = state.get("continuation_capsule")
    capsule_is_current = bool(
        isinstance(capsule, dict)
        and capsule.get("acceptance_revision")
        == state.get("acceptance_revision")
        and capsule.get("plan_revision") == current_plan_revision(state)
        and capsule.get("workspace_sha256") == current["sha256"]
    )
    continuation = {
        "capsule": capsule,
        "capsule_is_current": capsule_is_current,
        "checkpoint": state.get("checkpoint"),
        "next_action": state.get("next_action"),
        "stories_by_status": stories_by_status,
        "current_blockers": current_blockers,
        "workspace_drift": workspace_drift,
        "stale_review_roles": stale_roles,
        "completion_ready": completion is not None,
        "ledger": {
            "event_count": state["ledger"]["event_count"],
            "tail_sha256": state["ledger"]["tail_sha256"],
        },
        "workspace": {
            "current_sha256": current["sha256"],
            "last_event_sha256": state["workspace"][
                "last_event_workspace_sha256"
            ],
        },
        "authority": {"status": "not_recorded"},
    }
    return stable_result(
        not needs_review and not plan_issues,
        status,
        issues=[*plan_issues, *divergence],
        result={
            "goal_id": state["goal_id"],
            "host": state["host"],
            "assurance": state["assurance"],
            "delivery": goal_delivery(state),
            "acceptance_revision": state["acceptance_revision"],
            "plan_revision": current_plan_revision(state),
            "workspace_sha256": current["sha256"],
            "workspace_drift": workspace_drift,
            "stale_review_roles": stale_roles,
            "open_story_ids": sorted(
                story_id
                for story_id, story in state["stories"].items()
                if story.get("status") in {"open", "returned"}
            ),
            "completion_ready": completion is not None,
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
            "continuation": continuation,
        },
    )


def revise_acceptance_command(args: argparse.Namespace) -> dict[str, Any]:
    revision_path = Path(args.revision).expanduser().resolve()
    try:
        artifact = strict_json(revision_path)
        policy_issues = input_policy_issues(
            artifact,
            "acceptance revision",
        )
        if policy_issues:
            raise ValueError("; ".join(policy_issues))
        if set(artifact) not in (
            {"reason", "acceptance"},
            {"reason", "acceptance", "steering"},
        ):
            raise ValueError(
                "revision artifact requires reason and acceptance, with "
                "optional steering"
            )
        reason = artifact.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("revision reason is required")
        acceptance = validate_acceptance(artifact.get("acceptance"))
        raw_steering = artifact.get("steering")
        normalized_steering = (
            normalize_steering(raw_steering)
            if "steering" in artifact
            else None
        )
        normalized_reason = reason.strip()
        paid_data_issues = prohibited_paid_data_reasons(
            "\n".join(
                [
                    normalized_reason,
                    *(item["text"] for item in acceptance),
                ]
            )
        )
        if paid_data_issues:
            raise ValueError("; ".join(paid_data_issues))
        plan_source = (
            unresolved_absolute_path(args.plan) if args.plan else None
        )
        carry_forward_plan = bool(
            getattr(args, "carry_forward_plan", False)
        )
        if plan_source is not None and carry_forward_plan:
            raise ValueError(
                "--plan and --carry-forward-plan are mutually exclusive"
            )
        if plan_source is not None and (
            plan_source.is_symlink() or not plan_source.is_file()
        ):
            raise ValueError("plan artifact must be a regular file")
        root = Path(args.root).expanduser().resolve()
        state_dir = command_state_dir(args.state_dir)
        with state_lock(
            state_dir,
            artifact_names=CORE_ARTIFACTS,
        ):
            state, errors, current, _events = load_and_verify(
                root,
                state_dir,
                check_workspace=True,
                recover=True,
            )
            if errors or state is None or current is None:
                return stable_result(False, "blocked", issues=errors)
            blocked = mutation_blockers(state, allow_plan_repair=True)
            if blocked:
                return stable_result(False, "blocked", issues=blocked)
            latest_revision = state["acceptance_revisions"][-1]
            acceptance_is_retry = (
                latest_revision.get("acceptance") == acceptance
                and latest_revision.get("reason") == normalized_reason
                and latest_revision.get("steering") == normalized_steering
            )
            steering = normalized_steering
            if steering is not None and not acceptance_is_retry:
                steering = validate_steering(
                    steering,
                    state["acceptance"],
                    acceptance,
                )
            target_revision = (
                state["acceptance_revision"]
                if acceptance_is_retry
                else state["acceptance_revision"] + 1
            )
            current_plan = state.get("plan")
            plan_is_current = not current_plan_binding_issues(state)
            needs_current_plan = state.get("assurance") in {
                "strict",
                "release",
            }
            if (
                needs_current_plan
                and (not acceptance_is_retry or not plan_is_current)
                and plan_source is None
                and not carry_forward_plan
            ):
                raise ValueError(
                    "strict/release acceptance revision requires a current "
                    "reviewed Plan; pass --plan, or explicitly carry forward "
                    "an unchanged Plan for a non-material revision"
                )
            bound: dict[str, Any] | None = None
            if carry_forward_plan:
                if not isinstance(current_plan, dict):
                    raise ValueError(
                        "no reviewed Plan is available to carry forward"
                    )
                previous_acceptance = (
                    state["acceptance_revisions"][-2].get("acceptance")
                    if acceptance_is_retry
                    and len(state["acceptance_revisions"]) > 1
                    else state["acceptance"]
                )
                if acceptance != previous_acceptance:
                    raise ValueError(
                        "--carry-forward-plan is limited to non-material "
                        "revisions with unchanged acceptance"
                    )
                if (
                    acceptance_is_retry
                    and current_plan.get("acceptance_revision")
                    == target_revision
                ):
                    bound = None
                else:
                    source = stored_artifact_path(
                        state_dir,
                        current_plan["artifact_path"],
                    )
                    bound = plan_binding(
                        state_dir,
                        source,
                        revision=current_plan_revision(state) + 1,
                        acceptance_revision=target_revision,
                        recorded_at=now(),
                        carried_forward_from_revision=current_plan["revision"],
                    )
            if plan_source is not None:
                if (
                    acceptance_is_retry
                    and isinstance(current_plan, dict)
                    and current_plan.get("acceptance_revision")
                    == target_revision
                ):
                    if file_digest(plan_source) != current_plan.get("sha256"):
                        raise ValueError(
                            "acceptance revision already binds a different plan"
                        )
                else:
                    bound = plan_binding(
                        state_dir,
                        plan_source,
                        revision=current_plan_revision(state) + 1,
                        acceptance_revision=target_revision,
                        recorded_at=now(),
                    )
            if not acceptance_is_retry:
                value = acceptance_revision(
                    target_revision,
                    acceptance,
                    reason=normalized_reason,
                    recorded_at=now(),
                    steering=steering,
                )
                event = make_event(
                    state,
                    goal_id=state["goal_id"],
                    event_type="acceptance_revised",
                    payload={"acceptance_revision": value},
                    workspace=current,
                )
                state = persist_event(state_dir, state, event)
            if bound is not None:
                plan_event = make_event(
                    state,
                    goal_id=state["goal_id"],
                    event_type="plan_bound",
                    payload={"plan": bound},
                    workspace=current,
                )
                state = persist_event(state_dir, state, plan_event)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        return stable_result(False, "blocked", issues=[str(exc)])
    return stable_result(
        True,
        "active",
        result={
            "acceptance_revision": state["acceptance_revision"],
            "plan_revision": current_plan_revision(state),
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
        },
    )


def validate_blocker(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "id",
            "status",
            "required",
            "summary",
            "next_action",
        }
        or not is_portable_id(value.get("id"))
        or value.get("status") not in {"open", "resolved"}
        or not isinstance(value.get("required"), bool)
        or not isinstance(value.get("summary"), str)
        or not value["summary"].strip()
        or (
            value.get("next_action") is not None
            and (
                not isinstance(value.get("next_action"), str)
                or not value["next_action"].strip()
            )
        )
    ):
        raise ValueError("checkpoint blocker is invalid")
    return {
        "id": value["id"],
        "status": value["status"],
        "required": value["required"],
        "summary": value["summary"].strip(),
        "next_action": value["next_action"],
    }


def validate_checkpoint(
    artifact: dict[str, Any],
    state: dict[str, Any],
    workspace_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if set(artifact) != {
        "kind",
        "summary",
        "acceptance_status",
        "blockers",
        "next_action",
    }:
        raise ValueError("checkpoint artifact contains unknown or missing fields")
    if not is_portable_id(artifact.get("kind")):
        raise ValueError("checkpoint kind is invalid")
    if not isinstance(artifact.get("summary"), str) or not artifact[
        "summary"
    ].strip():
        raise ValueError("checkpoint summary is required")
    statuses = artifact.get("acceptance_status")
    if not isinstance(statuses, dict):
        raise ValueError("checkpoint acceptance_status must be an object")
    known_ids = {item["id"] for item in state["acceptance"]}
    if not set(statuses).issubset(known_ids):
        raise ValueError("checkpoint references unknown acceptance IDs")
    normalized_statuses: dict[str, Any] = {}
    for acceptance_id, value in statuses.items():
        if (
            not isinstance(value, dict)
            or set(value) != {"status", "evidence_refs"}
            or value.get("status")
            not in {"pending", "partial", "passed", "blocked", "unverified"}
            or not isinstance(value.get("evidence_refs"), list)
            or not all(
                isinstance(item, str) and item.strip()
                for item in value["evidence_refs"]
            )
        ):
            raise ValueError("checkpoint acceptance status is invalid")
        normalized_statuses[acceptance_id] = value
    blockers_value = artifact.get("blockers")
    if not isinstance(blockers_value, list):
        raise ValueError("checkpoint blockers must be an array")
    blockers = [validate_blocker(value) for value in blockers_value]
    blocker_ids = [item["id"] for item in blockers]
    if len(blocker_ids) != len(set(blocker_ids)):
        raise ValueError("checkpoint blocker IDs must be unique")
    next_action = artifact.get("next_action")
    if next_action is not None and (
        not isinstance(next_action, str) or not next_action.strip()
    ):
        raise ValueError("checkpoint next_action is invalid")
    has_nonpassing_acceptance = any(
        item.get("status") in {"pending", "partial", "blocked", "unverified"}
        for item in normalized_statuses.values()
    )
    has_open_blocker = any(
        blocker.get("status") == "open" for blocker in blockers
    )
    paid_data_issues = prohibited_paid_data_reasons(
        artifact["summary"],
        allow_reported_violation=(
            has_nonpassing_acceptance or has_open_blocker
        ),
    )
    for blocker in blockers:
        paid_data_issues.extend(
            prohibited_paid_data_reasons(
                blocker["summary"],
                allow_reported_violation=blocker.get("status") == "open",
            )
        )
    paid_data_issues.extend(
        prohibited_paid_data_reasons(
            "\n".join(
                value
                for value in [
                    next_action,
                    *(blocker.get("next_action") for blocker in blockers),
                ]
                if isinstance(value, str)
            )
        )
    )
    if paid_data_issues:
        raise ValueError("; ".join(paid_data_issues))
    checkpoint = {
        "kind": artifact["kind"],
        "summary": artifact["summary"].strip(),
        "acceptance_status": normalized_statuses,
        "blockers": blocker_ids,
        "next_action": next_action,
        "recorded_at": now(),
        "workspace_sha256": workspace_sha256,
    }
    return checkpoint, blockers


def checkpoint_command(args: argparse.Namespace) -> dict[str, Any]:
    try:
        artifact = strict_json(Path(args.checkpoint).expanduser().resolve())
        policy_issues = input_policy_issues(artifact, "checkpoint")
        if policy_issues:
            raise ValueError("; ".join(policy_issues))
        root = Path(args.root).expanduser().resolve()
        state_dir = command_state_dir(args.state_dir)
        with state_lock(
            state_dir,
            artifact_names=CORE_ARTIFACTS,
        ):
            state, errors, current, _events = load_and_verify(
                root,
                state_dir,
                check_workspace=True,
                recover=True,
            )
            if errors or state is None or current is None:
                return stable_result(False, "blocked", issues=errors)
            blocked = mutation_blockers(
                state,
                allow_suspended=True,
                allow_plan_repair=True,
            )
            if blocked:
                return stable_result(False, "blocked", issues=blocked)
            checkpoint, blockers = validate_checkpoint(
                artifact, state, current["sha256"]
            )
            for blocker in blockers:
                event = make_event(
                    state,
                    goal_id=state["goal_id"],
                    event_type="blocker_classified",
                    payload={"blocker": blocker},
                    workspace=current,
                )
                state = persist_event(state_dir, state, event)
            event = make_event(
                state,
                goal_id=state["goal_id"],
                event_type="checkpoint_recorded",
                payload={"checkpoint": checkpoint},
                workspace=current,
            )
            state = persist_event(state_dir, state, event)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        return stable_result(False, "blocked", issues=[str(exc)])
    return stable_result(
        True,
        state["host"]["last_observed_state"],
        result={
            "checkpoint": state["checkpoint"],
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
        },
    )


def normalize_capsule_text_list(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not all(
            isinstance(item, str) and item.strip()
            for item in value
        )
    ):
        raise ValueError(f"continuation capsule {label} is invalid")
    normalized = [item.strip() for item in value]
    if len(normalized) != len(set(normalized)):
        raise ValueError(
            f"continuation capsule {label} must be unique"
        )
    return normalized


def normalize_capsule_workers(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("continuation capsule worker_states is invalid")
    workers: list[dict[str, Any]] = []
    for worker in value:
        if (
            not isinstance(worker, dict)
            or set(worker) != {"id", "status", "story_id"}
            or not is_portable_id(worker.get("id"))
            or not is_portable_id(worker.get("status"))
            or (
                worker.get("story_id") is not None
                and not is_portable_id(worker.get("story_id"))
            )
        ):
            raise ValueError(
                "continuation capsule worker_states is invalid"
            )
        workers.append(
            {
                "id": worker["id"],
                "status": worker["status"],
                "story_id": worker["story_id"],
            }
        )
    worker_ids = [worker["id"] for worker in workers]
    if len(worker_ids) != len(set(worker_ids)):
        raise ValueError("continuation capsule worker IDs must be unique")
    return workers


def continuation_capsule(
    artifact: dict[str, Any],
    state: dict[str, Any],
    workspace_sha256: str,
) -> dict[str, Any]:
    required = {
        "kind",
        "context_sha256",
        "open_work",
        "worker_states",
        "current_evidence_refs",
        "stale_evidence_refs",
        "pending_authority",
        "no_repeat",
        "next_action",
    }
    if set(artifact) != required:
        raise ValueError(
            "continuation capsule contains unknown or missing fields"
        )
    if artifact.get("kind") not in {"handoff", "suspension"}:
        raise ValueError("continuation capsule kind is invalid")
    if SHA256.fullmatch(str(artifact.get("context_sha256", ""))) is None:
        raise ValueError("continuation capsule context_sha256 is invalid")
    open_work = normalize_capsule_text_list(
        artifact.get("open_work"), "open_work"
    )
    worker_states = normalize_capsule_workers(
        artifact.get("worker_states")
    )
    current_evidence_refs = normalize_capsule_text_list(
        artifact.get("current_evidence_refs"),
        "current_evidence_refs",
    )
    stale_evidence_refs = normalize_capsule_text_list(
        artifact.get("stale_evidence_refs"),
        "stale_evidence_refs",
    )
    if set(current_evidence_refs) & set(stale_evidence_refs):
        raise ValueError(
            "continuation evidence cannot be current and stale"
        )
    pending_authority = normalize_capsule_text_list(
        artifact.get("pending_authority"), "pending_authority"
    )
    no_repeat = normalize_capsule_text_list(
        artifact.get("no_repeat"), "no_repeat"
    )
    next_action = artifact.get("next_action")
    if next_action is not None and (
        not isinstance(next_action, str) or not next_action.strip()
    ):
        raise ValueError("continuation capsule next_action is invalid")
    next_action = next_action.strip() if isinstance(next_action, str) else None
    actionable_paid_data = prohibited_paid_data_reasons(
        "\n".join([*open_work, *pending_authority, next_action or ""])
    )
    if actionable_paid_data:
        raise ValueError("; ".join(actionable_paid_data))
    body = {
        "kind": artifact["kind"],
        "context_sha256": artifact["context_sha256"],
        "acceptance_revision": state["acceptance_revision"],
        "plan_revision": current_plan_revision(state),
        "workspace_sha256": workspace_sha256,
        "open_work": open_work,
        "open_story_ids": sorted(
            story_id
            for story_id, story in state["stories"].items()
            if story.get("status") in {"open", "returned"}
        ),
        "worker_states": worker_states,
        "current_evidence_refs": current_evidence_refs,
        "stale_evidence_refs": stale_evidence_refs,
        "blocker_ids": sorted(
            blocker_id
            for blocker_id, blocker in state["blockers"].items()
            if blocker.get("status") == "open"
        ),
        "pending_authority": pending_authority,
        "no_repeat": no_repeat,
        "next_action": next_action,
        "recorded_at": now(),
    }
    return {**body, "sha256": digest(body)}


def continuation_capsule_command(
    args: argparse.Namespace,
) -> dict[str, Any]:
    try:
        artifact = strict_json(Path(args.capsule).expanduser().resolve())
        policy_issues = input_policy_issues(
            artifact,
            "continuation capsule",
        )
        if policy_issues:
            raise ValueError("; ".join(policy_issues))
        root = Path(args.root).expanduser().resolve()
        state_dir = command_state_dir(args.state_dir)
        with state_lock(
            state_dir,
            artifact_names=CORE_ARTIFACTS,
        ):
            state, errors, current, _events = load_and_verify(
                root,
                state_dir,
                check_workspace=True,
                recover=True,
            )
            if errors or state is None or current is None:
                return stable_result(False, "blocked", issues=errors)
            blocked = mutation_blockers(
                state,
                allow_suspended=True,
                allow_plan_repair=True,
            )
            if blocked:
                return stable_result(False, "blocked", issues=blocked)
            capsule = continuation_capsule(
                artifact,
                state,
                current["sha256"],
            )
            event = make_event(
                state,
                goal_id=state["goal_id"],
                event_type="continuation_capsule_recorded",
                payload={"continuation_capsule": capsule},
                workspace=current,
            )
            state = persist_event(state_dir, state, event)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        return stable_result(False, "blocked", issues=[str(exc)])
    return stable_result(
        True,
        state["host"]["last_observed_state"],
        result={
            "continuation_capsule": state["continuation_capsule"],
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
        },
    )


def story_envelope_issues(
    envelope: dict[str, Any],
    state: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    try:
        import goal_runtime
    except ImportError:
        from . import goal_runtime
    issues.extend(goal_runtime.story_envelope_input_issues(envelope))
    if envelope.get("document_type") != "quant_story_envelope":
        issues.append("envelope document_type is invalid")
    if envelope.get("schema_version") != 1:
        issues.append("envelope schema_version must equal 1")
    story_id = envelope.get("story_id")
    if not is_portable_id(story_id):
        issues.append("envelope story_id is invalid")
    elif story_id in state.get("stories", {}):
        issues.append("story_id cannot be reused")
    if envelope.get("goal_id") != state.get("goal_id"):
        issues.append("envelope goal_id mismatch")
    if envelope.get("project_binding_sha256") != state.get(
        "project_binding", {}
    ).get("identity_sha256"):
        issues.append("envelope project binding mismatch")
    if envelope.get("mode") not in {"advisory", "read_only", "write"}:
        issues.append("envelope mode is invalid")
    if envelope.get("external_effects") != "none":
        issues.append("story envelope cannot grant external effects")
    if envelope.get("cost_class") != "no_billable_action":
        issues.append("story envelope cannot grant billable action")
    acceptance_text = envelope.get("acceptance")
    paid_data_text = [str(envelope.get("objective", ""))]
    if isinstance(acceptance_text, list):
        paid_data_text.extend(
            item.get("text", "")
            for item in acceptance_text
            if isinstance(item, dict)
        )
    issues.extend(
        prohibited_paid_data_reasons(
            "\n".join(paid_data_text)
        )
    )
    for field in ("write_scope", "protected_scope", "depends_on"):
        values = envelope.get(field)
        if (
            not isinstance(values, list)
            or len(values) != len(set(values))
            or not all(isinstance(value, str) for value in values)
        ):
            issues.append(f"envelope {field} is invalid")
    for field in ("write_scope", "protected_scope"):
        values = envelope.get(field)
        if isinstance(values, list) and not all(
            portable_relative(value) for value in values
        ):
            issues.append(f"envelope {field} escapes project root")
    issues.extend(
        goal_runtime.story_acceptance_issues(
            envelope.get("acceptance"),
            state.get("acceptance"),
        )
    )
    dependencies = envelope.get("depends_on")
    if isinstance(dependencies, list):
        for dependency in dependencies:
            story = state.get("stories", {}).get(dependency)
            if not isinstance(story, dict) or story.get("status") != "accepted":
                issues.append(f"story dependency is not accepted: {dependency}")
    if envelope.get("baseline_workspace_sha256") != current.get("sha256"):
        issues.append("envelope baseline workspace mismatch")
    if envelope.get("envelope_sha256") != goal_runtime.envelope_hash(envelope):
        issues.append("envelope SHA-256 is invalid")
    mode = envelope.get("mode")
    write_scope = envelope.get("write_scope")
    if mode != "write" and write_scope:
        issues.append("non-write story cannot declare write_scope")
    if mode == "write" and not write_scope:
        issues.append("write story requires write_scope")
    if mode == "write":
        open_write = [
            story_id
            for story_id, story in state.get("stories", {}).items()
            if story.get("mode") == "write"
            and story.get("status") in {"open", "returned"}
        ]
        if open_write:
            issues.append(
                "workspace already has a write-story owner: "
                + ", ".join(open_write)
            )
    manifest_protected = protected_patterns(state)
    declared_protected = set(envelope.get("protected_scope", []))
    missing_protected = sorted(
        pattern
        for pattern in manifest_protected
        if pattern not in declared_protected
    )
    if missing_protected:
        issues.append(
            "story omits manifest protected scope: "
            + ", ".join(missing_protected)
        )
    return issues


def story_issue_command(args: argparse.Namespace) -> dict[str, Any]:
    try:
        envelope = strict_json(Path(args.envelope).expanduser().resolve())
        root = Path(args.root).expanduser().resolve()
        state_dir = command_state_dir(args.state_dir)
        with state_lock(
            state_dir,
            artifact_names=CORE_ARTIFACTS,
        ):
            state, errors, current, _events = load_and_verify(
                root,
                state_dir,
                check_workspace=True,
                recover=True,
            )
            if errors or state is None or current is None:
                return stable_result(False, "blocked", issues=errors)
            try:
                import goal_runtime
            except ImportError:
                from . import goal_runtime
            scoped_values: list[str] = []
            scope_is_valid = True
            for field in ("write_scope", "protected_scope"):
                values = envelope.get(field)
                if (
                    not isinstance(values, list)
                    or not all(
                        isinstance(value, str)
                        and portable_relative(value)
                        for value in values
                    )
                ):
                    scope_is_valid = False
                    break
                scoped_values.extend(values)
            symlink_issues = (
                goal_runtime.project_scope_symlink_issues(
                    root,
                    state_dir,
                    scoped_values,
                )
                if scope_is_valid
                else []
            )
            state_scope_issues = (
                goal_runtime.project_scope_state_issues(
                    root,
                    state_dir,
                    scoped_values,
                )
                if scope_is_valid
                else []
            )
            if symlink_issues or state_scope_issues:
                return stable_result(
                    False,
                    "blocked",
                    issues=[*symlink_issues, *state_scope_issues],
                )
            scoped_current = (
                workspace_snapshot(
                    root,
                    state_dir,
                    [*workspace_patterns(state), *scoped_values],
                )
                if scope_is_valid
                else current
            )
            issues = [
                *mutation_blockers(state),
                *story_envelope_issues(
                    envelope,
                    state,
                    scoped_current,
                ),
            ]
            if issues:
                return stable_result(False, "blocked", issues=issues)
            story_id = envelope["story_id"]
            envelope_path = state_artifact_path(
                state_dir,
                ("stories",),
                story_id,
                create_parent=True,
            )
            baseline_path = state_artifact_path(
                state_dir,
                ("stories",),
                story_id,
                suffix=".baseline.json",
                create_parent=True,
            )
            write_unbound_immutable(
                state_dir, envelope_path, canonical_bytes(envelope)
            )
            write_unbound_immutable(
                state_dir, baseline_path, canonical_bytes(scoped_current)
            )
            event = make_event(
                state,
                goal_id=state["goal_id"],
                event_type="story_issued",
                payload={
                    "story_id": story_id,
                    "mode": envelope["mode"],
                    "envelope_sha256": envelope["envelope_sha256"],
                    "baseline_workspace_sha256": scoped_current["sha256"],
                    "plan_revision": current_plan_revision(state),
                    "acceptance_revision": state["acceptance_revision"],
                    "acceptance_ids": [
                        item["id"] for item in envelope["acceptance"]
                    ],
                    "write_scope": envelope["write_scope"],
                    "protected_scope": envelope["protected_scope"],
                },
                workspace=scoped_current,
            )
            state = persist_event(state_dir, state, event)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        return stable_result(False, "blocked", issues=[str(exc)])
    return stable_result(
        True,
        "active",
        result={
            "story_id": story_id,
            "status": state["stories"][story_id]["status"],
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
        },
    )


def story_return_command(args: argparse.Namespace) -> dict[str, Any]:
    try:
        receipt = strict_json(Path(args.receipt).expanduser().resolve())
        root = Path(args.root).expanduser().resolve()
        state_dir = command_state_dir(args.state_dir)
        with state_lock(
            state_dir,
            artifact_names=CORE_ARTIFACTS,
        ):
            state, errors, current, _events = load_and_verify(
                root,
                state_dir,
                check_workspace=True,
                recover=True,
            )
            if errors or state is None or current is None:
                return stable_result(False, "blocked", issues=errors)
            blocked = mutation_blockers(state)
            story_id = receipt.get("story_id")
            story = state.get("stories", {}).get(story_id)
            if (
                not isinstance(story, dict)
                or story.get("status") not in {"open", "returned"}
            ):
                blocked.append("receipt story is not open for return")
            elif (
                story.get("plan_revision") != current_plan_revision(state)
                or story.get("acceptance_revision")
                != state.get("acceptance_revision")
            ):
                blocked.append("receipt story revision is stale")
            if blocked:
                return stable_result(False, "blocked", issues=blocked)
            try:
                import goal_runtime
            except ImportError:
                from . import goal_runtime
            envelope = strict_json(
                state_artifact_path(state_dir, ("stories",), story_id)
            )
            baseline = strict_json(
                state_artifact_path(
                    state_dir,
                    ("stories",),
                    story_id,
                    suffix=".baseline.json",
                )
            )
            issues = goal_runtime.validate_receipt_against_story(
                receipt,
                envelope,
                baseline,
                current,
                root,
                state_dir,
            )
            if issues:
                return stable_result(False, "blocked", issues=issues)
            return_count = int(story.get("return_count", 0)) + 1
            artifact_id = f"{story_id}-r{return_count}"
            stored_path = state_artifact_path(
                state_dir,
                ("receipts", "stories"),
                artifact_id,
                create_parent=True,
            )
            write_unbound_immutable(
                state_dir, stored_path, canonical_bytes(receipt)
            )
            relative = stored_path.relative_to(state_dir).as_posix()
            event = make_event(
                state,
                goal_id=state["goal_id"],
                event_type="story_returned",
                payload={
                    "story_id": story_id,
                    "receipt_sha256": receipt["receipt_sha256"],
                    "receipt_path": relative,
                    "return_count": return_count,
                    "workspace_sha256": current["sha256"],
                },
                workspace=current,
            )
            state = persist_event(state_dir, state, event)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        return stable_result(False, "blocked", issues=[str(exc)])
    return stable_result(
        True,
        "ready_for_review",
        result={
            "story_id": story_id,
            "return_count": return_count,
            "workspace_sha256": current["sha256"],
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
        },
    )


def story_accept_command(args: argparse.Namespace) -> dict[str, Any]:
    try:
        root = Path(args.root).expanduser().resolve()
        state_dir = command_state_dir(args.state_dir)
        with state_lock(
            state_dir,
            artifact_names=CORE_ARTIFACTS,
        ):
            state, errors, current, _events = load_and_verify(
                root,
                state_dir,
                check_workspace=True,
                recover=True,
            )
            if errors or state is None or current is None:
                return stable_result(False, "blocked", issues=errors)
            issues = mutation_blockers(state)
            story = state.get("stories", {}).get(args.story_id)
            if not isinstance(story, dict) or story.get("status") != "returned":
                issues.append("story is not ready for acceptance")
            elif story.get("returned_workspace_sha256") != current["sha256"]:
                issues.append(
                    "story delivery is stale for the current workspace"
                )
            if issues:
                return stable_result(False, "blocked", issues=issues)
            event = make_event(
                state,
                goal_id=state["goal_id"],
                event_type="story_accepted",
                payload={
                    "story_id": args.story_id,
                    "receipt_sha256": story["receipt_sha256"],
                },
                workspace=current,
            )
            state = persist_event(state_dir, state, event)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        return stable_result(False, "blocked", issues=[str(exc)])
    return stable_result(
        True,
        "active",
        result={
            "story_id": args.story_id,
            "status": "accepted",
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
        },
    )


def completion_evidence_candidate(
    receipt: dict[str, Any],
    state: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    """Return the cycle-free evidence projection reviewed by the critic.

    The terminal gate, mutable final ledger-tail binding, and finalization
    timestamp are omitted. Everything that can change the substantive
    completion claim remains in the projection, including non-terminal gate
    evidence and the current ledger proof context.
    """

    raw_gates = receipt.get("gates")
    gates = raw_gates if isinstance(raw_gates, dict) else {}
    nonterminal_gates = {
        name: gates[name]
        for name in sorted(gates)
        if name != "terminal_critic"
    }
    raw_required = receipt.get("required_gates")
    required = raw_required if isinstance(raw_required, list) else []
    goal_binding = receipt.get("goal_binding")
    binding = goal_binding if isinstance(goal_binding, dict) else {}
    review_map = current_review_map(state, current.get("sha256"))
    review_receipts = {
        role: review["receipt_sha256"]
        for role, review in sorted(review_map.items())
        if role != "terminal_critic"
        and isinstance(review.get("receipt_sha256"), str)
    }
    blockers = state.get("blockers")
    blocker_projection = (
        {
            blocker_id: blockers[blocker_id]
            for blocker_id in sorted(blockers)
        }
        if isinstance(blockers, dict)
        else {}
    )
    plan = state.get("plan")
    project_binding_value = state.get("project_binding")
    project_binding_sha256 = (
        project_binding_value.get("identity_sha256")
        if isinstance(project_binding_value, dict)
        else None
    )
    return {
        "document_type": "quant_completion_evidence_candidate",
        "schema_version": 1,
        "project_id": receipt.get("project_id"),
        "objective": receipt.get("objective"),
        "scope": receipt.get("scope"),
        "required_gates": sorted(
            {
                name
                for name in required
                if isinstance(name, str)
                and name != "terminal_critic"
            }
        ),
        "gates": nonterminal_gates,
        "cost_authority": receipt.get("cost_authority"),
        "context": receipt.get("context"),
        "goal_binding": {
            "goal_id": binding.get("goal_id"),
            "objective_sha256": binding.get("objective_sha256"),
            "acceptance_ids": binding.get("acceptance_ids"),
            "acceptance_claims": binding.get("acceptance_claims"),
        },
        "ledger_proof": {
            "project_binding_sha256": project_binding_sha256,
            "delivery": goal_delivery(state),
            "workspace_sha256": current.get("sha256"),
            "plan_revision": current_plan_revision(state),
            "plan_sha256": (
                plan.get("sha256") if isinstance(plan, dict) else ""
            ),
            "acceptance_revision": state.get("acceptance_revision"),
            "acceptance_ids": [
                item["id"]
                for item in state.get("acceptance", [])
                if isinstance(item, dict)
                and is_portable_id(item.get("id"))
            ],
            "review_receipt_sha256_by_role": review_receipts,
            "blockers": blocker_projection,
        },
    }


def completion_evidence_candidate_sha256(
    receipt: dict[str, Any],
    state: dict[str, Any],
    current: dict[str, Any],
) -> str:
    return digest(completion_evidence_candidate(receipt, state, current))


def candidate_observation_time_issues(
    receipt: dict[str, Any],
) -> list[str]:
    """Bind every schema-defined candidate evidence time before completion."""

    candidate_completed_at = parse_time(receipt.get("completed_at"))
    if candidate_completed_at is None:
        return []
    observations: list[tuple[str, Any]] = []
    gates = receipt.get("gates")
    if isinstance(gates, dict):
        for gate_name, gate in sorted(gates.items()):
            if gate_name == "terminal_critic" or not isinstance(gate, dict):
                continue
            evidence = gate.get("evidence")
            if not isinstance(evidence, list):
                continue
            for index, item in enumerate(evidence):
                if not isinstance(item, dict):
                    continue
                label = (
                    f"gate {gate_name!r} evidence {index}"
                )
                observations.append(
                    (f"{label} checked_at", item.get("checked_at"))
                )
                data_identity = item.get("data_identity")
                if isinstance(data_identity, dict):
                    for field in ("collected_at", "source_as_of"):
                        observations.append(
                            (
                                f"{label} data_identity.{field}",
                                data_identity.get(field),
                            )
                        )
    cost_authority = receipt.get("cost_authority")
    actions = (
        cost_authority.get("actions")
        if isinstance(cost_authority, dict)
        else None
    )
    if isinstance(actions, list):
        for index, action in enumerate(actions):
            if isinstance(action, dict):
                observations.append(
                    (
                        "cost_authority.actions"
                        f"[{index}].evidence_checked_at",
                        action.get("evidence_checked_at"),
                    )
                )
    issues: list[str] = []
    for label, value in observations:
        observed_at = parse_time(value)
        if observed_at is None:
            issues.append(
                f"evidence candidate {label} is invalid"
            )
        elif observed_at > candidate_completed_at:
            issues.append(
                f"evidence candidate {label} occurs after candidate "
                "completed_at"
            )
    return issues


def completion_evidence_candidate_issues(
    receipt: dict[str, Any],
    state: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    """Check that a terminal candidate represents the current proof bundle."""

    issues: list[str] = []
    if receipt.get("schema_version") != 3:
        issues.append("evidence candidate schema_version must equal 3")
    if receipt.get("project_id") != state.get("project_id"):
        issues.append("evidence candidate project_id mismatch")
    if receipt.get("objective") != state.get("objective"):
        issues.append("evidence candidate objective mismatch")
    if parse_time(receipt.get("completed_at")) is None:
        issues.append("evidence candidate completed_at is invalid")
    issues.extend(
        review_completion_time_issues(
            receipt,
            state,
            current,
        )
    )
    scope = receipt.get("scope")
    if not isinstance(scope, dict):
        issues.append("evidence candidate scope must be an object")
    elif scope.get("assurance") != state.get("assurance"):
        issues.append("evidence candidate assurance mismatch")
    context = receipt.get("context")
    plan = state.get("plan")
    expected_plan_sha256 = (
        plan.get("sha256") if isinstance(plan, dict) else ""
    )
    if not isinstance(context, dict):
        issues.append("evidence candidate context must be an object")
    elif context.get("plan_sha256") != expected_plan_sha256:
        issues.append("evidence candidate plan binding mismatch")
    cost_authority = receipt.get("cost_authority")
    if not isinstance(cost_authority, dict):
        issues.append("evidence candidate cost authority is missing")

    expected_acceptance = {
        item["id"]
        for item in state.get("acceptance", [])
        if isinstance(item, dict) and is_portable_id(item.get("id"))
    }
    binding = receipt.get("goal_binding")
    if not isinstance(binding, dict):
        issues.append("evidence candidate goal binding is missing")
        binding = {}
    if binding.get("goal_id") != state.get("goal_id"):
        issues.append("evidence candidate goal_id mismatch")
    if binding.get("objective_sha256") != state.get("objective_sha256"):
        issues.append("evidence candidate objective hash mismatch")
    bound_acceptance = binding.get("acceptance_ids")
    if (
        not isinstance(bound_acceptance, list)
        or len(bound_acceptance) != len(set(bound_acceptance))
        or set(bound_acceptance) != expected_acceptance
    ):
        issues.append(
            "evidence candidate must bind every current acceptance ID"
        )

    policy = state.get("proof_policy")
    policy_required = (
        policy.get("required_gates")
        if isinstance(policy, dict)
        else []
    )
    raw_required = receipt.get("required_gates")
    if (
        not isinstance(raw_required, list)
        or len(raw_required) != len(set(raw_required))
        or set(raw_required) != set(policy_required)
    ):
        issues.append("evidence candidate required gates mismatch")
        raw_required = []
    gates = receipt.get("gates")
    if not isinstance(gates, dict):
        issues.append("evidence candidate gates must be an object")
        gates = {}
    issues.extend(candidate_observation_time_issues(receipt))
    nonterminal_required = {
        name for name in policy_required if name != "terminal_critic"
    }
    review_map = current_review_map(state, current.get("sha256"))
    for gate_name in sorted(nonterminal_required):
        gate = gates.get(gate_name)
        evidence = (
            gate.get("evidence") if isinstance(gate, dict) else None
        )
        if (
            not isinstance(gate, dict)
            or gate.get("status") != "passed"
            or not isinstance(evidence, list)
            or not evidence
        ):
            issues.append(
                f"evidence candidate gate {gate_name!r} is not passed"
            )
            continue
        matched_snapshot = False
        matched_review = gate_name not in review_map
        for item in evidence:
            extensions = (
                item.get("extensions")
                if isinstance(item, dict)
                else None
            )
            ledger_binding = (
                extensions.get("goal_ledger")
                if isinstance(extensions, dict)
                else None
            )
            if not isinstance(ledger_binding, dict):
                continue
            if (
                ledger_binding.get("goal_id") == state.get("goal_id")
                and ledger_binding.get("workspace_sha256")
                == current.get("sha256")
                and ledger_binding.get("plan_revision")
                == current_plan_revision(state)
                and ledger_binding.get("acceptance_revision")
                == state.get("acceptance_revision")
            ):
                matched_snapshot = True
                review = review_map.get(gate_name)
                if review is not None and ledger_binding.get(
                    "review_receipt_sha256"
                ) == review.get("receipt_sha256"):
                    matched_review = True
        if not matched_snapshot:
            issues.append(
                f"evidence candidate gate {gate_name!r} lacks current "
                "snapshot binding"
            )
        if not matched_review:
            issues.append(
                f"evidence candidate gate {gate_name!r} lacks current "
                "Review Verdict binding"
            )

    claims = binding.get("acceptance_claims")
    if not isinstance(claims, dict) or set(claims) != expected_acceptance:
        issues.append(
            "evidence candidate acceptance_claims must cover every "
            "current acceptance ID"
        )
        claims = {}
    for acceptance_id in sorted(expected_acceptance):
        acceptance_claims = claims.get(acceptance_id)
        if not isinstance(acceptance_claims, list) or not acceptance_claims:
            issues.append(
                f"evidence candidate acceptance {acceptance_id!r} "
                "has no direct evidence"
            )
            continue
        for claim in acceptance_claims:
            if not isinstance(claim, dict):
                issues.append(
                    f"evidence candidate acceptance {acceptance_id!r} "
                    "has an invalid claim"
                )
                continue
            gate_name = claim.get("gate")
            evidence_index = claim.get("evidence_index")
            if gate_name == "terminal_critic":
                issues.append(
                    "evidence candidate acceptance claims cannot depend "
                    "on the terminal critic"
                )
                continue
            gate = gates.get(gate_name)
            evidence = (
                gate.get("evidence") if isinstance(gate, dict) else None
            )
            if (
                not isinstance(gate, dict)
                or gate.get("status") != "passed"
                or not isinstance(evidence, list)
                or not isinstance(evidence_index, int)
                or isinstance(evidence_index, bool)
                or evidence_index < 0
                or evidence_index >= len(evidence)
                or not isinstance(evidence[evidence_index], dict)
            ):
                issues.append(
                    f"evidence candidate acceptance {acceptance_id!r} "
                    "references invalid evidence"
                )
                continue
            if claim.get("evidence_sha256") != digest(
                evidence[evidence_index]
            ):
                issues.append(
                    f"evidence candidate acceptance {acceptance_id!r} "
                    "evidence hash mismatch"
                )
    return issues


def completion_evidence_candidate_binding_issues(
    receipt: dict[str, Any],
    state: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    """Bind the final receipt projection to the current terminal verdict."""

    issues = completion_evidence_candidate_issues(
        receipt,
        state,
        current,
    )
    candidate_sha256 = completion_evidence_candidate_sha256(
        receipt,
        state,
        current,
    )
    review_map = current_review_map(state, current.get("sha256"))
    policy = state.get("proof_policy")
    required_roles = (
        policy.get("required_review_roles", [])
        if isinstance(policy, dict)
        else []
    )
    terminal = review_map.get("terminal_critic")
    if "terminal_critic" in required_roles:
        if terminal is None:
            issues.append(
                "completion evidence candidate lacks a current terminal "
                "critic"
            )
        elif terminal.get(
            "evidence_candidate_sha256"
        ) != candidate_sha256:
            issues.append(
                "final evidence candidate does not match terminal critic"
            )
    completion = state.get("completion_ready")
    if isinstance(completion, dict):
        if completion.get(
            "evidence_candidate_sha256"
        ) != candidate_sha256:
            issues.append(
                "completion_ready evidence candidate hash mismatch"
            )
        expected_terminal_receipt = (
            terminal.get("receipt_sha256")
            if isinstance(terminal, dict)
            else None
        )
        if completion.get(
            "terminal_review_receipt_sha256"
        ) != expected_terminal_receipt:
            issues.append(
                "completion_ready terminal review binding mismatch"
            )
    return issues


def review_receipt_hash(receipt: dict[str, Any]) -> str:
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    return digest(unsigned)


def review_receipt_issues(
    receipt: dict[str, Any],
    state: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    required_fields = {
        "document_type",
        "schema_version",
        "goal_id",
        "review_id",
        "role",
        "status",
        "plan_revision",
        "acceptance_revision",
        "acceptance_ids",
        "workspace_sha256",
        "summary",
        "findings",
        "checked_at",
        "receipt_sha256",
    }
    optional_fields = {"$schema", "evidence_candidate_sha256"}
    required_fields.add("review_scope")
    optional_fields.add("carry_forward_from_receipt_sha256")
    if set(receipt) - (required_fields | optional_fields):
        issues.append("review receipt contains unknown fields")
    if not required_fields.issubset(receipt):
        issues.append("review receipt is missing required fields")
    if receipt.get("document_type") != "quant_review_receipt":
        issues.append("review receipt document_type is invalid")
    if receipt.get("schema_version") != 1:
        issues.append("review receipt schema_version must equal 1")
    if receipt.get("goal_id") != state.get("goal_id"):
        issues.append("review receipt goal_id mismatch")
    if not is_portable_id(receipt.get("review_id")):
        issues.append("review receipt review_id is invalid")
    if receipt.get("role") not in REVIEW_ROLES:
        issues.append("review receipt role is invalid")
    selected_roles = state.get("proof_policy", {}).get(
        "required_review_roles",
        [],
    )
    if (
        receipt.get("role") in REVIEW_ROLES
        and receipt.get("role") not in selected_roles
    ):
        issues.append(
            "review receipt role is not selected by Goal proof policy"
        )
    if receipt.get("status") not in {"passed", "needs_repair", "blocked"}:
        issues.append("review receipt status is invalid")
    if receipt.get("plan_revision") != current_plan_revision(state):
        issues.append("review receipt plan revision is stale")
    if receipt.get("acceptance_revision") != state.get(
        "acceptance_revision"
    ):
        issues.append("review receipt acceptance revision is stale")
    expected_acceptance = {item["id"] for item in state["acceptance"]}
    bound_acceptance = receipt.get("acceptance_ids")
    receipt_acceptance_ids = {
        value
        for value in bound_acceptance
        if isinstance(value, str)
    } if isinstance(bound_acceptance, list) else set()
    if (
        not isinstance(bound_acceptance, list)
        or not bound_acceptance
        or len(bound_acceptance) != len(receipt_acceptance_ids)
        or not receipt_acceptance_ids.issubset(expected_acceptance)
    ):
        issues.append(
            "review receipt acceptance IDs must be a non-empty current subset"
        )
    if (
        receipt.get("role") == "terminal_critic"
        and (
            not isinstance(bound_acceptance, list)
            or receipt_acceptance_ids != expected_acceptance
        )
    ):
        issues.append(
            "terminal critic must cover all current acceptance IDs"
        )
    candidate_sha256 = receipt.get("evidence_candidate_sha256")
    if receipt.get("role") == "terminal_critic":
        if (
            not isinstance(candidate_sha256, str)
            or SHA256.fullmatch(candidate_sha256) is None
        ):
            issues.append(
                "terminal critic requires evidence_candidate_sha256"
            )
    elif candidate_sha256 is not None and (
        not isinstance(candidate_sha256, str)
        or SHA256.fullmatch(candidate_sha256) is None
    ):
        issues.append("review receipt evidence candidate hash is invalid")
    if receipt.get("workspace_sha256") != current.get("sha256"):
        issues.append("review receipt workspace snapshot is stale")
    review_scope = receipt.get("review_scope")
    if (
        not isinstance(review_scope, dict)
        or set(review_scope) != {"patterns", "sha256"}
    ):
        issues.append("review receipt scope binding is invalid")
    else:
        patterns = review_scope.get("patterns")
        if receipt.get("role") != "terminal_critic" and not patterns:
            issues.append(
                "non-terminal review requires a non-empty path scope"
            )
        try:
            expected_scope = review_scope_binding(
                Path(state["project_binding"]["root_realpath"]),
                Path(state["state_root"]["path_realpath"]),
                patterns,
            )
        except (KeyError, TypeError, ValueError) as exc:
            issues.append(f"review receipt scope binding is invalid: {exc}")
        else:
            if review_scope != expected_scope:
                issues.append("review receipt path scope is stale")
    if not isinstance(receipt.get("summary"), str) or not receipt[
        "summary"
    ].strip():
        issues.append("review receipt summary is required")
    findings = receipt.get("findings")
    if not isinstance(findings, list):
        issues.append("review receipt findings must be an array")
        findings = []
    finding_ids: list[str] = []
    blocking_open = False
    resolved_blocking_finding_ids: set[str] = set()
    for finding in findings:
        if (
            not isinstance(finding, dict)
            or set(finding)
            != {
                "id",
                "severity",
                "status",
                "summary",
                "evidence_refs",
            }
            or not is_portable_id(finding.get("id"))
            or finding.get("severity")
            not in {"blocking", "non_blocking", "info"}
            or finding.get("status") not in {"open", "resolved"}
            or not isinstance(finding.get("summary"), str)
            or not finding["summary"].strip()
            or not isinstance(finding.get("evidence_refs"), list)
            or not all(
                isinstance(value, str) and value.strip()
                for value in finding["evidence_refs"]
            )
            or (
                finding.get("severity") == "blocking"
                and not finding["evidence_refs"]
            )
        ):
            issues.append("review receipt finding is invalid")
            continue
        finding_ids.append(finding["id"])
        if (
            finding["severity"] == "blocking"
            and finding["status"] == "resolved"
        ):
            resolved_blocking_finding_ids.add(finding["id"])
        if (
            finding["severity"] == "blocking"
            and finding["status"] == "open"
        ):
            blocking_open = True
    if isinstance(receipt.get("summary"), str):
        issues.extend(
            prohibited_paid_data_reasons(
                receipt["summary"],
                allow_reported_violation=receipt.get("status")
                in {"needs_repair", "blocked"},
            )
        )
    for finding in findings:
        if isinstance(finding, dict) and isinstance(
            finding.get("summary"), str
        ):
            issues.extend(
                prohibited_paid_data_reasons(
                    finding["summary"],
                    allow_reported_violation=(
                        receipt.get("status")
                        in {"needs_repair", "blocked"}
                        and finding.get("severity") == "blocking"
                        and finding.get("status") == "open"
                    ),
                )
            )
    if len(finding_ids) != len(set(finding_ids)):
        issues.append("review receipt finding IDs must be unique")
    if receipt.get("status") == "passed" and blocking_open:
        issues.append("passed review cannot contain open blocking findings")
    if (
        receipt.get("status") in {"needs_repair", "blocked"}
        and not blocking_open
    ):
        issues.append(
            "non-passing review requires an open blocking finding"
        )
    if parse_time(receipt.get("checked_at")) is None:
        issues.append("review receipt checked_at is invalid")
    if receipt.get("receipt_sha256") != review_receipt_hash(receipt):
        issues.append("review receipt SHA-256 is invalid")
    current_review_statuses = current_review_status_map(
        state,
        current["sha256"],
    )
    current_reviews = {
        role: review
        for role, review in current_review_statuses.items()
        if review.get("status") == "passed"
    }
    for review in state.get("reviews", []):
        if review.get("review_id") == receipt.get("review_id"):
            issues.append("review_id cannot be reused")
    prior_role_review = current_review_statuses.get(receipt.get("role"))
    carry_forward = receipt.get("carry_forward_from_receipt_sha256")
    if carry_forward is not None:
        relevant_history = [
            review
            for review in state.get("reviews", [])
            if review.get("role") == receipt.get("role")
            and review.get("plan_revision")
            == receipt.get("plan_revision")
            and review.get("acceptance_revision")
            == receipt.get("acceptance_revision")
            and bool(
                receipt_acceptance_ids.intersection(
                    {
                        value
                        for value in review.get("acceptance_ids", [])
                        if isinstance(value, str)
                    }
                )
            )
        ]
        prior = relevant_history[-1] if relevant_history else None
        if (
            not isinstance(carry_forward, str)
            or SHA256.fullmatch(carry_forward) is None
        ):
            issues.append("review carry-forward hash is invalid")
        elif receipt.get("role") == "terminal_critic":
            issues.append("terminal critic cannot be carried forward")
        elif receipt.get("status") != "passed":
            issues.append("only a passed review can carry forward")
        elif (
            not isinstance(prior, dict)
            or prior.get("status") != "passed"
            or prior.get("receipt_sha256") != carry_forward
        ):
            issues.append(
                "review carry-forward requires the latest relevant "
                "passed verdict"
            )
        elif (
            prior.get("role") != receipt.get("role")
            or prior.get("plan_revision")
            != receipt.get("plan_revision")
            or prior.get("acceptance_revision")
            != receipt.get("acceptance_revision")
            or prior.get("acceptance_ids")
            != receipt.get("acceptance_ids")
            or prior.get("review_scope") != review_scope
            or prior.get("workspace_sha256")
            == receipt.get("workspace_sha256")
        ):
            issues.append(
                "review carry-forward context or unchanged scope mismatch"
            )
    if (
        isinstance(prior_role_review, dict)
        and prior_role_review.get("status") == "passed"
        and receipt.get("status") == "passed"
    ):
        issues.append(
            "current snapshot already has a passed verdict for this role"
        )
    outstanding_findings = {
        finding_id: acceptance_ids
        for (review_role, finding_id), acceptance_ids
        in outstanding_review_blocking_findings(
            state,
            role=receipt.get("role"),
        ).items()
        if review_role == receipt.get("role")
    }
    for finding_id in sorted(resolved_blocking_finding_ids):
        required_ids = outstanding_findings.get(finding_id)
        if not isinstance(required_ids, set):
            issues.append(
                "blocking finding resolution has no outstanding finding: "
                + finding_id
            )
            continue
        missing_ids = sorted(required_ids - receipt_acceptance_ids)
        if missing_ids:
            issues.append(
                "blocking finding resolution does not cover acceptance "
                f"IDs for {finding_id}: " + ", ".join(missing_ids)
            )
    if outstanding_findings and receipt.get("status") == "passed":
        required_acceptance_ids = set().union(
            *outstanding_findings.values()
        )
        missing_acceptance_ids = sorted(
            required_acceptance_ids - receipt_acceptance_ids
        )
        if missing_acceptance_ids:
            issues.append(
                "passed review does not cover prior blocking acceptance "
                "IDs: " + ", ".join(missing_acceptance_ids)
            )
        unresolved = sorted(
            set(outstanding_findings)
            - resolved_blocking_finding_ids
        )
        if unresolved:
            issues.append(
                "passed review does not resolve prior blocking findings: "
                + ", ".join(unresolved)
            )
    if receipt.get("role") == "terminal_critic":
        unresolved_other_reviews = {
            key: value
            for key, value in outstanding_review_blocking_findings(
                state
            ).items()
            if key[0] != "terminal_critic"
        }
        if unresolved_other_reviews:
            issues.append(
                "terminal critic cannot pass unresolved review blocking "
                "findings: "
                + ", ".join(
                    f"{role}:{finding_id}"
                    for role, finding_id in sorted(
                        unresolved_other_reviews
                    )
                )
            )
        missing = {
            "architecture_review",
            "adversarial_qa",
        } - set(current_reviews)
        if missing:
            issues.append(
                "terminal critic requires current architecture and "
                "adversarial reviews"
            )
        required_blockers = [
            blocker_id
            for blocker_id, blocker in state.get("blockers", {}).items()
            if blocker.get("required") is True
            and blocker.get("status") != "resolved"
        ]
        if required_blockers:
            issues.append(
                "terminal critic cannot pass unresolved required blockers"
            )
    return issues


def review_record_command(args: argparse.Namespace) -> dict[str, Any]:
    try:
        receipt = strict_json(Path(args.review).expanduser().resolve())
        policy_issues = input_policy_issues(receipt, "review receipt")
        if policy_issues:
            raise ValueError("; ".join(policy_issues))
        evidence_candidate = (
            strict_json(
                Path(args.evidence_candidate).expanduser().resolve()
            )
            if args.evidence_candidate
            else None
        )
        root = Path(args.root).expanduser().resolve()
        state_dir = command_state_dir(args.state_dir)
        with state_lock(
            state_dir,
            artifact_names=CORE_ARTIFACTS,
        ):
            state, errors, current, _events = load_and_verify(
                root,
                state_dir,
                check_workspace=True,
                recover=True,
            )
            if errors or state is None or current is None:
                return stable_result(False, "blocked", issues=errors)
            issues = [
                *mutation_blockers(state),
                *review_receipt_issues(receipt, state, current),
            ]
            if receipt.get("role") == "terminal_critic":
                if evidence_candidate is None:
                    issues.append(
                        "terminal critic requires --evidence-candidate"
                    )
                else:
                    issues.extend(
                        completion_evidence_candidate_issues(
                            evidence_candidate,
                            state,
                            current,
                        )
                    )
                    binding = evidence_candidate.get("goal_binding")
                    if (
                        not isinstance(binding, dict)
                        or binding.get("ledger_tail_sha256")
                        != state["ledger"]["tail_sha256"]
                    ):
                        issues.append(
                            "evidence candidate ledger tail is not current"
                        )
                    candidate_sha256 = (
                        completion_evidence_candidate_sha256(
                            evidence_candidate,
                            state,
                            current,
                        )
                    )
                    if receipt.get(
                        "evidence_candidate_sha256"
                    ) != candidate_sha256:
                        issues.append(
                            "terminal critic evidence candidate hash "
                            "mismatch"
                        )
                    issues.extend(
                        terminal_review_chronology_issues(
                            receipt.get("checked_at"),
                            state,
                            current,
                            candidate_completed_at=(
                                evidence_candidate.get("completed_at")
                            ),
                        )
                    )
            elif evidence_candidate is not None:
                issues.append(
                    "--evidence-candidate is only valid for terminal critic"
                )
            if issues:
                return stable_result(False, "blocked", issues=issues)
            review_id = receipt["review_id"]
            stored = state_artifact_path(
                state_dir,
                ("reviews",),
                review_id,
                create_parent=True,
            )
            write_unbound_immutable(
                state_dir, stored, canonical_bytes(receipt)
            )
            review = {
                "review_id": review_id,
                "role": receipt["role"],
                "status": receipt["status"],
                "plan_revision": receipt["plan_revision"],
                "acceptance_revision": receipt["acceptance_revision"],
                "acceptance_ids": receipt["acceptance_ids"],
                "workspace_sha256": receipt["workspace_sha256"],
                "receipt_sha256": receipt["receipt_sha256"],
                "review_scope": receipt["review_scope"],
                "carry_forward_from_receipt_sha256": receipt.get(
                    "carry_forward_from_receipt_sha256"
                ),
                "open_blocking_finding_ids": sorted(
                    finding["id"]
                    for finding in receipt["findings"]
                    if finding["severity"] == "blocking"
                    and finding["status"] == "open"
                ),
                "resolved_finding_ids": sorted(
                    finding["id"]
                    for finding in receipt["findings"]
                    if finding["severity"] == "blocking"
                    and finding["status"] == "resolved"
                ),
                "recorded_at": receipt["checked_at"],
                "event_seq": state["ledger"]["event_count"] + 1,
            }
            if receipt["role"] == "terminal_critic":
                review["evidence_candidate_sha256"] = receipt[
                    "evidence_candidate_sha256"
                ]
            event = make_event(
                state,
                goal_id=state["goal_id"],
                event_type="review_recorded",
                payload={"review": review},
                workspace=current,
            )
            state = persist_event(state_dir, state, event)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        return stable_result(False, "blocked", issues=[str(exc)])
    return stable_result(
        True,
        "active",
        result={
            "review_id": review_id,
            "role": review["role"],
            "status": review["status"],
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
        },
    )


def completion_ready_command(args: argparse.Namespace) -> dict[str, Any]:
    receipt_path = Path(args.receipt).expanduser().resolve()
    try:
        receipt = strict_json(receipt_path)
        root = Path(args.root).expanduser().resolve()
        state_dir = command_state_dir(args.state_dir)
        with state_lock(
            state_dir,
            artifact_names=CORE_ARTIFACTS,
        ):
            state, errors, current, _events = load_and_verify(
                root,
                state_dir,
                check_workspace=True,
                recover=True,
            )
            if errors or state is None or current is None:
                return stable_result(False, "blocked", issues=errors)
            receipt_sha256 = digest(receipt)
            existing = state.get("completion_ready")
            if isinstance(existing, dict):
                if existing.get("receipt_sha256") == receipt_sha256:
                    issues = [
                        *current_completion_consistency_issues(
                            state,
                            current,
                        ),
                        *completion_evidence_candidate_binding_issues(
                            receipt,
                            state,
                            current,
                        ),
                    ]
                    if issues:
                        return stable_result(
                            False, "blocked", issues=issues
                        )
                    return stable_result(
                        True,
                        "completion_ready",
                        result={
                            "goal_id": state["goal_id"],
                            "receipt_sha256": receipt_sha256,
                            "host_state": state["host"][
                                "last_observed_state"
                            ],
                            "ledger_tail_sha256": state["ledger"][
                                "tail_sha256"
                            ],
                            "idempotent": True,
                        },
                    )
                return stable_result(
                    False,
                    "blocked",
                    issues=[
                        "completion_ready already binds a different receipt"
                    ],
                )
            issues = [
                *mutation_blockers(state),
                *completion_context_issues(state, current),
                *completion_evidence_candidate_binding_issues(
                    receipt,
                    state,
                    current,
                ),
            ]
            if issues:
                return stable_result(False, "blocked", issues=issues)
            try:
                from validate_evidence_v3 import validate_receipt
            except ImportError:
                from .validate_evidence_v3 import validate_receipt
            validation_args = argparse.Namespace(
                project_root=str(root),
                manifest=args.manifest,
                goal_state=str(state_dir / STATE_NAME),
                require_capability=args.require_capability,
                require_automation=False,
                require_release=False,
                minimum_assurance=state["assurance"],
                input_binding_capture=args.input_binding_capture,
                team_packet=getattr(args, "team_packet", None),
                team_delivery=getattr(args, "team_delivery", []),
                team_integration=getattr(args, "team_integration", None),
                team_artifact_root=getattr(
                    args, "team_artifact_root", None
                ),
                team_workspace_root=getattr(
                    args, "team_workspace_root", None
                ),
                team_baseline_root=getattr(
                    args, "team_baseline_root", None
                ),
                team_worker_root=getattr(args, "team_worker_root", []),
            )
            evidence_errors = validate_receipt(receipt, validation_args)
            if evidence_errors:
                return stable_result(
                    False,
                    "blocked",
                    issues=[
                        f"evidence receipt: {error}"
                        for error in evidence_errors
                    ],
                )
            receipts_dir = state_artifact_dir(
                state_dir, "receipts", create=True
            )
            completion_number = len(state["completion_history"]) + 1
            relative = f"receipts/final-r{completion_number}.json"
            final_path = receipts_dir / f"final-r{completion_number}.json"
            write_unbound_immutable(
                state_dir, final_path, canonical_bytes(receipt)
            )
            pre_tail = state["ledger"]["tail_sha256"]
            candidate_sha256 = completion_evidence_candidate_sha256(
                receipt,
                state,
                current,
            )
            terminal_review = current_review_map(
                state,
                current["sha256"],
            ).get("terminal_critic")
            completion = {
                "receipt_sha256": receipt_sha256,
                "receipt_path": relative,
                "pre_ledger_tail_sha256": pre_tail,
                "evidence_candidate_sha256": candidate_sha256,
                "terminal_review_receipt_sha256": (
                    terminal_review.get("receipt_sha256")
                    if isinstance(terminal_review, dict)
                    else None
                ),
                "workspace_sha256": current["sha256"],
                "plan_revision": current_plan_revision(state),
                "acceptance_revision": state["acceptance_revision"],
                "recorded_at": now(),
                "event_seq": state["ledger"]["event_count"] + 1,
            }
            event = make_event(
                state,
                goal_id=state["goal_id"],
                event_type="completion_ready",
                payload={"completion": completion},
                workspace=current,
            )
            state = persist_event(state_dir, state, event)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        return stable_result(False, "blocked", issues=[str(exc)])
    return stable_result(
        True,
        "completion_ready",
        result={
            "goal_id": state["goal_id"],
            "receipt_sha256": receipt_sha256,
            "host_state": state["host"]["last_observed_state"],
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
            "host_mutated": False,
        },
    )


def observe_host_command(args: argparse.Namespace) -> dict[str, Any]:
    try:
        observation = strict_json(
            Path(args.observation).expanduser().resolve()
        )
        policy_issues = input_policy_issues(
            observation,
            "host observation",
        )
        if policy_issues:
            raise ValueError("; ".join(policy_issues))
        if set(observation) != {
            "goal_id",
            "state",
            "observed_at",
            "source",
        }:
            raise ValueError(
                "host observation requires goal_id, state, observed_at, source"
            )
        if observation.get("state") not in HOST_STATES:
            raise ValueError("host observation state is invalid")
        if parse_time(observation.get("observed_at")) is None:
            raise ValueError("host observation time is invalid")
        if (
            not isinstance(observation.get("source"), str)
            or not observation["source"].strip()
        ):
            raise ValueError("host observation source is required")
        root = Path(args.root).expanduser().resolve()
        state_dir = command_state_dir(args.state_dir)
        with state_lock(
            state_dir,
            artifact_names=CORE_ARTIFACTS,
        ):
            state, errors, current, _events = load_and_verify(
                root,
                state_dir,
                check_workspace=True,
                recover=True,
            )
            if errors or state is None or current is None:
                return stable_result(False, "blocked", issues=errors)
            if observation["goal_id"] != state["host"]["goal_id"]:
                return stable_result(
                    False,
                    "blocked",
                    issues=["host observation goal_id mismatch"],
                )
            observed_at = parse_time(observation["observed_at"])
            previous_at = parse_time(state["host"]["observed_at"])
            if (
                observed_at is None
                or previous_at is None
                or observed_at < previous_at
            ):
                return stable_result(
                    False,
                    "blocked",
                    issues=["host observation is older than ledger state"],
                )
            if (
                observed_at == previous_at
                and observation["state"]
                != state["host"]["last_observed_state"]
            ):
                return stable_result(
                    False,
                    "blocked",
                    issues=[
                        "host observation conflicts at the same timestamp"
                    ],
                )
            previous_state = state["host"]["last_observed_state"]
            if (
                previous_state in TERMINAL_HOST_STATES
                and observation["state"] != previous_state
            ):
                return stable_result(
                    False,
                    "blocked",
                    issues=[
                        f"terminal host Goal is {previous_state} and cannot "
                        "reopen through ordinary observation; create a new "
                        "Goal generation"
                    ],
                )
            host = {
                "goal_id": observation["goal_id"],
                "last_observed_state": observation["state"],
                "observed_at": observation["observed_at"],
                "source": observation["source"].strip(),
            }
            if host == state["host"]:
                divergence = host_ledger_divergence(state, current)
                status = (
                    "review_required"
                    if divergence
                    else host["last_observed_state"]
                )
                return stable_result(
                    not divergence,
                    status,
                    issues=divergence,
                    result={
                        "host": host,
                        "completion_ready": (
                            state.get("completion_ready") is not None
                        ),
                        "ledger_tail_sha256": state["ledger"]["tail_sha256"],
                        "idempotent": True,
                    },
                )
            event_type = {
                "cancelled": "goal_cancelled",
                "superseded": "goal_superseded",
            }.get(observation["state"], "host_state_observed")
            event = make_event(
                state,
                goal_id=state["goal_id"],
                event_type=event_type,
                payload={"host": host},
                workspace=current,
            )
            state = persist_event(state_dir, state, event)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        return stable_result(False, "blocked", issues=[str(exc)])
    completion = state.get("completion_ready")
    divergence = host_ledger_divergence(state, current)
    status = (
        "review_required"
        if divergence
        else state["host"]["last_observed_state"]
    )
    return stable_result(
        not divergence,
        status,
        issues=divergence,
        result={
            "host": state["host"],
            "completion_ready": completion is not None,
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="goal_ledger")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--root", required=True)
    init.add_argument("--state-dir")
    init.add_argument("--project-local", action="store_true")
    init.add_argument("--goal-id", required=True)
    init.add_argument("--host-goal-id", required=True)
    init.add_argument("--host-state", choices=sorted(HOST_STATES), default="active")
    init.add_argument("--host-source", default="codex-host")
    init.add_argument("--project-id", required=True)
    init.add_argument("--objective", required=True)
    init.add_argument("--acceptance", required=True)
    init.add_argument(
        "--assurance",
        choices=ASSURANCE_LEVELS,
        default="standard",
    )
    init.add_argument("--delivery", choices=DELIVERY_LEVELS)
    init.add_argument("--activation-reason", action="append", default=[])
    init.add_argument("--plan")
    init.add_argument("--manifest")
    init.add_argument("--require-capability", action="append", default=[])

    resume = subparsers.add_parser("resume")
    resume.add_argument("--root", required=True)
    resume.add_argument("--state-dir", required=True)

    revise = subparsers.add_parser("revise-acceptance")
    revise.add_argument("--root", required=True)
    revise.add_argument("--state-dir", required=True)
    revise.add_argument("--revision", required=True)
    revise.add_argument("--plan")
    revise.add_argument("--carry-forward-plan", action="store_true")

    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint.add_argument("--root", required=True)
    checkpoint.add_argument("--state-dir", required=True)
    checkpoint.add_argument("--checkpoint", required=True)

    capsule = subparsers.add_parser("continuation-capsule")
    capsule.add_argument("--root", required=True)
    capsule.add_argument("--state-dir", required=True)
    capsule.add_argument("--capsule", required=True)

    issue = subparsers.add_parser("story-issue")
    issue.add_argument("--root", required=True)
    issue.add_argument("--state-dir", required=True)
    issue.add_argument("--envelope", required=True)

    returned = subparsers.add_parser("story-return")
    returned.add_argument("--root", required=True)
    returned.add_argument("--state-dir", required=True)
    returned.add_argument("--receipt", required=True)

    accept = subparsers.add_parser("story-accept")
    accept.add_argument("--root", required=True)
    accept.add_argument("--state-dir", required=True)
    accept.add_argument("--story-id", required=True)

    review = subparsers.add_parser("review-record")
    review.add_argument("--root", required=True)
    review.add_argument("--state-dir", required=True)
    review.add_argument("--review", required=True)
    review.add_argument("--evidence-candidate")

    complete = subparsers.add_parser("completion-ready")
    complete.add_argument("--root", required=True)
    complete.add_argument("--state-dir", required=True)
    complete.add_argument("--receipt", required=True)
    complete.add_argument("--manifest")
    complete.add_argument("--input-binding-capture")
    complete.add_argument("--team-packet")
    complete.add_argument("--team-delivery", action="append", default=[])
    complete.add_argument("--team-integration")
    complete.add_argument("--team-artifact-root")
    complete.add_argument("--team-workspace-root")
    complete.add_argument("--team-baseline-root")
    complete.add_argument("--team-worker-root", action="append", default=[])
    complete.add_argument("--require-capability", action="append", default=[])

    observe = subparsers.add_parser("observe-host")
    observe.add_argument("--root", required=True)
    observe.add_argument("--state-dir", required=True)
    observe.add_argument("--observation", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    commands = {
        "init": init_command,
        "resume": resume_command,
        "revise-acceptance": revise_acceptance_command,
        "checkpoint": checkpoint_command,
        "continuation-capsule": continuation_capsule_command,
        "story-issue": story_issue_command,
        "story-return": story_return_command,
        "story-accept": story_accept_command,
        "review-record": review_record_command,
        "completion-ready": completion_ready_command,
        "observe-host": observe_host_command,
    }
    try:
        result = commands[args.command](args)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        result = stable_result(False, "blocked", issues=[str(exc)])
    return emit(result)


if __name__ == "__main__":
    raise SystemExit(main())
