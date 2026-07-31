from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "shared" / "scripts"
TESTS = ROOT / "tests"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import capability_model
import goal_runtime
import validate_evidence_v3
from test_evidence_v3 import evidence, manifest_base, receipt_base, run
from test_goal_runtime import command as goal_command
from test_goal_runtime import make_repo


def validation_args(root: Path, manifest: Path) -> argparse.Namespace:
    return argparse.Namespace(
        project_root=str(root),
        manifest=str(manifest),
        goal_state=None,
        require_capability=[],
        require_automation=False,
        require_release=False,
        minimum_assurance=None,
        input_binding_capture=None,
    )


class EvidenceV3RedTeamTests(unittest.TestCase):
    def test_every_paid_alias_is_rejected_from_receipt_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_base()), encoding="utf-8"
            )
            baseline = receipt_base(manifest_path)
            args = validation_args(root, manifest_path)
            for field in sorted(capability_model.PAID_TRANSITION_FIELDS):
                with self.subTest(field=field):
                    receipt = copy.deepcopy(baseline)
                    receipt["cost_authority"][field] = True
                    errors = validate_evidence_v3.validate_receipt(
                        receipt, args
                    )
                    self.assertTrue(
                        any(field in error for error in errors), errors
                    )

    def test_receipt_policy_scan_preserves_inert_metadata_but_blocks_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_base()), encoding="utf-8"
            )
            args = validation_args(root, manifest_path)
            benign = receipt_base(manifest_path)
            benign["gates"]["contract"]["evidence"][0]["extensions"] = {
                "token_count": 4096,
                "charge_density_unit": "C/cm2",
                "database_upgrade_notes": "migrate SQLite to Postgres",
                "add_on_module": "optional visualizer",
                "note": "paid fallback enabled",
            }
            self.assertEqual(
                validate_evidence_v3.validate_receipt(benign, args),
                [],
            )

            unsafe = copy.deepcopy(benign)
            unsafe["gates"]["contract"]["evidence"][0]["extensions"].update(
                {
                    "PAYGEnabled": True,
                    "observed_config": (
                        "connectionString=" + "c" * 24
                    ),
                }
            )
            errors = validate_evidence_v3.validate_receipt(unsafe, args)

        joined = "\n".join(errors)
        self.assertIn("PAYGEnabled must be false", joined)
        self.assertIn("contains an inline credential", joined)

    def test_unknown_secret_and_malformed_scope_fail_without_traceback(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_base()), encoding="utf-8"
            )
            receipt = receipt_base(manifest_path)
            receipt["api_token"] = "fixture-secret-value"
            receipt["scope"]["capabilities"] = [{}]
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(root, manifest_path, receipt_path)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("api_token", completed.stdout)
        self.assertIn("scope.capabilities", completed.stdout)
        self.assertNotIn("Traceback", completed.stderr)

    def test_extra_failed_gate_is_not_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_base()), encoding="utf-8"
            )
            receipt = receipt_base(manifest_path)
            receipt["gates"]["independent_check"] = {
                "status": "failed",
                "evidence": [evidence("The check found a defect.")],
            }
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(root, manifest_path, receipt_path)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "supplied gate 'independent_check' must be passed",
            completed.stdout,
        )

    def test_standalone_receipt_cannot_omit_manifest_capability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = manifest_base()
            manifest["assurance"] = "standard"
            manifest["capabilities"] = ["web-ui"]
            manifest["capability_config"] = {"web-ui": {}}
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            receipt = receipt_base(manifest_path)
            receipt["scope"]["assurance"] = "standard"
            receipt["required_gates"].append("verification")
            receipt["gates"]["verification"] = {
                "status": "passed",
                "evidence": [evidence("The bounded verification passed.")],
            }
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(root, manifest_path, receipt_path)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "standalone receipt scope must include all manifest capabilities",
            completed.stdout,
        )

    def test_manifestless_research_goal_completes_with_acceptance_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_repo(base)
            state_dir = base / "state"
            objective = "Verify a bounded research conclusion."
            initialized = goal_command(
                "init",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--goal-id",
                "research-goal",
                "--project-id",
                "sample",
                "--objective",
                objective,
                "--acceptance",
                "a1=The conclusion is supported by evidence.",
                "--assurance",
                "light",
            )
            self.assertEqual(
                initialized.returncode,
                0,
                initialized.stdout + initialized.stderr,
            )
            state = goal_runtime.strict_json(
                state_dir / goal_runtime.STATE_NAME
            )
            events, event_errors = goal_runtime.read_ledger(
                state_dir / goal_runtime.LEDGER_NAME
            )
            self.assertEqual(event_errors, [])
            proof = evidence("The research conclusion was independently read.")
            proof_sha = validate_evidence_v3.canonical_sha256(proof)
            head = events[0]["workspace"]["head"] or ""
            receipt: dict[str, object] = {
                "schema_version": 3,
                "project_id": "sample",
                "objective": objective,
                "scope": {
                    "capabilities": [],
                    "assurance": "light",
                    "remote_actions": False,
                    "analysis_control_ids": [],
                },
                "required_gates": ["contract", "cost"],
                "gates": {
                    "contract": {
                        "status": "passed",
                        "evidence": [proof],
                    },
                    "cost": {
                        "status": "passed",
                        "evidence": [
                            evidence("No remote or billable action occurred.")
                        ],
                    },
                },
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
                    "goal_id": "research-goal",
                    "objective_sha256": state["objective_sha256"],
                    "ledger_tail_sha256": state["ledger"]["tail_sha256"],
                    "acceptance_ids": ["a1"],
                    "acceptance_claims": {
                        "a1": [
                            {
                                "gate": "contract",
                                "evidence_index": 0,
                                "evidence_sha256": proof_sha,
                            }
                        ]
                    },
                },
                "completed_at": "2026-07-26T00:20:00Z",
            }
            receipt_path = base / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            import subprocess

            validated = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_evidence.py"),
                    str(receipt_path),
                    "--project-root",
                    str(root),
                    "--goal-state",
                    str(state_dir / goal_runtime.STATE_NAME),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                validated.returncode,
                0,
                validated.stdout + validated.stderr,
            )
            completed = goal_command(
                "complete",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stdout + completed.stderr,
            )
            revalidated = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_evidence.py"),
                    str(receipt_path),
                    "--project-root",
                    str(root),
                    "--goal-state",
                    str(state_dir / goal_runtime.STATE_NAME),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                revalidated.returncode,
                0,
                revalidated.stdout + revalidated.stderr,
            )
            immutable = goal_command(
                "checkpoint",
                "--root",
                str(root),
                "--state-dir",
                str(state_dir),
                "--summary",
                "Must not mutate a completed goal.",
            )
        self.assertNotEqual(immutable.returncode, 0)
        self.assertIn("status is complete", immutable.stdout)


if __name__ == "__main__":
    unittest.main()
