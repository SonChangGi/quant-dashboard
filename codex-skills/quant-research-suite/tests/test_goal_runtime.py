from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "shared" / "scripts"
SCRIPT = SCRIPTS / "goal_runtime.py"
sys.path.insert(0, str(SCRIPTS))

import goal_runtime
import goal_primitives
import validate_evidence_v3


def command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def git(root: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise AssertionError(completed.stderr)


def make_repo(base: Path) -> Path:
    root = base / "project"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "app.txt").write_text("base\n", encoding="utf-8")
    (root / "README.md").write_text("base\n", encoding="utf-8")
    git(root, "init")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-m", "baseline")
    return root


def write_manifest(
    root: Path,
    *,
    project_id: str = "sample",
    capabilities: list[str] | None = None,
    protected_paths: list[str] | None = None,
    assurance: str = "standard",
) -> Path:
    path = root / "project-manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "project": {
                    "id": project_id,
                    "purpose": "Test the durable goal runtime.",
                },
                "assurance": assurance,
                "profiles": [],
                "capabilities": capabilities or [],
                "adapters": {},
                "contracts": {
                    "protected_paths": protected_paths or [],
                    "test_commands": [],
                },
                "capability_config": {},
                "authority": {
                    "cost_policy": (
                        "zero-spend-unless-user-first-requests-specific-"
                        "paid-action"
                    ),
                    "paid_action_authority": None,
                    "paid_fallback_enabled": False,
                },
                "extensions": {},
            }
        ),
        encoding="utf-8",
    )
    return path


def initialize(
    root: Path,
    state: Path,
    *,
    manifest: Path | None = None,
    goal_id: str = "goal-sample",
    project_id: str = "sample",
    capabilities: list[str] | None = None,
    profiles: list[str] | None = None,
    assurance: str = "standard",
    bind_manifest: bool | None = None,
) -> dict[str, object]:
    selected_capabilities = (
        ["repo-mutation"] if capabilities is None else capabilities
    )
    should_bind_manifest = (
        "repo-mutation" in selected_capabilities
        if bind_manifest is None
        else bind_manifest
    )
    if manifest is None and should_bind_manifest:
        manifest = write_manifest(
            root,
            project_id=project_id,
            capabilities=[
                value
                for value in selected_capabilities
                if value != "multi-agent-write"
            ],
            assurance=assurance,
        )
        git(root, "add", manifest.name)
        git(root, "commit", "-m", "bind goal test manifest")
    arguments = [
        "init",
        "--root",
        str(root),
        "--state-dir",
        str(state),
        "--goal-id",
        goal_id,
        "--project-id",
        project_id,
        "--objective",
        "Deliver the requested behavior.",
        "--acceptance",
        "a1=The behavior is verified.",
        "--assurance",
        assurance,
    ]
    for capability in selected_capabilities:
        arguments.extend(["--require-capability", capability])
    for profile in profiles or []:
        arguments.extend(["--profile", profile])
    if manifest is not None:
        arguments.extend(["--manifest", str(manifest)])
    completed = command(*arguments)
    if completed.returncode:
        raise AssertionError(completed.stdout + completed.stderr)
    return json.loads((state / "goal-state.json").read_text())


def issue_envelope(
    root: Path,
    state_dir: Path,
    envelope_path: Path,
    *,
    write_scope: list[str],
    protected_scope: list[str] | None = None,
    external_effects: str = "none",
    story_id: str = "story-change",
    mode: str = "write",
) -> dict[str, object]:
    state = json.loads((state_dir / "goal-state.json").read_text())
    snapshot = goal_runtime.workspace_snapshot(
        root,
        state_dir,
        goal_runtime.manifest_protected_patterns(state),
    )
    envelope: dict[str, object] = {
        "document_type": "quant_story_envelope",
        "schema_version": 1,
        "goal_id": state["goal_id"],
        "story_id": story_id,
        "project_binding_sha256": state["project_binding"][
            "identity_sha256"
        ],
        "objective": "Change the bounded source file.",
        "mode": mode,
        "write_scope": write_scope,
        "protected_scope": (
            ["analysis/**", "data/**"]
            if protected_scope is None
            else protected_scope
        ),
        "depends_on": [],
        "acceptance": state["acceptance"],
        "external_effects": external_effects,
        "cost_class": "no_billable_action",
        "baseline_workspace_sha256": snapshot["sha256"],
        "issued_at": "2026-07-26T00:00:00Z",
    }
    envelope["envelope_sha256"] = goal_runtime.envelope_hash(envelope)
    envelope_path.write_text(
        json.dumps(envelope), encoding="utf-8"
    )
    return envelope


def write_story_receipt(
    root: Path,
    state_dir: Path,
    path: Path,
    envelope: dict[str, object],
) -> dict[str, object]:
    state = json.loads((state_dir / "goal-state.json").read_text())
    current = goal_runtime.workspace_snapshot(
        root,
        state_dir,
        goal_runtime.manifest_protected_patterns(state),
    )
    baseline = goal_runtime.load_story_baseline(
        state_dir, str(envelope["story_id"])
    )
    receipt: dict[str, object] = {
        "document_type": "quant_story_receipt",
        "schema_version": 1,
        "goal_id": envelope["goal_id"],
        "story_id": envelope["story_id"],
        "envelope_sha256": envelope["envelope_sha256"],
        "status": "ready_for_review",
        "summary": "Bounded story evidence reviewed.",
        "changed_paths": goal_runtime.changed_since(
            baseline, current, root
        ),
        "claims": [
            {
                "acceptance_id": item["id"],
                "status": "passed",
                "evidence_ids": ["e1"],
            }
            for item in envelope["acceptance"]
        ],
        "evidence": [
            {
                "id": "e1",
                "kind": "inspection",
                "status": "passed",
                "summary": "The bounded result was inspected.",
            }
        ],
        "workspace_sha256": current["sha256"],
        "completed_at": "2026-07-26T00:01:00Z",
    }
    receipt["receipt_sha256"] = goal_runtime.receipt_hash(receipt)
    path.write_text(json.dumps(receipt), encoding="utf-8")
    return receipt


def final_research_receipt(
    root: Path,
    state_dir: Path,
) -> dict[str, object]:
    state = json.loads((state_dir / "goal-state.json").read_text())
    checked_at = "2026-07-26T00:01:00Z"
    evidence = {
        "kind": "inspection",
        "status": "verified",
        "summary": "The acceptance evidence was independently reviewed.",
        "source": "local bounded review",
        "checked_at": checked_at,
    }
    gates = {
        name: {"status": "passed", "evidence": [dict(evidence)]}
        for name in ("contract", "cost", "verification")
    }
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return {
        "schema_version": 3,
        "project_id": state["project_id"],
        "objective": state["objective"],
        "scope": {
            "capabilities": [],
            "assurance": "standard",
            "remote_actions": False,
            "analysis_control_ids": [],
        },
        "required_gates": ["contract", "cost", "verification"],
        "gates": gates,
        "cost_authority": {
            "policy": (
                "zero-spend-unless-user-first-requests-specific-paid-action"
            ),
            "classification": "no_billable_action",
            "decision": "allow",
            "paid_action_requested": False,
            "actions": [],
        },
        "context": {
            "manifest_sha256": "",
            "plan_sha256": "",
            "base_commit": head,
            "head_commit": head,
        },
        "goal_binding": {
            "goal_id": state["goal_id"],
            "objective_sha256": state["objective_sha256"],
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
            "acceptance_ids": ["a1"],
            "acceptance_claims": {
                "a1": [
                    {
                        "gate": "contract",
                        "evidence_index": 0,
                        "evidence_sha256": (
                            validate_evidence_v3.canonical_sha256(evidence)
                        ),
                    }
                ]
            },
        },
        "completed_at": "2026-07-26T00:02:00Z",
    }


class GoalRuntimeTests(unittest.TestCase):
    def test_paid_data_prose_is_rejected_in_goal_and_story_proof(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state = base / "state"
            blocked = command(
                "init",
                "--root",
                str(root),
                "--state-dir",
                str(state),
                "--goal-id",
                "paid-data",
                "--project-id",
                "sample",
                "--objective",
                "Download premium price data.",
                "--acceptance",
                "a1=The behavior is verified.",
            )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("paid data acquisition", blocked.stdout)

        receipt = json.loads(
            (
                ROOT / "shared" / "templates" / "story-receipt.example.json"
            ).read_text(encoding="utf-8")
        )
        receipt["summary"] = (
            "Subscribed to a paid market-data API and used its price feed."
        )
        issues = goal_runtime.story_receipt_input_issues(receipt)
        self.assertTrue(
            any("paid data acquisition" in issue for issue in issues),
            issues,
        )
        receipt["summary"] = "Paid data was not used."
        self.assertFalse(
            any(
                "paid data acquisition" in issue
                for issue in goal_runtime.story_receipt_input_issues(receipt)
            )
        )

    def test_runtime_reexports_shared_durable_primitives(self) -> None:
        for name in (
            "append_event",
            "atomic_bytes",
            "atomic_json",
            "canonical_bytes",
            "digest",
            "ensure_core_state_artifacts",
            "ensure_state_location",
            "file_digest",
            "fsync_directory",
            "git",
            "git_value",
            "non_git_snapshot",
            "open_regular_nofollow",
            "path_state",
            "portable_relative",
            "project_binding",
            "protected_path_snapshot",
            "sanitize_origin",
            "snapshot_paths",
            "state_lock",
            "strict_json",
            "verify_workspace_snapshot",
            "workspace_snapshot",
        ):
            with self.subTest(name=name):
                self.assertIs(
                    getattr(goal_runtime, name),
                    getattr(goal_primitives, name),
                )

    def test_legacy_workspace_snapshot_keeps_v1_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            root.mkdir()
            script = root / "run.sh"
            script.write_text("#!/bin/sh\n", encoding="utf-8")
            script.chmod(0o755)
            target = base / "target"
            target.mkdir()
            (root / "linked-directory").symlink_to(
                target, target_is_directory=True
            )
            legacy = goal_runtime.workspace_snapshot(root)
            strong = goal_primitives.workspace_snapshot(
                root, snapshot_version=2
            )
        self.assertNotIn("snapshot_version", legacy)
        self.assertNotIn("mode", legacy["paths"]["run.sh"])
        self.assertNotIn("linked-directory", legacy["paths"])
        self.assertEqual(strong["snapshot_version"], 2)
        self.assertEqual(strong["paths"]["run.sh"]["mode"], 0o755)
        self.assertEqual(
            strong["paths"]["linked-directory"]["kind"], "symlink"
        )

    def test_broad_protected_scope_never_captures_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            nested_git = root / "vendor" / "embedded" / ".GIT"
            nested_git.mkdir(parents=True)
            (nested_git / "config").write_text(
                "[core]\n\trepositoryformatversion = 0\n",
                encoding="utf-8",
            )
            ignored = root / "ignored"
            ignored.mkdir()
            (ignored / "out.json").write_text(
                '{"ok": true}\n',
                encoding="utf-8",
            )
            state_dir = base / "external-state"
            state_dir.mkdir()
            snapshot = goal_primitives.workspace_snapshot(
                root,
                state_dir,
                ["**"],
                snapshot_version=2,
            )
            casefold_capture = goal_primitives.protected_path_snapshot(
                root,
                ["ignored/*.JSON"],
                state_dir,
                snapshot_version=2,
            )
        protected_paths = snapshot["protected_paths"]
        self.assertIn("src", protected_paths)
        self.assertIn("src/app.txt", protected_paths)
        self.assertFalse(
            any(
                ".git"
                in {segment.casefold() for segment in Path(path).parts}
                for path in protected_paths
            )
        )
        with self.assertRaisesRegex(
            ValueError,
            "selects Git metadata",
        ):
            goal_primitives.protected_path_snapshot(
                root,
                [".GIT/config"],
                state_dir,
                snapshot_version=2,
            )
        self.assertIn("ignored/out.json", casefold_capture)
        self.assertFalse(goal_primitives.portable_relative("."))
        self.assertFalse(goal_primitives.portable_relative("./"))
        self.assertFalse(goal_primitives.portable_relative("./src/**"))
        self.assertFalse(goal_primitives.portable_relative("src//**"))
        with self.assertRaisesRegex(
            ValueError,
            "must stay within project root",
        ):
            goal_primitives.protected_path_snapshot(
                root,
                ["."],
                state_dir,
                snapshot_version=2,
            )

    def test_recursive_scope_includes_tree_root_without_sibling_broadening(
        self,
    ) -> None:
        self.assertTrue(goal_runtime.matches("generated", ["generated/**"]))
        self.assertTrue(
            goal_runtime.matches("generated/out.txt", ["generated/**"])
        )
        self.assertFalse(
            goal_runtime.matches("generated-other", ["generated/**"])
        )
        self.assertFalse(
            goal_runtime.matches("generated-other/out.txt", ["generated/**"])
        )
        self.assertTrue(goal_runtime.matches("src/direct.py", ["src/*"]))
        self.assertFalse(
            goal_runtime.matches("src/nested/module.py", ["src/*"])
        )
        self.assertTrue(goal_runtime.matches("root.json", ["**/*.json"]))
        self.assertTrue(
            goal_runtime.matches("nested/root.json", ["**/*.json"])
        )
        self.assertFalse(
            goal_runtime.matches("root.json.bak", ["**/*.json"])
        )
        self.assertTrue(
            goal_runtime.matches_protected(
                "src/Protected.txt",
                ["src/protected.txt"],
            )
        )
        self.assertFalse(
            goal_runtime.matches(
                "src/Protected.txt",
                ["src/protected.txt"],
            )
        )

    def test_committed_in_scope_story_change_is_reviewable_and_accepted(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "envelope.json"
            envelope = issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
            )
            issued = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            self.assertEqual(issued.returncode, 0, issued.stdout)
            (root / "src" / "app.txt").write_text(
                "committed in scope\n", encoding="utf-8"
            )
            git(root, "add", "src/app.txt")
            git(root, "commit", "-m", "bounded story change")
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            receipt_path = base / "receipt.json"
            receipt = write_story_receipt(
                root, state_dir, receipt_path, envelope
            )
            accepted = command(
                "story-accept",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertEqual(resumed.returncode, 2, resumed.stdout)
        self.assertEqual(
            json.loads(resumed.stdout)["result"]["drift_paths"],
            ["src/app.txt"],
        )
        self.assertEqual(receipt["changed_paths"], ["src/app.txt"])
        self.assertEqual(accepted.returncode, 0, accepted.stdout)

    def test_committed_out_of_scope_changes_cover_all_git_path_statuses(
        self,
    ) -> None:
        operations = ("add", "modify", "delete", "rename")
        for operation in operations:
            with self.subTest(operation=operation):
                with tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    root = make_repo(base)
                    state_dir = base / "state"
                    initialize(root, state_dir)
                    envelope_path = base / "envelope.json"
                    issue_envelope(
                        root,
                        state_dir,
                        envelope_path,
                        write_scope=["src/**"],
                    )
                    issued = command(
                        "story-issue",
                        "--root",
                        str(root),
                        "--state-dir",
                        str(state_dir),
                        "--envelope",
                        str(envelope_path),
                    )
                    self.assertEqual(issued.returncode, 0, issued.stdout)
                    if operation == "add":
                        (root / "outside.txt").write_text(
                            "added\n", encoding="utf-8"
                        )
                    elif operation == "modify":
                        (root / "README.md").write_text(
                            "modified\n", encoding="utf-8"
                        )
                    elif operation == "delete":
                        (root / "README.md").unlink()
                    else:
                        (root / "README.md").rename(
                            root / "src" / "renamed-readme.md"
                        )
                    git(root, "add", "-A")
                    git(root, "commit", "-m", f"{operation} path")
                    resumed = command(
                        "resume",
                        "--root",
                        str(root),
                        "--state-dir",
                        str(state_dir),
                    )
                self.assertNotEqual(
                    resumed.returncode, 0, resumed.stdout
                )
                self.assertIn(
                    "outside story write scope", resumed.stdout
                )
                expected = (
                    "outside.txt"
                    if operation == "add"
                    else "README.md"
                )
                self.assertIn(expected, resumed.stdout)

    def test_history_rewrite_after_story_issue_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "envelope.json"
            issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
            )
            issued = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            self.assertEqual(issued.returncode, 0, issued.stdout)
            (root / "src" / "app.txt").write_text(
                "rewritten history\n", encoding="utf-8"
            )
            git(root, "add", "src/app.txt")
            git(root, "commit", "--amend", "--no-edit")
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn(
            "baseline HEAD is not an ancestor", resumed.stdout
        )

    def test_generic_pending_recovery_supports_custom_artifact_names(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            state_name = "state.json"
            ledger_name = "events.jsonl"
            pending_name = "pending.json"
            event = goal_primitives.seal_hash_chain_event(
                {
                    "seq": 1,
                    "type": "created",
                    "payload": {},
                    "workspace": {},
                    "previous_sha256": goal_primitives.GENESIS,
                }
            )
            updated_state = {
                "ledger": {
                    "event_count": 1,
                    "tail_sha256": event["event_sha256"],
                }
            }
            goal_primitives.atomic_json(
                state_dir / pending_name,
                goal_primitives.pending_transaction(
                    event,
                    updated_state,
                    document_type="test_pending_event",
                ),
            )

            recovered = goal_primitives.recover_pending_transaction(
                state_dir,
                allowed_event_types={"created"},
                state_name=state_name,
                ledger_name=ledger_name,
                pending_name=pending_name,
                pending_document_type="test_pending_event",
                artifact_names=(
                    ".lock",
                    state_name,
                    ledger_name,
                    pending_name,
                ),
            )
            events, errors = goal_primitives.read_hash_chain(
                state_dir / ledger_name,
                allowed_event_types={"created"},
            )
            recovered_state = json.loads(
                (state_dir / state_name).read_text()
            )
            pending_exists = (state_dir / pending_name).exists()

        self.assertTrue(recovered)
        self.assertEqual(errors, [])
        self.assertEqual(events, [event])
        self.assertEqual(recovered_state, updated_state)
        self.assertFalse(pending_exists)

    def test_init_and_verify_hash_linked_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state = base / "state"
            initialized = initialize(root, state)
            verified = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state),
            )
            ledger = [
                json.loads(line)
                for line in (state / "ledger.jsonl").read_text().splitlines()
            ]
        self.assertEqual(
            verified.returncode, 0, verified.stdout + verified.stderr
        )
        self.assertEqual(initialized["ledger"]["event_count"], 1)
        self.assertEqual(ledger[0]["previous_sha256"], "0" * 64)
        self.assertEqual(
            ledger[0]["event_sha256"],
            initialized["ledger"]["tail_sha256"],
        )

    def test_ledger_edit_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state = base / "state"
            initialize(root, state)
            path = state / "ledger.jsonl"
            event = json.loads(path.read_text())
            event["summary"] = "tampered"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            verified = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state),
            )
        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("invalid event hash", verified.stdout)

    def test_in_scope_interruption_requires_review_then_accepts_receipt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "envelope.json"
            envelope = issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
            )
            issued = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            self.assertEqual(
                issued.returncode, 0, issued.stdout + issued.stderr
            )
            (root / "src" / "app.txt").write_text(
                "changed\n", encoding="utf-8"
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            self.assertEqual(resumed.returncode, 2)
            self.assertEqual(
                json.loads(resumed.stdout)["status"], "review_required"
            )
            current = goal_runtime.workspace_snapshot(root, state_dir)
            receipt: dict[str, object] = {
                "document_type": "quant_story_receipt",
                "schema_version": 1,
                "goal_id": envelope["goal_id"],
                "story_id": envelope["story_id"],
                "envelope_sha256": envelope["envelope_sha256"],
                "status": "ready_for_review",
                "summary": "Bounded change verified.",
                "changed_paths": ["src/app.txt"],
                "claims": [
                    {
                        "acceptance_id": item["id"],
                        "status": "passed",
                        "evidence_ids": ["e1"],
                    }
                    for item in envelope["acceptance"]
                ],
                "evidence": [
                    {
                        "id": "e1",
                        "kind": "inspection",
                        "status": "passed",
                        "summary": "Source inspected.",
                        "ref": "src/app.txt",
                        "sha256": None,
                    }
                ],
                "workspace_sha256": current["sha256"],
                "completed_at": "2026-07-26T00:01:00Z",
            }
            receipt["receipt_sha256"] = goal_runtime.receipt_hash(receipt)
            receipt_path = base / "receipt.json"
            receipt_path.write_text(
                json.dumps(receipt), encoding="utf-8"
            )
            accepted = command(
                "story-accept",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            verified = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertEqual(
            accepted.returncode, 0, accepted.stdout + accepted.stderr
        )
        self.assertEqual(
            verified.returncode, 0, verified.stdout + verified.stderr
        )
        self.assertEqual(
            json.loads(verified.stdout)["result"]["open_story_ids"], []
        )

    def test_out_of_scope_drift_and_external_effect_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            unsafe = base / "unsafe.json"
            issue_envelope(
                root,
                state_dir,
                unsafe,
                write_scope=["src/**"],
                external_effects="deploy",
            )
            rejected = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(unsafe),
            )
            self.assertNotEqual(rejected.returncode, 0)
            safe = base / "safe.json"
            issue_envelope(
                root, state_dir, safe, write_scope=["src/**"]
            )
            opened = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(safe),
            )
            self.assertEqual(opened.returncode, 0)
            (root / "README.md").write_text(
                "unexpected\n", encoding="utf-8"
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn("outside story write scope", resumed.stdout)

    def test_staged_drift_is_not_hidden_from_story_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "envelope.json"
            issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
            )
            opened = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            self.assertEqual(opened.returncode, 0)
            (root / "src" / "app.txt").write_text(
                "staged\n", encoding="utf-8"
            )
            git(root, "add", "src/app.txt")
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertEqual(resumed.returncode, 2)
        self.assertEqual(
            json.loads(resumed.stdout)["result"]["drift_paths"],
            ["src/app.txt"],
        )

    def test_story_cannot_omit_manifest_protected_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            manifest = write_manifest(
                root,
                capabilities=["repo-mutation"],
                protected_paths=["analysis/**"],
            )
            git(root, "add", "project-manifest.json")
            git(root, "commit", "-m", "add manifest")
            state_dir = base / "state"
            initialize(root, state_dir, manifest=manifest)
            envelope_path = base / "envelope.json"
            issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
                protected_scope=[],
            )
            rejected = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn(
            "omits manifest protected scope: analysis/**",
            rejected.stdout,
        )

    def test_intent_fields_are_bound_to_genesis_ledger_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            path = state_dir / "goal-state.json"
            state = json.loads(path.read_text())
            state["required_capabilities"] = []
            state["intent_sha256"] = goal_runtime.intent_sha256(state)
            path.write_text(json.dumps(state), encoding="utf-8")
            verified = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("goal intent is not ledger-bound", verified.stdout)

    def test_manifest_must_be_valid_contained_and_match_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            outside = write_manifest(
                base, capabilities=["repo-mutation"]
            )
            outside_result = command(
                "init",
                "--root",
                str(root),
                "--state-dir",
                str(base / "outside-state"),
                "--goal-id",
                "outside-manifest",
                "--project-id",
                "sample",
                "--objective",
                "Bounded objective.",
                "--acceptance",
                "a1=Verified.",
                "--manifest",
                str(outside),
            )
            mismatch = write_manifest(
                root,
                project_id="different",
                capabilities=["repo-mutation"],
            )
            mismatch_result = command(
                "init",
                "--root",
                str(root),
                "--state-dir",
                str(base / "mismatch-state"),
                "--goal-id",
                "mismatch-manifest",
                "--project-id",
                "sample",
                "--objective",
                "Bounded objective.",
                "--acceptance",
                "a1=Verified.",
                "--manifest",
                str(mismatch),
            )
            legacy = root / "legacy-manifest.json"
            legacy.write_text(
                json.dumps({"schema_version": 1}), encoding="utf-8"
            )
            legacy_result = command(
                "init",
                "--root",
                str(root),
                "--state-dir",
                str(base / "legacy-state"),
                "--goal-id",
                "legacy-manifest",
                "--project-id",
                "sample",
                "--objective",
                "Bounded objective.",
                "--acceptance",
                "a1=Verified.",
                "--manifest",
                str(legacy),
            )
        self.assertNotEqual(outside_result.returncode, 0)
        self.assertIn("within the project root", outside_result.stdout)
        self.assertNotEqual(mismatch_result.returncode, 0)
        self.assertIn("does not match --project-id", mismatch_result.stdout)
        self.assertNotEqual(legacy_result.returncode, 0)
        self.assertIn("schema_version 2 manifest", legacy_result.stdout)

    def test_manifest_capabilities_bound_task_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            manifest = write_manifest(root)
            git(root, "add", "project-manifest.json")
            git(root, "commit", "-m", "manifest")
            rejected = command(
                "init",
                "--root",
                str(root),
                "--state-dir",
                str(base / "state"),
                "--goal-id",
                "capability-overlay",
                "--project-id",
                "sample",
                "--objective",
                "Bounded objective.",
                "--acceptance",
                "a1=Verified.",
                "--manifest",
                str(manifest),
                "--require-capability",
                "repo-mutation",
            )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("overlay exceeds manifest", rejected.stdout)

    def test_manifest_assurance_is_an_init_floor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            manifest = write_manifest(
                root,
                capabilities=["repo-mutation"],
                assurance="release",
            )
            git(root, "add", "project-manifest.json")
            git(root, "commit", "-m", "release manifest")
            state_dir = base / "state"
            state = initialize(
                root,
                state_dir,
                manifest=manifest,
                assurance="light",
            )
        self.assertEqual(state["assurance"], "release")

    def test_manifestless_goal_respects_explicit_light_assurance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state = initialize(
                root,
                base / "state",
                capabilities=[],
                assurance="light",
            )
        self.assertEqual(state["assurance"], "light")

    def test_gitignored_protected_path_drift_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            (root / ".gitignore").write_text("secret/\n", encoding="utf-8")
            secret = root / "secret"
            secret.mkdir()
            (secret / "value.json").write_text(
                '{"value": 1}\n', encoding="utf-8"
            )
            manifest = write_manifest(
                root,
                capabilities=["repo-mutation"],
                protected_paths=["secret/**"],
            )
            git(root, "add", ".gitignore", "project-manifest.json")
            git(root, "commit", "-m", "protected ignored contract")
            state_dir = base / "state"
            initialize(root, state_dir, manifest=manifest)
            envelope_path = base / "envelope.json"
            issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
                protected_scope=["secret/**"],
            )
            opened = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            self.assertEqual(opened.returncode, 0, opened.stdout)
            (secret / "value.json").write_text(
                '{"value": 2}\n', encoding="utf-8"
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn("drift touches protected scope", resumed.stdout)
        self.assertIn("secret/value.json", resumed.stdout)

    def test_story_id_traversal_and_reuse_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            traversal_path = base / "traversal.json"
            issue_envelope(
                root,
                state_dir,
                traversal_path,
                write_scope=["src/**"],
                story_id="../../escaped",
            )
            traversal = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(traversal_path),
            )
            self.assertNotEqual(traversal.returncode, 0)
            self.assertFalse((base / "escaped.json").exists())

            first_path = base / "first.json"
            issue_envelope(
                root,
                state_dir,
                first_path,
                write_scope=[],
                story_id="same-story",
                mode="read_only",
            )
            first = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(first_path),
            )
            self.assertEqual(first.returncode, 0, first.stdout)
            state = json.loads((state_dir / "goal-state.json").read_text())
            current = goal_runtime.workspace_snapshot(root, state_dir)
            envelope = json.loads(first_path.read_text())
            receipt: dict[str, object] = {
                "document_type": "quant_story_receipt",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "same-story",
                "envelope_sha256": envelope["envelope_sha256"],
                "status": "ready_for_review",
                "summary": "Read-only review complete.",
                "changed_paths": [],
                "claims": [
                    {
                        "acceptance_id": item["id"],
                        "status": "passed",
                        "evidence_ids": ["e1"],
                    }
                    for item in envelope["acceptance"]
                ],
                "evidence": [
                    {
                        "id": "e1",
                        "kind": "inspection",
                        "status": "passed",
                    }
                ],
                "workspace_sha256": current["sha256"],
                "completed_at": "2026-07-26T00:01:00Z",
            }
            receipt["receipt_sha256"] = goal_runtime.receipt_hash(receipt)
            receipt_path = base / "read-only-receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            accepted = command(
                "story-accept",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            self.assertEqual(accepted.returncode, 0, accepted.stdout)
            reused_path = base / "reused.json"
            issue_envelope(
                root,
                state_dir,
                reused_path,
                write_scope=[],
                story_id="same-story",
                mode="read_only",
            )
            reused = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(reused_path),
            )
        self.assertNotEqual(reused.returncode, 0)
        self.assertIn("story_id cannot be reused", reused.stdout)

    def test_story_envelope_and_accepted_receipt_are_ledger_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "envelope.json"
            issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=[],
                mode="read_only",
            )
            opened = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            self.assertEqual(opened.returncode, 0, opened.stdout)
            stored = state_dir / "stories" / "story-change.json"
            envelope = json.loads(stored.read_text())
            envelope["objective"] = "Broadened after issue."
            envelope["envelope_sha256"] = goal_runtime.envelope_hash(envelope)
            stored.write_text(json.dumps(envelope), encoding="utf-8")
            verified = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("envelope is not ledger-bound", verified.stdout)

    def test_story_and_receipt_parent_symlinks_cannot_write_outside_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)

            story_state = base / "story-state"
            initialize(root, story_state, capabilities=[])
            external_stories = base / "external-stories"
            external_stories.mkdir()
            (story_state / "stories").symlink_to(
                external_stories, target_is_directory=True
            )
            story_envelope_path = base / "story-envelope.json"
            issue_envelope(
                root,
                story_state,
                story_envelope_path,
                write_scope=[],
                mode="read_only",
            )
            story_rejected = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(story_state),
                "--envelope",
                str(story_envelope_path),
            )
            self.assertNotEqual(story_rejected.returncode, 0)
            self.assertIn("symbolic link", story_rejected.stdout)
            self.assertEqual(list(external_stories.iterdir()), [])

            receipt_state = base / "receipt-state"
            initialize(
                root,
                receipt_state,
                capabilities=[],
                goal_id="receipt-symlink-goal",
            )
            receipt_envelope_path = base / "receipt-envelope.json"
            envelope = issue_envelope(
                root,
                receipt_state,
                receipt_envelope_path,
                write_scope=[],
                mode="read_only",
            )
            opened = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(receipt_state),
                "--envelope",
                str(receipt_envelope_path),
            )
            self.assertEqual(opened.returncode, 0, opened.stdout)
            external_receipts = base / "external-receipts"
            external_receipts.mkdir()
            (receipt_state / "receipts").symlink_to(
                external_receipts, target_is_directory=True
            )
            receipt_path = base / "story-receipt.json"
            write_story_receipt(
                root, receipt_state, receipt_path, envelope
            )
            receipt_rejected = command(
                "story-accept",
                "--root",
                str(root),
                "--state-dir",
                str(receipt_state),
                "--receipt",
                str(receipt_path),
            )
            external_receipt_contents = list(
                external_receipts.iterdir()
            )
        self.assertNotEqual(receipt_rejected.returncode, 0)
        self.assertIn("symbolic link", receipt_rejected.stdout)
        self.assertEqual(external_receipt_contents, [])

    def test_read_only_story_can_coexist_with_one_write_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(
                root,
                state_dir,
                capabilities=["repo-mutation", "multi-agent-write"],
            )
            review_path = base / "review.json"
            issue_envelope(
                root,
                state_dir,
                review_path,
                write_scope=[],
                story_id="review-story",
                mode="read_only",
            )
            review = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(review_path),
            )
            self.assertEqual(review.returncode, 0, review.stdout)
            write_path = base / "write.json"
            issue_envelope(
                root,
                state_dir,
                write_path,
                write_scope=["src/**"],
                story_id="write-story",
            )
            write = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(write_path),
            )
            state = json.loads((state_dir / "goal-state.json").read_text())
            events = [
                json.loads(line)
                for line in (state_dir / "ledger.jsonl").read_text().splitlines()
            ]
        self.assertEqual(write.returncode, 0, write.stdout)
        self.assertEqual(
            state["open_story_ids"], ["review-story", "write-story"]
        )
        self.assertTrue(
            state["runtime_facts"]["multi_agent_write_used"]
        )
        self.assertEqual(
            events[-1]["payload"]["runtime_capabilities"],
            ["multi-agent-write"],
        )
        self.assertEqual(state["assurance"], "standard")

    def test_legacy_runtime_rejects_agent_team_execution_at_init(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            result = command(
                "init",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--goal-id",
                "legacy-team",
                "--project-id",
                "sample",
                "--objective",
                "Reject an unsupported legacy runtime proof lane.",
                "--acceptance",
                "a1=The unsupported runtime is rejected.",
                "--assurance",
                "standard",
                "--require-capability",
                "agent-team-execution",
            )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "legacy goal runtime does not support runtime capabilities: "
            "agent-team-execution",
            result.stdout,
        )
        self.assertIn("host-aligned Goal ledger", result.stdout)
        self.assertFalse(state_dir.exists())

    def test_legacy_runtime_rejects_preexisting_agent_team_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            state = initialize(
                root,
                state_dir,
                capabilities=[],
                bind_manifest=False,
            )
            state["runtime_capabilities"] = ["agent-team-execution"]
            state["intent_sha256"] = goal_runtime.intent_sha256(state)
            ledger_path = state_dir / goal_runtime.LEDGER_NAME
            events = [
                json.loads(line)
                for line in ledger_path.read_text(encoding="utf-8").splitlines()
            ]
            events[0]["payload"]["intent_sha256"] = state["intent_sha256"]
            events[0] = goal_runtime.seal_hash_chain_event(events[0])
            state["ledger"]["tail_sha256"] = events[0]["event_sha256"]
            (state_dir / goal_runtime.STATE_NAME).write_text(
                json.dumps(state),
                encoding="utf-8",
            )
            ledger_path.write_text(
                json.dumps(events[0]) + "\n",
                encoding="utf-8",
            )

            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            receipt_path = base / "receipt.json"
            receipt_path.write_text("{}\n", encoding="utf-8")
            completed = command(
                "complete",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )

        for result in (resumed, completed):
            with self.subTest(command=result.args[2]):
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(
                    "legacy goal runtime does not support runtime capabilities: "
                    "agent-team-execution",
                    result.stdout,
                )

    def test_verify_is_read_only_and_resume_recovers_pending_event(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            with goal_runtime.state_lock(state_dir):
                state, errors, current = goal_runtime.load_and_verify(
                    root, state_dir, check_workspace=True
                )
                self.assertEqual(errors, [])
                assert state is not None and current is not None
                event = goal_runtime.make_event(
                    state,
                    "checkpoint",
                    summary="Interrupted checkpoint.",
                    payload={"kind": "test"},
                    workspace=current,
                )
                original_atomic = goal_runtime.atomic_json

                def fail_state_write(
                    path: Path, value: dict[str, object]
                ) -> None:
                    if path.name == goal_runtime.STATE_NAME:
                        raise OSError("simulated crash")
                    original_atomic(path, value)

                with mock.patch.object(
                    goal_runtime,
                    "atomic_json",
                    side_effect=fail_state_write,
                ):
                    with self.assertRaises(OSError):
                        goal_runtime.persist_event(
                            state_dir,
                            state,
                            event,
                            workspace=current,
                        )
            state_before = (state_dir / "goal-state.json").read_bytes()
            ledger_before = (state_dir / "ledger.jsonl").read_bytes()
            verified = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            self.assertNotEqual(verified.returncode, 0)
            self.assertIn("verify remains read-only", verified.stdout)
            self.assertEqual(
                (state_dir / "goal-state.json").read_bytes(), state_before
            )
            self.assertEqual(
                (state_dir / "ledger.jsonl").read_bytes(), ledger_before
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            final_verify = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertEqual(resumed.returncode, 0, resumed.stdout)
        self.assertEqual(final_verify.returncode, 0, final_verify.stdout)
        self.assertFalse((state_dir / goal_runtime.PENDING_NAME).exists())

    def test_accepted_receipt_cannot_be_rewritten_after_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "envelope.json"
            envelope = issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=[],
                mode="read_only",
            )
            opened = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            self.assertEqual(opened.returncode, 0, opened.stdout)
            receipt_path = base / "receipt.json"
            write_story_receipt(
                root, state_dir, receipt_path, envelope
            )
            accepted = command(
                "story-accept",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            self.assertEqual(accepted.returncode, 0, accepted.stdout)
            stored_path = state_dir / "receipts" / "story-change.json"
            stored = json.loads(stored_path.read_text())
            stored["summary"] = "Rewritten after primary review."
            stored["receipt_sha256"] = goal_runtime.receipt_hash(stored)
            stored_path.write_text(json.dumps(stored), encoding="utf-8")
            verified = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("receipt is not ledger-bound", verified.stdout)

    def test_story_acceptance_keeps_its_issue_baseline_after_checkpoint(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "envelope.json"
            envelope = issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
            )
            opened = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            self.assertEqual(opened.returncode, 0, opened.stdout)
            (root / "src" / "app.txt").write_text(
                "first change\n", encoding="utf-8"
            )
            checkpointed = command(
                "checkpoint",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--summary",
                "Reviewed first bounded change.",
            )
            self.assertEqual(
                checkpointed.returncode,
                0,
                checkpointed.stdout + checkpointed.stderr,
            )
            (root / "src" / "second.txt").write_text(
                "second change\n", encoding="utf-8"
            )
            receipt_path = base / "receipt.json"
            receipt = write_story_receipt(
                root, state_dir, receipt_path, envelope
            )
            accepted = command(
                "story-accept",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertEqual(
            receipt["changed_paths"],
            ["src/app.txt", "src/second.txt"],
        )
        self.assertEqual(accepted.returncode, 0, accepted.stdout)

    def test_complete_status_blocks_all_later_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            with goal_runtime.state_lock(state_dir):
                state, errors, current = goal_runtime.load_and_verify(
                    root, state_dir, check_workspace=True
                )
                self.assertEqual(errors, [])
                assert state is not None and current is not None
                pre_completion_tail = state["ledger"]["tail_sha256"]
                final_receipt = {
                    "schema_version": 3,
                    "test": True,
                    "goal_binding": {
                        "ledger_tail_sha256": pre_completion_tail
                    },
                }
                receipts = goal_runtime.artifact_parent(
                    state_dir, "receipts", create=True
                )
                goal_runtime.atomic_json(
                    receipts / "final.json", final_receipt
                )
                final_receipt_sha256 = goal_runtime.digest(final_receipt)
                event = goal_runtime.make_event(
                    state,
                    "status_changed",
                    summary="Test completion.",
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
                goal_runtime.persist_event(
                    state_dir, state, event, workspace=current
                )
            checkpointed = command(
                "checkpoint",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--summary",
                "Must not run.",
            )
            envelope_path = base / "after-complete.json"
            issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=[],
                mode="read_only",
            )
            issued = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
        self.assertNotEqual(checkpointed.returncode, 0)
        self.assertIn("after goal status is complete", checkpointed.stdout)
        self.assertNotEqual(issued.returncode, 0)
        self.assertIn("after goal status is complete", issued.stdout)

    def test_manifestless_research_goal_requires_real_v3_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir, capabilities=[])
            receipt = final_research_receipt(root, state_dir)
            receipt_path = base / "final.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            fake = json.loads(json.dumps(receipt))
            fake["goal_binding"]["acceptance_claims"] = {}
            fake_path = base / "fake.json"
            fake_path.write_text(json.dumps(fake), encoding="utf-8")
            rejected = command(
                "complete",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(fake_path),
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("acceptance_claims", rejected.stdout)
            active = json.loads(
                (state_dir / "goal-state.json").read_text()
            )
            self.assertEqual(active["status"], "active")

            completed = command(
                "complete",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            verified = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            ledger = [
                json.loads(line)
                for line in (state_dir / "ledger.jsonl").read_text().splitlines()
            ]
            final_intent_sha256 = json.loads(
                (state_dir / "goal-state.json").read_text()
            )["intent_sha256"]
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(verified.returncode, 0, verified.stdout)
        self.assertEqual(
            json.loads(verified.stdout)["result"]["status"], "complete"
        )
        completion = ledger[-1]
        self.assertEqual(
            completion["payload"]["final_receipt_sha256"],
            goal_runtime.digest(receipt),
        )
        self.assertEqual(
            completion["payload"]["pre_completion_ledger_tail_sha256"],
            completion["previous_sha256"],
        )
        self.assertEqual(
            completion["payload"]["goal_intent_sha256"],
            final_intent_sha256,
        )

    def test_manifestless_project_capability_completion_is_blocked(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir, bind_manifest=False)
            receipt = final_research_receipt(root, state_dir)
            receipt["scope"]["capabilities"] = ["repo-mutation"]
            receipt_path = base / "final.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            rejected = command(
                "complete",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn(
            "manifest-less research completion cannot prove",
            rejected.stdout,
        )

    def test_manifestless_goal_cannot_issue_a_write_story(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir, capabilities=[])
            envelope_path = base / "write.json"
            envelope = issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
            )
            opened = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
        self.assertNotEqual(opened.returncode, 0)
        self.assertIn(
            "write story requires a bound schema_version 2 manifest",
            opened.stdout,
        )

    def test_write_story_requires_effective_repo_mutation_capability(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            manifest = write_manifest(root, capabilities=[])
            git(root, "add", manifest.name)
            git(root, "commit", "-m", "read-only manifest")
            state_dir = base / "state"
            initialize(
                root,
                state_dir,
                manifest=manifest,
                capabilities=[],
            )
            envelope_path = base / "write.json"
            issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
            )
            rejected = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn(
            "requires effective repo-mutation capability",
            rejected.stdout,
        )

    def test_story_acceptance_text_must_match_goal_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "weakened-envelope.json"
            envelope = issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
                protected_scope=[],
            )
            envelope["acceptance"][0]["text"] = "A weaker substitute."
            envelope["envelope_sha256"] = goal_runtime.envelope_hash(
                envelope
            )
            envelope_path.write_text(
                json.dumps(envelope),
                encoding="utf-8",
            )
            issued = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
        self.assertNotEqual(issued.returncode, 0)
        self.assertIn(
            "exactly match current Goal acceptance",
            issued.stdout,
        )

    def test_story_receipt_rejects_branch_hop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "branch-envelope.json"
            envelope = issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
                protected_scope=[],
            )
            issued = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            self.assertEqual(issued.returncode, 0, issued.stdout)
            git(root, "switch", "-c", "other-story-branch")
            receipt_path = base / "branch-receipt.json"
            write_story_receipt(
                root,
                state_dir,
                receipt_path,
                envelope,
            )
            accepted = command(
                "story-accept",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertNotEqual(accepted.returncode, 0)
        self.assertIn(
            "workspace branch or project kind changed",
            accepted.stdout,
        )


if __name__ == "__main__":
    unittest.main()
