from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "shared" / "scripts"
SCRIPT = SCRIPTS / "goal_ledger.py"
sys.path.insert(0, str(SCRIPTS))

import goal_ledger
import goal_primitives
import goal_runtime
import validate_evidence_v3


POLICY = "zero-spend-unless-user-first-requests-specific-paid-action"


def command(
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
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


def make_project(base: Path, *, use_git: bool = False) -> Path:
    root = base / "project"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "app.txt").write_text("base\n", encoding="utf-8")
    if use_git:
        git(root, "init")
        git(root, "config", "user.name", "Fixture")
        git(root, "config", "user.email", "fixture@example.invalid")
        git(root, "add", ".")
        git(root, "commit", "-m", "baseline")
    return root


def write_json(path: Path, value: object) -> Path:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return path


def later_than(value: str, *, minutes: int = 1) -> str:
    parsed = goal_ledger.parse_time(value)
    if parsed is None:
        raise AssertionError(f"invalid fixture timestamp: {value}")
    return (
        (parsed + timedelta(minutes=minutes))
        .isoformat()
        .replace("+00:00", "Z")
    )


def initialize(
    base: Path,
    root: Path,
    *,
    assurance: str = "standard",
    delivery: str | None = None,
    capabilities: list[str] | None = None,
    state_dir: Path | None = None,
    use_default_state: bool = False,
) -> tuple[Path, dict[str, object]]:
    acceptance = write_json(
        base / "acceptance.json",
        {
            "acceptance": [
                {"id": "a1", "text": "The behavior is directly verified."}
            ]
        },
    )
    plan = base / "plan.md"
    plan.write_text("# Reviewed plan\n", encoding="utf-8")
    selected_state = state_dir or (base / "state")
    arguments = [
        "init",
        "--root",
        str(root),
        "--goal-id",
        "goal-sample",
        "--host-goal-id",
        "host-goal-sample",
        "--project-id",
        "sample",
        "--objective",
        "Deliver the requested behavior.",
        "--acceptance",
        str(acceptance),
        "--assurance",
        assurance,
        "--activation-reason",
        "recovery",
    ]
    if not use_default_state:
        arguments.extend(["--state-dir", str(selected_state)])
    if assurance in {"strict", "release"}:
        arguments.extend(["--plan", str(plan)])
    if delivery is not None:
        arguments.extend(["--delivery", delivery])
    for capability in capabilities or []:
        arguments.extend(["--require-capability", capability])
    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(base / "codex-home")
    completed = command(*arguments, env=environment)
    if completed.returncode:
        raise AssertionError(completed.stdout + completed.stderr)
    payload = json.loads(completed.stdout)
    actual_state = Path(payload["result"]["state_dir"])
    return actual_state, json.loads(
        (actual_state / goal_ledger.STATE_NAME).read_text(encoding="utf-8")
    )


def current_snapshot(root: Path, state_dir: Path) -> dict[str, object]:
    return goal_ledger.workspace_snapshot(root, state_dir)


def story_snapshot(
    root: Path,
    state_dir: Path,
    write_scope: list[str],
    protected_scope: list[str],
) -> dict[str, object]:
    state = json.loads(
        (state_dir / goal_ledger.STATE_NAME).read_text(encoding="utf-8")
    )
    return goal_ledger.workspace_snapshot(
        root,
        state_dir,
        [
            *goal_ledger.workspace_patterns(state),
            *write_scope,
            *protected_scope,
        ],
    )


def review_receipt(
    state: dict[str, object],
    workspace_sha256: str,
    role: str,
    review_id: str,
    *,
    status: str = "passed",
    acceptance_ids: list[str] | None = None,
    evidence_candidate_sha256: str | None = None,
    review_scope: dict[str, object] | None = None,
    carry_forward_from_receipt_sha256: str | None = None,
    findings: list[dict[str, object]] | None = None,
    checked_at: str = "2026-07-27T00:10:00Z",
) -> dict[str, object]:
    value: dict[str, object] = {
        "document_type": "quant_review_receipt",
        "schema_version": 1,
        "goal_id": state["goal_id"],
        "review_id": review_id,
        "role": role,
        "status": status,
        "plan_revision": goal_ledger.current_plan_revision(state),
        "acceptance_revision": state["acceptance_revision"],
        "acceptance_ids": (
            acceptance_ids
            if acceptance_ids is not None
            else [item["id"] for item in state["acceptance"]]
        ),
        "workspace_sha256": workspace_sha256,
        "review_scope": (
            review_scope
            if review_scope is not None
            else {
                "patterns": [],
                "sha256": goal_primitives.digest(
                    {"patterns": [], "paths": {}}
                ),
            }
        ),
        "summary": "The frozen snapshot was independently reviewed.",
        "findings": findings or [],
        "checked_at": checked_at,
    }
    if evidence_candidate_sha256 is not None:
        value["evidence_candidate_sha256"] = (
            evidence_candidate_sha256
        )
    if carry_forward_from_receipt_sha256 is not None:
        value["carry_forward_from_receipt_sha256"] = (
            carry_forward_from_receipt_sha256
        )
    value["receipt_sha256"] = goal_ledger.review_receipt_hash(value)
    return value


def record_review(
    base: Path,
    root: Path,
    state_dir: Path,
    role: str,
    review_id: str,
    *,
    acceptance_ids: list[str] | None = None,
    status: str = "passed",
    scope_patterns: list[str] | None = None,
    carry_forward_from_receipt_sha256: str | None = None,
    findings: list[dict[str, object]] | None = None,
) -> subprocess.CompletedProcess[str]:
    state = json.loads(
        (state_dir / goal_ledger.STATE_NAME).read_text(encoding="utf-8")
    )
    snapshot = current_snapshot(root, state_dir)
    candidate_path: Path | None = None
    candidate_sha256: str | None = None
    if role == "terminal_critic":
        candidate = evidence_receipt(root, state_dir)
        candidate["completed_at"] = "2026-07-27T00:25:00Z"
        candidate_path = write_json(
            base / f"{review_id}-candidate.json",
            candidate,
        )
        candidate_sha256 = (
            goal_ledger.completion_evidence_candidate_sha256(
                candidate,
                state,
                snapshot,
            )
        )
    receipt = write_json(
        base / f"{review_id}.json",
        review_receipt(
            state,
            snapshot["sha256"],
            role,
            review_id,
            status=status,
            acceptance_ids=acceptance_ids,
            evidence_candidate_sha256=candidate_sha256,
            review_scope=goal_ledger.review_scope_binding(
                root,
                state_dir,
                (
                    []
                    if role == "terminal_critic"
                    else (
                        scope_patterns
                        if scope_patterns is not None
                        else ["src/**"]
                    )
                ),
            ),
            carry_forward_from_receipt_sha256=(
                carry_forward_from_receipt_sha256
            ),
            findings=findings,
            checked_at=(
                "2026-07-27T00:27:00Z"
                if role == "terminal_critic"
                else "2026-07-27T00:10:00Z"
            ),
        ),
    )
    arguments = [
        "review-record",
        "--root",
        str(root),
        "--state-dir",
        str(state_dir),
        "--review",
        str(receipt),
    ]
    if candidate_path is not None:
        arguments.extend(
            ["--evidence-candidate", str(candidate_path)]
        )
    return command(*arguments)


def evidence_receipt(
    root: Path,
    state_dir: Path,
) -> dict[str, object]:
    state = json.loads(
        (state_dir / goal_ledger.STATE_NAME).read_text(encoding="utf-8")
    )
    events, errors = goal_ledger.read_ledger(
        state_dir / goal_ledger.LEDGER_NAME
    )
    if errors:
        raise AssertionError(errors)
    snapshot = current_snapshot(root, state_dir)
    review_map = goal_ledger.current_review_map(
        state, snapshot["sha256"]
    )
    gates: dict[str, object] = {}
    for gate_name in state["proof_policy"]["required_gates"]:
        review = review_map.get(gate_name)
        checked_at = (
            review["recorded_at"]
            if isinstance(review, dict)
            else "2026-07-27T00:20:00Z"
        )
        ledger_extension: dict[str, object] = {
            "goal_id": state["goal_id"],
            "workspace_sha256": snapshot["sha256"],
            "plan_revision": goal_ledger.current_plan_revision(state),
            "acceptance_revision": state["acceptance_revision"],
        }
        if isinstance(review, dict):
            ledger_extension["review_receipt_sha256"] = review[
                "receipt_sha256"
            ]
        evidence = {
            "kind": "inspection",
            "status": "verified",
            "summary": f"{gate_name} was verified for the frozen snapshot.",
            "source": "deterministic Goal ledger fixture",
            "checked_at": checked_at,
            "extensions": {"goal_ledger": ledger_extension},
        }
        gates[gate_name] = {"status": "passed", "evidence": [evidence]}
    acceptance_claims = {}
    verification = gates["verification"]["evidence"][0]
    for item in state["acceptance"]:
        acceptance_claims[item["id"]] = [
            {
                "gate": "verification",
                "evidence_index": 0,
                "evidence_sha256": validate_evidence_v3.canonical_sha256(
                    verification
                ),
            }
        ]
    plan = state.get("plan")
    return {
        "schema_version": 3,
        "project_id": state["project_id"],
        "objective": state["objective"],
        "scope": {
            "capabilities": state["proof_policy"][
                "required_capabilities"
            ],
            "assurance": state["assurance"],
            "delivery": goal_ledger.goal_delivery(state),
            "remote_actions": (
                goal_ledger.goal_delivery(state) == "release"
            ),
            "analysis_control_ids": [],
        },
        "required_gates": state["proof_policy"]["required_gates"],
        "gates": gates,
        "cost_authority": {
            "policy": POLICY,
            "classification": "no_billable_action",
            "decision": "allow",
            "paid_action_requested": False,
            "actions": [],
        },
        "context": {
            "manifest_sha256": "",
            "plan_sha256": (
                plan["sha256"] if isinstance(plan, dict) else ""
            ),
            "base_commit": events[0]["workspace"].get("head") or "",
            "head_commit": snapshot.get("head") or "",
        },
        "goal_binding": {
            "goal_id": state["goal_id"],
            "objective_sha256": state["objective_sha256"],
            "ledger_tail_sha256": state["ledger"]["tail_sha256"],
            "acceptance_ids": [
                item["id"] for item in state["acceptance"]
            ],
            "acceptance_claims": acceptance_claims,
        },
        "completed_at": "2026-07-27T00:30:00Z",
    }


class GoalLedgerTests(unittest.TestCase):
    def test_checkpoint_proof_prose_rejects_paid_data_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(base, root)
            artifact = {
                "kind": "implementation",
                "summary": "Downloaded premium price data.",
                "acceptance_status": {
                    "a1": {
                        "status": "partial",
                        "evidence_refs": ["inspection"],
                    }
                },
                "blockers": [],
                "next_action": "Continue local verification.",
            }
            checkpoint = write_json(base / "checkpoint.json", artifact)
            blocked = command(
                "checkpoint",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--checkpoint",
                str(checkpoint),
            )
            artifact["summary"] = "Paid data was not used."
            checkpoint = write_json(base / "safe-checkpoint.json", artifact)
            safe = command(
                "checkpoint",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--checkpoint",
                str(checkpoint),
            )
            workspace_sha256 = current_snapshot(root, state_dir)["sha256"]
            reported = {
                "kind": "implementation",
                "summary": "The implementation uses paid data.",
                "acceptance_status": {
                    "a1": {
                        "status": "partial",
                        "evidence_refs": ["inspection"],
                    }
                },
                "blockers": [],
                "next_action": "Replace the paid data source with a free source.",
            }
            goal_ledger.validate_checkpoint(
                reported,
                state,
                workspace_sha256,
            )
            reported["acceptance_status"]["a1"]["status"] = "passed"
            with self.assertRaisesRegex(
                ValueError, "paid data acquisition"
            ):
                goal_ledger.validate_checkpoint(
                    reported,
                    state,
                    workspace_sha256,
                )
            reported["acceptance_status"]["a1"]["status"] = "partial"
            reported["next_action"] = "Use a paid data API next."
            with self.assertRaisesRegex(
                ValueError, "paid data acquisition"
            ):
                goal_ledger.validate_checkpoint(
                    reported,
                    state,
                    workspace_sha256,
                )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("paid data acquisition", blocked.stdout)
        self.assertEqual(safe.returncode, 0, safe.stdout + safe.stderr)

    def test_standard_release_delivery_keeps_standard_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(
                base,
                root,
                assurance="standard",
                delivery="release",
                capabilities=["remote-release"],
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(state["assurance"], "standard")
        self.assertEqual(state["delivery"], "release")
        self.assertEqual(
            state["proof_policy"]["required_review_roles"],
            ["integration_review"],
        )
        self.assertIn(
            "release", state["proof_policy"]["required_gates"]
        )
        self.assertNotIn(
            "independent_reaudit",
            state["proof_policy"]["required_gates"],
        )

    def test_plan_artifact_policy_blocks_secret_paid_and_binary_copy(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            state_dir = base / "state"
            state_dir.mkdir()
            credential_fixture = (
                "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
            )
            fixtures = {
                "secret.md": (
                    f"API key: {credential_fixture}\n"
                ).encode(),
                "paid.md": (
                    "The user approved the paid plan upgrade.\n"
                ).encode(),
                "paid-data.md": (
                    "Use a paid market data provider subscription.\n"
                ).encode(),
                "binary.pdf": b"%PDF-\xff\x00",
                "duplicate.json": (
                    '{"section": 1, "section": 2}\n'
                ).encode(),
            }
            for name, content in fixtures.items():
                with self.subTest(name=name):
                    source = base / name
                    source.write_bytes(content)
                    with self.assertRaises(ValueError):
                        goal_ledger.plan_binding(
                            state_dir,
                            source,
                            revision=1,
                            acceptance_revision=1,
                            recorded_at="2026-07-27T00:00:00Z",
                        )
            safe = base / "safe.md"
            safe.write_text(
                "Paid actions require separate user approval.\n",
                encoding="utf-8",
            )
            binding = goal_ledger.plan_binding(
                state_dir,
                safe,
                revision=1,
                acceptance_revision=1,
                recorded_at="2026-07-27T00:00:00Z",
            )
            suffix, content = goal_ledger.validated_plan_artifact(
                ROOT
                / "shared"
                / "templates"
                / "approved-plan.example.md"
            )

        self.assertEqual(binding["artifact_path"], "plans/plan-r1.md")
        self.assertEqual(suffix, ".md")
        self.assertIn(
            b"Paid data: permanently prohibited", content
        )

    def test_non_git_strict_default_state_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(
                base,
                root,
                assurance="strict",
                use_default_state=True,
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(state["document_type"], "quant_goal_ledger_state")
        self.assertEqual(state["assurance"], "strict")
        self.assertEqual(state["ledger"]["event_count"], 2)
        self.assertIn("quant-goals", state_dir.as_posix())

    def test_typed_steering_operations_explain_acceptance_changes(self) -> None:
        cases = (
            (
                [{"id": "a", "text": "Before."}],
                [{"id": "a", "text": "After."}],
                [{"op": "clarify", "source_ids": ["a"], "target_ids": ["a"]}],
            ),
            (
                [{"id": "a", "text": "Keep."}],
                [
                    {"id": "a", "text": "Keep."},
                    {"id": "b", "text": "Added."},
                ],
                [{"op": "add", "source_ids": [], "target_ids": ["b"]}],
            ),
            (
                [
                    {"id": "a", "text": "Keep."},
                    {"id": "b", "text": "Retire."},
                ],
                [{"id": "a", "text": "Keep."}],
                [{"op": "retire", "source_ids": ["b"], "target_ids": []}],
            ),
            (
                [{"id": "a", "text": "Broad."}],
                [
                    {"id": "a1", "text": "First."},
                    {"id": "a2", "text": "Second."},
                ],
                [
                    {
                        "op": "split",
                        "source_ids": ["a"],
                        "target_ids": ["a1", "a2"],
                    }
                ],
            ),
            (
                [
                    {"id": "a", "text": "First."},
                    {"id": "b", "text": "Second."},
                ],
                [{"id": "ab", "text": "Combined."}],
                [
                    {
                        "op": "merge",
                        "source_ids": ["a", "b"],
                        "target_ids": ["ab"],
                    }
                ],
            ),
            (
                [{"id": "a", "text": "Old."}],
                [{"id": "b", "text": "New."}],
                [
                    {
                        "op": "replace",
                        "source_ids": ["a"],
                        "target_ids": ["b"],
                    }
                ],
            ),
            (
                [
                    {"id": "a", "text": "First."},
                    {"id": "b", "text": "Second."},
                    {"id": "c", "text": "Third."},
                ],
                [
                    {"id": "c", "text": "Third."},
                    {"id": "a", "text": "First."},
                    {"id": "b", "text": "Second."},
                ],
                [
                    {
                        "op": "reorder",
                        "source_ids": ["a", "b", "c"],
                        "target_ids": ["c", "a", "b"],
                    }
                ],
            ),
        )
        for previous, current, steering in cases:
            with self.subTest(op=steering[0]["op"]):
                self.assertEqual(
                    goal_ledger.validate_steering(
                        steering,
                        previous,
                        current,
                    ),
                    steering,
                )

    def test_typed_steering_rejects_unexplained_or_forged_changes(self) -> None:
        previous = [
            {"id": "a", "text": "Before."},
            {"id": "b", "text": "Keep."},
        ]
        current = [
            {"id": "a", "text": "After."},
            {"id": "b", "text": "Keep."},
            {"id": "c", "text": "Added."},
        ]
        invalid = (
            [{"op": "add", "source_ids": [], "target_ids": ["c"]}],
            [{"op": "clarify", "source_ids": ["x"], "target_ids": ["x"]}],
            [
                {
                    "op": "replace",
                    "source_ids": ["a"],
                    "target_ids": ["c"],
                }
            ],
            [{"op": "unknown", "source_ids": [], "target_ids": ["c"]}],
            [{"op": [], "source_ids": [], "target_ids": ["c"]}],
        )
        for steering in invalid:
            with self.subTest(steering=steering):
                with self.assertRaises(ValueError):
                    goal_ledger.validate_steering(
                        steering,
                        previous,
                        current,
                    )

    def test_typed_steering_rejects_overlapping_change_accounting(self) -> None:
        previous = [
            {"id": "a", "text": "First."},
            {"id": "b", "text": "Second."},
        ]
        current = [{"id": "c", "text": "Combined."}]
        steering = [
            {
                "op": "merge",
                "source_ids": ["a", "b"],
                "target_ids": ["c"],
            },
            {
                "op": "replace",
                "source_ids": ["a"],
                "target_ids": ["c"],
            },
        ]
        with self.assertRaisesRegex(ValueError, "more than once"):
            goal_ledger.validate_steering(steering, previous, current)

    def test_non_string_steering_op_returns_stable_cli_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            revision = write_json(
                base / "invalid-op.json",
                {
                    "reason": "Reject a malformed operation type.",
                    "acceptance": [
                        {"id": "a1", "text": "The revised result is verified."}
                    ],
                    "steering": [
                        {
                            "op": [],
                            "source_ids": ["a1"],
                            "target_ids": ["a1"],
                        }
                    ],
                },
            )
            revised = command(
                "revise-acceptance",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--revision",
                str(revision),
            )
        self.assertNotEqual(revised.returncode, 0)
        payload = json.loads(revised.stdout)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("unknown steering operation", payload["issues"][0])

    def test_resume_continuation_is_derived_and_healthy_resume_is_byte_stable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            checkpoint = write_json(
                base / "checkpoint.json",
                {
                    "kind": "implementation",
                    "summary": "Record resumable progress.",
                    "acceptance_status": {
                        "a1": {
                            "status": "partial",
                            "evidence_refs": ["local-check"],
                        }
                    },
                    "blockers": [
                        {
                            "id": "needs-input",
                            "status": "open",
                            "required": True,
                            "summary": "A material input is pending.",
                            "next_action": "Obtain the missing input.",
                        }
                    ],
                    "next_action": "Obtain the missing input.",
                },
            )
            recorded = command(
                "checkpoint",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--checkpoint",
                str(checkpoint),
            )
            self.assertEqual(recorded.returncode, 0, recorded.stdout)
            state_path = state_dir / goal_ledger.STATE_NAME
            ledger_path = state_dir / goal_ledger.LEDGER_NAME
            before = (state_path.read_bytes(), ledger_path.read_bytes())
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            after = (state_path.read_bytes(), ledger_path.read_bytes())
        self.assertEqual(resumed.returncode, 0, resumed.stdout)
        self.assertEqual(before, after)
        result = json.loads(resumed.stdout)["result"]
        continuation = result["continuation"]
        self.assertEqual(continuation["checkpoint"]["kind"], "implementation")
        self.assertEqual(
            continuation["next_action"],
            "Obtain the missing input.",
        )
        self.assertEqual(
            continuation["current_blockers"][0]["id"],
            "needs-input",
        )
        self.assertEqual(
            continuation["stories_by_status"],
            {
                "accepted": [],
                "open": [],
                "returned": [],
                "superseded": [],
            },
        )
        self.assertFalse(continuation["workspace_drift"])
        self.assertEqual(
            continuation["authority"],
            {"status": "not_recorded"},
        )
        self.assertEqual(
            continuation["ledger"]["tail_sha256"],
            result["ledger_tail_sha256"],
        )
        self.assertEqual(
            continuation["workspace"]["current_sha256"],
            result["workspace_sha256"],
        )

    def test_resume_continuation_reports_workspace_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            state_path = state_dir / goal_ledger.STATE_NAME
            ledger_path = state_dir / goal_ledger.LEDGER_NAME
            before = (state_path.read_bytes(), ledger_path.read_bytes())
            (root / "src" / "app.txt").write_text(
                "changed\n",
                encoding="utf-8",
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            after = (state_path.read_bytes(), ledger_path.read_bytes())
        self.assertEqual(resumed.returncode, 2, resumed.stdout)
        self.assertEqual(before, after)
        result = json.loads(resumed.stdout)["result"]
        self.assertTrue(result["workspace_drift"])
        self.assertTrue(result["continuation"]["workspace_drift"])
        self.assertNotEqual(
            result["continuation"]["workspace"]["current_sha256"],
            result["continuation"]["workspace"]["last_event_sha256"],
        )

    def test_non_git_snapshot_tracks_directory_symlink_and_file_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir = base / "state"
            initial = current_snapshot(root, state_dir)
            target = base / "target"
            target.mkdir()
            link = root / "linked-directory"
            link.symlink_to(target, target_is_directory=True)
            linked = current_snapshot(root, state_dir)
            script = root / "run.sh"
            script.write_text("#!/bin/sh\n", encoding="utf-8")
            script.chmod(0o644)
            non_executable = current_snapshot(root, state_dir)
            script.chmod(0o755)
            executable = current_snapshot(root, state_dir)
        self.assertNotEqual(initial["sha256"], linked["sha256"])
        self.assertEqual(
            linked["paths"]["linked-directory"]["kind"], "symlink"
        )
        self.assertNotEqual(
            non_executable["sha256"], executable["sha256"]
        )
        self.assertEqual(executable["paths"]["run.sh"]["mode"], 0o755)

    def test_acceptance_and_plan_revisions_are_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base, root, assurance="strict"
            )
            revision = write_json(
                base / "revision.json",
                {
                    "reason": "Clarify the same objective.",
                    "acceptance": [
                        {
                            "id": "a1",
                            "text": "The behavior is verified twice.",
                        },
                        {
                            "id": "a2",
                            "text": "The evidence remains reproducible.",
                        },
                    ],
                    "steering": [
                        {
                            "op": "clarify",
                            "source_ids": ["a1"],
                            "target_ids": ["a1"],
                        },
                        {
                            "op": "add",
                            "source_ids": [],
                            "target_ids": ["a2"],
                        },
                    ],
                },
            )
            revised_plan = base / "plan-r2.md"
            revised_plan.write_text("# Reviewed plan revision 2\n", encoding="utf-8")
            revised = command(
                "revise-acceptance",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--revision",
                str(revision),
                "--plan",
                str(revised_plan),
            )
            replayed = command(
                "revise-acceptance",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--revision",
                str(revision),
                "--plan",
                str(revised_plan),
            )
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(encoding="utf-8")
            )
            events, errors = goal_ledger.read_ledger(
                state_dir / goal_ledger.LEDGER_NAME
            )
        self.assertEqual(revised.returncode, 0, revised.stdout + revised.stderr)
        self.assertEqual(
            replayed.returncode,
            0,
            replayed.stdout + replayed.stderr,
        )
        self.assertEqual(errors, [])
        self.assertEqual(state["acceptance_revision"], 2)
        self.assertEqual(len(state["acceptance_revisions"]), 2)
        self.assertNotIn("steering", state["acceptance_revisions"][0])
        latest_revision = state["acceptance_revisions"][1]
        self.assertEqual(
            [item["op"] for item in latest_revision["steering"]],
            ["clarify", "add"],
        )
        self.assertEqual(
            latest_revision["sha256"],
            goal_ledger.digest(
                {
                    key: value
                    for key, value in latest_revision.items()
                    if key != "sha256"
                }
            ),
        )
        self.assertEqual(goal_ledger.current_plan_revision(state), 2)
        self.assertEqual(
            [event["type"] for event in events][-2:],
            ["acceptance_revised", "plan_bound"],
        )
        self.assertEqual(
            [event["type"] for event in events].count("acceptance_revised"),
            1,
        )
        self.assertEqual(state["plan"]["acceptance_revision"], 2)

    def test_invalid_strict_plan_does_not_leave_goal_genesis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            acceptance = write_json(
                base / "acceptance.json",
                {
                    "acceptance": [
                        {"id": "a1", "text": "The result is verified."}
                    ]
                },
            )
            state_dir = base / "state"
            initialized = command(
                "init",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--goal-id",
                "goal-invalid-plan",
                "--host-goal-id",
                "host-goal-invalid-plan",
                "--project-id",
                "sample",
                "--objective",
                "Reject partial strict initialization.",
                "--acceptance",
                str(acceptance),
                "--assurance",
                "strict",
                "--plan",
                str(base / "missing-plan.md"),
            )
        self.assertNotEqual(initialized.returncode, 0)
        self.assertIn("plan artifact must be a regular file", initialized.stdout)
        self.assertFalse((state_dir / goal_ledger.STATE_NAME).exists())
        self.assertFalse((state_dir / goal_ledger.LEDGER_NAME).exists())

    def test_acceptance_plan_retry_is_idempotent_after_preflight_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base, root, assurance="strict"
            )
            revision = write_json(
                base / "retry-revision.json",
                {
                    "reason": "Clarify the same objective once.",
                    "acceptance": [
                        {"id": "a1", "text": "The retry stays idempotent."}
                    ],
                },
            )
            plan = base / "retry-plan.md"
            failed = command(
                "revise-acceptance",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--revision",
                str(revision),
                "--plan",
                str(plan),
            )
            after_failure = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            plan.write_text("# Reviewed retry plan\n", encoding="utf-8")
            first = command(
                "revise-acceptance",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--revision",
                str(revision),
                "--plan",
                str(plan),
            )
            second = command(
                "revise-acceptance",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--revision",
                str(revision),
                "--plan",
                str(plan),
            )
            final_state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            events, errors = goal_ledger.read_ledger(
                state_dir / goal_ledger.LEDGER_NAME
            )
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(after_failure["acceptance_revision"], 1)
        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertEqual(errors, [])
        self.assertEqual(final_state["acceptance_revision"], 2)
        self.assertEqual(goal_ledger.current_plan_revision(final_state), 2)
        self.assertEqual(
            [event["type"] for event in events].count("acceptance_revised"),
            1,
        )
        self.assertEqual(
            [event["type"] for event in events].count("plan_bound"),
            2,
        )

    def test_story_return_accept_and_story_reuse_are_guarded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(base, root)
            snapshot = story_snapshot(root, state_dir, ["src/**"], [])
            envelope: dict[str, object] = {
                "document_type": "quant_story_envelope",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-change",
                "project_binding_sha256": state["project_binding"][
                    "identity_sha256"
                ],
                "objective": "Change the bounded source.",
                "mode": "write",
                "write_scope": ["src/**"],
                "protected_scope": [],
                "depends_on": [],
                "acceptance": state["acceptance"],
                "external_effects": "none",
                "cost_class": "no_billable_action",
                "baseline_workspace_sha256": snapshot["sha256"],
                "issued_at": "2026-07-27T00:00:00Z",
            }
            envelope["envelope_sha256"] = goal_runtime.envelope_hash(envelope)
            envelope_path = write_json(base / "envelope.json", envelope)
            issued = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            self.assertEqual(issued.returncode, 0, issued.stdout + issued.stderr)
            (root / "src" / "app.txt").write_text(
                "changed\n", encoding="utf-8"
            )
            current = current_snapshot(root, state_dir)
            baseline = json.loads(
                (
                    state_dir / "stories" / "story-change.baseline.json"
                ).read_text(encoding="utf-8")
            )
            receipt: dict[str, object] = {
                "document_type": "quant_story_receipt",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-change",
                "envelope_sha256": envelope["envelope_sha256"],
                "status": "ready_for_review",
                "summary": "The bounded change was verified.",
                "changed_paths": goal_runtime.changed_since(baseline, current),
                "claims": [
                    {
                        "acceptance_id": "a1",
                        "status": "passed",
                        "evidence_ids": ["e1"],
                    }
                ],
                "evidence": [
                    {
                        "id": "e1",
                        "kind": "inspection",
                        "status": "passed",
                        "summary": "The changed source was inspected.",
                    }
                ],
                "workspace_sha256": current["sha256"],
                "completed_at": "2026-07-27T00:05:00Z",
            }
            receipt["receipt_sha256"] = goal_runtime.receipt_hash(receipt)
            receipt_path = write_json(base / "story-receipt.json", receipt)
            returned = command(
                "story-return",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            self.assertEqual(
                returned.returncode, 0, returned.stdout + returned.stderr
            )
            (root / "src" / "app.txt").write_text(
                "changed again\n", encoding="utf-8"
            )
            current = current_snapshot(root, state_dir)
            receipt["summary"] = "The repaired delivery was verified."
            receipt["changed_paths"] = goal_runtime.changed_since(
                baseline, current
            )
            receipt["workspace_sha256"] = current["sha256"]
            receipt["completed_at"] = "2026-07-27T00:06:00Z"
            receipt["receipt_sha256"] = goal_runtime.receipt_hash(receipt)
            second_receipt_path = write_json(
                base / "story-receipt-r2.json", receipt
            )
            returned_again = command(
                "story-return",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(second_receipt_path),
            )
            accepted = command(
                "story-accept",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--story-id",
                "story-change",
            )
            reused = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            first_stored = (
                state_dir
                / "receipts"
                / "stories"
                / "story-change-r1.json"
            )
            first_value = json.loads(
                first_stored.read_text(encoding="utf-8")
            )
            first_value["summary"] = "rewritten old return"
            write_json(first_stored, first_value)
            rewritten = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertEqual(
            returned_again.returncode,
            0,
            returned_again.stdout + returned_again.stderr,
        )
        self.assertEqual(
            json.loads(returned_again.stdout)["result"]["return_count"],
            2,
        )
        self.assertEqual(
            accepted.returncode, 0, accepted.stdout + accepted.stderr
        )
        self.assertNotEqual(reused.returncode, 0)
        self.assertIn("cannot be reused", reused.stdout)
        self.assertNotEqual(rewritten.returncode, 0)
        self.assertIn("receipt is not ledger-bound", rewritten.stdout)

    def test_recursive_write_scope_accepts_a_new_tree_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(base, root)
            snapshot = story_snapshot(
                root,
                state_dir,
                ["generated/**"],
                [],
            )
            envelope: dict[str, object] = {
                "document_type": "quant_story_envelope",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-generated-tree",
                "project_binding_sha256": state["project_binding"][
                    "identity_sha256"
                ],
                "objective": "Create the bounded generated tree.",
                "mode": "write",
                "write_scope": ["generated/**"],
                "protected_scope": [],
                "depends_on": [],
                "acceptance": state["acceptance"],
                "external_effects": "none",
                "cost_class": "no_billable_action",
                "baseline_workspace_sha256": snapshot["sha256"],
                "issued_at": "2026-07-27T00:00:00Z",
            }
            envelope["envelope_sha256"] = goal_runtime.envelope_hash(envelope)
            envelope_path = write_json(
                base / "generated-envelope.json", envelope
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
            self.assertEqual(issued.returncode, 0, issued.stdout + issued.stderr)
            generated = root / "generated"
            generated.mkdir()
            (generated / "out.txt").write_text("result\n", encoding="utf-8")
            current = current_snapshot(root, state_dir)
            baseline = json.loads(
                (
                    state_dir
                    / "stories"
                    / "story-generated-tree.baseline.json"
                ).read_text(encoding="utf-8")
            )
            changed_paths = goal_runtime.changed_since(baseline, current)
            receipt: dict[str, object] = {
                "document_type": "quant_story_receipt",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-generated-tree",
                "envelope_sha256": envelope["envelope_sha256"],
                "status": "ready_for_review",
                "summary": "The generated tree was directly verified.",
                "changed_paths": changed_paths,
                "claims": [
                    {
                        "acceptance_id": "a1",
                        "status": "passed",
                        "evidence_ids": ["e1"],
                    }
                ],
                "evidence": [
                    {
                        "id": "e1",
                        "kind": "inspection",
                        "status": "passed",
                        "summary": "The generated result was inspected.",
                    }
                ],
                "workspace_sha256": current["sha256"],
                "completed_at": "2026-07-27T00:05:00Z",
            }
            receipt["receipt_sha256"] = goal_runtime.receipt_hash(receipt)
            receipt_path = write_json(
                base / "generated-story-receipt.json", receipt
            )
            returned = command(
                "story-return",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertEqual(
            changed_paths, ["generated", "generated/out.txt"]
        )
        self.assertEqual(
            returned.returncode, 0, returned.stdout + returned.stderr
        )

    def test_companion_ledger_keeps_one_active_write_story(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)

            def make_envelope(
                story_id: str,
                write_scope: list[str],
            ) -> Path:
                current_state = json.loads(
                    (state_dir / goal_ledger.STATE_NAME).read_text(
                        encoding="utf-8"
                    )
                )
                snapshot = story_snapshot(
                    root,
                    state_dir,
                    write_scope,
                    [],
                )
                envelope: dict[str, object] = {
                    "document_type": "quant_story_envelope",
                    "schema_version": 1,
                    "goal_id": current_state["goal_id"],
                    "story_id": story_id,
                    "project_binding_sha256": current_state[
                        "project_binding"
                    ]["identity_sha256"],
                    "objective": "Deliver one bounded write Story.",
                    "mode": "write",
                    "write_scope": write_scope,
                    "protected_scope": [],
                    "depends_on": [],
                    "acceptance": current_state["acceptance"],
                    "external_effects": "none",
                    "cost_class": "no_billable_action",
                    "baseline_workspace_sha256": snapshot["sha256"],
                    "issued_at": "2026-07-27T00:00:00Z",
                }
                envelope["envelope_sha256"] = goal_runtime.envelope_hash(
                    envelope
                )
                return write_json(base / f"{story_id}.json", envelope)

            first_envelope = make_envelope("story-first", ["src/**"])
            first = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(first_envelope),
            )
            self.assertEqual(first.returncode, 0, first.stdout)
            second_envelope = make_envelope("story-second", ["docs/**"])
            second = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(second_envelope),
            )
        self.assertNotEqual(second.returncode, 0)
        self.assertIn(
            "workspace already has a write-story owner",
            second.stdout,
        )

    def test_gitignored_story_deliverable_stays_in_workspace_identity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base, use_git=True)
            (root / ".gitignore").write_text("dist/\n", encoding="utf-8")
            git(root, "add", ".gitignore")
            git(root, "commit", "-m", "ignore generated delivery")
            state_dir, state = initialize(base, root)
            snapshot = story_snapshot(root, state_dir, ["dist/**"], [])
            envelope: dict[str, object] = {
                "document_type": "quant_story_envelope",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-ignored-output",
                "project_binding_sha256": state["project_binding"][
                    "identity_sha256"
                ],
                "objective": "Create the ignored bounded output.",
                "mode": "write",
                "write_scope": ["dist/**"],
                "protected_scope": [],
                "depends_on": [],
                "acceptance": state["acceptance"],
                "external_effects": "none",
                "cost_class": "no_billable_action",
                "baseline_workspace_sha256": snapshot["sha256"],
                "issued_at": "2026-07-27T00:00:00Z",
            }
            envelope["envelope_sha256"] = goal_runtime.envelope_hash(envelope)
            envelope_path = write_json(
                base / "ignored-envelope.json", envelope
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
            issued_state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            stored_baseline = json.loads(
                (
                    state_dir
                    / "stories"
                    / "story-ignored-output.baseline.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                envelope["baseline_workspace_sha256"],
                stored_baseline["sha256"],
            )
            self.assertEqual(
                envelope["baseline_workspace_sha256"],
                issued_state["stories"]["story-ignored-output"][
                    "baseline_workspace_sha256"
                ],
            )
            output = root / "dist" / "out.json"
            output.parent.mkdir()
            output.write_text('{"value": 1}\n', encoding="utf-8")
            first = current_snapshot(root, state_dir)
            baseline = json.loads(
                (
                    state_dir
                    / "stories"
                    / "story-ignored-output.baseline.json"
                ).read_text(encoding="utf-8")
            )
            receipt: dict[str, object] = {
                "document_type": "quant_story_receipt",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-ignored-output",
                "envelope_sha256": envelope["envelope_sha256"],
                "status": "ready_for_review",
                "summary": "The ignored output was directly verified.",
                "changed_paths": goal_runtime.changed_since(
                    baseline, first, root
                ),
                "claims": [
                    {
                        "acceptance_id": "a1",
                        "status": "passed",
                        "evidence_ids": ["e1"],
                    }
                ],
                "evidence": [
                    {
                        "id": "e1",
                        "kind": "inspection",
                        "status": "passed",
                        "summary": "The ignored JSON was inspected.",
                    }
                ],
                "workspace_sha256": first["sha256"],
                "completed_at": "2026-07-27T00:05:00Z",
            }
            receipt["receipt_sha256"] = goal_runtime.receipt_hash(receipt)
            receipt_path = write_json(base / "ignored-receipt.json", receipt)
            returned = command(
                "story-return",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            output.write_text('{"value": 2}\n', encoding="utf-8")
            second = current_snapshot(root, state_dir)
        self.assertEqual(returned.returncode, 0, returned.stdout)
        self.assertIn("dist/out.json", first["protected_paths"])
        self.assertNotEqual(first["sha256"], second["sha256"])

    def test_acceptance_revision_supersedes_open_story(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(base, root)
            snapshot = story_snapshot(root, state_dir, ["src/**"], [])
            envelope: dict[str, object] = {
                "document_type": "quant_story_envelope",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-stale-revision",
                "project_binding_sha256": state["project_binding"][
                    "identity_sha256"
                ],
                "objective": "Bind the story to the current revision.",
                "mode": "write",
                "write_scope": ["src/**"],
                "protected_scope": [],
                "depends_on": [],
                "acceptance": state["acceptance"],
                "external_effects": "none",
                "cost_class": "no_billable_action",
                "baseline_workspace_sha256": snapshot["sha256"],
                "issued_at": "2026-07-27T00:00:00Z",
            }
            envelope["envelope_sha256"] = goal_runtime.envelope_hash(envelope)
            envelope_path = write_json(base / "stale-envelope.json", envelope)
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
            revision = write_json(
                base / "story-revision.json",
                {
                    "reason": "Clarify the same objective.",
                    "acceptance": [
                        {"id": "a1", "text": "The revised result is verified."}
                    ],
                    "steering": [
                        {
                            "op": "clarify",
                            "source_ids": ["a1"],
                            "target_ids": ["a1"],
                        }
                    ],
                },
            )
            revised = command(
                "revise-acceptance",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--revision",
                str(revision),
            )
            stale_receipt = write_json(
                base / "stale-receipt.json",
                {"story_id": "story-stale-revision"},
            )
            returned = command(
                "story-return",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(stale_receipt),
            )
            final_state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
        self.assertEqual(revised.returncode, 0, revised.stdout)
        self.assertEqual(
            final_state["stories"]["story-stale-revision"]["status"],
            "superseded",
        )
        self.assertNotEqual(returned.returncode, 0)
        self.assertIn("not open for return", returned.stdout)

    def test_host_story_acceptance_text_must_match_goal_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(base, root)
            snapshot = story_snapshot(root, state_dir, ["src/**"], [])
            weakened = json.loads(json.dumps(state["acceptance"]))
            weakened[0]["text"] = "A weaker substitute."
            envelope: dict[str, object] = {
                "document_type": "quant_story_envelope",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-weakened",
                "project_binding_sha256": state["project_binding"][
                    "identity_sha256"
                ],
                "objective": "Do not weaken acceptance.",
                "mode": "write",
                "write_scope": ["src/**"],
                "protected_scope": [],
                "depends_on": [],
                "acceptance": weakened,
                "external_effects": "none",
                "cost_class": "no_billable_action",
                "baseline_workspace_sha256": snapshot["sha256"],
                "issued_at": "2026-07-27T00:00:00Z",
            }
            envelope["envelope_sha256"] = goal_runtime.envelope_hash(envelope)
            envelope_path = write_json(base / "weakened.json", envelope)
            issued = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            weakened_stored = (
                state_dir / "stories" / "story-weakened.json"
            ).exists()
        self.assertNotEqual(issued.returncode, 0)
        self.assertIn(
            "exactly match current Goal acceptance",
            issued.stdout,
        )
        self.assertFalse(weakened_stored)

    def test_host_story_receipt_rejects_branch_hop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base, use_git=True)
            state_dir, state = initialize(base, root)
            snapshot = story_snapshot(root, state_dir, ["src/**"], [])
            envelope: dict[str, object] = {
                "document_type": "quant_story_envelope",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-branch-hop",
                "project_binding_sha256": state["project_binding"][
                    "identity_sha256"
                ],
                "objective": "Stay on the issued branch.",
                "mode": "write",
                "write_scope": ["src/**"],
                "protected_scope": [],
                "depends_on": [],
                "acceptance": state["acceptance"],
                "external_effects": "none",
                "cost_class": "no_billable_action",
                "baseline_workspace_sha256": snapshot["sha256"],
                "issued_at": "2026-07-27T00:00:00Z",
            }
            envelope["envelope_sha256"] = goal_runtime.envelope_hash(envelope)
            envelope_path = write_json(base / "branch-envelope.json", envelope)
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
            git(root, "switch", "-c", "other-host-story-branch")
            current = current_snapshot(root, state_dir)
            baseline = json.loads(
                (
                    state_dir
                    / "stories"
                    / "story-branch-hop.baseline.json"
                ).read_text(encoding="utf-8")
            )
            receipt: dict[str, object] = {
                "document_type": "quant_story_receipt",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-branch-hop",
                "envelope_sha256": envelope["envelope_sha256"],
                "status": "ready_for_review",
                "summary": "No change was required.",
                "changed_paths": goal_runtime.changed_since(
                    baseline,
                    current,
                    root,
                ),
                "claims": [
                    {
                        "acceptance_id": "a1",
                        "status": "passed",
                        "evidence_ids": ["e1"],
                    }
                ],
                "evidence": [
                    {
                        "id": "e1",
                        "kind": "inspection",
                        "status": "passed",
                        "summary": "The branch was inspected.",
                    }
                ],
                "workspace_sha256": current["sha256"],
                "completed_at": "2026-07-27T00:05:00Z",
            }
            receipt["receipt_sha256"] = goal_runtime.receipt_hash(receipt)
            receipt_path = write_json(base / "branch-receipt.json", receipt)
            returned = command(
                "story-return",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertNotEqual(returned.returncode, 0)
        self.assertIn(
            "workspace branch or project kind changed",
            returned.stdout,
        )

    def test_story_input_cannot_store_unknown_secret_field(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(base, root)
            snapshot = story_snapshot(root, state_dir, ["src/**"], [])
            envelope: dict[str, object] = {
                "document_type": "quant_story_envelope",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-secret",
                "project_binding_sha256": state["project_binding"][
                    "identity_sha256"
                ],
                "objective": "Reject secret-bearing state.",
                "mode": "write",
                "write_scope": ["src/**"],
                "protected_scope": [],
                "depends_on": [],
                "acceptance": state["acceptance"],
                "external_effects": "none",
                "cost_class": "no_billable_action",
                "baseline_workspace_sha256": snapshot["sha256"],
                "issued_at": "2026-07-27T00:00:00Z",
                "api_key": "fixture-credential-value",
            }
            envelope["envelope_sha256"] = goal_runtime.envelope_hash(envelope)
            envelope_path = write_json(base / "secret-envelope.json", envelope)
            issued = command(
                "story-issue",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            secret_stored = (
                state_dir / "stories" / "story-secret.json"
            ).exists()
        self.assertNotEqual(issued.returncode, 0)
        self.assertIn("contains unknown fields", issued.stdout)
        self.assertIn("must not contain a secret value", issued.stdout)
        self.assertFalse(secret_stored)

    def test_strict_reviews_share_snapshot_and_terminal_is_last(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base, root, assurance="strict"
            )
            premature = record_review(
                base,
                root,
                state_dir,
                "terminal_critic",
                "terminal-premature",
            )
            self.assertNotEqual(premature.returncode, 0)
            architect = record_review(
                base,
                root,
                state_dir,
                "architecture_review",
                "architect-1",
            )
            adversarial = record_review(
                base,
                root,
                state_dir,
                "adversarial_qa",
                "adversarial-1",
            )
            terminal = record_review(
                base,
                root,
                state_dir,
                "terminal_critic",
                "terminal-1",
            )
            duplicate = record_review(
                base,
                root,
                state_dir,
                "terminal_critic",
                "terminal-2",
            )
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(encoding="utf-8")
            )
            snapshot = current_snapshot(root, state_dir)
            issues = goal_ledger.completion_context_issues(state, snapshot)
            checkpoint = write_json(
                base / "post-terminal-checkpoint.json",
                {
                    "kind": "evidence",
                    "summary": "Add acceptance evidence after the critic.",
                    "acceptance_status": {
                        "a1": {
                            "status": "passed",
                            "evidence_refs": ["late-evidence"],
                        }
                    },
                    "blockers": [],
                    "next_action": "Refresh the terminal verdict.",
                },
            )
            recorded = command(
                "checkpoint",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--checkpoint",
                str(checkpoint),
            )
            self.assertEqual(recorded.returncode, 0, recorded.stdout)
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            same_snapshot = current_snapshot(root, state_dir)
            late_event_issues = goal_ledger.completion_context_issues(
                state, same_snapshot
            )
            refreshed_terminal = record_review(
                base,
                root,
                state_dir,
                "terminal_critic",
                "terminal-refreshed",
            )
            self.assertEqual(
                refreshed_terminal.returncode,
                0,
                refreshed_terminal.stdout + refreshed_terminal.stderr,
            )
            refreshed_state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            refreshed_issues = goal_ledger.completion_context_issues(
                refreshed_state, same_snapshot
            )
            (root / "src" / "app.txt").write_text(
                "repaired\n", encoding="utf-8"
            )
            changed = current_snapshot(root, state_dir)
            stale_issues = goal_ledger.completion_context_issues(
                refreshed_state, changed
            )
        for completed in (architect, adversarial, terminal):
            self.assertEqual(
                completed.returncode,
                0,
                completed.stdout + completed.stderr,
            )
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertEqual(issues, [])
        self.assertTrue(
            any(
                "terminal_critic" in issue
                for issue in late_event_issues
            )
        )
        self.assertEqual(refreshed_issues, [])
        self.assertTrue(
            any("current snapshot reviews" in issue for issue in stale_issues)
        )

    def test_unselected_review_roles_and_their_blockers_fail_closed(
        self,
    ) -> None:
        cases = (
            ("light", "integration_review"),
            ("standard", "architecture_review"),
        )
        for assurance, role in cases:
            with self.subTest(assurance=assurance, role=role):
                with tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    root = make_project(base)
                    state_dir, state = initialize(
                        base,
                        root,
                        assurance=assurance,
                    )
                    finding = {
                        "id": "unexpected-blocker",
                        "severity": "blocking",
                        "status": "open",
                        "summary": "An unselected lane found a blocker.",
                        "evidence_refs": ["src/app.txt"],
                    }
                    rejected = record_review(
                        base,
                        root,
                        state_dir,
                        role,
                        "unexpected-review",
                        status="needs_repair",
                        findings=[finding],
                    )
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertIn(
                        "role is not selected by Goal proof policy",
                        rejected.stdout,
                    )

                    snapshot = current_snapshot(root, state_dir)
                    state["reviews"].append(
                        {
                            "review_id": "legacy-unexpected-review",
                            "role": role,
                            "status": "needs_repair",
                            "plan_revision": (
                                goal_ledger.current_plan_revision(state)
                            ),
                            "acceptance_revision": state[
                                "acceptance_revision"
                            ],
                            "acceptance_ids": ["a1"],
                            "workspace_sha256": snapshot["sha256"],
                            "receipt_sha256": "a" * 64,
                            "review_scope": (
                                goal_ledger.review_scope_binding(
                                    root,
                                    state_dir,
                                    ["src/**"],
                                )
                            ),
                            "carry_forward_from_receipt_sha256": None,
                            "open_blocking_finding_ids": [
                                "unexpected-blocker"
                            ],
                            "resolved_finding_ids": [],
                            "recorded_at": "2026-07-27T00:10:00Z",
                            "event_seq": 2,
                        }
                    )
                    issues = goal_ledger.completion_context_issues(
                        state,
                        snapshot,
                    )
                self.assertTrue(
                    any(
                        "unresolved review blocking findings" in issue
                        and f"{role}:unexpected-blocker" in issue
                        for issue in issues
                    )
                )

    def test_standard_completion_requires_current_review_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            before = evidence_receipt(root, state_dir)
            before_path = write_json(base / "before.json", before)
            blocked = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(before_path),
            )
            self.assertNotEqual(blocked.returncode, 0)
            reviewed = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-1",
            )
            self.assertEqual(
                reviewed.returncode, 0, reviewed.stdout + reviewed.stderr
            )
            receipt = evidence_receipt(root, state_dir)
            receipt_path = write_json(base / "receipt.json", receipt)
            ready = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(encoding="utf-8")
            )
        self.assertEqual(ready.returncode, 0, ready.stdout + ready.stderr)
        self.assertIsNotNone(state["completion_ready"])
        self.assertEqual(
            json.loads(ready.stdout)["result"]["host_mutated"],
            False,
        )

    def test_ignored_declared_review_scope_stales_current_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base, use_git=True)
            (root / ".gitignore").write_text(
                "reviewed/\n", encoding="utf-8"
            )
            git(root, "add", ".gitignore")
            git(root, "commit", "-m", "ignore reviewed artifacts")
            reviewed_dir = root / "reviewed"
            reviewed_dir.mkdir()
            reviewed_path = reviewed_dir / "out.txt"
            reviewed_path.write_text("v1\n", encoding="utf-8")
            state_dir, _state = initialize(base, root)
            reviewed = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "ignored-scope-v1",
                scope_patterns=["reviewed/**"],
            )
            self.assertEqual(reviewed.returncode, 0, reviewed.stdout)
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            before = current_snapshot(root, state_dir)
            self.assertEqual(
                goal_ledger.completion_context_issues(state, before),
                [],
            )

            reviewed_path.write_text("v2\n", encoding="utf-8")
            after = current_snapshot(root, state_dir)
            issues = goal_ledger.completion_context_issues(state, after)
        self.assertEqual(before["sha256"], after["sha256"])
        self.assertTrue(
            any("current snapshot reviews" in issue for issue in issues)
        )

    def test_review_scope_rejects_symlink_and_internal_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            outside = base / "outside"
            outside.mkdir()
            (outside / "secret.txt").write_text(
                "outside\n",
                encoding="utf-8",
            )
            (root / "link").symlink_to(
                outside,
                target_is_directory=True,
            )
            with self.assertRaisesRegex(
                ValueError,
                "review scope selects or traverses project symbolic link",
            ):
                goal_ledger.review_scope_binding(
                    root,
                    state_dir,
                    ["link/secret.txt"],
                )
            with self.assertRaisesRegex(
                ValueError,
                "review scope selects or traverses project symbolic link",
            ):
                goal_ledger.review_scope_binding(
                    root,
                    state_dir,
                    ["LiNk"],
                )
            for alias in ("./link", ".//link"):
                with self.subTest(alias=alias):
                    with self.assertRaisesRegex(
                        ValueError,
                        "unique portable paths",
                    ):
                        goal_ledger.review_scope_binding(
                            root,
                            state_dir,
                            [alias],
                        )
            with self.assertRaisesRegex(
                ValueError,
                "selects Git metadata",
            ):
                goal_ledger.review_scope_binding(
                    root,
                    state_dir,
                    [".git/config"],
                )
            local_state = root / ".goal-state"
            local_state.mkdir()
            with self.assertRaisesRegex(
                ValueError,
                "Goal state",
            ):
                goal_ledger.review_scope_binding(
                    root,
                    local_state,
                    [".goal-state/**"],
                )

    def test_generic_review_scope_implicitly_excludes_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir = root / ".goal-state"
            state_dir.mkdir()
            (state_dir / "private.json").write_text(
                '{"secret": true}\n',
                encoding="utf-8",
            )

            binding = goal_ledger.review_scope_binding(
                root,
                state_dir,
                ["**"],
            )
            captured = goal_primitives.protected_path_snapshot(
                root,
                ["**"],
                state_dir,
                snapshot_version=2,
            )

        self.assertEqual(binding["patterns"], ["**"])
        self.assertFalse(
            any(
                ".goal-state" in Path(path).parts
                for path in captured
            )
        )

    def test_review_can_carry_forward_only_across_unchanged_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base, use_git=True)
            unrelated = root / "notes.txt"
            unrelated.write_text("v1\n", encoding="utf-8")
            git(root, "add", "notes.txt")
            git(root, "commit", "-m", "add unrelated notes")
            state_dir, _state = initialize(base, root)
            first = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-v1",
            )
            self.assertEqual(first.returncode, 0, first.stdout)
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            first_hash = state["reviews"][-1]["receipt_sha256"]
            first_workspace = state["reviews"][-1]["workspace_sha256"]

            unrelated.write_text("v2\n", encoding="utf-8")
            carried = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-carried",
                carry_forward_from_receipt_sha256=first_hash,
            )
            self.assertEqual(carried.returncode, 0, carried.stdout)
            carried_state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            carried_review = carried_state["reviews"][-1]
            self.assertNotEqual(
                first_workspace,
                carried_review["workspace_sha256"],
            )
            self.assertEqual(
                carried_review["carry_forward_from_receipt_sha256"],
                first_hash,
            )

            (root / "src" / "app.txt").write_text(
                "reviewed scope changed\n", encoding="utf-8"
            )
            changed_scope = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-bad-carry",
                carry_forward_from_receipt_sha256=(
                    carried_review["receipt_sha256"]
                ),
            )
        self.assertNotEqual(changed_scope.returncode, 0)
        self.assertIn(
            "unchanged scope mismatch",
            changed_scope.stdout,
        )

    def test_passed_review_must_resolve_prior_blocking_finding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            open_finding = {
                "id": "finding-1",
                "severity": "blocking",
                "status": "open",
                "summary": "The failure path is not covered.",
                "evidence_refs": ["src/app.txt"],
            }
            negative = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-needs-repair",
                status="needs_repair",
                findings=[open_finding],
            )
            self.assertEqual(negative.returncode, 0, negative.stdout)
            (root / "src" / "app.txt").write_text(
                "repaired snapshot\n",
                encoding="utf-8",
            )
            unresolved = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-unresolved",
            )
            self.assertNotEqual(unresolved.returncode, 0)
            self.assertIn(
                "does not resolve prior blocking findings",
                unresolved.stdout,
            )
            resolved_finding = dict(open_finding)
            resolved_finding["status"] = "resolved"
            resolved_finding["summary"] = "The failure path is now covered."
            empty_evidence_finding = dict(resolved_finding)
            empty_evidence_finding["evidence_refs"] = []
            empty_evidence = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-empty-resolution",
                findings=[empty_evidence_finding],
            )
            self.assertNotEqual(empty_evidence.returncode, 0)
            self.assertIn(
                "review receipt finding is invalid",
                empty_evidence.stdout,
            )
            resolved = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-resolved",
                findings=[resolved_finding],
            )
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
        self.assertEqual(resolved.returncode, 0, resolved.stdout)
        self.assertEqual(state["reviews"][-1]["status"], "passed")
        self.assertEqual(
            state["reviews"][-1]["resolved_finding_ids"],
            ["finding-1"],
        )

    def test_blocking_resolution_preserves_acceptance_coverage(self) -> None:
        directions = (
            (["a1", "a2"], ["a1"], False),
            (["a1"], ["a1", "a2"], True),
        )
        for blocked_ids, repair_ids, should_pass in directions:
            with self.subTest(
                blocked_ids=blocked_ids,
                repair_ids=repair_ids,
            ):
                with tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    root = make_project(base)
                    state_dir, _state = initialize(base, root)
                    revision = write_json(
                        base / "acceptance-r2.json",
                        {
                            "reason": "Add a second repair criterion.",
                            "acceptance": [
                                {
                                    "id": "a1",
                                    "text": (
                                        "The behavior is directly verified."
                                    ),
                                },
                                {
                                    "id": "a2",
                                    "text": "The failure path is verified.",
                                },
                            ],
                        },
                    )
                    revised = command(
                        "revise-acceptance",
                        "--root",
                        str(root),
                        "--state-dir",
                        str(state_dir),
                        "--revision",
                        str(revision),
                    )
                    self.assertEqual(revised.returncode, 0, revised.stdout)
                    open_finding = {
                        "id": "coverage-finding",
                        "severity": "blocking",
                        "status": "open",
                        "summary": "The review surface needs repair.",
                        "evidence_refs": ["src/app.txt"],
                    }
                    negative = record_review(
                        base,
                        root,
                        state_dir,
                        "integration_review",
                        "coverage-negative",
                        status="needs_repair",
                        acceptance_ids=blocked_ids,
                        findings=[open_finding],
                    )
                    self.assertEqual(
                        negative.returncode,
                        0,
                        negative.stdout,
                    )
                    if blocked_ids == ["a1", "a2"]:
                        narrowed = record_review(
                            base,
                            root,
                            state_dir,
                            "integration_review",
                            "coverage-narrowed-reopen",
                            status="needs_repair",
                            acceptance_ids=["a1"],
                            findings=[open_finding],
                        )
                        self.assertEqual(
                            narrowed.returncode,
                            0,
                            narrowed.stdout,
                        )
                    (root / "src" / "app.txt").write_text(
                        "repaired\n",
                        encoding="utf-8",
                    )
                    resolved_finding = dict(open_finding)
                    resolved_finding["status"] = "resolved"
                    resolved_finding["summary"] = "The repair is verified."
                    repaired = record_review(
                        base,
                        root,
                        state_dir,
                        "integration_review",
                        "coverage-repaired",
                        acceptance_ids=repair_ids,
                        findings=[resolved_finding],
                    )
                if should_pass:
                    self.assertEqual(
                        repaired.returncode,
                        0,
                        repaired.stdout,
                    )
                else:
                    self.assertNotEqual(repaired.returncode, 0)
                    self.assertIn(
                        "does not cover prior blocking acceptance IDs",
                        repaired.stdout,
                    )

    def test_severity_downgrade_cannot_clear_blocking_finding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            open_finding = {
                "id": "original-bug",
                "severity": "blocking",
                "status": "open",
                "summary": "The original blocker remains.",
                "evidence_refs": ["src/app.txt"],
            }
            negative = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "downgrade-negative",
                status="needs_repair",
                findings=[open_finding],
            )
            self.assertEqual(negative.returncode, 0, negative.stdout)
            downgraded = dict(open_finding)
            downgraded.update(
                {
                    "severity": "info",
                    "status": "resolved",
                    "summary": "Attempt to downgrade the original blocker.",
                    "evidence_refs": [],
                }
            )
            replacement = {
                "id": "replacement-bug",
                "severity": "blocking",
                "status": "open",
                "summary": "A replacement blocker is recorded.",
                "evidence_refs": ["src/app.txt"],
            }
            intermediate = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "downgrade-intermediate",
                status="needs_repair",
                findings=[downgraded, replacement],
            )
            self.assertEqual(
                intermediate.returncode,
                0,
                intermediate.stdout,
            )
            (root / "src" / "app.txt").write_text(
                "partial repair\n",
                encoding="utf-8",
            )
            resolved_replacement = dict(replacement)
            resolved_replacement["status"] = "resolved"
            resolved_replacement["summary"] = "Replacement is repaired."
            bypass = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "downgrade-bypass",
                findings=[resolved_replacement],
            )
        self.assertNotEqual(bypass.returncode, 0)
        self.assertIn("original-bug", bypass.stdout)
        self.assertIn(
            "does not resolve prior blocking findings",
            bypass.stdout,
        )

    def test_older_pass_cannot_bypass_newer_blocking_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base, use_git=True)
            unrelated = root / "notes.txt"
            unrelated.write_text("v1\n", encoding="utf-8")
            git(root, "add", "notes.txt")
            git(root, "commit", "-m", "add notes")
            state_dir, _state = initialize(base, root)
            passed = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-passed",
            )
            self.assertEqual(passed.returncode, 0, passed.stdout)
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            older_pass_hash = state["reviews"][-1]["receipt_sha256"]
            negative = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-later-blocker",
                status="needs_repair",
                findings=[
                    {
                        "id": "finding-later",
                        "severity": "blocking",
                        "status": "open",
                        "summary": "A later review found a blocker.",
                        "evidence_refs": ["src/app.txt"],
                    }
                ],
            )
            self.assertEqual(negative.returncode, 0, negative.stdout)
            unrelated.write_text("v2\n", encoding="utf-8")
            bypass = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-bypass",
                carry_forward_from_receipt_sha256=older_pass_hash,
            )
        self.assertNotEqual(bypass.returncode, 0)
        self.assertIn(
            "latest relevant passed verdict",
            bypass.stdout,
        )

    def test_overlapping_review_subset_cannot_bypass_newer_blocker(
        self,
    ) -> None:
        directions = (
            (["a1"], ["a1", "a2"]),
            (["a1", "a2"], ["a1"]),
        )
        for passed_ids, blocked_ids in directions:
            with self.subTest(
                passed_ids=passed_ids,
                blocked_ids=blocked_ids,
            ):
                with tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    root = make_project(base)
                    state_dir, _state = initialize(base, root)
                    revision = write_json(
                        base / "acceptance-r2.json",
                        {
                            "reason": "Add a second review criterion.",
                            "acceptance": [
                                {
                                    "id": "a1",
                                    "text": (
                                        "The behavior is directly verified."
                                    ),
                                },
                                {
                                    "id": "a2",
                                    "text": "The failure path is verified.",
                                },
                            ],
                        },
                    )
                    revised = command(
                        "revise-acceptance",
                        "--root",
                        str(root),
                        "--state-dir",
                        str(state_dir),
                        "--revision",
                        str(revision),
                    )
                    self.assertEqual(
                        revised.returncode,
                        0,
                        revised.stdout,
                    )
                    passed = record_review(
                        base,
                        root,
                        state_dir,
                        "integration_review",
                        "overlap-passed",
                        acceptance_ids=passed_ids,
                    )
                    self.assertEqual(passed.returncode, 0, passed.stdout)
                    state = json.loads(
                        (state_dir / goal_ledger.STATE_NAME).read_text(
                            encoding="utf-8"
                        )
                    )
                    older_pass_hash = state["reviews"][-1][
                        "receipt_sha256"
                    ]
                    negative = record_review(
                        base,
                        root,
                        state_dir,
                        "integration_review",
                        "overlap-blocked",
                        status="needs_repair",
                        acceptance_ids=blocked_ids,
                        findings=[
                            {
                                "id": "overlap-finding",
                                "severity": "blocking",
                                "status": "open",
                                "summary": (
                                    "An overlapping review found a blocker."
                                ),
                                "evidence_refs": ["src/app.txt"],
                            }
                        ],
                    )
                    self.assertEqual(
                        negative.returncode,
                        0,
                        negative.stdout,
                    )
                    (root / "notes.txt").write_text(
                        "unrelated drift\n",
                        encoding="utf-8",
                    )
                    bypass = record_review(
                        base,
                        root,
                        state_dir,
                        "integration_review",
                        "overlap-bypass",
                        acceptance_ids=passed_ids,
                        carry_forward_from_receipt_sha256=(
                            older_pass_hash
                        ),
                    )
                self.assertNotEqual(bypass.returncode, 0)
                self.assertIn(
                    "latest relevant passed verdict",
                    bypass.stdout,
                )

    def test_manifest_free_strict_completion_uses_layered_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base, root, assurance="strict"
            )
            for role, review_id in (
                ("architecture_review", "architect-1"),
                ("adversarial_qa", "adversarial-1"),
                ("terminal_critic", "terminal-1"),
            ):
                reviewed = record_review(
                    base, root, state_dir, role, review_id
                )
                self.assertEqual(
                    reviewed.returncode,
                    0,
                    reviewed.stdout + reviewed.stderr,
                )
            receipt = evidence_receipt(root, state_dir)
            receipt_path = write_json(base / "strict-receipt.json", receipt)
            ready = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertEqual(ready.returncode, 0, ready.stdout + ready.stderr)

    def test_release_ledger_requires_remote_release_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(
                base,
                root,
                assurance="release",
            )
            self.assertIn(
                "remote-release",
                state["proof_policy"]["required_capabilities"],
            )
            for role, review_id in (
                ("architecture_review", "release-architect"),
                ("adversarial_qa", "release-adversarial"),
                ("terminal_critic", "release-terminal"),
            ):
                reviewed = record_review(
                    base,
                    root,
                    state_dir,
                    role,
                    review_id,
                )
                self.assertEqual(
                    reviewed.returncode,
                    0,
                    reviewed.stdout + reviewed.stderr,
                )
            receipt = evidence_receipt(root, state_dir)
            receipt_path = write_json(
                base / "release-receipt.json",
                receipt,
            )
            blocked = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("release_identity", blocked.stdout)

    def test_same_state_host_observation_keeps_terminal_review_fresh(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base,
                root,
                assurance="strict",
            )
            for role, review_id in (
                ("architecture_review", "same-state-architect"),
                ("adversarial_qa", "same-state-adversarial"),
                ("terminal_critic", "same-state-terminal"),
            ):
                reviewed = record_review(
                    base,
                    root,
                    state_dir,
                    role,
                    review_id,
                )
                self.assertEqual(reviewed.returncode, 0, reviewed.stdout)
            before = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            observation = write_json(
                base / "same-active-state.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "active",
                    "observed_at": later_than(
                        before["host"]["observed_at"]
                    ),
                    "source": "codex-host",
                },
            )
            observed = command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(observation),
            )
            self.assertEqual(observed.returncode, 0, observed.stdout)
            after = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            snapshot = current_snapshot(root, state_dir)
            issues = goal_ledger.completion_context_issues(after, snapshot)
            receipt = evidence_receipt(root, state_dir)
            receipt_path = write_json(
                base / "same-state-receipt.json",
                receipt,
            )
            ready = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertEqual(issues, [])
        self.assertEqual(ready.returncode, 0, ready.stdout + ready.stderr)

    def test_terminal_critic_binds_cycle_free_evidence_candidate(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base,
                root,
                assurance="strict",
            )
            for role, review_id in (
                ("architecture_review", "architect-1"),
                ("adversarial_qa", "adversarial-1"),
            ):
                reviewed = record_review(
                    base,
                    root,
                    state_dir,
                    role,
                    review_id,
                )
                self.assertEqual(
                    reviewed.returncode,
                    0,
                    reviewed.stdout + reviewed.stderr,
                )
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            snapshot = current_snapshot(root, state_dir)
            candidate = evidence_receipt(root, state_dir)
            candidate_sha256 = (
                goal_ledger.completion_evidence_candidate_sha256(
                    candidate,
                    state,
                    snapshot,
                )
            )
            cycle_only_changes = json.loads(json.dumps(candidate))
            cycle_only_changes["goal_binding"][
                "ledger_tail_sha256"
            ] = "0" * 64
            cycle_only_changes["gates"]["terminal_critic"] = {
                "status": "passed",
                "evidence": [
                    {
                        "kind": "inspection",
                        "status": "verified",
                        "summary": "A later terminal envelope.",
                        "source": "terminal fixture",
                        "checked_at": "2026-07-27T00:20:00Z",
                    }
                ],
            }
            self.assertEqual(
                goal_ledger.completion_evidence_candidate_sha256(
                    cycle_only_changes,
                    state,
                    snapshot,
                ),
                candidate_sha256,
            )
            missing_candidate_receipt = write_json(
                base / "terminal-missing-candidate.json",
                review_receipt(
                    state,
                    snapshot["sha256"],
                    "terminal_critic",
                    "terminal-missing-candidate",
                ),
            )
            missing = command(
                "review-record",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--review",
                str(missing_candidate_receipt),
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("evidence_candidate", missing.stdout)
            terminal = record_review(
                base,
                root,
                state_dir,
                "terminal_critic",
                "terminal-1",
            )
            self.assertEqual(
                terminal.returncode,
                0,
                terminal.stdout + terminal.stderr,
            )
            final_receipt = evidence_receipt(root, state_dir)
            post_terminal_state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                goal_ledger.completion_evidence_candidate_sha256(
                    final_receipt,
                    post_terminal_state,
                    snapshot,
                ),
                candidate_sha256,
            )
            final_receipt["gates"]["cleanup"]["evidence"][0][
                "summary"
            ] = "Changed after the terminal critic."
            final_path = write_json(
                base / "changed-after-terminal.json",
                final_receipt,
            )
            blocked = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(final_path),
            )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn(
            "final evidence candidate does not match terminal critic",
            blocked.stdout,
        )

    def test_terminal_candidate_allows_honest_finalization_time(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base,
                root,
                assurance="strict",
            )
            for role, review_id in (
                ("architecture_review", "time-architect"),
                ("adversarial_qa", "time-adversarial"),
            ):
                reviewed = record_review(
                    base,
                    root,
                    state_dir,
                    role,
                    review_id,
                )
                self.assertEqual(reviewed.returncode, 0, reviewed.stdout)
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            snapshot = current_snapshot(root, state_dir)
            candidate = evidence_receipt(root, state_dir)
            candidate["completed_at"] = "2026-07-27T00:25:00Z"
            candidate_sha256 = (
                goal_ledger.completion_evidence_candidate_sha256(
                    candidate,
                    state,
                    snapshot,
                )
            )
            candidate_path = write_json(
                base / "time-candidate.json",
                candidate,
            )
            terminal_receipt = review_receipt(
                state,
                snapshot["sha256"],
                "terminal_critic",
                "time-terminal",
                evidence_candidate_sha256=candidate_sha256,
                review_scope=goal_ledger.review_scope_binding(
                    root,
                    state_dir,
                    [],
                ),
                checked_at="2026-07-27T00:27:00Z",
            )
            terminal_path = write_json(
                base / "time-terminal.json",
                terminal_receipt,
            )
            terminal = command(
                "review-record",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--review",
                str(terminal_path),
                "--evidence-candidate",
                str(candidate_path),
            )
            self.assertEqual(terminal.returncode, 0, terminal.stdout)

            final_state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            final_receipt = evidence_receipt(root, state_dir)
            final_receipt["completed_at"] = "2026-07-27T00:30:00Z"
            final_receipt["gates"]["terminal_critic"]["evidence"][0][
                "checked_at"
            ] = "2026-07-27T00:27:00Z"
            self.assertEqual(
                goal_ledger.completion_evidence_candidate_sha256(
                    final_receipt,
                    final_state,
                    snapshot,
                ),
                candidate_sha256,
            )
            final_path = write_json(
                base / "time-final.json",
                final_receipt,
            )
            ready = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(final_path),
            )
        self.assertEqual(ready.returncode, 0, ready.stdout + ready.stderr)

    def test_terminal_time_follows_candidate_and_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base,
                root,
                assurance="strict",
            )
            for role, review_id in (
                ("architecture_review", "order-architect"),
                ("adversarial_qa", "order-adversarial"),
            ):
                reviewed = record_review(
                    base,
                    root,
                    state_dir,
                    role,
                    review_id,
                )
                self.assertEqual(reviewed.returncode, 0, reviewed.stdout)
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            snapshot = current_snapshot(root, state_dir)
            candidate = evidence_receipt(root, state_dir)
            candidate["completed_at"] = "2026-07-27T00:25:00Z"
            candidate_sha256 = (
                goal_ledger.completion_evidence_candidate_sha256(
                    candidate,
                    state,
                    snapshot,
                )
            )
            candidate_path = write_json(
                base / "order-candidate.json",
                candidate,
            )
            late_evidence_candidate = evidence_receipt(root, state_dir)
            late_evidence_candidate["completed_at"] = (
                "2026-07-27T00:15:00Z"
            )
            self.assertEqual(
                goal_ledger.completion_evidence_candidate_sha256(
                    late_evidence_candidate,
                    state,
                    snapshot,
                ),
                candidate_sha256,
            )
            late_evidence_path = write_json(
                base / "order-late-evidence-candidate.json",
                late_evidence_candidate,
            )
            evidence_terminal_receipt = review_receipt(
                state,
                snapshot["sha256"],
                "terminal_critic",
                "order-terminal-late-evidence",
                evidence_candidate_sha256=candidate_sha256,
                review_scope=goal_ledger.review_scope_binding(
                    root,
                    state_dir,
                    [],
                ),
                checked_at="2026-07-27T00:25:00Z",
            )
            evidence_terminal_path = write_json(
                base / "order-terminal-late-evidence.json",
                evidence_terminal_receipt,
            )
            late_evidence = command(
                "review-record",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--review",
                str(evidence_terminal_path),
                "--evidence-candidate",
                str(late_evidence_path),
            )
            self.assertNotEqual(late_evidence.returncode, 0)
            self.assertIn(
                "evidence candidate gate 'cleanup' evidence 0 checked_at "
                "occurs after candidate completed_at",
                late_evidence.stdout,
            )

            early_receipt = review_receipt(
                state,
                snapshot["sha256"],
                "terminal_critic",
                "order-terminal-early",
                evidence_candidate_sha256=candidate_sha256,
                review_scope=goal_ledger.review_scope_binding(
                    root,
                    state_dir,
                    [],
                ),
                checked_at="2026-07-27T00:05:00Z",
            )
            early_path = write_json(
                base / "order-terminal-early.json",
                early_receipt,
            )
            early = command(
                "review-record",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--review",
                str(early_path),
                "--evidence-candidate",
                str(candidate_path),
            )
            self.assertNotEqual(early.returncode, 0)
            self.assertIn(
                "terminal critic checked_at precedes Completion Evidence "
                "Candidate completed_at",
                early.stdout,
            )
            self.assertIn(
                "terminal critic checked_at precedes current Review "
                "Verdict 'architecture_review' recorded_at",
                early.stdout,
            )

            valid_receipt = review_receipt(
                state,
                snapshot["sha256"],
                "terminal_critic",
                "order-terminal-valid",
                evidence_candidate_sha256=candidate_sha256,
                review_scope=goal_ledger.review_scope_binding(
                    root,
                    state_dir,
                    [],
                ),
                checked_at="2026-07-27T00:27:00Z",
            )
            valid_path = write_json(
                base / "order-terminal-valid.json",
                valid_receipt,
            )
            valid = command(
                "review-record",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--review",
                str(valid_path),
                "--evidence-candidate",
                str(candidate_path),
            )
            self.assertEqual(valid.returncode, 0, valid.stdout)

            persisted = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            persisted["reviews"][-1]["recorded_at"] = (
                "2026-07-27T00:05:00Z"
            )
            legacy_issues = goal_ledger.completion_context_issues(
                persisted,
                snapshot,
            )
        self.assertIn(
            "terminal critic checked_at precedes current Review "
            "Verdict 'architecture_review' recorded_at",
            legacy_issues,
        )

    def test_completion_rejects_time_before_current_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base,
                root,
                assurance="strict",
            )
            for role, review_id in (
                ("architecture_review", "causal-architect"),
                ("adversarial_qa", "causal-adversarial"),
            ):
                reviewed = record_review(
                    base,
                    root,
                    state_dir,
                    role,
                    review_id,
                )
                self.assertEqual(reviewed.returncode, 0, reviewed.stdout)
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            snapshot = current_snapshot(root, state_dir)
            candidate = evidence_receipt(root, state_dir)
            candidate["completed_at"] = "2026-07-27T00:25:00Z"
            candidate_sha256 = (
                goal_ledger.completion_evidence_candidate_sha256(
                    candidate,
                    state,
                    snapshot,
                )
            )
            candidate_path = write_json(
                base / "causal-candidate.json",
                candidate,
            )
            terminal_receipt = review_receipt(
                state,
                snapshot["sha256"],
                "terminal_critic",
                "causal-terminal",
                evidence_candidate_sha256=candidate_sha256,
                review_scope=goal_ledger.review_scope_binding(
                    root,
                    state_dir,
                    [],
                ),
                checked_at="2026-07-27T00:40:00Z",
            )
            terminal_path = write_json(
                base / "causal-terminal.json",
                terminal_receipt,
            )
            terminal = command(
                "review-record",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--review",
                str(terminal_path),
                "--evidence-candidate",
                str(candidate_path),
            )
            self.assertEqual(terminal.returncode, 0, terminal.stdout)

            final_state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            final_receipt = evidence_receipt(root, state_dir)
            final_receipt["completed_at"] = "2026-07-27T00:30:00Z"
            self.assertEqual(
                goal_ledger.completion_evidence_candidate_sha256(
                    final_receipt,
                    final_state,
                    snapshot,
                ),
                candidate_sha256,
            )
            final_path = write_json(
                base / "causal-final.json",
                final_receipt,
            )
            ready = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(final_path),
            )
        self.assertNotEqual(ready.returncode, 0)
        self.assertIn(
            "current Review Verdict 'terminal_critic' was recorded after "
            "receipt completed_at",
            ready.stdout,
        )

    def test_terminal_rejects_late_release_evidence_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base,
                root,
                assurance="release",
            )
            for role, review_id in (
                ("architecture_review", "release-time-architect"),
                ("adversarial_qa", "release-time-adversarial"),
            ):
                reviewed = record_review(
                    base,
                    root,
                    state_dir,
                    role,
                    review_id,
                )
                self.assertEqual(reviewed.returncode, 0, reviewed.stdout)
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            snapshot = current_snapshot(root, state_dir)

            def remote_cost(checked_at: str) -> dict[str, object]:
                action: dict[str, object] = {
                    "action_id": "release-1",
                    "provider": "github",
                    "account_or_project": "owner/sample",
                    "resource_or_sku": "repository-release",
                    "evidence_source": "provider plan inspection",
                    "evidence_checked_at": checked_at,
                    "classification": "verified_zero_charge",
                    "decision": "allow",
                    "billing_mode": "hard-free-no-overage",
                    "remaining_free_quota": 10,
                    "planned_usage": 1,
                    "hard_stop_enabled": True,
                    "maximum_cost": 0,
                }
                for field in validate_evidence_v3.PAID_TRANSITION_FIELDS:
                    action[field] = False
                return {
                    "policy": POLICY,
                    "classification": "verified_zero_charge",
                    "decision": "allow",
                    "paid_action_requested": False,
                    "actions": [action],
                }

            late_cost_candidate = evidence_receipt(root, state_dir)
            late_cost_candidate["completed_at"] = (
                "2026-07-27T00:25:00Z"
            )
            late_cost_candidate["cost_authority"] = remote_cost(
                "2026-07-27T00:29:00Z"
            )
            late_cost_sha256 = (
                goal_ledger.completion_evidence_candidate_sha256(
                    late_cost_candidate,
                    state,
                    snapshot,
                )
            )
            late_cost_path = write_json(
                base / "late-cost-candidate.json",
                late_cost_candidate,
            )
            late_cost_review = review_receipt(
                state,
                snapshot["sha256"],
                "terminal_critic",
                "late-cost-terminal",
                evidence_candidate_sha256=late_cost_sha256,
                review_scope=goal_ledger.review_scope_binding(
                    root,
                    state_dir,
                    [],
                ),
                checked_at="2026-07-27T00:27:00Z",
            )
            late_cost_review_path = write_json(
                base / "late-cost-terminal.json",
                late_cost_review,
            )
            cost_blocked = command(
                "review-record",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--review",
                str(late_cost_review_path),
                "--evidence-candidate",
                str(late_cost_path),
            )
            self.assertNotEqual(cost_blocked.returncode, 0)
            self.assertIn(
                "evidence candidate cost_authority.actions[0]."
                "evidence_checked_at occurs after candidate completed_at",
                cost_blocked.stdout,
            )

            late_data_candidate = evidence_receipt(root, state_dir)
            late_data_candidate["completed_at"] = (
                "2026-07-27T00:25:00Z"
            )
            late_data_candidate["cost_authority"] = remote_cost(
                "2026-07-27T00:20:00Z"
            )
            cleanup_evidence = late_data_candidate["gates"]["cleanup"][
                "evidence"
            ][0]
            cleanup_evidence["artifact_sha256"] = "a" * 64
            cleanup_evidence["data_identity"] = {
                "source_ids": ["fixture"],
                "artifact_sha256": "a" * 64,
                "rights_checked": True,
                "collected_at": "2026-07-27T00:29:00Z",
                "source_as_of": "2026-07-27T00:29:00Z",
                "freshness_status": "current",
            }
            late_data_sha256 = (
                goal_ledger.completion_evidence_candidate_sha256(
                    late_data_candidate,
                    state,
                    snapshot,
                )
            )
            late_data_path = write_json(
                base / "late-data-candidate.json",
                late_data_candidate,
            )
            late_data_review = review_receipt(
                state,
                snapshot["sha256"],
                "terminal_critic",
                "late-data-terminal",
                evidence_candidate_sha256=late_data_sha256,
                review_scope=goal_ledger.review_scope_binding(
                    root,
                    state_dir,
                    [],
                ),
                checked_at="2026-07-27T00:27:00Z",
            )
            late_data_review_path = write_json(
                base / "late-data-terminal.json",
                late_data_review,
            )
            data_blocked = command(
                "review-record",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--review",
                str(late_data_review_path),
                "--evidence-candidate",
                str(late_data_path),
            )
            self.assertNotEqual(data_blocked.returncode, 0)
            self.assertIn(
                "evidence candidate gate 'cleanup' evidence 0 "
                "data_identity.collected_at occurs after candidate "
                "completed_at",
                data_blocked.stdout,
            )

            valid_candidate = evidence_receipt(root, state_dir)
            valid_candidate["completed_at"] = "2026-07-27T00:25:00Z"
            valid_candidate["cost_authority"] = remote_cost(
                "2026-07-27T00:20:00Z"
            )
            valid_sha256 = (
                goal_ledger.completion_evidence_candidate_sha256(
                    valid_candidate,
                    state,
                    snapshot,
                )
            )
            valid_path = write_json(
                base / "valid-release-candidate.json",
                valid_candidate,
            )
            valid_review = review_receipt(
                state,
                snapshot["sha256"],
                "terminal_critic",
                "valid-release-terminal",
                evidence_candidate_sha256=valid_sha256,
                review_scope=goal_ledger.review_scope_binding(
                    root,
                    state_dir,
                    [],
                ),
                checked_at="2026-07-27T00:27:00Z",
            )
            valid_review_path = write_json(
                base / "valid-release-terminal.json",
                valid_review,
            )
            valid = command(
                "review-record",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--review",
                str(valid_review_path),
                "--evidence-candidate",
                str(valid_path),
            )
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

    def test_review_subsets_are_preserved_and_required_lanes_complete(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base,
                root,
                assurance="strict",
            )
            revision = write_json(
                base / "acceptance-r2.json",
                {
                    "reason": "Add an independently reviewable criterion.",
                    "acceptance": [
                        {"id": "a1", "text": "The behavior is verified."},
                        {"id": "a2", "text": "The failure path is verified."},
                    ],
                },
            )
            plan = base / "plan-r2.md"
            plan.write_text("# Reviewed plan revision 2\n", encoding="utf-8")
            revised = command(
                "revise-acceptance",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--revision",
                str(revision),
                "--plan",
                str(plan),
            )
            self.assertEqual(revised.returncode, 0, revised.stdout)
            architect = record_review(
                base,
                root,
                state_dir,
                "architecture_review",
                "architect-a1",
                acceptance_ids=["a1"],
            )
            adversarial = record_review(
                base,
                root,
                state_dir,
                "adversarial_qa",
                "adversarial-a2",
                acceptance_ids=["a2"],
            )
            for reviewed in (architect, adversarial):
                self.assertEqual(
                    reviewed.returncode,
                    0,
                    reviewed.stdout + reviewed.stderr,
                )
            state_before_terminal = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            snapshot = current_snapshot(root, state_dir)
            candidate = evidence_receipt(root, state_dir)
            candidate_path = write_json(
                base / "terminal-subset-candidate.json",
                candidate,
            )
            candidate_sha256 = (
                goal_ledger.completion_evidence_candidate_sha256(
                    candidate,
                    state_before_terminal,
                    snapshot,
                )
            )
            subset_terminal_receipt = write_json(
                base / "terminal-subset.json",
                review_receipt(
                    state_before_terminal,
                    snapshot["sha256"],
                    "terminal_critic",
                    "terminal-subset",
                    acceptance_ids=["a1"],
                    evidence_candidate_sha256=candidate_sha256,
                ),
            )
            subset_terminal = command(
                "review-record",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--review",
                str(subset_terminal_receipt),
                "--evidence-candidate",
                str(candidate_path),
            )
            self.assertNotEqual(subset_terminal.returncode, 0)
            self.assertIn(
                "terminal critic must cover all current acceptance IDs",
                subset_terminal.stdout,
            )
            terminal = record_review(
                base,
                root,
                state_dir,
                "terminal_critic",
                "terminal-all",
            )
            self.assertEqual(terminal.returncode, 0, terminal.stdout)
            receipt = evidence_receipt(root, state_dir)
            receipt_path = write_json(
                base / "subset-receipt.json",
                receipt,
            )
            ready = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
        self.assertEqual(ready.returncode, 0, ready.stdout + ready.stderr)
        review_ids = {
            review["review_id"]: review["acceptance_ids"]
            for review in state["reviews"]
        }
        self.assertEqual(review_ids["architect-a1"], ["a1"])
        self.assertEqual(review_ids["adversarial-a2"], ["a2"])
        self.assertEqual(
            set(review_ids["terminal-all"]),
            {"a1", "a2"},
        )

    def test_completion_rejects_unmapped_acceptance_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            reviewed = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-1",
            )
            self.assertEqual(reviewed.returncode, 0)
            receipt = evidence_receipt(root, state_dir)
            receipt["goal_binding"]["acceptance_claims"] = {}
            receipt_path = write_json(base / "unmapped.json", receipt)
            blocked = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("acceptance_claims", blocked.stdout)

    def test_explicit_gitignored_project_local_state_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base, use_git=True)
            (root / ".gitignore").write_text(
                ".goal-state/\n", encoding="utf-8"
            )
            git(root, "add", ".gitignore")
            git(root, "commit", "-m", "ignore local Goal state")
            acceptance = write_json(
                base / "acceptance-local.json",
                {
                    "acceptance": [
                        {"id": "a1", "text": "Local state is isolated."}
                    ]
                },
            )
            state_dir = root / ".goal-state"
            initialized = command(
                "init",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--project-local",
                "--goal-id",
                "goal-local",
                "--host-goal-id",
                "host-goal-local",
                "--project-id",
                "sample",
                "--objective",
                "Verify an explicit co-located evidence archive.",
                "--acceptance",
                str(acceptance),
                "--assurance",
                "light",
                "--activation-reason",
                "portability",
            )
            copied_root = base / "copied-project"
            shutil.copytree(root, copied_root, symlinks=True)
            copied_resume = command(
                "resume",
                "--root",
                str(copied_root),
                "--state-dir",
                str(copied_root / ".goal-state"),
            )
        self.assertEqual(
            initialized.returncode,
            0,
            initialized.stdout + initialized.stderr,
        )
        self.assertNotEqual(copied_resume.returncode, 0)
        self.assertTrue(
            any(
                phrase in copied_resume.stdout
                for phrase in (
                    "project binding mismatch",
                    "state root binding mismatch",
                    "state root path does not match",
                    "state-root binding changed",
                )
            ),
            copied_resume.stdout,
        )

    def test_project_local_state_requires_actual_artifacts_to_be_ignored(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base, use_git=True)
            (root / ".gitignore").write_text(
                ".quant-goal-state-probe\n",
                encoding="utf-8",
            )
            git(root, "add", ".gitignore")
            git(root, "commit", "-m", "ignore only the obsolete probe")
            acceptance = write_json(
                base / "probe-acceptance.json",
                {
                    "acceptance": [
                        {
                            "id": "a1",
                            "text": "State remains outside tracked work.",
                        }
                    ]
                },
            )
            state_dir = root / "state"
            blocked = command(
                "init",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--project-local",
                "--goal-id",
                "goal-probe-only",
                "--host-goal-id",
                "host-probe-only",
                "--project-id",
                "sample",
                "--objective",
                "Reject a false Git ignore boundary.",
                "--acceptance",
                str(acceptance),
                "--assurance",
                "light",
                "--activation-reason",
                "machine-audit",
            )
            status = subprocess.run(
                ["git", "-C", str(root), "status", "--short"],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("must already be gitignored", blocked.stdout)
        self.assertFalse(state_dir.exists())
        self.assertEqual(status.returncode, 0)
        self.assertEqual(status.stdout, "")

    def test_init_validates_host_binding_and_reports_observed_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            acceptance = write_json(
                base / "host-init-acceptance.json",
                {
                    "acceptance": [
                        {"id": "a1", "text": "Host state is observed."}
                    ]
                },
            )
            invalid_state_dir = base / "invalid-host-source"
            common = [
                "--root",
                str(root),
                "--project-id",
                "sample",
                "--objective",
                "Bind the observed host state.",
                "--acceptance",
                str(acceptance),
                "--assurance",
                "light",
                "--activation-reason",
                "recovery",
            ]
            invalid = command(
                "init",
                "--state-dir",
                str(invalid_state_dir),
                "--goal-id",
                "goal-invalid-host",
                "--host-goal-id",
                "host-invalid",
                "--host-source",
                "",
                *common,
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("host_source is required", invalid.stdout)
            self.assertFalse(invalid_state_dir.exists())

            waiting_state_dir = base / "waiting-state"
            waiting = command(
                "init",
                "--state-dir",
                str(waiting_state_dir),
                "--goal-id",
                "goal-waiting",
                "--host-goal-id",
                "host-waiting",
                "--host-state",
                "waiting",
                *common,
            )
            self.assertEqual(waiting.returncode, 0, waiting.stdout)
            self.assertEqual(json.loads(waiting.stdout)["status"], "waiting")
            waiting_state = json.loads(
                (waiting_state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                waiting_state["host"]["last_observed_state"],
                "waiting",
            )

            completed_state_dir = base / "completed-state"
            completed = command(
                "init",
                "--state-dir",
                str(completed_state_dir),
                "--goal-id",
                "goal-completed",
                "--host-goal-id",
                "host-completed",
                "--host-state",
                "completed",
                *common,
            )
            completed_state = json.loads(
                (completed_state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(
            json.loads(completed.stdout)["status"],
            "review_required",
        )
        self.assertIn(
            "host_completed_without_completion_ready",
            completed.stdout,
        )
        self.assertEqual(
            completed_state["host"]["last_observed_state"],
            "completed",
        )

    def test_host_divergence_is_reported_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, initial_state = initialize(base, root)
            observation = write_json(
                base / "host.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "completed",
                    "observed_at": later_than(
                        initial_state["host"]["observed_at"]
                    ),
                    "source": "codex-host",
                },
            )
            observed = command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(observation),
            )
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(encoding="utf-8")
            )
        self.assertEqual(observed.returncode, 2)
        self.assertIn(
            "host_completed_without_completion_ready", observed.stdout
        )
        self.assertIn(
            "reopen the same host Goal or create a new Goal",
            observed.stdout,
        )
        self.assertEqual(state["host"]["last_observed_state"], "completed")
        self.assertIsNone(state["completion_ready"])

    def test_reverse_host_divergence_is_reported_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, initial_state = initialize(
                base,
                root,
                assurance="light",
            )
            receipt = evidence_receipt(root, state_dir)
            receipt_path = write_json(base / "receipt.json", receipt)
            ready = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            self.assertEqual(ready.returncode, 0, ready.stdout)
            observation = write_json(
                base / "host-still-active.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "active",
                    "observed_at": later_than(
                        initial_state["host"]["observed_at"]
                    ),
                    "source": "codex-host",
                },
            )
            observed = command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(observation),
            )
            observed_again = command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(observation),
            )
        self.assertEqual(observed.returncode, 2)
        self.assertIn(
            "completion_ready_host_not_completed", observed.stdout
        )
        self.assertEqual(observed_again.returncode, 2)
        self.assertIn(
            "completion_ready_host_not_completed", observed_again.stdout
        )

    def test_completion_requires_active_host_and_completed_readback_is_stable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, initial_state = initialize(
                base,
                root,
                assurance="light",
            )
            waiting_time = later_than(
                initial_state["host"]["observed_at"]
            )
            waiting = write_json(
                base / "waiting.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "waiting",
                    "observed_at": waiting_time,
                    "source": "codex-host",
                },
            )
            observed_waiting = command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(waiting),
            )
            self.assertEqual(
                json.loads(observed_waiting.stdout)["status"], "waiting"
            )
            waiting_receipt = evidence_receipt(root, state_dir)
            waiting_receipt_path = write_json(
                base / "waiting-receipt.json", waiting_receipt
            )
            blocked = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(waiting_receipt_path),
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("requires an active host Goal", blocked.stdout)
            active_time = later_than(waiting_time)
            active = write_json(
                base / "active.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "active",
                    "observed_at": active_time,
                    "source": "codex-host",
                },
            )
            observed_active = command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(active),
            )
            self.assertEqual(observed_active.returncode, 0)
            receipt = evidence_receipt(root, state_dir)
            receipt_path = write_json(base / "receipt.json", receipt)
            ready = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            self.assertEqual(ready.returncode, 0, ready.stdout)
            completed = write_json(
                base / "completed.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "completed",
                    "observed_at": later_than(active_time),
                    "source": "codex-host",
                },
            )
            observed_completed = command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(completed),
            )
            retried = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertEqual(observed_completed.returncode, 0)
        self.assertEqual(
            json.loads(observed_completed.stdout)["status"], "completed"
        )
        self.assertEqual(retried.returncode, 0, retried.stdout)
        self.assertTrue(json.loads(retried.stdout)["result"]["idempotent"])

    def test_completion_retry_rejects_workspace_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base,
                root,
                assurance="light",
            )
            receipt = evidence_receipt(root, state_dir)
            receipt_path = write_json(base / "receipt.json", receipt)
            ready = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            self.assertEqual(ready.returncode, 0, ready.stdout)
            (root / "src" / "app.txt").write_text(
                "drifted after completion\n", encoding="utf-8"
            )
            retried = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
        self.assertNotEqual(retried.returncode, 0)
        self.assertIn("workspace snapshot is stale", retried.stdout)

    def test_completion_revisions_preserve_prior_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base,
                root,
                assurance="light",
            )
            first_receipt = evidence_receipt(root, state_dir)
            first_path = write_json(base / "first.json", first_receipt)
            first = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(first_path),
            )
            self.assertEqual(first.returncode, 0, first.stdout)
            checkpoint = write_json(
                base / "checkpoint.json",
                {
                    "kind": "repair",
                    "summary": "Record a completion-affecting checkpoint.",
                    "acceptance_status": {
                        "a1": {
                            "status": "passed",
                            "evidence_refs": ["first"],
                        }
                    },
                    "blockers": [],
                    "next_action": "Reassemble current evidence.",
                },
            )
            recorded = command(
                "checkpoint",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--checkpoint",
                str(checkpoint),
            )
            self.assertEqual(recorded.returncode, 0, recorded.stdout)
            second_receipt = evidence_receipt(root, state_dir)
            second_path = write_json(base / "second.json", second_receipt)
            second = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(second_path),
            )
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            first_retained = (
                state_dir / "receipts" / "final-r1.json"
            ).is_file()
            second_retained = (
                state_dir / "receipts" / "final-r2.json"
            ).is_file()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(len(state["completion_history"]), 2)
        self.assertEqual(
            state["completion_ready"]["receipt_path"],
            "receipts/final-r2.json",
        )
        self.assertTrue(first_retained)
        self.assertTrue(second_retained)

    def test_completion_retry_preserves_unbound_prejournal_receipt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base,
                root,
                assurance="light",
            )
            first_receipt = evidence_receipt(root, state_dir)
            first_path = write_json(base / "first-attempt.json", first_receipt)
            arguments = argparse.Namespace(
                root=str(root),
                state_dir=str(state_dir),
                receipt=str(first_path),
                manifest=None,
                input_binding_capture=None,
                require_capability=[],
            )
            with mock.patch.object(
                goal_ledger,
                "persist_event",
                side_effect=OSError(
                    "simulated crash before completion journal"
                ),
            ):
                interrupted = goal_ledger.completion_ready_command(arguments)
            interrupted_state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            unbound = state_dir / "receipts" / "final-r1.json"
            self.assertTrue(unbound.is_file())
            self.assertEqual(interrupted_state["completion_history"], [])

            (root / "src" / "app.txt").write_text(
                "fresh completion snapshot\n",
                encoding="utf-8",
            )
            second_receipt = evidence_receipt(root, state_dir)
            second_path = write_json(
                base / "second-attempt.json",
                second_receipt,
            )
            retried = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(second_path),
            )
            final_state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            orphaned = list((state_dir / "orphaned").glob("*.orphan"))
            orphaned_bytes = [path.read_bytes() for path in orphaned]
            final_receipt = json.loads(unbound.read_text(encoding="utf-8"))
        self.assertFalse(interrupted["ok"])
        self.assertIn(
            "simulated crash before completion journal",
            interrupted["issues"],
        )
        self.assertEqual(retried.returncode, 0, retried.stdout)
        self.assertEqual(len(final_state["completion_history"]), 1)
        self.assertEqual(final_receipt, second_receipt)
        self.assertEqual(len(orphaned), 1)
        self.assertEqual(
            orphaned_bytes[0],
            goal_primitives.canonical_bytes(first_receipt),
        )

    def test_completion_receipt_rewrite_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base,
                root,
                assurance="light",
            )
            receipt = evidence_receipt(root, state_dir)
            receipt_path = write_json(base / "receipt.json", receipt)
            ready = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            self.assertEqual(ready.returncode, 0, ready.stdout)
            stored = state_dir / "receipts" / "final-r1.json"
            rewritten_value = json.loads(
                stored.read_text(encoding="utf-8")
            )
            rewritten_value["objective"] = "Rewritten after completion."
            write_json(stored, rewritten_value)
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn("final receipt is not ledger-bound", resumed.stdout)

    def test_init_is_idempotent_for_the_same_goal_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(base, root)
            initial_tail = state["ledger"]["tail_sha256"]
            repeated = command(
                "init",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--goal-id",
                "goal-sample",
                "--host-goal-id",
                "host-goal-sample",
                "--project-id",
                "sample",
                "--objective",
                "Deliver the requested behavior.",
                "--acceptance",
                str(base / "acceptance.json"),
                "--assurance",
                "standard",
                "--activation-reason",
                "recovery",
            )
            repeated_state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
        self.assertEqual(
            repeated.returncode,
            0,
            repeated.stdout + repeated.stderr,
        )
        self.assertEqual(repeated_state["ledger"]["event_count"], 1)
        self.assertEqual(
            repeated_state["ledger"]["tail_sha256"], initial_tail
        )

    def test_stale_host_observation_cannot_rewind_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, initial_state = initialize(base, root)
            newer_time = later_than(
                initial_state["host"]["observed_at"], minutes=2
            )
            newer = write_json(
                base / "newer.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "waiting",
                    "observed_at": newer_time,
                    "source": "codex-host",
                },
            )
            accepted = command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(newer),
            )
            self.assertEqual(accepted.returncode, 0, accepted.stdout)
            self.assertEqual(
                json.loads(accepted.stdout)["status"], "waiting"
            )
            stale = write_json(
                base / "stale.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "active",
                    "observed_at": initial_state["host"]["observed_at"],
                    "source": "codex-host",
                },
            )
            rejected = command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(stale),
            )
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("older than ledger state", rejected.stdout)
        self.assertEqual(state["host"]["last_observed_state"], "waiting")

    def test_cancelled_strict_goal_does_not_request_fresh_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, initial_state = initialize(
                base,
                root,
                assurance="strict",
            )
            for role, review_id in (
                ("architecture_review", "architect-1"),
                ("adversarial_qa", "adversarial-1"),
                ("terminal_critic", "terminal-1"),
            ):
                reviewed = record_review(
                    base, root, state_dir, role, review_id
                )
                self.assertEqual(reviewed.returncode, 0, reviewed.stdout)
            cancelled = write_json(
                base / "cancelled.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "cancelled",
                    "observed_at": later_than(
                        initial_state["host"]["observed_at"]
                    ),
                    "source": "codex-host",
                },
            )
            observed = command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(cancelled),
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertEqual(observed.returncode, 0, observed.stdout)
        self.assertEqual(json.loads(observed.stdout)["status"], "cancelled")
        self.assertEqual(resumed.returncode, 0, resumed.stdout)
        self.assertEqual(json.loads(resumed.stdout)["status"], "cancelled")

    def test_tampering_review_rewrite_and_symlink_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            reviewed = record_review(
                base,
                root,
                state_dir,
                "integration_review",
                "integration-1",
            )
            self.assertEqual(reviewed.returncode, 0)
            review_path = state_dir / "reviews" / "integration-1.json"
            value = json.loads(review_path.read_text(encoding="utf-8"))
            value["summary"] = "rewritten"
            write_json(review_path, value)
            rewritten = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            self.assertNotEqual(rewritten.returncode, 0)
            self.assertIn("not ledger-bound", rewritten.stdout)

            ledger = state_dir / goal_ledger.LEDGER_NAME
            original = ledger.read_text(encoding="utf-8")
            first = json.loads(original.splitlines()[0])
            first["payload"]["objective"] = "tampered"
            ledger.write_text(
                json.dumps(first) + "\n" + "\n".join(original.splitlines()[1:]) + "\n",
                encoding="utf-8",
            )
            tampered = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            self.assertNotEqual(tampered.returncode, 0)
            self.assertIn("invalid event hash", tampered.stdout)

    def test_pending_torn_write_recovers_exact_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(base, root)
            current = current_snapshot(root, state_dir)
            event = goal_ledger.make_event(
                state,
                goal_id=state["goal_id"],
                event_type="host_state_observed",
                payload={
                    "host": {
                        "goal_id": "host-goal-sample",
                        "last_observed_state": "waiting",
                        "observed_at": "2026-07-27T00:50:00Z",
                        "source": "codex-host",
                    }
                },
                workspace=current,
            )

            def torn_append(path: Path, value: dict[str, object]) -> None:
                encoded = goal_primitives.canonical_bytes(value)
                with path.open("ab") as handle:
                    handle.write(encoded[: max(1, len(encoded) // 2)])
                    handle.flush()
                    os.fsync(handle.fileno())
                raise OSError("simulated interruption")

            with mock.patch.object(
                goal_ledger, "append_event", side_effect=torn_append
            ):
                with self.assertRaises(OSError):
                    goal_ledger.persist_event(state_dir, state, event)
            self.assertTrue((state_dir / goal_ledger.PENDING_NAME).is_file())
            self.assertTrue(goal_ledger.recover_pending(state_dir))
            loaded, errors, _snapshot, events = goal_ledger.load_and_verify(
                root,
                state_dir,
                check_workspace=True,
            )
        self.assertEqual(errors, [])
        self.assertEqual(len(events), 2)
        self.assertEqual(
            loaded["host"]["last_observed_state"], "waiting"
        )

    def test_fixed_state_artifact_symlink_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            ledger = state_dir / goal_ledger.LEDGER_NAME
            retained = state_dir / "retained-ledger"
            ledger.rename(retained)
            ledger.symlink_to(retained)
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn("must not be a symlink", resumed.stdout)

    def test_immutable_artifact_parent_symlink_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(
                base, root, assurance="strict"
            )
            plans = state_dir / "plans"
            retained = base / "outside-plans"
            plans.rename(retained)
            plans.symlink_to(retained, target_is_directory=True)
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(resumed.returncode, 0)
        self.assertIn(
            "state artifact directory must not be a symlink: plans",
            resumed.stdout,
        )

    def test_suspended_host_states_block_active_work_but_allow_checkpoint(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, initial_state = initialize(
                base,
                root,
                assurance="light",
            )
            revision = write_json(
                base / "suspended-revision.json",
                {
                    "reason": "This must wait for host reactivation.",
                    "acceptance": initial_state["acceptance"],
                },
            )
            timestamp = initial_state["host"]["observed_at"]
            for index, host_state in enumerate(
                ("waiting", "paused", "blocked"),
                start=1,
            ):
                timestamp = later_than(timestamp)
                observation = write_json(
                    base / f"{host_state}.json",
                    {
                        "goal_id": "host-goal-sample",
                        "state": host_state,
                        "observed_at": timestamp,
                        "source": "codex-host",
                    },
                )
                observed = command(
                    "observe-host",
                    "--root",
                    str(root),
                    "--state-dir",
                    str(state_dir),
                    "--observation",
                    str(observation),
                )
                self.assertEqual(observed.returncode, 0, observed.stdout)

                state = json.loads(
                    (state_dir / goal_ledger.STATE_NAME).read_text(
                        encoding="utf-8"
                    )
                )
                snapshot = story_snapshot(
                    root,
                    state_dir,
                    ["src/**"],
                    [],
                )
                envelope: dict[str, object] = {
                    "document_type": "quant_story_envelope",
                    "schema_version": 1,
                    "goal_id": state["goal_id"],
                    "story_id": "suspended-story",
                    "project_binding_sha256": state["project_binding"][
                        "identity_sha256"
                    ],
                    "objective": "Do not start while suspended.",
                    "mode": "write",
                    "write_scope": ["src/**"],
                    "protected_scope": [],
                    "depends_on": [],
                    "acceptance": state["acceptance"],
                    "external_effects": "none",
                    "cost_class": "no_billable_action",
                    "baseline_workspace_sha256": snapshot["sha256"],
                    "issued_at": "2026-07-27T00:00:00Z",
                }
                envelope["envelope_sha256"] = goal_runtime.envelope_hash(
                    envelope
                )
                envelope_path = write_json(
                    base / f"{host_state}-envelope.json", envelope
                )
                review_path = write_json(
                    base / f"{host_state}-review.json",
                    review_receipt(
                        state,
                        snapshot["sha256"],
                        "integration_review",
                        f"suspended-review-{index}",
                    ),
                )
                receipt_path = write_json(
                    base / f"{host_state}-final.json",
                    evidence_receipt(root, state_dir),
                )
                active_work = (
                    command(
                        "revise-acceptance",
                        "--root",
                        str(root),
                        "--state-dir",
                        str(state_dir),
                        "--revision",
                        str(revision),
                    ),
                    command(
                        "story-issue",
                        "--root",
                        str(root),
                        "--state-dir",
                        str(state_dir),
                        "--envelope",
                        str(envelope_path),
                    ),
                    command(
                        "review-record",
                        "--root",
                        str(root),
                        "--state-dir",
                        str(state_dir),
                        "--review",
                        str(review_path),
                    ),
                    command(
                        "completion-ready",
                        "--root",
                        str(root),
                        "--state-dir",
                        str(state_dir),
                        "--receipt",
                        str(receipt_path),
                    ),
                )
                for blocked in active_work:
                    self.assertNotEqual(blocked.returncode, 0)
                    self.assertIn(
                        "active-work mutation requires active",
                        blocked.stdout,
                    )

                checkpoint = write_json(
                    base / f"{host_state}-checkpoint.json",
                    {
                        "kind": "progress",
                        "summary": f"Record {host_state} host state.",
                        "acceptance_status": {
                            "a1": {
                                "status": "pending",
                                "evidence_refs": [],
                            }
                        },
                        "blockers": [],
                        "next_action": "Wait for host reactivation.",
                    },
                )
                recorded = command(
                    "checkpoint",
                    "--root",
                    str(root),
                    "--state-dir",
                    str(state_dir),
                    "--checkpoint",
                    str(checkpoint),
                )
                self.assertEqual(recorded.returncode, 0, recorded.stdout)
                self.assertEqual(
                    json.loads(recorded.stdout)["status"], host_state
                )

    def test_story_return_and_accept_require_active_host(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(base, root)
            snapshot = story_snapshot(root, state_dir, ["src/**"], [])
            envelope: dict[str, object] = {
                "document_type": "quant_story_envelope",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-suspended",
                "project_binding_sha256": state["project_binding"][
                    "identity_sha256"
                ],
                "objective": "Return only while the host is active.",
                "mode": "write",
                "write_scope": ["src/**"],
                "protected_scope": [],
                "depends_on": [],
                "acceptance": state["acceptance"],
                "external_effects": "none",
                "cost_class": "no_billable_action",
                "baseline_workspace_sha256": snapshot["sha256"],
                "issued_at": "2026-07-27T00:00:00Z",
            }
            envelope["envelope_sha256"] = goal_runtime.envelope_hash(envelope)
            envelope_path = write_json(base / "envelope.json", envelope)
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
                "bounded change\n", encoding="utf-8"
            )
            current = current_snapshot(root, state_dir)
            baseline = json.loads(
                (
                    state_dir
                    / "stories"
                    / "story-suspended.baseline.json"
                ).read_text(encoding="utf-8")
            )
            receipt: dict[str, object] = {
                "document_type": "quant_story_receipt",
                "schema_version": 1,
                "goal_id": state["goal_id"],
                "story_id": "story-suspended",
                "envelope_sha256": envelope["envelope_sha256"],
                "status": "ready_for_review",
                "summary": "The bounded change was verified.",
                "changed_paths": goal_runtime.changed_since(
                    baseline, current
                ),
                "claims": [
                    {
                        "acceptance_id": "a1",
                        "status": "passed",
                        "evidence_ids": ["e1"],
                    }
                ],
                "evidence": [
                    {
                        "id": "e1",
                        "kind": "inspection",
                        "status": "passed",
                        "summary": "The source was inspected.",
                    }
                ],
                "workspace_sha256": current["sha256"],
                "completed_at": "2026-07-27T00:05:00Z",
            }
            receipt["receipt_sha256"] = goal_runtime.receipt_hash(receipt)
            receipt_path = write_json(base / "story-receipt.json", receipt)
            first_time = later_than(state["host"]["observed_at"])
            waiting = write_json(
                base / "waiting-story.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "waiting",
                    "observed_at": first_time,
                    "source": "codex-host",
                },
            )
            command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(waiting),
            )
            blocked_return = command(
                "story-return",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            active_time = later_than(first_time)
            active = write_json(
                base / "active-story.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "active",
                    "observed_at": active_time,
                    "source": "codex-host",
                },
            )
            command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(active),
            )
            returned = command(
                "story-return",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            paused = write_json(
                base / "paused-story.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "paused",
                    "observed_at": later_than(active_time),
                    "source": "codex-host",
                },
            )
            command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(paused),
            )
            blocked_accept = command(
                "story-accept",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--story-id",
                "story-suspended",
            )
        self.assertNotEqual(blocked_return.returncode, 0)
        self.assertIn(
            "active-work mutation requires active", blocked_return.stdout
        )
        self.assertEqual(returned.returncode, 0, returned.stdout)
        self.assertNotEqual(blocked_accept.returncode, 0)
        self.assertIn(
            "active-work mutation requires active", blocked_accept.stdout
        )

    def test_completed_readback_does_not_reanchor_stale_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, state = initialize(
                base,
                root,
                assurance="light",
            )
            receipt_path = write_json(
                base / "final.json",
                evidence_receipt(root, state_dir),
            )
            ready = command(
                "completion-ready",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            self.assertEqual(ready.returncode, 0, ready.stdout)
            (root / "src" / "app.txt").write_text(
                "changed after proof\n", encoding="utf-8"
            )
            completed = write_json(
                base / "completed-after-drift.json",
                {
                    "goal_id": "host-goal-sample",
                    "state": "completed",
                    "observed_at": later_than(
                        state["host"]["observed_at"]
                    ),
                    "source": "codex-host",
                },
            )
            observed = command(
                "observe-host",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--observation",
                str(completed),
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            persisted = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
        for result in (observed, resumed):
            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "review_required")
            self.assertIn(
                "completion_ready_inconsistent", result.stdout
            )
            self.assertIn("workspace snapshot is stale", result.stdout)
        self.assertEqual(
            persisted["host"]["last_observed_state"], "completed"
        )
        self.assertIsNotNone(persisted["completion_ready"])

    def test_state_root_symlink_and_directory_replacement_are_blocked(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            retained = base / "retained-state"
            state_dir.rename(retained)
            state_dir.symlink_to(retained, target_is_directory=True)
            symlinked = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            state_dir.unlink()
            shutil.copytree(retained, state_dir)
            replaced = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
        self.assertNotEqual(symlinked.returncode, 0)
        self.assertIn(
            "declared state directory must not be a symlink",
            symlinked.stdout,
        )
        self.assertNotEqual(replaced.returncode, 0)
        self.assertIn(
            "goal ledger state-root binding changed",
            replaced.stdout,
        )

    def test_strict_revision_requires_current_plan_or_explicit_carry_forward(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, initial_state = initialize(
                base,
                root,
                assurance="strict",
            )
            material = write_json(
                base / "material-revision.json",
                {
                    "reason": "Change the required result.",
                    "acceptance": [
                        {
                            "id": "a1",
                            "text": "The materially changed result is verified.",
                        }
                    ],
                    "steering": [
                        {
                            "op": "clarify",
                            "source_ids": ["a1"],
                            "target_ids": ["a1"],
                        }
                    ],
                },
            )
            missing_plan = command(
                "revise-acceptance",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--revision",
                str(material),
            )
            invalid_carry = command(
                "revise-acceptance",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--revision",
                str(material),
                "--carry-forward-plan",
            )
            unchanged = write_json(
                base / "non-material-revision.json",
                {
                    "reason": "Record a non-material wording review.",
                    "acceptance": initial_state["acceptance"],
                },
            )
            carried = command(
                "revise-acceptance",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--revision",
                str(unchanged),
                "--carry-forward-plan",
            )
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
        self.assertNotEqual(missing_plan.returncode, 0)
        self.assertIn(
            "requires a current reviewed Plan",
            missing_plan.stdout,
        )
        self.assertNotEqual(invalid_carry.returncode, 0)
        self.assertIn(
            "limited to non-material revisions",
            invalid_carry.stdout,
        )
        self.assertEqual(carried.returncode, 0, carried.stdout)
        self.assertEqual(state["acceptance_revision"], 2)
        self.assertEqual(state["plan"]["acceptance_revision"], 2)
        self.assertEqual(state["plan"]["revision"], 2)
        self.assertEqual(
            state["plan"]["carried_forward_from_revision"],
            1,
        )
        self.assertEqual(
            state["plan"]["sha256"],
            state["plan_revisions"][0]["sha256"],
        )

    def test_terminal_host_goal_cannot_reopen_through_observation(
        self,
    ) -> None:
        for terminal_state in ("completed", "cancelled", "superseded"):
            with self.subTest(terminal_state=terminal_state):
                with tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    root = make_project(base)
                    state_dir, initial_state = initialize(
                        base,
                        root,
                        assurance="light",
                    )
                    terminal_time = later_than(
                        initial_state["host"]["observed_at"]
                    )
                    terminal = write_json(
                        base / f"{terminal_state}.json",
                        {
                            "goal_id": "host-goal-sample",
                            "state": terminal_state,
                            "observed_at": terminal_time,
                            "source": "codex-host",
                        },
                    )
                    command(
                        "observe-host",
                        "--root",
                        str(root),
                        "--state-dir",
                        str(state_dir),
                        "--observation",
                        str(terminal),
                    )
                    before = json.loads(
                        (state_dir / goal_ledger.STATE_NAME).read_text(
                            encoding="utf-8"
                        )
                    )
                    active = write_json(
                        base / f"{terminal_state}-active.json",
                        {
                            "goal_id": "host-goal-sample",
                            "state": "active",
                            "observed_at": later_than(terminal_time),
                            "source": "codex-host",
                        },
                    )
                    reopened = command(
                        "observe-host",
                        "--root",
                        str(root),
                        "--state-dir",
                        str(state_dir),
                        "--observation",
                        str(active),
                    )
                    after = json.loads(
                        (state_dir / goal_ledger.STATE_NAME).read_text(
                            encoding="utf-8"
                        )
                    )
                self.assertNotEqual(reopened.returncode, 0)
                self.assertIn(
                    "cannot reopen through ordinary observation",
                    reopened.stdout,
                )
                self.assertEqual(
                    after["host"]["last_observed_state"],
                    terminal_state,
                )
                self.assertEqual(after["ledger"], before["ledger"])

    def test_continuation_capsule_is_persisted_and_resumed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_project(base)
            state_dir, _state = initialize(base, root)
            checkpoint = write_json(
                base / "capsule-checkpoint.json",
                {
                    "kind": "research",
                    "summary": "A free source fallback remains open.",
                    "acceptance_status": {
                        "a1": {
                            "status": "partial",
                            "evidence_refs": ["free-source-a"],
                        }
                    },
                    "blockers": [
                        {
                            "id": "source-gap",
                            "status": "open",
                            "required": True,
                            "summary": "The first free source is incomplete.",
                            "next_action": "Try another no-billing free source.",
                        }
                    ],
                    "next_action": "Try another no-billing free source.",
                },
            )
            recorded_checkpoint = command(
                "checkpoint",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--checkpoint",
                str(checkpoint),
            )
            self.assertEqual(
                recorded_checkpoint.returncode,
                0,
                recorded_checkpoint.stdout,
            )
            capsule_path = write_json(
                base / "capsule.json",
                {
                    "kind": "handoff",
                    "context_sha256": goal_ledger.digest(
                        {"context": "free-source-research"}
                    ),
                    "open_work": ["find-free-source-b"],
                    "worker_states": [
                        {
                            "id": "source-scout",
                            "status": "waiting",
                            "story_id": None,
                        }
                    ],
                    "current_evidence_refs": ["free-source-a"],
                    "stale_evidence_refs": ["old-source-snapshot"],
                    "pending_authority": ["public-readback"],
                    "no_repeat": ["do-not-query-source-a-again"],
                    "next_action": "Try another no-billing free source.",
                },
            )
            recorded = command(
                "continuation-capsule",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--capsule",
                str(capsule_path),
            )
            state = json.loads(
                (state_dir / goal_ledger.STATE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            events, errors = goal_ledger.read_ledger(
                state_dir / goal_ledger.LEDGER_NAME
            )
            resumed = command(
                "resume",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
            )
            paid_capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
            paid_capsule["next_action"] = (
                "Use a paid market data provider subscription."
            )
            paid_path = write_json(base / "paid-capsule.json", paid_capsule)
            paid = command(
                "continuation-capsule",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--capsule",
                str(paid_path),
            )
        self.assertEqual(recorded.returncode, 0, recorded.stdout)
        self.assertEqual(errors, [])
        self.assertEqual(events[-1]["type"], "continuation_capsule_recorded")
        capsule = state["continuation_capsule"]
        self.assertEqual(capsule["acceptance_revision"], 1)
        self.assertEqual(capsule["plan_revision"], 0)
        self.assertEqual(capsule["blocker_ids"], ["source-gap"])
        self.assertEqual(
            capsule["no_repeat"],
            ["do-not-query-source-a-again"],
        )
        self.assertEqual(resumed.returncode, 0, resumed.stdout)
        projected = json.loads(resumed.stdout)["result"]["continuation"]
        self.assertTrue(projected["capsule_is_current"])
        self.assertEqual(projected["capsule"], capsule)
        self.assertNotEqual(paid.returncode, 0)
        self.assertIn(
            "paid data acquisition is outside",
            paid.stdout,
        )


if __name__ == "__main__":
    unittest.main()
