from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "shared" / "scripts"
TESTS = ROOT / "tests"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import goal_runtime
from test_goal_runtime import (
    command,
    git,
    initialize,
    issue_envelope,
    make_repo,
)


POLICY = "zero-spend-unless-user-first-requests-specific-paid-action"


def valid_manifest(*, protected: list[str]) -> dict[str, object]:
    return {
        "schema_version": 2,
        "project": {
            "id": "sample",
            "purpose": "Exercise durable Goal security boundaries.",
        },
        "assurance": "light",
        "profiles": [],
        "capabilities": ["repo-mutation"],
        "adapters": {},
        "contracts": {
            "protected_paths": protected,
            "test_commands": [],
        },
        "capability_config": {},
        "authority": {
            "cost_policy": POLICY,
            "paid_action_authority": None,
            "paid_fallback_enabled": False,
        },
        "extensions": {},
    }


def ready_story_receipt(
    envelope: dict[str, object],
    current: dict[str, object],
    changed_paths: list[str],
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "document_type": "quant_story_receipt",
        "schema_version": 1,
        "goal_id": envelope["goal_id"],
        "story_id": envelope["story_id"],
        "envelope_sha256": envelope["envelope_sha256"],
        "status": "ready_for_review",
        "summary": "The bounded story was verified.",
        "changed_paths": changed_paths,
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
                "summary": "The changed surface was inspected.",
                "ref": changed_paths[0] if changed_paths else "no-change",
                "sha256": None,
            }
        ],
        "workspace_sha256": current["sha256"],
        "completed_at": "2026-07-26T00:01:00Z",
    }
    receipt["receipt_sha256"] = goal_runtime.receipt_hash(receipt)
    return receipt


class GoalRuntimeRedTeamTests(unittest.TestCase):
    def test_case_alias_cannot_bypass_protected_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            protected = root / "src" / "Protected.txt"
            protected.write_text("protected\n", encoding="utf-8")
            git(root, "add", "src/Protected.txt")
            git(root, "commit", "-m", "add protected case fixture")
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "envelope.json"
            issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
                protected_scope=["src/protected.txt"],
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

            protected.write_text("changed\n", encoding="utf-8")
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )

        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn("protected scope", resumed.stdout)
        self.assertIn("src/Protected.txt", resumed.stdout)

    def test_existing_external_symlink_in_story_scope_blocks_issue(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            outside = base / "outside"
            outside.mkdir()
            (root / "src" / "external").symlink_to(
                outside, target_is_directory=True
            )
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
        self.assertNotEqual(issued.returncode, 0)
        self.assertIn("project symbolic link", issued.stdout)
        self.assertIn("src/external", issued.stdout)

    def test_scope_traversal_through_external_symlink_blocks_issue(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            outside = base / "outside"
            outside.mkdir()
            (root / "vendor").symlink_to(
                outside, target_is_directory=True
            )
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "envelope.json"
            issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["vendor/generated/**"],
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
        self.assertIn("project symbolic link", issued.stdout)
        self.assertIn("vendor", issued.stdout)

    def test_existing_project_symlink_in_protected_scope_blocks_issue(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(valid_manifest(protected=["analysis/**"])),
                encoding="utf-8",
            )
            git(root, "add", "manifest.json")
            git(root, "commit", "-m", "protected scope")
            protected_target = root / "protected-target"
            protected_target.mkdir()
            (root / "analysis").symlink_to(
                protected_target, target_is_directory=True
            )
            state_dir = base / "state"
            initialize(root, state_dir, manifest=manifest)
            envelope_path = base / "envelope.json"
            issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
                protected_scope=["analysis/**"],
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
        self.assertIn("project symbolic link", issued.stdout)
        self.assertIn("analysis", issued.stdout)

    def test_project_local_goal_state_and_git_metadata_cannot_be_story_scope(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            (root / ".gitignore").write_text(
                ".goal-state/\n",
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(valid_manifest(protected=[])),
                encoding="utf-8",
            )
            git(root, "add", ".gitignore", "manifest.json")
            git(root, "commit", "-m", "allow project-local Goal state")
            state_dir = root / ".goal-state"
            initialize(root, state_dir, manifest=manifest)

            state_envelope = base / "state-envelope.json"
            issue_envelope(
                root,
                state_dir,
                state_envelope,
                story_id="story-state",
                write_scope=[".goal-state/**"],
            )
            state_issue = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(state_envelope),
            )

            git_envelope = base / "git-envelope.json"
            issue_envelope(
                root,
                state_dir,
                git_envelope,
                story_id="story-git",
                write_scope=[".git/**"],
            )
            git_issue = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(git_envelope),
            )

            wildcard_git_envelope = base / "wildcard-git-envelope.json"
            issue_envelope(
                root,
                state_dir,
                wildcard_git_envelope,
                story_id="story-wildcard-git",
                write_scope=[".git*/**"],
            )
            wildcard_git_issue = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(wildcard_git_envelope),
            )

            casefold_git_envelope = base / "casefold-git-envelope.json"
            issue_envelope(
                root,
                state_dir,
                casefold_git_envelope,
                story_id="story-casefold-git",
                write_scope=[".GIT/**"],
            )
            casefold_git_issue = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(casefold_git_envelope),
            )
        self.assertNotEqual(state_issue.returncode, 0)
        self.assertIn("project-local Goal state", state_issue.stdout)
        self.assertNotEqual(git_issue.returncode, 0)
        self.assertIn("write_scope is invalid", git_issue.stdout)
        self.assertNotEqual(wildcard_git_issue.returncode, 0)
        self.assertIn(
            "write_scope is invalid",
            wildcard_git_issue.stdout,
        )
        self.assertNotEqual(casefold_git_issue.returncode, 0)
        self.assertIn(
            "write_scope is invalid",
            casefold_git_issue.stdout,
        )

    def test_new_external_symlink_in_story_scope_blocks_acceptance(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            outside = base / "outside"
            outside.mkdir()
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
            (root / "src" / "external").symlink_to(
                outside, target_is_directory=True
            )
            current = goal_runtime.workspace_snapshot(root, state_dir)
            receipt = ready_story_receipt(
                envelope, current, ["src/external"]
            )
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
        self.assertNotEqual(accepted.returncode, 0)
        self.assertIn("project symbolic link", accepted.stdout)
        self.assertIn("src/external", accepted.stdout)

    def test_post_init_state_root_symlink_substitution_is_blocked(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            relocated = base / "relocated-state"
            state_dir.rename(relocated)
            state_dir.symlink_to(relocated, target_is_directory=True)
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn(
            "state directory root must not be a symbolic link",
            resumed.stdout,
        )

    def test_core_state_symlinks_cannot_escape_during_init(self) -> None:
        for artifact_name in (".lock", goal_runtime.LEDGER_NAME):
            with self.subTest(artifact=artifact_name):
                with tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    root = make_repo(base)
                    state_dir = base / f"state-{artifact_name.lstrip('.')}"
                    state_dir.mkdir()
                    outside = base / f"outside-{artifact_name.lstrip('.')}"
                    (state_dir / artifact_name).symlink_to(outside)

                    initialized = command(
                        "init",
                        "--root",
                        str(root),
                        "--state-dir",
                        str(state_dir),
                        "--goal-id",
                        "symlink-state-goal",
                        "--project-id",
                        "sample",
                        "--objective",
                        "Reject core state symlink escapes.",
                        "--acceptance",
                        "s1=No external state artifact is written.",
                        "--assurance",
                        "light",
                    )

                    self.assertNotEqual(initialized.returncode, 0)
                    self.assertFalse(outside.exists())
                    self.assertTrue(
                        (state_dir / artifact_name).is_symlink()
                    )

    def test_intent_rehash_cannot_escape_genesis_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            state_path = state_dir / "goal-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["assurance"] = "light"
            state["required_outcomes"] = ["downgraded-after-init"]
            state["intent_sha256"] = goal_runtime.intent_sha256(state)
            state_path.write_text(json.dumps(state), encoding="utf-8")

            verified = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("intent is not ledger-bound", verified.stdout)

    def test_story_id_traversal_is_rejected_without_escape_write(self) -> None:
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
            envelope["story_id"] = "../../escaped"
            envelope["envelope_sha256"] = goal_runtime.envelope_hash(envelope)
            envelope_path.write_text(json.dumps(envelope), encoding="utf-8")

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
        self.assertIn("portable ID", issued.stdout)
        self.assertFalse((base / "escaped.json").exists())

    def test_rehashed_story_envelope_remains_ledger_bound(self) -> None:
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
            self.assertEqual(
                issued.returncode, 0, issued.stdout + issued.stderr
            )
            stored = state_dir / "stories" / "story-change.json"
            envelope = json.loads(stored.read_text(encoding="utf-8"))
            envelope["write_scope"] = ["**"]
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

    def test_gitignored_protected_file_drift_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            ignored = root / "ignored"
            ignored.mkdir()
            protected = ignored / "result.json"
            protected.write_text('{"value": 1}\n', encoding="utf-8")
            (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(valid_manifest(protected=["ignored/**"])),
                encoding="utf-8",
            )
            git(root, "add", ".gitignore", "manifest.json")
            git(root, "commit", "-m", "protected fixture")

            state_dir = base / "state"
            initialize(root, state_dir, manifest=manifest)
            envelope_path = base / "envelope.json"
            issue_envelope(
                root,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
                protected_scope=["ignored/**"],
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
            protected.write_text('{"value": 2}\n', encoding="utf-8")
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn("ignored/result.json", resumed.stdout)
        self.assertIn("protected scope", resumed.stdout)

    def test_read_only_story_can_coexist_with_single_write_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            write_path = base / "write.json"
            issue_envelope(
                root,
                state_dir,
                write_path,
                write_scope=["src/**"],
            )
            issued_write = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(write_path),
            )
            self.assertEqual(
                issued_write.returncode,
                0,
                issued_write.stdout + issued_write.stderr,
            )

            state = json.loads(
                (state_dir / "goal-state.json").read_text(encoding="utf-8")
            )
            snapshot = goal_runtime.workspace_snapshot(root, state_dir)
            read_only: dict[str, object] = {
                "document_type": "quant_story_envelope",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-audit",
                "project_binding_sha256": state["project_binding"][
                    "identity_sha256"
                ],
                "objective": "Audit without changing files.",
                "mode": "read_only",
                "write_scope": [],
                "protected_scope": [],
                "depends_on": [],
                "acceptance": state["acceptance"],
                "external_effects": "none",
                "cost_class": "no_billable_action",
                "baseline_workspace_sha256": snapshot["sha256"],
                "issued_at": "2026-07-26T00:00:00Z",
            }
            read_only["envelope_sha256"] = goal_runtime.envelope_hash(
                read_only
            )
            read_path = base / "read.json"
            read_path.write_text(json.dumps(read_only), encoding="utf-8")
            issued_read = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(read_path),
            )
            self.assertEqual(
                issued_read.returncode,
                0,
                issued_read.stdout + issued_read.stderr,
            )

            (root / "src" / "app.txt").write_text(
                "interrupted\n", encoding="utf-8"
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertEqual(resumed.returncode, 2)
        payload = json.loads(resumed.stdout)
        self.assertEqual(payload["status"], "review_required")
        self.assertEqual(payload["result"]["story_id"], "story-change")

    def test_accepted_receipt_rehash_remains_ledger_bound(self) -> None:
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
            current = goal_runtime.workspace_snapshot(root, state_dir)
            receipt = ready_story_receipt(
                envelope, current, ["src/app.txt"]
            )
            receipt_path = base / "receipt.json"
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
            self.assertEqual(
                accepted.returncode, 0, accepted.stdout + accepted.stderr
            )
            stored = state_dir / "receipts" / "story-change.json"
            tampered = json.loads(stored.read_text(encoding="utf-8"))
            tampered["summary"] = "Rewritten after primary acceptance."
            tampered["receipt_sha256"] = goal_runtime.receipt_hash(tampered)
            stored.write_text(json.dumps(tampered), encoding="utf-8")

            verified = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(verified.returncode, 0)
        self.assertIn("receipt is not ledger-bound", verified.stdout)

    def test_story_id_cannot_be_reused_after_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            envelope_path = base / "first.json"
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
            current = goal_runtime.workspace_snapshot(root, state_dir)
            receipt = ready_story_receipt(
                envelope, current, ["src/app.txt"]
            )
            receipt_path = base / "receipt.json"
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
            self.assertEqual(
                accepted.returncode, 0, accepted.stdout + accepted.stderr
            )

            reused_path = base / "reused.json"
            issue_envelope(
                root,
                state_dir,
                reused_path,
                write_scope=["src/**"],
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
        self.assertIn("cannot be reused", reused.stdout)

    def test_recovery_checkpoint_does_not_erase_story_baseline(self) -> None:
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
            checkpoint = command(
                "checkpoint",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--summary",
                "Reviewed the interrupted in-scope change.",
            )
            self.assertEqual(
                checkpoint.returncode,
                0,
                checkpoint.stdout + checkpoint.stderr,
            )
            current = goal_runtime.workspace_snapshot(root, state_dir)
            receipt = ready_story_receipt(
                envelope, current, ["src/app.txt"]
            )
            receipt_path = base / "receipt.json"
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
        self.assertEqual(
            accepted.returncode, 0, accepted.stdout + accepted.stderr
        )

    def test_interrupted_event_state_write_recovers_on_resume_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            state = goal_runtime.strict_json(
                state_dir / goal_runtime.STATE_NAME
            )
            current = goal_runtime.workspace_snapshot(root, state_dir)
            event = goal_runtime.make_event(
                state,
                "checkpoint",
                summary="Crash fixture",
                payload={"kind": "crash-fixture"},
                workspace=current,
            )
            original_atomic_json = goal_runtime.atomic_json

            def fail_state_write(
                path: Path, value: dict[str, object]
            ) -> None:
                if path.name == goal_runtime.STATE_NAME:
                    raise OSError("injected state write failure")
                original_atomic_json(path, value)

            with mock.patch.object(
                goal_runtime,
                "atomic_json",
                side_effect=fail_state_write,
            ):
                with self.assertRaisesRegex(
                    OSError, "injected state write failure"
                ):
                    goal_runtime.persist_event(
                        state_dir,
                        state,
                        event,
                        current,
                    )
            pending = state_dir / goal_runtime.PENDING_NAME
            self.assertTrue(pending.is_file())
            pending_before = pending.read_bytes()
            state_before = (
                state_dir / goal_runtime.STATE_NAME
            ).read_bytes()
            read_only = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            self.assertNotEqual(read_only.returncode, 0)
            self.assertEqual(pending.read_bytes(), pending_before)
            self.assertEqual(
                (state_dir / goal_runtime.STATE_NAME).read_bytes(),
                state_before,
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            recovered = goal_runtime.strict_json(
                state_dir / goal_runtime.STATE_NAME
            )
        self.assertEqual(
            resumed.returncode, 0, resumed.stdout + resumed.stderr
        )
        self.assertFalse(pending.exists())
        self.assertEqual(recovered["ledger"]["event_count"], 2)

    def test_torn_journalled_ledger_tail_is_repaired_on_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            state = goal_runtime.strict_json(
                state_dir / goal_runtime.STATE_NAME
            )
            current = goal_runtime.workspace_snapshot(root, state_dir)
            event = goal_runtime.make_event(
                state,
                "checkpoint",
                summary="Torn append fixture",
                payload={"kind": "torn-append-fixture"},
                workspace=current,
            )
            updated = goal_runtime.update_state_for_event(
                state, event, workspace=current
            )
            goal_runtime.atomic_json(
                state_dir / goal_runtime.PENDING_NAME,
                goal_runtime.pending_transaction(event, updated),
            )
            ledger = state_dir / goal_runtime.LEDGER_NAME
            event_line = goal_runtime.canonical_bytes(event)
            torn_prefix = event_line[: max(1, len(event_line) // 3)]
            with ledger.open("ab") as handle:
                handle.write(torn_prefix)
                handle.flush()
            ledger_before = ledger.read_bytes()

            read_only = command(
                "verify",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            self.assertNotEqual(read_only.returncode, 0)
            self.assertEqual(ledger.read_bytes(), ledger_before)

            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            events, errors = goal_runtime.read_ledger(ledger)
            recovered = goal_runtime.strict_json(
                state_dir / goal_runtime.STATE_NAME
            )

        self.assertEqual(
            resumed.returncode, 0, resumed.stdout + resumed.stderr
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(events), 2)
        self.assertEqual(events[-1]["event_sha256"], event["event_sha256"])
        self.assertEqual(recovered["ledger"]["event_count"], 2)
        self.assertFalse((state_dir / goal_runtime.PENDING_NAME).exists())

    def test_unrelated_corrupt_ledger_tail_is_never_auto_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            state = goal_runtime.strict_json(
                state_dir / goal_runtime.STATE_NAME
            )
            current = goal_runtime.workspace_snapshot(root, state_dir)
            event = goal_runtime.make_event(
                state,
                "checkpoint",
                summary="Unrelated corruption fixture",
                payload={"kind": "unrelated-corruption-fixture"},
                workspace=current,
            )
            updated = goal_runtime.update_state_for_event(
                state, event, workspace=current
            )
            pending = state_dir / goal_runtime.PENDING_NAME
            goal_runtime.atomic_json(
                pending,
                goal_runtime.pending_transaction(event, updated),
            )
            ledger = state_dir / goal_runtime.LEDGER_NAME
            with ledger.open("ab") as handle:
                handle.write(b"unrelated-corrupt-tail")
                handle.flush()
            ledger_before = ledger.read_bytes()
            pending_before = pending.read_bytes()

            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            ledger_after = ledger.read_bytes()
            pending_after = pending.read_bytes()

        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn("cannot recover pending transaction", resumed.stdout)
        self.assertEqual(ledger_after, ledger_before)
        self.assertEqual(pending_after, pending_before)

    def test_conflicting_valid_no_newline_event_is_blocked_without_mutation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            initialize(root, state_dir)
            state = goal_runtime.strict_json(
                state_dir / goal_runtime.STATE_NAME
            )
            current = goal_runtime.workspace_snapshot(root, state_dir)
            expected = goal_runtime.make_event(
                state,
                "checkpoint",
                summary="Expected pending event",
                payload={"kind": "expected"},
                workspace=current,
            )
            updated = goal_runtime.update_state_for_event(
                state, expected, workspace=current
            )
            pending = state_dir / goal_runtime.PENDING_NAME
            goal_runtime.atomic_json(
                pending,
                goal_runtime.pending_transaction(expected, updated),
            )
            conflicting = goal_runtime.make_event(
                state,
                "checkpoint",
                summary="Conflicting valid event",
                payload={"kind": "conflict"},
                workspace=current,
            )
            ledger = state_dir / goal_runtime.LEDGER_NAME
            ledger.write_bytes(
                ledger.read_bytes()
                + goal_runtime.canonical_bytes(conflicting)
            )
            ledger_before = ledger.read_bytes()
            pending_before = pending.read_bytes()

            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            ledger_after = ledger.read_bytes()
            pending_after = pending.read_bytes()

        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn("pending goal event conflicts", resumed.stdout)
        self.assertEqual(ledger_after, ledger_before)
        self.assertEqual(pending_after, pending_before)


if __name__ == "__main__":
    unittest.main()
