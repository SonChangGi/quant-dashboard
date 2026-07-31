#!/usr/bin/env python3
"""Read-only context, doctor, and onboarding commands for the skill suite."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from capability_model import CapabilityError, resolve
from project_inventory import run_git, scan_visible_files


SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPT_DIR.parent
MANIFEST_RELATIVE = Path(".codex/quant-project.json")
LEGACY_V1_REFERENCES = (
    "references/operating-principles.md",
    "references/cost-and-authority.md",
    "references/data-automation.md",
    "references/research-and-planning.md",
    "references/goal-and-subagents.md",
    "references/developer-runbook.md",
)


def strict_object(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON value is prohibited: {value}")

    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def response(
    *,
    ok: bool,
    status: str,
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


def parse_adapters(values: list[str]) -> dict[str, Any]:
    adapters: dict[str, Any] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("adapter must use role=id")
        role, adapter_id = (item.strip() for item in value.split("=", 1))
        if not role or not adapter_id:
            raise ValueError("adapter must use non-empty role=id")
        previous = adapters.get(role)
        if previous is None:
            adapters[role] = adapter_id
        elif isinstance(previous, list):
            if adapter_id not in previous:
                previous.append(adapter_id)
        elif previous != adapter_id:
            adapters[role] = [previous, adapter_id]
    return adapters


def context_command(args: argparse.Namespace) -> dict[str, Any]:
    manifest: dict[str, Any] = {}
    manifest_path: Path | None = None
    if args.manifest:
        manifest_path = Path(args.manifest).expanduser().resolve()
        if not manifest_path.is_file():
            return response(
                ok=False,
                status="blocked",
                issues=[f"manifest does not exist: {manifest_path}"],
            )
        try:
            manifest = strict_object(manifest_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return response(
                ok=False,
                status="blocked",
                issues=[f"invalid manifest: {exc}"],
            )
    schema_version = manifest.get("schema_version") if manifest else None
    if manifest_path is not None and (
        type(schema_version) is not int or schema_version not in (1, 2)
    ):
        return response(
            ok=False,
            status="blocked",
            issues=[
                "manifest schema_version must equal 1 or 2 for context routing"
            ],
        )
    try:
        if schema_version == 1:
            resolved = resolve(
                {},
                capabilities=args.capability,
                profiles=args.profile,
                assurance=args.assurance or "strict",
                delivery=args.delivery,
                adapters=parse_adapters(args.adapter),
            )
            resolved["required_references"] = list(
                dict.fromkeys(
                    [
                        *resolved["required_references"],
                        *LEGACY_V1_REFERENCES,
                    ]
                )
            )
            resolved["compatibility"] = {
                "mode": "manifest-v1-strict",
                "manifest_schema_version": 1,
                "evidence_receipt_schema_version": 2,
                "note": (
                    "Legacy references preserve the existing strict contract; "
                    "CLI-selected v2 modules are supplemental."
                ),
            }
        else:
            resolved = resolve(
                manifest,
                capabilities=args.capability,
                profiles=args.profile,
                assurance=args.assurance,
                delivery=args.delivery,
                adapters=parse_adapters(args.adapter),
            )
            resolved["compatibility"] = {
                "mode": (
                    "manifest-v2-capability"
                    if schema_version == 2
                    else "task-context"
                ),
                "manifest_schema_version": schema_version,
                "evidence_receipt_schema_version": (
                    3 if schema_version == 2 else None
                ),
            }
    except (CapabilityError, ValueError) as exc:
        return response(
            ok=False,
            status="blocked",
            issues=[str(exc)],
        )
    resolved["manifest"] = (
        str(manifest_path) if manifest_path is not None else None
    )
    resolved["shared_root"] = str(SHARED_DIR)
    resolved["reference_paths"] = [
        str(SHARED_DIR / relative)
        for relative in resolved["required_references"]
    ]
    missing = [
        path
        for path in resolved["reference_paths"]
        if not Path(path).is_file()
    ]
    if missing:
        return response(
            ok=False,
            status="blocked",
            issues=[f"required reference is missing: {path}" for path in missing],
            result=resolved,
        )
    return response(ok=True, status="pass", result=resolved)


def run_validator(root: Path, manifest: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "validate_project.py"),
        "--root",
        str(root),
        "--manifest",
        str(manifest),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "checked": True,
            "valid": False,
            "errors": [
                completed.stderr.strip() or "validator returned invalid JSON"
            ],
        }
    return {
        "checked": True,
        "valid": completed.returncode == 0 and payload.get("valid") is True,
        "schema_version": payload.get("schema_version"),
        "errors": payload.get("errors", []),
        "warnings": payload.get("warnings", []),
        "resolved": payload.get("resolved"),
    }


def sanitize_origin(value: str) -> str:
    if "://" not in value:
        return value.split("?", 1)[0].split("#", 1)[0]
    from urllib.parse import urlsplit, urlunsplit

    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def git_summary(root: Path) -> dict[str, Any]:
    inside = run_git(root, "rev-parse", "--is-inside-work-tree")
    if not inside.get("ok") or inside.get("value") != "true":
        return {"kind": "directory", "is_git": False}
    origin_result = run_git(root, "remote", "get-url", "origin")
    origin = (
        sanitize_origin(origin_result.get("value", ""))
        if origin_result.get("ok")
        else ""
    )
    status = run_git(root, "status", "--short", "--untracked-files=all")
    changed = (
        [line for line in status.get("value", "").splitlines() if line]
        if status.get("ok")
        else []
    )
    return {
        "kind": "git",
        "is_git": True,
        "branch": run_git(root, "branch", "--show-current").get("value", ""),
        "head": run_git(root, "rev-parse", "HEAD").get("value", ""),
        "git_common_dir": run_git(
            root, "rev-parse", "--path-format=absolute", "--git-common-dir"
        ).get("value", ""),
        "origin": origin,
        "dirty": bool(changed),
        "changed_entries": changed,
    }


def inspect_goal_state_read_only(
    root: Path,
    state_dir: Path,
) -> dict[str, Any]:
    try:
        from goal_runtime import load_and_verify
    except (ImportError, OSError) as exc:
        return response(
            ok=False,
            status="blocked",
            issues=[f"goal runtime is unavailable: {exc}"],
        )
    try:
        state, errors, current = load_and_verify(
            root,
            state_dir,
            check_workspace=True,
            recover=False,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return response(
            ok=False,
            status="blocked",
            issues=[f"goal state inspection failed: {exc}"],
        )
    if errors:
        return response(ok=False, status="blocked", issues=errors)
    assert state is not None and current is not None
    return response(
        ok=True,
        status="pass",
        result={
            "goal_id": state["goal_id"],
            "status": state["status"],
            "open_story_ids": state["open_story_ids"],
            "ledger": state["ledger"],
            "current_workspace_sha256": current["sha256"],
            "writes_performed": False,
        },
    )


def doctor_command(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        return response(
            ok=False,
            status="blocked",
            issues=[f"project root does not exist: {root}"],
        )
    issues: list[str] = []
    manifest = root / MANIFEST_RELATIVE
    if manifest.is_symlink():
        manifest_state = {
            "checked": False,
            "valid": False,
            "present": True,
            "note": "Manifest symlinks are not followed.",
        }
        issues.append("manifest: symlink is not followed")
    elif manifest.is_file():
        manifest_state = run_validator(root, manifest)
        if not manifest_state["valid"]:
            issues.extend(
                f"manifest: {message}"
                for message in manifest_state.get("errors", [])
            )
    else:
        manifest_state = {
            "checked": False,
            "valid": None,
            "present": False,
            "note": "A manifest is optional; use onboard --dry-run for candidates.",
        }
    suite_files = [
        SCRIPT_DIR / "capability_model.py",
        SCRIPT_DIR / "validate_project.py",
        SHARED_DIR / "core" / "invariants.md",
        SHARED_DIR / "core" / "authority.md",
        SHARED_DIR / "core" / "evidence-semantics.md",
        SHARED_DIR / "core" / "context-routing.md",
    ]
    missing_suite_files = [
        str(path) for path in suite_files if not path.is_file()
    ]
    issues.extend(
        f"suite resource missing: {path}" for path in missing_suite_files
    )
    goal_state: dict[str, Any] | None = None
    if args.state_dir:
        state_dir = Path(args.state_dir).expanduser().resolve()
        script = SCRIPT_DIR / "goal_runtime.py"
        if not script.is_file():
            issues.append("goal runtime is unavailable")
        else:
            goal_state = inspect_goal_state_read_only(root, state_dir)
            if not goal_state.get("ok"):
                issues.extend(
                    f"goal state: {message}"
                    for message in goal_state.get("issues", [])
                )
    return response(
        ok=not issues,
        status="pass" if not issues else "blocked",
        issues=issues,
        result={
            "root": str(root),
            "git": git_summary(root),
            "manifest": manifest_state,
            "suite": {
                "shared_root": str(SHARED_DIR),
                "missing_files": missing_suite_files,
            },
            "goal_state": goal_state,
            "writes_performed": False,
        },
    )


def text_hint(path: Path, patterns: dict[str, str]) -> list[str]:
    if path.is_symlink():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return []
    return [label for label, token in patterns.items() if token in text]


def add_candidate(
    candidates: dict[str, dict[str, Any]],
    capability: str,
    evidence: str,
    confidence: str,
) -> None:
    rank = {"low": 0, "medium": 1, "high": 2}
    current = candidates.setdefault(
        capability,
        {"id": capability, "confidence": confidence, "evidence": []},
    )
    if rank[confidence] > rank[current["confidence"]]:
        current["confidence"] = confidence
    if evidence not in current["evidence"]:
        current["evidence"].append(evidence)


def onboard_command(args: argparse.Namespace) -> dict[str, Any]:
    if not args.dry_run:
        return response(
            ok=False,
            status="blocked",
            issues=[
                "onboard is proposal-only and requires the literal --dry-run"
            ],
        )
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        return response(
            ok=False,
            status="blocked",
            issues=[f"project root does not exist: {root}"],
        )
    files, scan = scan_visible_files(root, max_depth=args.max_depth)
    names = {path.as_posix() for path in files}
    candidates: dict[str, dict[str, Any]] = {}
    adapters: set[str] = set()
    questions: list[str] = []

    git_state = git_summary(root)
    if git_state.get("is_git"):
        adapters.add(
            "github"
            if "github.com" in git_state.get("origin", "")
            else "x-scm"
        )

    package_path = root / "package.json"
    if "package.json" in names:
        hits = text_hint(
            package_path,
            {
                "react": '"react"',
                "typescript": "typescript",
                "vite": '"vite"',
            },
        )
        if hits:
            add_candidate(
                candidates,
                "web-ui",
                "package.json:" + ",".join(hits),
                "high",
            )
    if any(
        name in names
        for name in ("index.html", "src/index.html", "public/index.html")
    ):
        add_candidate(candidates, "web-ui", "HTML entrypoint", "high")
    if any(path.suffix == ".py" for path in files):
        add_candidate(
            candidates,
            "analysis",
            "Python source present; confirm whether it is authoritative analysis",
            "low",
        )
    chart_tokens = ("chart", "plot", "svg", "recharts", "echarts", "d3")
    chart_files = [
        path
        for path in files
        if path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".html"}
        and any(token in path.name.lower() for token in chart_tokens)
    ]
    if chart_files:
        add_candidate(
            candidates,
            "interactive-chart",
            f"chart-like source:{chart_files[0].as_posix()}",
            "medium",
        )
        questions.append(
            "Does the chart support pointer, keyboard, selection, or range interaction?"
        )

    workflow_files = [
        path
        for path in files
        if len(path.parts) >= 3
        and path.parts[:2] == (".github", "workflows")
        and path.suffix in {".yml", ".yaml"}
    ]
    for workflow in workflow_files:
        workflow_path = root / workflow
        if workflow_path.is_symlink():
            continue
        try:
            text = workflow_path.read_text(
                encoding="utf-8", errors="replace"
            ).lower()
        except OSError:
            continue
        adapters.add("github-actions")
        if "schedule:" in text or "cron:" in text:
            add_candidate(
                candidates,
                "scheduled-automation",
                f"{workflow.as_posix()}:schedule",
                "high",
            )
        if "deploy-pages" in text or "github-pages" in text:
            add_candidate(
                candidates,
                "publication",
                f"{workflow.as_posix()}:Pages deployment",
                "medium",
            )
            add_candidate(
                candidates,
                "public-web",
                f"{workflow.as_posix()}:Pages deployment",
                "medium",
            )
            adapters.add("github-pages")

    if "vercel.json" in names:
        adapters.add("vercel")
        add_candidate(candidates, "public-web", "vercel.json", "medium")
    if any(path.parts and path.parts[0] == "supabase" for path in files):
        adapters.add("supabase")
        add_candidate(candidates, "backend", "supabase project files", "medium")
    fastapi_files = [
        path
        for path in files
        if path.suffix == ".py"
        and "fastapi" in text_hint(root / path, {"fastapi": "fastapi"})
    ]
    if fastapi_files:
        adapters.add("fastapi")
        add_candidate(
            candidates,
            "backend",
            f"FastAPI import:{fastapi_files[0].as_posix()}",
            "high",
        )

    if "web-ui" in candidates and "analysis" in candidates:
        questions.append(
            "Which visible controls are display-only, stored-result selectors, "
            "analysis inputs, or operations?"
        )
    if "analysis" in candidates:
        questions.append(
            "Which entrypoints and result fields are authoritative and protected?"
        )
    if "external-data" not in candidates and any(
        token in name.lower()
        for name in names
        for token in ("collect", "fetch", "download", "provider")
    ):
        add_candidate(
            candidates,
            "external-data",
            "collector-like filename; inspect provider contract",
            "low",
        )
        questions.append(
            "Which external sources are required, optional, rights-approved, and fresh?"
        )
    if not scan["complete"]:
        questions.append(
            "The bounded scan is incomplete. Inspect the reported skipped or "
            "deeper paths before accepting capability candidates."
        )

    candidate_values = sorted(candidates.values(), key=lambda item: item["id"])
    candidate_ids = {item["id"] for item in candidate_values}
    # Keep onboarding advisory and consistent with the shared capability model.
    # It must not silently raise every data or automation project to the
    # dashboard-specific strict profile.
    resolved = resolve(
        {},
        capabilities=sorted(candidate_ids),
        assurance="light",
    )
    return response(
        ok=True,
        status="pass",
        result={
            "mode": "dry-run",
            "writes_performed": False,
            "network_used": False,
            "root": str(root),
            "project_kind": git_state["kind"],
            "scan": scan,
            "candidate_coverage": (
                "complete" if scan["complete"] else "partial"
            ),
            "capability_candidates": candidate_values,
            "adapter_hints": sorted(adapters),
            "recommended_assurance": resolved["assurance"],
            "recommended_delivery": resolved["delivery"],
            "questions": list(dict.fromkeys(questions)),
            "manifest_present": (
                not (root / MANIFEST_RELATIVE).is_symlink()
                and (root / MANIFEST_RELATIVE).is_file()
            ),
            "note": (
                "Candidates are evidence-backed suggestions, not activated "
                "capabilities or authority. Repository presence alone does not "
                "activate the task-scoped repo-mutation capability."
            ),
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quantctl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    context = subparsers.add_parser("context")
    context.add_argument("--manifest")
    context.add_argument("--capability", action="append", default=[])
    context.add_argument("--profile", action="append", default=[])
    context.add_argument("--adapter", action="append", default=[])
    context.add_argument(
        "--assurance",
        choices=("light", "standard", "strict", "release"),
    )
    context.add_argument(
        "--delivery",
        choices=("local", "release"),
    )

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--root", required=True)
    doctor.add_argument("--state-dir")

    onboard = subparsers.add_parser("onboard")
    onboard.add_argument("--root", required=True)
    onboard.add_argument("--dry-run", action="store_true")
    onboard.add_argument("--max-depth", type=int, default=6)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "context":
            value = context_command(args)
        elif args.command == "doctor":
            value = doctor_command(args)
        else:
            value = onboard_command(args)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        value = response(ok=False, status="blocked", issues=[str(exc)])
    return emit(value)


if __name__ == "__main__":
    raise SystemExit(main())
