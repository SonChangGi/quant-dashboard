#!/usr/bin/env python3
"""Small durable goal runtime with a hash-linked ledger and drift checks."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
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
        git,
        git_value,
        non_git_snapshot,
        open_regular_nofollow,
        parse_hash_chain_text,
        path_state,
        pending_transaction,
        portable_relative,
        project_binding,
        protected_path_snapshot,
        read_hash_chain,
        recover_pending_transaction,
        sanitize_origin,
        scope_pattern_selects_git_metadata,
        seal_hash_chain_event,
        snapshot_paths,
        state_lock,
        strict_json,
        verify_workspace_snapshot,
        workspace_snapshot,
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
        git,
        git_value,
        non_git_snapshot,
        open_regular_nofollow,
        parse_hash_chain_text,
        path_state,
        pending_transaction,
        portable_relative,
        project_binding,
        protected_path_snapshot,
        read_hash_chain,
        recover_pending_transaction,
        sanitize_origin,
        scope_pattern_selects_git_metadata,
        seal_hash_chain_event,
        snapshot_paths,
        state_lock,
        strict_json,
        verify_workspace_snapshot,
        workspace_snapshot,
    )


STATE_NAME = "goal-state.json"
LEDGER_NAME = "ledger.jsonl"
PENDING_NAME = "pending-event.json"
PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
GOAL_ID_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyz0123456789-_"
)
EVENT_TYPES = frozenset(
    {
        "goal_created",
        "story_opened",
        "story_accepted",
        "story_reopened",
        "story_cancelled",
        "checkpoint",
        "status_changed",
    }
)
LEGACY_SUPPORTED_RUNTIME_CAPABILITIES = frozenset({"multi-agent-write"})


def legacy_runtime_capability_issues(values: Any) -> list[str]:
    """Reject runtime proof lanes that this legacy state machine cannot prove."""

    if not isinstance(values, list):
        return []
    unsupported = sorted(
        {
            value
            for value in values
            if isinstance(value, str)
            and value not in LEGACY_SUPPORTED_RUNTIME_CAPABILITIES
        }
    )
    if not unsupported:
        return []
    return [
        "legacy goal runtime does not support runtime capabilities: "
        + ", ".join(unsupported)
        + "; use the host-aligned Goal ledger and standalone team protocol"
    ]


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def portable_id(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 128
        and all(character in GOAL_ID_CHARS for character in value)
    )


def resolved_state_dir(path_value: str) -> Path:
    """Resolve a state root without accepting a substituted symlink."""

    unresolved = Path(path_value).expanduser()
    if unresolved.is_symlink():
        raise ValueError(
            "state directory root must not be a symbolic link"
        )
    return unresolved.resolve()


def clear_pending(state_dir: Path) -> None:
    clear_pending_transaction(
        state_dir,
        pending_name=PENDING_NAME,
    )


def recover_pending(state_dir: Path) -> bool:
    """Finish a journalled event/state write after an interrupted process."""

    return recover_pending_transaction(
        state_dir,
        allowed_event_types=EVENT_TYPES,
        state_name=STATE_NAME,
        ledger_name=LEDGER_NAME,
        pending_name=PENDING_NAME,
        artifact_names=(".lock", STATE_NAME, LEDGER_NAME, PENDING_NAME),
        atomic_json_writer=atomic_json,
        atomic_bytes_writer=atomic_bytes,
        append_event_writer=append_event,
    )


def make_event(
    state: dict[str, Any],
    event_type: str,
    *,
    summary: str,
    payload: dict[str, Any] | None = None,
    story_id: str | None = None,
    workspace: dict[str, Any],
) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unsupported event type: {event_type}")
    ledger = state.get("ledger", {})
    event = {
        "document_type": "quant_goal_event",
        "schema_version": 1,
        "goal_id": state["goal_id"],
        "seq": int(ledger.get("event_count", 0)) + 1,
        "type": event_type,
        "at": now(),
        "story_id": story_id,
        "summary": summary,
        "payload": payload or {},
        "evidence": [],
        "workspace": {
            "sha256": workspace["sha256"],
            "head": workspace.get("head"),
            "branch": workspace.get("branch"),
            "changed_paths": sorted(snapshot_paths(workspace)),
        },
        "previous_sha256": ledger.get("tail_sha256", GENESIS),
    }
    return seal_hash_chain_event(event)


def intent_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "goal_id": state.get("goal_id"),
        "project_id": state.get("project_id"),
        "objective": state.get("objective"),
        "acceptance": state.get("acceptance"),
        "required_outcomes": state.get("required_outcomes"),
        "project_binding_sha256": (
            state.get("project_binding", {}).get("identity_sha256")
            if isinstance(state.get("project_binding"), dict)
            else None
        ),
        "plan": state.get("plan"),
        "manifest": state.get("manifest"),
        "assurance": state.get("assurance"),
        "profiles": state.get("profiles"),
        "required_capabilities": state.get("required_capabilities"),
        "runtime_capabilities": state.get("runtime_capabilities"),
    }


def intent_sha256(state: dict[str, Any]) -> str:
    return digest(intent_payload(state))


def parse_ledger_text(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    return parse_hash_chain_text(
        text,
        allowed_event_types=EVENT_TYPES,
        label="ledger",
    )


def read_ledger(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    return read_hash_chain(
        path,
        allowed_event_types=EVENT_TYPES,
        label="ledger",
        missing_error="ledger.jsonl is missing",
    )


def event_payload(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("payload")
    return value if isinstance(value, dict) else {}


def event_workspace(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("workspace")
    return value if isinstance(value, dict) else {}


def reduce_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    status = "active"
    open_ids: list[str] = []
    checkpoint: dict[str, Any] | None = None
    accepted: set[str] = set()
    write_story_ids: list[str] = []
    for event in events:
        story_id = event.get("story_id")
        event_type = event.get("type")
        if event_type in {"story_opened", "story_reopened"} and story_id:
            if story_id not in open_ids:
                open_ids.append(story_id)
            accepted.discard(story_id)
            runtime_capabilities = event_payload(event).get(
                "runtime_capabilities", []
            )
            if (
                "multi-agent-write" in runtime_capabilities
                and story_id not in write_story_ids
            ):
                write_story_ids.append(story_id)
        elif event_type in {"story_accepted", "story_cancelled"} and story_id:
            if story_id in open_ids:
                open_ids.remove(story_id)
            if event_type == "story_accepted":
                accepted.add(story_id)
                checkpoint = {
                    "event_seq": event["seq"],
                    "workspace_sha256": event_workspace(event).get(
                        "sha256"
                    ),
                }
        elif event_type == "checkpoint":
            checkpoint = {
                "event_seq": event["seq"],
                "workspace_sha256": event_workspace(event).get("sha256"),
            }
        elif event_type == "goal_created":
            checkpoint = {
                "event_seq": event["seq"],
                "workspace_sha256": event_workspace(event).get("sha256"),
            }
        elif event_type == "status_changed":
            status = event_payload(event).get("status", status)
    return {
        "status": status,
        "open_story_ids": open_ids,
        "accepted_story_ids": sorted(accepted),
        "runtime_facts": {
            "multi_agent_write_used": bool(write_story_ids),
            "write_story_ids": write_story_ids,
        },
        "last_checkpoint": checkpoint,
        "event_count": len(events),
        "tail_sha256": events[-1]["event_sha256"] if events else GENESIS,
    }


def story_artifact_path(
    state_dir: Path,
    directory: str,
    story_id: Any,
    suffix: str = ".json",
) -> Path:
    if not portable_id(story_id):
        raise ValueError("story_id must be a portable ID")
    parent = artifact_parent(state_dir, directory)
    candidate = parent / f"{story_id}{suffix}"
    if candidate.is_symlink():
        raise ValueError("story artifact must not be a symbolic link")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(parent)
    except ValueError as exc:
        raise ValueError("story artifact resolves outside state directory") from exc
    return candidate


def artifact_parent(
    state_dir: Path,
    directory: str,
    *,
    create: bool = False,
) -> Path:
    if directory not in {"stories", "receipts"}:
        raise ValueError("unsupported story artifact directory")
    base = state_dir.resolve(strict=True)
    parent = base / directory
    if parent.is_symlink():
        raise ValueError(
            f"{directory} artifact parent must not be a symbolic link"
        )
    if create and not parent.exists():
        parent.mkdir()
        fsync_directory(base)
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError(
            f"{directory} artifact parent must be a real directory"
        )
    if parent.resolve(strict=True).parent != base:
        raise ValueError(
            f"{directory} artifact parent resolves outside state directory"
        )
    return parent


def verify_story_artifacts(
    state_dir: Path,
    state: dict[str, Any],
    events: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    opened: dict[str, dict[str, Any]] = {}
    accepted: dict[str, dict[str, Any]] = {}
    for event in events:
        story_id = event.get("story_id")
        if story_id is not None and not portable_id(story_id):
            errors.append("ledger contains a non-portable story_id")
            continue
        if event.get("type") == "story_opened" and story_id:
            if story_id in opened:
                errors.append(f"story_id was reused: {story_id}")
            opened[story_id] = event
        elif event.get("type") == "story_accepted" and story_id:
            if story_id not in opened:
                errors.append(
                    f"story {story_id} was accepted without being opened"
                )
            if story_id in accepted:
                errors.append(f"story {story_id} was accepted more than once")
            accepted[story_id] = event
    for story_id, event in opened.items():
        try:
            envelope = load_story(state_dir, story_id)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"story {story_id} envelope is invalid: {exc}")
            continue
        if event_payload(event).get(
            "envelope_sha256"
        ) != envelope.get("envelope_sha256"):
            errors.append(f"story {story_id} envelope is not ledger-bound")
        if envelope.get("goal_id") != state.get("goal_id"):
            errors.append(f"story {story_id} goal binding is invalid")
        state_binding = state.get("project_binding")
        state_binding_sha = (
            state_binding.get("identity_sha256")
            if isinstance(state_binding, dict)
            else None
        )
        if envelope.get("project_binding_sha256") != state_binding_sha:
            errors.append(f"story {story_id} project binding is invalid")
        expected_runtime = (
            ["multi-agent-write"]
            if envelope.get("mode") == "write"
            else []
        )
        if event_payload(event).get(
            "runtime_capabilities"
        ) != expected_runtime:
            errors.append(
                f"story {story_id} runtime capability fact is invalid"
            )
        try:
            baseline = strict_json(
                story_artifact_path(
                    state_dir, "stories", story_id, ".baseline.json"
                )
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"story {story_id} baseline is invalid: {exc}")
            continue
        if event_payload(event).get(
            "baseline_sha256"
        ) != digest(baseline):
            errors.append(f"story {story_id} baseline is not ledger-bound")
        if not verify_workspace_snapshot(baseline):
            errors.append(f"story {story_id} baseline snapshot is invalid")
        if baseline.get("sha256") != envelope.get(
            "baseline_workspace_sha256"
        ):
            errors.append(f"story {story_id} baseline does not match envelope")
    for story_id, event in accepted.items():
        try:
            receipt = strict_json(
                story_artifact_path(state_dir, "receipts", story_id)
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"story {story_id} receipt is invalid: {exc}")
            continue
        if receipt.get("receipt_sha256") != receipt_hash(receipt):
            errors.append(f"story {story_id} stored receipt hash is invalid")
        if event_payload(event).get(
            "receipt_sha256"
        ) != receipt.get("receipt_sha256"):
            errors.append(f"story {story_id} receipt is not ledger-bound")
        opened_event = opened.get(story_id, {})
        payload = event_payload(event)
        if payload.get("envelope_sha256") != event_payload(
            opened_event
        ).get("envelope_sha256"):
            errors.append(
                f"story {story_id} accepted envelope is not ledger-bound"
            )
        if payload.get("baseline_sha256") != event_payload(
            opened_event
        ).get("baseline_sha256"):
            errors.append(
                f"story {story_id} accepted baseline is not ledger-bound"
            )
        if receipt.get("envelope_sha256") != payload.get(
            "envelope_sha256"
        ):
            errors.append(
                f"story {story_id} receipt envelope binding is invalid"
            )
    completed = [
        event
        for event in events
        if event.get("type") == "status_changed"
        and event_payload(event).get("status") == "complete"
    ]
    if len(completed) > 1:
        errors.append("goal completion event appears more than once")
    if completed:
        try:
            final_path = artifact_parent(state_dir, "receipts") / "final.json"
            if final_path.is_symlink():
                raise ValueError(
                    "final receipt artifact must not be a symbolic link"
                )
            final_receipt = strict_json(final_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"final receipt is invalid: {exc}")
        else:
            completion = completed[0]
            payload = event_payload(completion)
            final_receipt_sha256 = digest(final_receipt)
            if (
                payload.get("final_receipt_sha256")
                != final_receipt_sha256
                or payload.get("receipt_sha256")
                != final_receipt_sha256
            ):
                errors.append("final receipt is not ledger-bound")
            pre_completion_tail = payload.get(
                "pre_completion_ledger_tail_sha256"
            )
            if (
                not isinstance(pre_completion_tail, str)
                or pre_completion_tail != completion.get("previous_sha256")
            ):
                errors.append(
                    "completion event pre-completion ledger tail is invalid"
                )
            binding = final_receipt.get("goal_binding")
            if (
                not isinstance(binding, dict)
                or binding.get("ledger_tail_sha256")
                != pre_completion_tail
            ):
                errors.append(
                    "final receipt does not bind the pre-completion ledger tail"
                )
            if payload.get("goal_intent_sha256") != state.get(
                "intent_sha256"
            ):
                errors.append(
                    "completion event goal intent binding is invalid"
                )
    return errors


def load_and_verify(
    root: Path,
    state_dir: Path,
    *,
    check_workspace: bool,
    recover: bool = False,
) -> tuple[dict[str, Any] | None, list[str], dict[str, Any] | None]:
    errors: list[str] = []
    if recover:
        try:
            recover_pending(state_dir)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return None, [f"pending transaction recovery failed: {exc}"], None
    elif (state_dir / PENDING_NAME).exists():
        return (
            None,
            [
                "pending transaction requires resume or a mutating command; "
                "verify remains read-only"
            ],
            None,
        )
    state_path = state_dir / STATE_NAME
    try:
        state = strict_json(state_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return None, [f"invalid goal state: {exc}"], None
    if state.get("document_type") != "quant_goal_state":
        errors.append("goal state document_type is invalid")
    if state.get("schema_version") != 2:
        errors.append("goal state schema_version must equal 2")
    if not portable_id(state.get("goal_id")):
        errors.append("goal state goal_id is invalid")
    if not isinstance(state.get("project_id"), str) or not PROJECT_ID.fullmatch(
        state["project_id"]
    ):
        errors.append("goal state project_id is invalid")
    if not isinstance(state.get("objective"), str) or not state[
        "objective"
    ].strip():
        errors.append("goal objective is invalid")
    acceptance = state.get("acceptance")
    if (
        not isinstance(acceptance, list)
        or not acceptance
        or not all(
            isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and bool(item["id"])
            and isinstance(item.get("text"), str)
            and bool(item["text"])
            for item in acceptance
        )
    ):
        errors.append("goal acceptance is invalid")
    else:
        acceptance_ids = [item["id"] for item in acceptance]
        if len(acceptance_ids) != len(set(acceptance_ids)):
            errors.append("goal acceptance IDs are not unique")
    for field in (
        "required_outcomes",
        "profiles",
        "required_capabilities",
        "runtime_capabilities",
    ):
        values = state.get(field)
        if (
            not isinstance(values, list)
            or not all(
                isinstance(value, str) and value for value in values
            )
            or len(values) != len(set(values))
        ):
            errors.append(f"goal state {field} is invalid")
    errors.extend(
        legacy_runtime_capability_issues(state.get("runtime_capabilities"))
    )
    open_story_ids = state.get("open_story_ids")
    if (
        not isinstance(open_story_ids, list)
        or not all(portable_id(value) for value in open_story_ids)
        or len(open_story_ids) != len(set(open_story_ids))
    ):
        errors.append("goal state open_story_ids is invalid")
    if state.get("status") not in {"active", "blocked", "complete"}:
        errors.append("goal state status is invalid")
    if digest(state.get("objective", "")) != state.get("objective_sha256"):
        errors.append("goal objective hash mismatch")
    if intent_sha256(state) != state.get("intent_sha256"):
        errors.append("goal intent hash mismatch")
    binding = project_binding(root)
    stored_binding = state.get("project_binding")
    if not isinstance(stored_binding, dict) or stored_binding.get(
        "identity_sha256"
    ) != binding["identity_sha256"]:
        errors.append("project binding changed")
    for field in ("plan", "manifest"):
        bound = state.get(field)
        if bound is None:
            continue
        if not isinstance(bound, dict):
            errors.append(f"{field} binding is invalid")
            continue
        path = Path(bound.get("path_realpath", ""))
        if not path.is_file() or file_digest(path) != bound.get("sha256"):
            errors.append(f"{field} binding changed")
        if field == "manifest":
            try:
                path.resolve().relative_to(root.resolve())
            except ValueError:
                errors.append("manifest binding resolves outside project root")

    events, ledger_errors = read_ledger(state_dir / LEDGER_NAME)
    errors.extend(ledger_errors)
    for event in events:
        if event.get("goal_id") != state.get("goal_id"):
            errors.append("ledger event goal_id mismatch")
    errors.extend(verify_story_artifacts(state_dir, state, events))
    if events:
        created = events[0]
        if created.get("type") != "goal_created":
            errors.append("ledger must begin with goal_created")
        elif event_payload(created).get(
            "intent_sha256"
        ) != state.get("intent_sha256"):
            errors.append("goal intent is not ledger-bound")
        complete_indexes = [
            index
            for index, event in enumerate(events)
            if event.get("type") == "status_changed"
            and event_payload(event).get("status") == "complete"
        ]
        if complete_indexes and complete_indexes[-1] != len(events) - 1:
            errors.append("ledger contains events after goal completion")
    reduced = reduce_events(events)
    ledger = state.get("ledger")
    if not isinstance(ledger, dict):
        errors.append("goal state ledger cache is invalid")
    else:
        if ledger.get("event_count") != reduced["event_count"]:
            errors.append("goal state ledger event_count mismatch")
        if ledger.get("tail_sha256") != reduced["tail_sha256"]:
            errors.append("goal state ledger tail mismatch")
    if state.get("status") != reduced["status"]:
        errors.append("goal state status does not match ledger")
    if state.get("open_story_ids") != reduced["open_story_ids"]:
        errors.append("goal state open stories do not match ledger")
    if state.get("runtime_facts") != reduced["runtime_facts"]:
        errors.append("goal state runtime facts do not match ledger")
    cached_checkpoint = state.get("last_checkpoint")
    if not isinstance(cached_checkpoint, dict):
        errors.append("goal state checkpoint cache is invalid")
    elif reduced["last_checkpoint"] and (
        cached_checkpoint.get("event_seq")
        != reduced["last_checkpoint"]["event_seq"]
        or cached_checkpoint.get("workspace_sha256")
        != reduced["last_checkpoint"]["workspace_sha256"]
    ):
        errors.append("goal state checkpoint does not match ledger")
    elif not verify_workspace_snapshot(cached_checkpoint.get("workspace")):
        errors.append("goal state checkpoint workspace is invalid")
    elif cached_checkpoint.get("workspace_sha256") != cached_checkpoint.get(
        "workspace", {}
    ).get("sha256"):
        errors.append("goal state checkpoint workspace hash mismatch")
    current = None
    if check_workspace and not errors:
        current = workspace_snapshot(
            root,
            state_dir,
            manifest_protected_patterns(state),
        )
    return state, errors, current


def update_state_for_event(
    state: dict[str, Any],
    event: dict[str, Any],
    *,
    workspace: dict[str, Any],
) -> dict[str, Any]:
    updated = json.loads(json.dumps(state))
    updated["ledger"] = {
        "path": LEDGER_NAME,
        "event_count": event["seq"],
        "tail_sha256": event["event_sha256"],
    }
    if event["type"] in {"story_opened", "story_reopened"}:
        if event["story_id"] not in updated["open_story_ids"]:
            updated["open_story_ids"].append(event["story_id"])
        if "multi-agent-write" in event.get("payload", {}).get(
            "runtime_capabilities", []
        ):
            runtime_facts = updated.setdefault(
                "runtime_facts",
                {
                    "multi_agent_write_used": False,
                    "write_story_ids": [],
                },
            )
            runtime_facts["multi_agent_write_used"] = True
            if event["story_id"] not in runtime_facts["write_story_ids"]:
                runtime_facts["write_story_ids"].append(event["story_id"])
    elif event["type"] in {"story_accepted", "story_cancelled"}:
        updated["open_story_ids"] = [
            value
            for value in updated["open_story_ids"]
            if value != event["story_id"]
        ]
        if event["type"] == "story_accepted":
            updated["last_checkpoint"] = {
                "event_seq": event["seq"],
                "workspace_sha256": workspace["sha256"],
                "workspace": workspace,
            }
    elif event["type"] in {
        "goal_created",
        "checkpoint",
    }:
        updated["last_checkpoint"] = {
            "event_seq": event["seq"],
            "workspace_sha256": workspace["sha256"],
            "workspace": workspace,
        }
    elif event["type"] == "status_changed":
        updated["status"] = event["payload"]["status"]
    updated["updated_at"] = event["at"]
    return updated


def persist_event(
    state_dir: Path,
    state: dict[str, Any],
    event: dict[str, Any],
    workspace: dict[str, Any],
) -> dict[str, Any]:
    updated = update_state_for_event(
        state, event, workspace=workspace
    )
    atomic_json(
        state_dir / PENDING_NAME,
        pending_transaction(event, updated),
    )
    append_event(state_dir / LEDGER_NAME, event)
    atomic_json(state_dir / STATE_NAME, updated)
    clear_pending(state_dir)
    return updated


def binding_file(path_value: str | None) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"bound file does not exist: {path}")
    return {"path_realpath": str(path), "sha256": file_digest(path)}


def validated_manifest_binding(
    root: Path,
    path_value: str | None,
    project_id: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not path_value:
        return None, {}
    path = Path(path_value).expanduser().resolve()
    try:
        relative = path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(
            "manifest must stay within the project root"
        ) from exc
    if not path.is_file():
        raise ValueError(f"bound manifest does not exist: {path}")
    manifest = strict_json(path)
    if manifest.get("schema_version") != 2:
        raise ValueError("goal runtime requires a schema_version 2 manifest")
    from validate_project_v2 import validate as validate_project_v2

    errors, _warnings = validate_project_v2(root, manifest)
    if errors:
        raise ValueError("invalid manifest: " + "; ".join(errors))
    manifest_project = manifest.get("project", {})
    if manifest_project.get("id") != project_id:
        raise ValueError(
            "manifest project.id does not match --project-id"
        )
    return (
        {
            "path_realpath": str(path),
            "path_project_relative": relative.as_posix(),
            "sha256": file_digest(path),
            "schema_version": 2,
            "project_id": project_id,
        },
        manifest,
    )


def protected_patterns_from_manifest(
    manifest: dict[str, Any],
) -> list[str]:
    contracts = manifest.get("contracts")
    values = (
        contracts.get("protected_paths")
        if isinstance(contracts, dict)
        else []
    )
    if not isinstance(values, list):
        return []
    return sorted(
        {
            value
            for value in values
            if isinstance(value, str) and portable_relative(value)
        }
    )


def parse_acceptance(values: list[str]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for value in values:
        if "=" not in value:
            raise ValueError("acceptance must use id=text")
        acceptance_id, text = (
            item.strip() for item in value.split("=", 1)
        )
        if not acceptance_id or not text:
            raise ValueError("acceptance must use non-empty id=text")
        result.append({"id": acceptance_id, "text": text})
    ids = [item["id"] for item in result]
    if len(ids) != len(set(ids)):
        raise ValueError("acceptance IDs must be unique")
    if not result:
        raise ValueError("at least one acceptance criterion is required")
    return result


def story_acceptance_issues(
    story_value: Any,
    goal_value: Any,
) -> list[str]:
    """Require a Story to quote an exact non-empty subset of Goal acceptance."""

    if not isinstance(story_value, list) or not story_value:
        return ["envelope acceptance must be non-empty"]
    normalized: list[dict[str, str]] = []
    for item in story_value:
        if (
            not isinstance(item, dict)
            or set(item) != {"id", "text"}
            or not isinstance(item.get("id"), str)
            or not item["id"]
            or not isinstance(item.get("text"), str)
            or not item["text"]
        ):
            return [
                "envelope acceptance items require non-empty id and text"
            ]
        normalized.append({"id": item["id"], "text": item["text"]})
    identifiers = [item["id"] for item in normalized]
    if len(identifiers) != len(set(identifiers)):
        return ["envelope acceptance IDs must be unique"]
    goal_by_id = {
        item["id"]: item["text"]
        for item in goal_value
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("text"), str)
    } if isinstance(goal_value, list) else {}
    if any(
        goal_by_id.get(item["id"]) != item["text"]
        for item in normalized
    ):
        return [
            "envelope acceptance must exactly match current Goal acceptance"
        ]
    return []


def untrusted_policy_issues(value: Any, label: str) -> list[str]:
    """Apply the canonical secret and paid-transition scanner to JSON input."""

    try:
        from capability_model import policy_violations
    except ImportError:
        from .capability_model import policy_violations
    return [
        f"{label} policy: {issue}"
        for issue in policy_violations(value)
    ]


def paid_data_prose_issues(
    values: list[Any],
    label: str,
    *,
    allow_reported_violation: bool = False,
) -> list[str]:
    """Reject proof or instruction prose that claims paid-data acquisition."""

    try:
        from capability_model import prohibited_paid_data_reasons
    except ImportError:
        from .capability_model import prohibited_paid_data_reasons
    text = "\n".join(
        value for value in values if isinstance(value, str)
    )
    return [
        f"{label}: {issue}"
        for issue in prohibited_paid_data_reasons(
            text,
            allow_reported_violation=allow_reported_violation,
        )
    ]


def story_envelope_input_issues(envelope: dict[str, Any]) -> list[str]:
    required = {
        "document_type",
        "schema_version",
        "goal_id",
        "story_id",
        "project_binding_sha256",
        "objective",
        "mode",
        "write_scope",
        "protected_scope",
        "depends_on",
        "acceptance",
        "external_effects",
        "cost_class",
        "baseline_workspace_sha256",
        "issued_at",
        "envelope_sha256",
    }
    allowed = required | {"$schema"}
    issues: list[str] = []
    if set(envelope) - allowed:
        issues.append("story envelope contains unknown fields")
    if not required.issubset(envelope):
        issues.append("story envelope is missing required fields")
    issues.extend(untrusted_policy_issues(envelope, "story envelope"))
    acceptance = envelope.get("acceptance")
    envelope_prose: list[Any] = [envelope.get("objective")]
    if isinstance(acceptance, list):
        envelope_prose.extend(
            item.get("text")
            for item in acceptance
            if isinstance(item, dict)
        )
    issues.extend(
        paid_data_prose_issues(
            envelope_prose,
            "story envelope paid-data policy",
        )
    )
    return issues


def story_receipt_input_issues(receipt: dict[str, Any]) -> list[str]:
    required = {
        "document_type",
        "schema_version",
        "goal_id",
        "story_id",
        "envelope_sha256",
        "status",
        "summary",
        "changed_paths",
        "claims",
        "evidence",
        "workspace_sha256",
        "completed_at",
        "receipt_sha256",
    }
    allowed = required | {"$schema"}
    issues: list[str] = []
    if set(receipt) - allowed:
        issues.append("story receipt contains unknown fields")
    if not required.issubset(receipt):
        issues.append("story receipt is missing required fields")
    issues.extend(untrusted_policy_issues(receipt, "story receipt"))
    evidence = receipt.get("evidence")
    receipt_prose: list[Any] = [receipt.get("summary")]
    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, dict):
                continue
            receipt_prose.extend(
                item.get(field) for field in ("summary", "ref")
            )
    issues.extend(
        paid_data_prose_issues(
            receipt_prose,
            "story receipt paid-data policy",
        )
    )
    return issues


def init_command(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).expanduser().resolve()
    state_dir = resolved_state_dir(args.state_dir)
    if not root.is_dir():
        return stable_result(False, "blocked", issues=["project root missing"])
    ensure_state_location(root, state_dir)
    if not portable_id(args.goal_id):
        return stable_result(
            False,
            "blocked",
            issues=["goal_id must use lowercase letters, digits, - or _"],
        )
    if not isinstance(args.project_id, str) or not PROJECT_ID.fullmatch(
        args.project_id
    ):
        return stable_result(
            False,
            "blocked",
            issues=[
                "project_id must use lowercase letters, digits, and hyphens"
            ],
        )
    if not isinstance(args.objective, str) or not args.objective.strip():
        return stable_result(
            False, "blocked", issues=["objective must be non-empty"]
        )
    acceptance = parse_acceptance(args.acceptance)
    policy_issues = untrusted_policy_issues(
        {
            "objective": args.objective,
            "acceptance": acceptance,
        },
        "goal state",
    )
    policy_issues.extend(
        paid_data_prose_issues(
            [
                args.objective,
                *(item.get("text") for item in acceptance),
            ],
            "goal state paid-data policy",
        )
    )
    if policy_issues:
        return stable_result(
            False,
            "blocked",
            issues=policy_issues,
        )
    outcomes = list(dict.fromkeys(args.require_outcome))
    if not all(
        isinstance(value, str) and value.strip() for value in outcomes
    ):
        return stable_result(
            False,
            "blocked",
            issues=["required outcomes must be non-empty strings"],
        )
    manifest_binding, manifest = validated_manifest_binding(
        root, args.manifest, args.project_id
    )
    from capability_model import (
        ASSURANCE_LEVELS,
        ASSURANCE_RANK,
        RUNTIME_CAPABILITIES,
        resolve,
    )

    manifest_context = resolve(manifest)
    requested_assurance = args.assurance
    if manifest:
        requested_assurance = ASSURANCE_LEVELS[
            max(
                ASSURANCE_RANK[args.assurance],
                ASSURANCE_RANK[manifest_context["assurance"]],
            )
        ]
    context = resolve(
        manifest,
        capabilities=args.require_capability,
        profiles=args.profile,
        assurance=requested_assurance,
    )
    effective_capabilities = context["effective_capabilities"]
    project_capabilities = [
        value
        for value in effective_capabilities
        if value not in RUNTIME_CAPABILITIES
    ]
    runtime_capabilities = [
        value
        for value in effective_capabilities
        if value in RUNTIME_CAPABILITIES
    ]
    runtime_issues = legacy_runtime_capability_issues(runtime_capabilities)
    if runtime_issues:
        return stable_result(False, "blocked", issues=runtime_issues)
    if manifest:
        manifest_project_capabilities = {
            value
            for value in manifest_context["effective_capabilities"]
            if value not in RUNTIME_CAPABILITIES
        }
        undeclared_task_capabilities = sorted(
            set(project_capabilities) - manifest_project_capabilities
        )
        if undeclared_task_capabilities:
            return stable_result(
                False,
                "blocked",
                issues=[
                    "goal capability/profile overlay exceeds manifest: "
                    + ", ".join(undeclared_task_capabilities)
                ],
            )
    created = now()
    workspace = workspace_snapshot(
        root,
        state_dir,
        protected_patterns_from_manifest(manifest),
    )
    state = {
        "document_type": "quant_goal_state",
        "schema_version": 2,
        "goal_id": args.goal_id,
        "project_id": args.project_id,
        "objective": args.objective,
        "objective_sha256": digest(args.objective),
        "acceptance": acceptance,
        "required_outcomes": outcomes,
        "status": "active",
        "project_binding": project_binding(root),
        "plan": binding_file(args.plan),
        "manifest": manifest_binding,
        "assurance": context["assurance"],
        "profiles": context["profiles"],
        "required_capabilities": project_capabilities,
        "runtime_capabilities": runtime_capabilities,
        "runtime_facts": {
            "multi_agent_write_used": False,
            "write_story_ids": [],
        },
        "open_story_ids": [],
        "ledger": {
            "path": LEDGER_NAME,
            "event_count": 0,
            "tail_sha256": GENESIS,
        },
        "last_checkpoint": {
            "event_seq": 0,
            "workspace_sha256": workspace["sha256"],
            "workspace": workspace,
        },
        "created_at": created,
        "updated_at": created,
    }
    state["intent_sha256"] = intent_sha256(state)
    with state_lock(state_dir, create=True):
        recover_pending(state_dir)
        if (state_dir / STATE_NAME).exists() or (
            state_dir / LEDGER_NAME
        ).exists():
            return stable_result(
                False,
                "blocked",
                issues=["goal state already exists"],
            )
        event = make_event(
            state,
            "goal_created",
            summary="Goal initialized",
            payload={
                "objective_sha256": state["objective_sha256"],
                "intent_sha256": state["intent_sha256"],
                "acceptance_ids": [
                    item["id"] for item in acceptance
                ],
            },
            workspace=workspace,
        )
        state = persist_event(
            state_dir, state, event, workspace=workspace
        )
    return stable_result(
        True,
        "pass",
        result={
            "goal_id": state["goal_id"],
            "state_dir": str(state_dir),
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
            "workspace_sha256": workspace["sha256"],
        },
    )


def verify_command(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).expanduser().resolve()
    state_dir = resolved_state_dir(args.state_dir)
    if not root.is_dir():
        return stable_result(False, "blocked", issues=["project root missing"])
    with state_lock(state_dir):
        state, errors, current = load_and_verify(
            root, state_dir, check_workspace=True
        )
    if errors:
        return stable_result(False, "blocked", issues=errors)
    assert state is not None and current is not None
    return stable_result(
        True,
        "pass",
        result={
            "goal_id": state["goal_id"],
            "status": state["status"],
            "open_story_ids": state["open_story_ids"],
            "ledger": state["ledger"],
            "current_workspace_sha256": current["sha256"],
        },
    )


def changed_since(
    baseline: dict[str, Any],
    current: dict[str, Any],
    root: Path | None = None,
) -> list[str]:
    baseline_paths = snapshot_paths(baseline)
    current_paths = snapshot_paths(current)
    paths = set(baseline_paths) | set(current_paths)
    changed = {
        path
        for path in paths
        if baseline_paths.get(path) != current_paths.get(path)
    }
    if baseline.get("diff_sha256") != current.get("diff_sha256"):
        changed.update(paths)
    if baseline.get("kind") == "git" and current.get("kind") == "git":
        baseline_head = baseline.get("head")
        current_head = current.get("head")
        if baseline_head != current_head:
            if (
                not isinstance(baseline_head, str)
                or not baseline_head
                or not isinstance(current_head, str)
                or not current_head
            ):
                raise ValueError(
                    "Git HEAD changed without a comparable commit range"
                )
            if root is None:
                raise ValueError(
                    "project root is required to verify committed story changes"
                )
            root = root.resolve()
            if git_value(root, "rev-parse", "HEAD") != current_head:
                raise ValueError(
                    "current workspace HEAD does not match the project root"
                )
            ancestor = git(
                root,
                "merge-base",
                "--is-ancestor",
                baseline_head,
                current_head,
            )
            if ancestor.returncode:
                if ancestor.returncode == 1:
                    raise ValueError(
                        "story baseline HEAD is not an ancestor of current HEAD"
                    )
                raise ValueError(
                    ancestor.stderr.strip()
                    or "Git ancestry verification failed"
                )
            committed = git(
                root,
                "diff",
                "--name-status",
                "-z",
                "--find-renames",
                baseline_head,
                current_head,
                "--",
            )
            if committed.returncode:
                raise ValueError(
                    committed.stderr.strip()
                    or "Git commit-range path scan failed"
                )
            tokens = committed.stdout.split("\0")
            index = 0
            while index < len(tokens):
                token = tokens[index]
                index += 1
                if not token:
                    continue
                if "\t" in token:
                    status, first_path = token.split("\t", 1)
                else:
                    status = token
                    if index >= len(tokens) or not tokens[index]:
                        raise ValueError(
                            "Git commit-range path scan was malformed"
                        )
                    first_path = tokens[index]
                    index += 1
                status_code = status[:1]
                if status_code not in {
                    "A",
                    "B",
                    "C",
                    "D",
                    "M",
                    "R",
                    "T",
                    "U",
                    "X",
                }:
                    raise ValueError(
                        "Git commit-range path scan returned "
                        f"unsupported status: {status}"
                    )
                if portable_relative(first_path):
                    changed.add(first_path)
                if status_code in {"C", "R"}:
                    if index >= len(tokens) or not tokens[index]:
                        raise ValueError(
                            "Git rename/copy path scan was malformed"
                        )
                    second_path = tokens[index]
                    index += 1
                    if portable_relative(second_path):
                        changed.add(second_path)
    return sorted(changed)


def _segment_glob_matches(path: str, pattern: str) -> bool:
    path_segments = tuple(path.rstrip("/").split("/"))
    pattern_segments = tuple(pattern.rstrip("/").split("/"))
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


def matches(path: str, patterns: list[str]) -> bool:
    return any(_segment_glob_matches(path, pattern) for pattern in patterns)


def matches_protected(path: str, patterns: list[str]) -> bool:
    """Match prohibited scope conservatively across filesystem case modes."""

    return any(
        _segment_glob_matches(path.casefold(), pattern.casefold())
        for pattern in patterns
    )


def _scope_can_touch_symlink(relative: str, pattern: str) -> bool:
    """Return whether a scope can select or traverse a project symlink."""

    path_segments = tuple(relative.rstrip("/").split("/"))
    pattern_segments = tuple(pattern.rstrip("/").split("/"))
    memo: dict[tuple[int, int], bool] = {}

    def visit(pattern_index: int, path_index: int) -> bool:
        key = (pattern_index, path_index)
        if key in memo:
            return memo[key]
        if path_index == len(path_segments):
            # The symlink itself matched the consumed prefix, or a descendant
            # below it can satisfy the remaining pattern.
            result = True
        elif pattern_index == len(pattern_segments):
            result = False
        elif pattern_segments[pattern_index] == "**":
            result = visit(pattern_index + 1, path_index) or visit(
                pattern_index, path_index + 1
            )
        else:
            result = fnmatch.fnmatchcase(
                path_segments[path_index].casefold(),
                pattern_segments[pattern_index].casefold(),
            ) and visit(pattern_index + 1, path_index + 1)
        memo[key] = result
        return result

    return visit(0, 0)


def project_scope_symlink_issues(
    root: Path,
    state_dir: Path,
    patterns: list[str],
    *,
    scope_label: str = "story",
) -> list[str]:
    """Find project symlinks selected by, or traversed by, bounded scopes."""

    if not patterns:
        return []
    root = root.resolve()
    excluded = state_dir.resolve()
    symlinks: set[str] = set()
    for current, directories, files in os.walk(
        root, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        retained: list[str] = []
        for name in sorted(directories):
            if name.casefold() == ".git":
                continue
            candidate = current_path / name
            if candidate.is_symlink():
                symlinks.add(candidate.relative_to(root).as_posix())
                continue
            if candidate.resolve() == excluded:
                continue
            retained.append(name)
        directories[:] = retained
        for name in sorted(files):
            candidate = current_path / name
            if candidate.is_symlink():
                symlinks.add(candidate.relative_to(root).as_posix())
    unsafe = sorted(
        relative
        for relative in symlinks
        if any(
            _scope_can_touch_symlink(relative, pattern)
            for pattern in patterns
        )
    )
    if not unsafe:
        return []
    return [
        f"{scope_label} scope selects or traverses project symbolic link: "
        + ", ".join(unsafe)
    ]


def project_scope_state_issues(
    root: Path,
    state_dir: Path,
    patterns: list[str],
    *,
    scope_label: str = "story",
) -> list[str]:
    """Reject scopes that can select or traverse project-local Goal state."""

    if not patterns:
        return []
    root = root.resolve()
    try:
        relative = state_dir.resolve().relative_to(root).as_posix()
    except ValueError:
        return []
    explicit_patterns = [
        pattern
        for pattern in patterns
        if _scope_can_touch_symlink(relative, pattern)
        and any(
            segment not in {"*", "**"}
            for segment in pattern.rstrip("/").split("/")
        )
    ]
    if relative == "." or explicit_patterns:
        return [
            f"{scope_label} scope selects or traverses project-local "
            f"Goal state: {relative}"
        ]
    return []


def snapshot_scope_symlink_issues(
    snapshot: dict[str, Any],
    patterns: list[str],
) -> list[str]:
    unsafe = sorted(
        path
        for path, state in snapshot_paths(snapshot).items()
        if isinstance(state, dict)
        and state.get("kind") == "symlink"
        and any(
            _scope_can_touch_symlink(path, pattern)
            for pattern in patterns
        )
    )
    if not unsafe:
        return []
    return [
        "story scope selects or traverses workspace symbolic link: "
        + ", ".join(unsafe)
    ]


def load_story(state_dir: Path, story_id: str) -> dict[str, Any]:
    envelope = strict_json(
        story_artifact_path(state_dir, "stories", story_id)
    )
    if envelope.get("story_id") != story_id:
        raise ValueError("stored story_id does not match filename")
    if envelope.get("envelope_sha256") != envelope_hash(envelope):
        raise ValueError("stored story envelope hash is invalid")
    return envelope


def load_story_baseline(
    state_dir: Path, story_id: str
) -> dict[str, Any]:
    return strict_json(
        story_artifact_path(
            state_dir, "stories", story_id, ".baseline.json"
        )
    )


def manifest_protected_patterns(state: dict[str, Any]) -> list[str]:
    binding = state.get("manifest")
    if not isinstance(binding, dict):
        return []
    path_value = binding.get("path_realpath")
    if not isinstance(path_value, str):
        return []
    manifest = strict_json(Path(path_value))
    if manifest.get("schema_version") != 2:
        return []
    return protected_patterns_from_manifest(manifest)


def resume_evaluation(
    state: dict[str, Any],
    state_dir: Path,
    current: dict[str, Any],
    root: Path | None = None,
) -> dict[str, Any]:
    checkpoint = state["last_checkpoint"]["workspace"]
    if current["sha256"] == checkpoint["sha256"]:
        return stable_result(
            True,
            "pass",
            result={
                "goal_id": state["goal_id"],
                "workspace_sha256": current["sha256"],
                "drift_paths": [],
            },
        )
    if (
        current.get("kind") != checkpoint.get("kind")
        or current.get("branch") != checkpoint.get("branch")
    ):
        return stable_result(
            False,
            "blocked",
            issues=["Git/project identity changed since checkpoint"],
        )
    open_ids = state.get("open_story_ids", [])
    open_stories: list[dict[str, Any]] = []
    try:
        open_stories = [
            load_story(state_dir, story_id) for story_id in open_ids
        ]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return stable_result(
            False,
            "blocked",
            issues=[f"open story envelope is invalid: {exc}"],
        )
    write_stories = [
        story for story in open_stories if story.get("mode") == "write"
    ]
    if len(write_stories) != 1:
        return stable_result(
            False,
            "blocked",
            issues=["workspace drift has no single write-story owner"],
        )
    story = write_stories[0]
    if root is None:
        root_value = state.get("project_binding", {}).get("root_realpath")
        if isinstance(root_value, str) and root_value:
            root = Path(root_value)
    drift = changed_since(checkpoint, current, root)
    write_scope = story.get("write_scope", [])
    protected = story.get("protected_scope", [])
    out_of_scope = [
        path for path in drift if not matches(path, write_scope)
    ]
    protected_drift = [
        path for path in drift if matches_protected(path, protected)
    ]
    if out_of_scope or protected_drift:
        issues = []
        if out_of_scope:
            issues.append(
                "drift outside story write scope: "
                + ", ".join(out_of_scope)
            )
        if protected_drift:
            issues.append(
                "drift touches protected scope: "
                + ", ".join(protected_drift)
            )
        return stable_result(False, "blocked", issues=issues)
    return stable_result(
        False,
        "review_required",
        issues=[
            "in-scope interrupted story changes require primary-owner review"
        ],
        result={
            "goal_id": state["goal_id"],
            "story_id": story["story_id"],
            "drift_paths": drift,
            "workspace_sha256": current["sha256"],
        },
    )


def resume_command(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).expanduser().resolve()
    state_dir = resolved_state_dir(args.state_dir)
    with state_lock(state_dir):
        state, errors, current = load_and_verify(
            root, state_dir, check_workspace=True, recover=True
        )
        if errors:
            return stable_result(False, "blocked", issues=errors)
        assert state is not None and current is not None
        return resume_evaluation(state, state_dir, current, root)


def inactive_issue(state: dict[str, Any], action: str) -> list[str]:
    if state.get("status") == "active":
        return []
    return [
        f"cannot {action} after goal status is {state.get('status')}"
    ]


def checkpoint_command(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).expanduser().resolve()
    state_dir = resolved_state_dir(args.state_dir)
    with state_lock(state_dir):
        state, errors, current = load_and_verify(
            root, state_dir, check_workspace=True, recover=True
        )
        if errors:
            return stable_result(False, "blocked", issues=errors)
        assert state is not None and current is not None
        lifecycle_issues = inactive_issue(state, "checkpoint")
        if lifecycle_issues:
            return stable_result(
                False, "blocked", issues=lifecycle_issues
            )
        paid_data_issues = paid_data_prose_issues(
            [args.summary],
            "checkpoint paid-data policy",
        )
        if paid_data_issues:
            return stable_result(
                False, "blocked", issues=paid_data_issues
            )
        evaluation = resume_evaluation(state, state_dir, current, root)
        if evaluation["status"] not in {"pass", "review_required"}:
            return evaluation
        event = make_event(
            state,
            "checkpoint",
            summary=args.summary,
            payload={"kind": args.kind},
            workspace=current,
        )
        state = persist_event(
            state_dir, state, event, workspace=current
        )
    return stable_result(
        True,
        "pass",
        result={
            "goal_id": state["goal_id"],
            "checkpoint": state["last_checkpoint"],
        },
    )


def envelope_hash(value: dict[str, Any]) -> str:
    unsigned = dict(value)
    unsigned.pop("$schema", None)
    unsigned.pop("envelope_sha256", None)
    return digest(unsigned)


def receipt_hash(value: dict[str, Any]) -> str:
    unsigned = dict(value)
    unsigned.pop("$schema", None)
    unsigned.pop("receipt_sha256", None)
    return digest(unsigned)


def valid_scope_patterns(values: Any) -> bool:
    return (
        isinstance(values, list)
        and all(
            isinstance(item, str)
            and portable_relative(item)
            and not scope_pattern_selects_git_metadata(item)
            for item in values
        )
        and len(values) == len(set(values))
    )


def write_story_contract_issues(
    root: Path,
    state: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    binding = state.get("manifest")
    if not isinstance(binding, dict):
        return [
            "write story requires a bound schema_version 2 manifest"
        ]
    path_value = binding.get("path_realpath")
    if not isinstance(path_value, str):
        return ["write story manifest binding is invalid"]
    try:
        manifest = strict_json(Path(path_value))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"write story manifest is invalid: {exc}"]
    if manifest.get("schema_version") != 2:
        issues.append("write story requires manifest schema_version 2")
    else:
        from validate_project_v2 import validate as validate_project_v2

        manifest_errors, _warnings = validate_project_v2(root, manifest)
        issues.extend(
            "write story project contract: " + message
            for message in manifest_errors
        )
    project = manifest.get("project")
    if (
        not isinstance(project, dict)
        or project.get("id") != state.get("project_id")
    ):
        issues.append("write story manifest project.id mismatch")
    if "repo-mutation" not in state.get("required_capabilities", []):
        issues.append(
            "write story requires effective repo-mutation capability"
        )
    return issues


def issue_story_command(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).expanduser().resolve()
    state_dir = resolved_state_dir(args.state_dir)
    envelope_path = Path(args.envelope).expanduser().resolve()
    try:
        envelope = strict_json(envelope_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return stable_result(
            False, "blocked", issues=[f"invalid envelope: {exc}"]
        )
    with state_lock(state_dir):
        state, errors, current = load_and_verify(
            root, state_dir, check_workspace=True, recover=True
        )
        if errors:
            return stable_result(False, "blocked", issues=errors)
        assert state is not None and current is not None
        issues: list[str] = inactive_issue(state, "issue a story")
        evaluation = resume_evaluation(state, state_dir, current, root)
        if not evaluation["ok"]:
            return evaluation
        issues.extend(story_envelope_input_issues(envelope))
        if envelope.get("document_type") != "quant_story_envelope":
            issues.append("envelope document_type is invalid")
        if envelope.get("schema_version") != 1:
            issues.append("envelope schema_version must equal 1")
        if envelope.get("goal_id") != state["goal_id"]:
            issues.append("envelope goal_id mismatch")
        if envelope.get("project_binding_sha256") != state[
            "project_binding"
        ]["identity_sha256"]:
            issues.append("envelope project binding mismatch")
        if envelope.get("envelope_sha256") != envelope_hash(envelope):
            issues.append("envelope SHA-256 is invalid")
        story_id = envelope.get("story_id")
        if not portable_id(story_id):
            issues.append("envelope story_id must be a portable ID")
        if envelope.get("mode") not in {
            "advisory",
            "read_only",
            "write",
        }:
            issues.append("envelope mode is invalid")
        if not valid_scope_patterns(envelope.get("write_scope")):
            issues.append("envelope write_scope is invalid")
        if not valid_scope_patterns(envelope.get("protected_scope")):
            issues.append("envelope protected_scope is invalid")
        else:
            missing_protected = sorted(
                set(manifest_protected_patterns(state))
                - set(envelope.get("protected_scope", []))
            )
            if missing_protected:
                issues.append(
                    "envelope omits manifest protected scope: "
                    + ", ".join(missing_protected)
                )
        if envelope.get("mode") == "write" and not envelope.get(
            "write_scope"
        ):
            issues.append("write story requires a non-empty write_scope")
        if envelope.get("mode") == "write":
            issues.extend(write_story_contract_issues(root, state))
            if valid_scope_patterns(
                envelope.get("write_scope")
            ) and valid_scope_patterns(envelope.get("protected_scope")):
                scopes = [
                    *envelope.get("write_scope", []),
                    *envelope.get("protected_scope", []),
                ]
                issues.extend(
                    project_scope_symlink_issues(
                        root, state_dir, scopes
                    )
                )
                issues.extend(
                    project_scope_state_issues(
                        root, state_dir, scopes
                    )
                )
        if envelope.get("mode") != "write" and envelope.get("write_scope"):
            issues.append("non-write story must have an empty write_scope")
        if envelope.get("external_effects") != "none":
            issues.append("story envelopes cannot grant external effects")
        if envelope.get("cost_class") != "no_billable_action":
            issues.append("story envelopes cannot grant billable action")
        if envelope.get("baseline_workspace_sha256") != current["sha256"]:
            issues.append("envelope baseline workspace mismatch")
        issues.extend(
            story_acceptance_issues(
                envelope.get("acceptance"),
                state.get("acceptance"),
            )
        )
        events, _ = read_ledger(state_dir / LEDGER_NAME)
        reduced = reduce_events(events)
        if any(event.get("story_id") == story_id for event in events):
            issues.append("story_id cannot be reused")
        depends = envelope.get("depends_on")
        if not isinstance(depends, list):
            issues.append("envelope depends_on must be an array")
        else:
            valid_dependencies = all(
                portable_id(value) for value in depends
            )
            if not valid_dependencies:
                issues.append(
                    "envelope depends_on values must be portable IDs"
                )
            elif len(depends) != len(set(depends)):
                issues.append("envelope depends_on must be unique")
            if valid_dependencies:
                unmet = sorted(
                    set(depends) - set(reduced["accepted_story_ids"])
                )
                if unmet:
                    issues.append(
                        "story dependencies are not accepted: "
                        + ", ".join(unmet)
                    )
        if story_id in state["open_story_ids"]:
            issues.append("story is already open")
        if envelope.get("mode") == "write":
            for open_id in state["open_story_ids"]:
                try:
                    if load_story(state_dir, open_id).get("mode") == "write":
                        issues.append(
                            "only one write story may be open at a time"
                        )
                except (OSError, ValueError, json.JSONDecodeError):
                    issues.append("existing story envelope is invalid")
        if issues:
            return stable_result(False, "blocked", issues=issues)
        artifact_parent(state_dir, "stories", create=True)
        atomic_json(
            story_artifact_path(state_dir, "stories", story_id),
            envelope,
        )
        atomic_json(
            story_artifact_path(
                state_dir, "stories", story_id, ".baseline.json"
            ),
            current,
        )
        event = make_event(
            state,
            "story_opened",
            summary=f"Story opened: {story_id}",
            payload={
                "mode": envelope["mode"],
                "envelope_sha256": envelope["envelope_sha256"],
                "baseline_sha256": digest(current),
                "runtime_capabilities": (
                    ["multi-agent-write"]
                    if envelope["mode"] == "write"
                    else []
                ),
            },
            story_id=story_id,
            workspace=current,
        )
        state = persist_event(
            state_dir, state, event, workspace=current
        )
    return stable_result(
        True,
        "pass",
        result={"story_id": story_id, "open_story_ids": state["open_story_ids"]},
    )


def validate_receipt_against_story(
    receipt: dict[str, Any],
    envelope: dict[str, Any],
    baseline: dict[str, Any],
    current: dict[str, Any],
    root: Path | None = None,
    state_dir: Path | None = None,
) -> list[str]:
    issues: list[str] = story_receipt_input_issues(receipt)
    if (
        baseline.get("kind") != current.get("kind")
        or baseline.get("branch") != current.get("branch")
    ):
        issues.append("story workspace branch or project kind changed")
    if receipt.get("document_type") != "quant_story_receipt":
        issues.append("receipt document_type is invalid")
    if receipt.get("schema_version") != 1:
        issues.append("receipt schema_version must equal 1")
    if receipt.get("goal_id") != envelope.get("goal_id"):
        issues.append("receipt goal_id mismatch")
    if receipt.get("story_id") != envelope.get("story_id"):
        issues.append("receipt story_id mismatch")
    if receipt.get("envelope_sha256") != envelope.get("envelope_sha256"):
        issues.append("receipt envelope_sha256 mismatch")
    if receipt.get("receipt_sha256") != receipt_hash(receipt):
        issues.append("receipt SHA-256 is invalid")
    if receipt.get("status") != "ready_for_review":
        issues.append("worker receipt status must be ready_for_review")
    evidence = receipt.get("evidence")
    evidence_ids: list[str] = []
    if not isinstance(evidence, list) or not evidence:
        issues.append("receipt evidence must be non-empty")
    else:
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(
                item.get("id"), str
            ):
                issues.append("receipt evidence items require IDs")
                continue
            evidence_ids.append(item["id"])
            if item.get("status") != "passed":
                issues.append("receipt evidence status must be passed")
        if len(evidence_ids) != len(set(evidence_ids)):
            issues.append("receipt evidence IDs must be unique")
    acceptance_ids = {
        item["id"]
        for item in envelope.get("acceptance", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    claims = receipt.get("claims")
    claim_ids: list[str] = []
    if not isinstance(claims, list):
        issues.append("receipt claims must be an array")
    else:
        for claim in claims:
            if not isinstance(claim, dict):
                issues.append("receipt claim must be an object")
                continue
            claim_id = claim.get("acceptance_id")
            claim_ids.append(claim_id)
            if not isinstance(claim_id, str) or not claim_id:
                issues.append("receipt claim acceptance_id is invalid")
            if claim.get("status") != "passed":
                issues.append("receipt claim status must be passed")
            references = claim.get("evidence_ids")
            if not isinstance(references, list) or not references:
                issues.append("receipt claim requires evidence_ids")
            elif not all(
                isinstance(reference, str) and reference
                for reference in references
            ):
                issues.append("receipt claim evidence_ids are invalid")
            elif not set(references).issubset(set(evidence_ids)):
                issues.append("receipt claim references unknown evidence")
        valid_claim_ids = all(
            isinstance(value, str) and value for value in claim_ids
        )
        if (
            not valid_claim_ids
            or set(claim_ids) != acceptance_ids
            or len(claim_ids) != len(acceptance_ids)
        ):
            issues.append(
                "receipt claims must cover each acceptance ID exactly once"
            )
    drift = changed_since(baseline, current, root)
    if receipt.get("changed_paths") != drift:
        issues.append("receipt changed_paths does not match workspace")
    mode = envelope.get("mode")
    if mode == "advisory":
        if receipt.get("workspace_sha256") is not None or drift:
            issues.append("advisory receipt cannot claim workspace changes")
    else:
        if receipt.get("workspace_sha256") != current["sha256"]:
            issues.append("receipt workspace_sha256 mismatch")
    if mode == "read_only" and drift:
        issues.append("read-only story changed the workspace")
    if mode == "write":
        scopes = [
            *envelope.get("write_scope", []),
            *envelope.get("protected_scope", []),
        ]
        if root is not None and state_dir is not None:
            issues.extend(
                project_scope_symlink_issues(root, state_dir, scopes)
            )
            issues.extend(
                project_scope_state_issues(root, state_dir, scopes)
            )
        else:
            issues.extend(snapshot_scope_symlink_issues(current, scopes))
        out_of_scope = [
            path
            for path in drift
            if not matches(path, envelope.get("write_scope", []))
        ]
        protected = [
            path
            for path in drift
            if matches_protected(
                path,
                envelope.get("protected_scope", []),
            )
        ]
        if out_of_scope:
            issues.append(
                "receipt changes outside write scope: "
                + ", ".join(out_of_scope)
            )
        if protected:
            issues.append(
                "receipt changes protected scope: " + ", ".join(protected)
            )
    return issues


def accept_story_command(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).expanduser().resolve()
    state_dir = resolved_state_dir(args.state_dir)
    receipt_path = Path(args.receipt).expanduser().resolve()
    try:
        receipt = strict_json(receipt_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return stable_result(
            False, "blocked", issues=[f"invalid receipt: {exc}"]
        )
    with state_lock(state_dir):
        state, errors, current = load_and_verify(
            root, state_dir, check_workspace=True, recover=True
        )
        if errors:
            return stable_result(False, "blocked", issues=errors)
        assert state is not None and current is not None
        lifecycle_issues = inactive_issue(state, "accept a story")
        if lifecycle_issues:
            return stable_result(
                False, "blocked", issues=lifecycle_issues
            )
        story_id = receipt.get("story_id")
        if story_id not in state.get("open_story_ids", []):
            return stable_result(
                False, "blocked", issues=["receipt story is not open"]
            )
        try:
            envelope = load_story(state_dir, story_id)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return stable_result(
                False,
                "blocked",
                issues=[f"invalid story envelope: {exc}"],
            )
        try:
            baseline = load_story_baseline(state_dir, story_id)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return stable_result(
                False,
                "blocked",
                issues=[f"invalid story baseline: {exc}"],
            )
        issues = validate_receipt_against_story(
            receipt,
            envelope,
            baseline,
            current,
            root,
            state_dir,
        )
        if issues:
            return stable_result(False, "blocked", issues=issues)
        artifact_parent(state_dir, "receipts", create=True)
        atomic_json(
            story_artifact_path(state_dir, "receipts", story_id),
            receipt,
        )
        event = make_event(
            state,
            "story_accepted",
            summary=f"Story accepted: {story_id}",
            payload={
                "receipt_sha256": receipt["receipt_sha256"],
                "envelope_sha256": envelope["envelope_sha256"],
                "baseline_sha256": digest(baseline),
            },
            story_id=story_id,
            workspace=current,
        )
        state = persist_event(
            state_dir, state, event, workspace=current
        )
    return stable_result(
        True,
        "pass",
        result={
            "story_id": story_id,
            "open_story_ids": state["open_story_ids"],
            "checkpoint": state["last_checkpoint"],
        },
    )

def complete_command(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).expanduser().resolve()
    state_dir = resolved_state_dir(args.state_dir)
    receipt_path = Path(args.receipt).expanduser().resolve()
    try:
        receipt = strict_json(receipt_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return stable_result(
            False, "blocked", issues=[f"invalid final receipt: {exc}"]
        )
    with state_lock(state_dir):
        state, errors, current = load_and_verify(
            root, state_dir, check_workspace=True, recover=True
        )
        if errors:
            return stable_result(False, "blocked", issues=errors)
        assert state is not None and current is not None
        lifecycle_issues = inactive_issue(state, "complete the goal")
        if lifecycle_issues:
            return stable_result(
                False, "blocked", issues=lifecycle_issues
            )
        evaluation = resume_evaluation(state, state_dir, current, root)
        if not evaluation["ok"]:
            return evaluation
        issues: list[str] = []
        if state["open_story_ids"]:
            issues.append("goal cannot complete with open stories")
        if receipt.get("schema_version") != 3:
            issues.append("final receipt must use schema_version 3")
        if receipt.get("project_id") != state["project_id"]:
            issues.append("final receipt project_id mismatch")
        if receipt.get("objective") != state["objective"]:
            issues.append("final receipt objective mismatch")
        binding = receipt.get("goal_binding")
        if not isinstance(binding, dict):
            issues.append("final receipt requires goal_binding")
        else:
            if binding.get("goal_id") != state["goal_id"]:
                issues.append("final receipt goal_id mismatch")
            if binding.get("objective_sha256") != state[
                "objective_sha256"
            ]:
                issues.append("final receipt objective hash mismatch")
            if binding.get("ledger_tail_sha256") != state["ledger"][
                "tail_sha256"
            ]:
                issues.append("final receipt ledger tail mismatch")
            acceptance_ids = {
                item["id"] for item in state["acceptance"]
            }
            bound_acceptance = binding.get("acceptance_ids")
            if (
                not isinstance(bound_acceptance, list)
                or not all(
                    isinstance(value, str) and value
                    for value in bound_acceptance
                )
                or len(bound_acceptance) != len(set(bound_acceptance))
                or set(bound_acceptance) != acceptance_ids
            ):
                issues.append(
                    "final receipt does not bind every goal acceptance"
                )
        manifest_binding = state.get("manifest")
        manifest_path: Path | None = None
        manifest_valid = True
        if not isinstance(manifest_binding, dict):
            unbound_capabilities = [
                *state.get("required_capabilities", []),
                *state.get("runtime_capabilities", []),
            ]
            if state.get("runtime_facts", {}).get(
                "multi_agent_write_used"
            ):
                unbound_capabilities.append("multi-agent-write-used")
            if unbound_capabilities:
                manifest_valid = False
                issues.append(
                    "manifest-less research completion cannot prove "
                    "project/runtime capabilities: "
                    + ", ".join(unbound_capabilities)
                )
        else:
            manifest_path = Path(
                manifest_binding.get("path_realpath", "")
            )
            try:
                manifest = strict_json(manifest_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                issues.append(f"bound manifest is invalid: {exc}")
                manifest = {}
            if manifest.get("schema_version") != 2:
                manifest_valid = False
                issues.append(
                    "goal completion requires a schema_version 2 manifest"
                )
        if manifest_valid:
            from validate_evidence_v3 import validate_receipt

            validation_args = argparse.Namespace(
                project_root=str(root),
                manifest=(
                    str(manifest_path)
                    if manifest_path is not None
                    else None
                ),
                goal_state=str(state_dir / STATE_NAME),
                require_capability=state.get(
                    "required_capabilities", []
                ),
                require_automation=False,
                require_release=False,
                minimum_assurance=state.get("assurance"),
                input_binding_capture=args.input_binding_capture,
            )
            issues.extend(
                "final evidence: " + message
                for message in validate_receipt(
                    receipt, validation_args
                )
            )
        if (
            "multi-agent-write" in state.get("runtime_capabilities", [])
            and not state.get("runtime_facts", {}).get(
                "multi_agent_write_used"
            )
        ):
            issues.append(
                "required multi-agent write handoff is not ledger-proven"
            )
        if issues:
            return stable_result(False, "blocked", issues=issues)
        receipts = artifact_parent(
            state_dir, "receipts", create=True
        )
        final_path = receipts / "final.json"
        if final_path.is_symlink():
            return stable_result(
                False,
                "blocked",
                issues=[
                    "final receipt artifact must not be a symbolic link"
                ],
            )
        atomic_json(final_path, receipt)
        final_receipt_sha256 = digest(receipt)
        pre_completion_tail = state["ledger"]["tail_sha256"]
        event = make_event(
            state,
            "status_changed",
            summary="Goal completed",
            payload={
                "status": "complete",
                "receipt_sha256": final_receipt_sha256,
                "final_receipt_sha256": final_receipt_sha256,
                "pre_completion_ledger_tail_sha256": (
                    pre_completion_tail
                ),
                "goal_intent_sha256": state["intent_sha256"],
            },
            workspace=current,
        )
        state = persist_event(
            state_dir, state, event, workspace=current
        )
    return stable_result(
        True,
        "pass",
        result={
            "goal_id": state["goal_id"],
            "status": state["status"],
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="goal_runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--root", required=True)
    init.add_argument("--state-dir", required=True)
    init.add_argument("--goal-id", required=True)
    init.add_argument("--project-id", required=True)
    init.add_argument("--objective", required=True)
    init.add_argument("--acceptance", action="append", default=[])
    init.add_argument("--require-outcome", action="append", default=[])
    init.add_argument("--require-capability", action="append", default=[])
    init.add_argument("--profile", action="append", default=[])
    init.add_argument(
        "--assurance",
        choices=("light", "standard", "strict", "release"),
        default="standard",
    )
    init.add_argument("--plan")
    init.add_argument("--manifest")

    for name in ("verify", "resume"):
        command = subparsers.add_parser(name)
        command.add_argument("--root", required=True)
        command.add_argument("--state-dir", required=True)

    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint.add_argument("--root", required=True)
    checkpoint.add_argument("--state-dir", required=True)
    checkpoint.add_argument("--kind", default="recovery-review")
    checkpoint.add_argument("--summary", required=True)

    issue = subparsers.add_parser("story-issue")
    issue.add_argument("--root", required=True)
    issue.add_argument("--state-dir", required=True)
    issue.add_argument("--envelope", required=True)

    accept = subparsers.add_parser("story-accept")
    accept.add_argument("--root", required=True)
    accept.add_argument("--state-dir", required=True)
    accept.add_argument("--receipt", required=True)

    complete = subparsers.add_parser("complete")
    complete.add_argument("--root", required=True)
    complete.add_argument("--state-dir", required=True)
    complete.add_argument("--receipt", required=True)
    complete.add_argument("--input-binding-capture")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        commands = {
            "init": init_command,
            "verify": verify_command,
            "resume": resume_command,
            "checkpoint": checkpoint_command,
            "story-issue": issue_story_command,
            "story-accept": accept_story_command,
            "complete": complete_command,
        }
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
