from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "shared" / "scripts"
SCRIPT = SCRIPTS / "validate_evidence.py"
sys.path.insert(0, str(SCRIPTS))

import capability_model
import goal_ledger
import validate_evidence_v3


POLICY = "zero-spend-unless-user-first-requests-specific-paid-action"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence(summary: str = "Verified.") -> dict[str, object]:
    return {
        "kind": "inspection",
        "status": "verified",
        "summary": summary,
        "source": "deterministic fixture",
        "checked_at": "2026-07-26T00:10:00Z",
    }


def rebind_capture_receipt(receipt_path: Path, capture_path: Path) -> None:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    bound = receipt["gates"]["input_binding"]["evidence"][0]
    bound["capture_sha256"] = sha(capture_path)
    bound["artifact_sha256"] = sha(capture_path)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")


def rebind_analysis_execution_evidence(
    receipt_path: Path,
    capture_path: Path,
    root: Path,
) -> None:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    evidence_items = receipt["gates"]["input_binding"]["evidence"]
    for control in capture["controls"]:
        for phase in ("baseline", "repeat", "variant"):
            run_item = control[phase]
            invocation = json.loads(
                (
                    root / run_item["invocation_artifact"]["path"]
                ).read_text(encoding="utf-8")
            )
            trace = run_item["execution_trace_artifact"]
            matching = [
                item
                for item in evidence_items
                if item.get("artifact_path") == trace["path"]
            ]
            if len(matching) != 1:
                raise AssertionError(
                    f"expected one execution evidence item for {trace['path']}"
                )
            item = matching[0]
            item["source"] = invocation["entrypoint_path"]
            item["command"] = invocation["binding"]["argv"][0]
            item["command_argv"] = invocation["binding"]["argv"]
            item["artifact_sha256"] = trace["sha256"]
            item["extensions"]["analysis_execution"] = {
                "run_id": invocation["run_id"],
                "entrypoint_sha256": invocation["entrypoint_sha256"],
                "input_sha256": invocation["input_sha256"],
                "result_sha256": invocation["result_sha256"],
            }
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")


def manifest_base() -> dict[str, object]:
    return {
        "schema_version": 2,
        "project": {
            "id": "sample",
            "purpose": "Produce a user-visible result.",
        },
        "assurance": "light",
        "profiles": [],
        "capabilities": [],
        "adapters": {},
        "contracts": {"protected_paths": [], "test_commands": []},
        "capability_config": {},
        "authority": {
            "cost_policy": POLICY,
            "paid_action_authority": None,
            "paid_fallback_enabled": False,
        },
        "extensions": {},
    }


def local_cost() -> dict[str, object]:
    return {
        "policy": POLICY,
        "classification": "no_billable_action",
        "decision": "allow",
        "paid_action_requested": False,
        "actions": [],
    }


def remote_cost() -> dict[str, object]:
    action: dict[str, object] = {
        "action_id": "release-1",
        "provider": "github",
        "account_or_project": "owner/sample",
        "resource_or_sku": "repository-release",
        "evidence_source": "provider plan inspection",
        "evidence_checked_at": "2026-07-26T00:05:00Z",
        "classification": "verified_zero_charge",
        "decision": "allow",
        "billing_mode": "hard-free-no-overage",
        "remaining_free_quota": 10,
        "planned_usage": 1,
        "hard_stop_enabled": True,
        "maximum_cost": 0,
    }
    for field in capability_model.PAID_TRANSITION_FIELDS:
        action[field] = False
    return {
        "policy": POLICY,
        "classification": "verified_zero_charge",
        "decision": "allow",
        "paid_action_requested": False,
        "actions": [action],
    }


def receipt_base(manifest_path: Path) -> dict[str, object]:
    return {
        "schema_version": 3,
        "project_id": "sample",
        "objective": "Verify the bounded local deliverable.",
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
                "evidence": [evidence()],
            },
            "cost": {
                "status": "passed",
                "evidence": [evidence("No remote or billable action.")],
            },
        },
        "cost_authority": local_cost(),
        "context": {
            "manifest_sha256": sha(manifest_path),
            "plan_sha256": "",
            "base_commit": "",
            "head_commit": "",
        },
        "goal_binding": None,
        "completed_at": "2026-07-26T00:20:00Z",
    }


def run(
    root: Path,
    manifest: Path,
    receipt: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(receipt),
            "--project-root",
            str(root),
            "--manifest",
            str(manifest),
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def run_without_manifest(
    root: Path,
    receipt: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(receipt),
            "--project-root",
            str(root),
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


class EvidenceV3Tests(unittest.TestCase):
    def test_paid_data_claim_in_proof_prose_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_base()), encoding="utf-8"
            )
            receipt = receipt_base(manifest_path)
            receipt["gates"]["contract"]["evidence"][0]["summary"] = (
                "Subscribed to a paid market-data API and used its "
                "price feed."
            )
            receipt_path = root / "receipt.json"
            receipt_path.write_text(
                json.dumps(receipt), encoding="utf-8"
            )
            blocked = run(root, manifest_path, receipt_path)
            receipt["gates"]["contract"]["evidence"][0]["summary"] = (
                "Paid data was not used."
            )
            receipt_path.write_text(
                json.dumps(receipt), encoding="utf-8"
            )
            safe = run(root, manifest_path, receipt_path)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn(
            "paid data acquisition is outside", blocked.stdout
        )
        self.assertEqual(
            safe.returncode, 0, safe.stdout + safe.stderr
        )

    def test_minimal_local_receipt_passes_without_goal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_base()), encoding="utf-8"
            )
            receipt_path = root / "receipt.json"
            receipt_path.write_text(
                json.dumps(receipt_base(manifest_path)),
                encoding="utf-8",
            )
            completed = run(root, manifest_path, receipt_path)
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )
        self.assertIn("capability-derived-v3", completed.stdout)

    def test_computed_gate_and_local_cost_cannot_be_downgraded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_base()), encoding="utf-8"
            )
            receipt = receipt_base(manifest_path)
            receipt["required_gates"] = ["contract"]
            receipt["cost_authority"]["classification"] = (
                "verified_zero_charge"
            )
            receipt_path = root / "receipt.json"
            receipt_path.write_text(
                json.dumps(receipt), encoding="utf-8"
            )
            completed = run(root, manifest_path, receipt_path)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("omits capability-derived gates: cost", completed.stdout)
        self.assertIn(
            "local scope cost classification", completed.stdout
        )

    def test_malformed_scope_fails_closed_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_base()), encoding="utf-8"
            )
            receipt = receipt_base(manifest_path)
            receipt["scope"]["capabilities"] = [{}]
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(root, manifest_path, receipt_path)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("scope.capabilities", completed.stdout)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)

    def test_standalone_scope_cannot_omit_manifest_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = manifest_base()
            manifest["capabilities"] = ["web-ui"]
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            receipt = receipt_base(manifest_path)
            receipt["scope"]["assurance"] = "standard"
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(root, manifest_path, receipt_path)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "standalone receipt scope must include all manifest capabilities",
            completed.stdout,
        )

    def test_any_supplied_failed_gate_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_base()), encoding="utf-8"
            )
            receipt = receipt_base(manifest_path)
            receipt["gates"]["optional_probe"] = {
                "status": "blocked",
                "evidence": [evidence("The probe was blocked.")],
            }
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(root, manifest_path, receipt_path)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "supplied gate 'optional_probe' must be passed",
            completed.stdout,
        )

    def test_unknown_secret_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_base()), encoding="utf-8"
            )
            receipt = receipt_base(manifest_path)
            receipt["gates"]["contract"]["evidence"][0]["api_token"] = (
                "not-a-real-secret"
            )
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(root, manifest_path, receipt_path)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unknown gates.contract.evidence", completed.stdout)
        self.assertIn("must not contain a secret value", completed.stdout)

    def test_every_paid_alias_is_fail_closed(self) -> None:
        for field in capability_model.PAID_TRANSITION_FIELDS:
            with self.subTest(field=field):
                receipt = {"cost_authority": remote_cost()}
                receipt["cost_authority"]["actions"][0][field] = True
                errors: list[str] = []
                validate_evidence_v3.validate_cost(
                    receipt,
                    True,
                    datetime(2026, 7, 26, 0, 20, tzinfo=timezone.utc),
                    errors,
                )
                self.assertTrue(
                    any(
                        f".{field} must be false" in error
                        for error in errors
                    ),
                    errors,
                )

    def capability_fixture(
        self, root: Path, capability: str
    ) -> tuple[Path, Path]:
        manifest = manifest_base()
        manifest["capabilities"] = [capability]
        if capability == "external-data":
            manifest["capability_config"] = {
                capability: {
                    "sources": [
                        {
                            "id": "prices",
                            "provider": "fixture",
                            "role": "required",
                            "rights_policy": "fixture-only",
                            "access_eligibility": (
                                "permanently-free-no-billing"
                            ),
                            "paid_fallback_enabled": False,
                        }
                    ]
                }
            }
        elif capability == "scheduled-automation":
            entrypoint = root / "refresh.sh"
            entrypoint.write_text("#!/bin/sh\n", encoding="utf-8")
            manifest["capability_config"] = {
                capability: {
                    "schedules": [
                        {
                            "id": "daily-refresh",
                            "entrypoint": "refresh.sh",
                            "schedule": "daily",
                            "timezone": "UTC",
                            "last_good_policy": "retain",
                            "retry_ceiling": 1,
                            "concurrency_ceiling": 1,
                            "cost_preflight": {
                                "precedes_remote_work": True
                            },
                        }
                    ]
                }
            }
        elif capability == "publication":
            manifest["capability_config"] = {
                capability: {
                    "last_good_policy": "retain",
                    "targets": [
                        {
                            "id": "public-json",
                            "public_url": "https://example.invalid/result.json",
                        }
                    ],
                }
            }
        elif capability == "remote-release":
            manifest["project"]["repository"] = "owner/sample"
            manifest["adapters"] = {"scm": "github"}
            manifest["capability_config"] = {
                capability: {
                    "kind": "scm",
                    "base_branch": "main",
                    "approved_account": "owner",
                }
            }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        context = capability_model.resolve(manifest)
        receipt = receipt_base(manifest_path)
        receipt["scope"] = {
            "capabilities": [capability],
            "assurance": context["assurance"],
            "remote_actions": capability == "remote-release",
            "analysis_control_ids": [],
        }
        receipt["required_gates"] = context["required_gates"]
        receipt["gates"] = {
            name: {"status": "passed", "evidence": [evidence()]}
            for name in context["required_gates"]
        }
        if capability == "remote-release":
            receipt["cost_authority"] = remote_cost()
        receipt_path = root / "receipt.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        return manifest_path, receipt_path

    def test_capability_gates_require_typed_evidence(self) -> None:
        expected = {
            "external-data": "typed data_identity evidence",
            "scheduled-automation": "typed schedule_identity evidence",
            "publication": "typed publication_identity evidence",
            "public-web": "typed public_readback evidence",
            "remote-release": "typed release_identity evidence",
        }
        for capability, message in expected.items():
            with self.subTest(capability=capability):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest_path, receipt_path = self.capability_fixture(
                        root, capability
                    )
                    completed = run(root, manifest_path, receipt_path)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(message, completed.stdout)

    def test_public_readback_identity_is_bound_to_captured_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, receipt_path = self.capability_fixture(
                root, "public-web"
            )
            capture = root / "public-response.json"
            capture.write_text('{"result":"ok"}\n', encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            item = receipt["gates"]["public_readback"]["evidence"][0]
            item["artifact_path"] = "public-response.json"
            item["artifact_sha256"] = sha(capture)
            item["public_readback"] = {
                "url": "https://example.invalid/result.json",
                "response_sha256": "0" * 64,
                "response_size": capture.stat().st_size,
                "result_identity": "run-1",
            }
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(root, manifest_path, receipt_path)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "response_sha256 must match captured bytes", completed.stdout
        )

    def test_standalone_context_cannot_claim_unverified_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_base()), encoding="utf-8"
            )
            receipt = receipt_base(manifest_path)
            receipt["context"]["plan_sha256"] = "a" * 64
            receipt["context"]["base_commit"] = "b" * 40
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(root, manifest_path, receipt_path)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("cannot claim an unbound plan_sha256", completed.stdout)
        self.assertIn(
            "non-Git standalone context must leave commits empty",
            completed.stdout,
        )

    def goal_fixture(
        self,
        base: Path,
        *,
        runtime_capability: str | None = None,
    ) -> tuple[Path, Path, Path, dict[str, object]]:
        project = base / "project"
        state_dir = base / "state"
        project.mkdir()
        command = [
            sys.executable,
            str(SCRIPTS / "goal_runtime.py"),
            "init",
            "--root",
            str(project),
            "--state-dir",
            str(state_dir),
            "--goal-id",
            "goal-1",
            "--project-id",
            "sample",
            "--objective",
            "Verify the bounded local deliverable.",
            "--acceptance",
            "a1=The evidence is verified.",
            "--assurance",
            "strict" if runtime_capability else "light",
        ]
        if runtime_capability:
            command.extend(["--require-capability", runtime_capability])
        initialized = subprocess.run(
            command, capture_output=True, text=True, check=False
        )
        self.assertEqual(
            initialized.returncode,
            0,
            initialized.stdout + initialized.stderr,
        )
        state_path = state_dir / "goal-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        receipt = {
            "schema_version": 3,
            "project_id": "sample",
            "objective": "Verify the bounded local deliverable.",
            "scope": {
                "capabilities": (
                    [runtime_capability] if runtime_capability else []
                ),
                "assurance": state["assurance"],
                "remote_actions": False,
                "analysis_control_ids": [],
            },
            "required_gates": [],
            "gates": {},
            "cost_authority": local_cost(),
            "context": {
                "manifest_sha256": "",
                "plan_sha256": "",
                "base_commit": "",
                "head_commit": "",
            },
            "goal_binding": {
                "goal_id": state["goal_id"],
                "objective_sha256": state["objective_sha256"],
                "ledger_tail_sha256": state["ledger"]["tail_sha256"],
                "acceptance_ids": ["a1"],
                "acceptance_claims": {},
            },
            "completed_at": "2026-07-26T00:20:00Z",
        }
        context = capability_model.resolve(
            {},
            capabilities=receipt["scope"]["capabilities"],
            assurance=state["assurance"],
        )
        receipt["required_gates"] = context["required_gates"]
        receipt["gates"] = {
            name: {"status": "passed", "evidence": [evidence()]}
            for name in context["required_gates"]
        }
        claimed = receipt["gates"]["contract"]["evidence"][0]
        receipt["goal_binding"]["acceptance_claims"] = {
            "a1": [
                {
                    "gate": "contract",
                    "evidence_index": 0,
                    "evidence_sha256": (
                        validate_evidence_v3.canonical_sha256(claimed)
                    ),
                }
            ]
        }
        receipt_path = base / "receipt.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        return project, state_dir, state_path, receipt

    def test_manifestless_goal_receipt_is_fully_ledger_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project, _, state_path, _ = self.goal_fixture(base)
            receipt_path = base / "receipt.json"
            completed = run_without_manifest(
                project,
                receipt_path,
                "--goal-state",
                str(state_path),
            )
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )

    def test_goal_ledger_tampering_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project, state_dir, state_path, _ = self.goal_fixture(base)
            ledger_path = state_dir / "ledger.jsonl"
            ledger = ledger_path.read_text(encoding="utf-8")
            ledger_path.write_text(
                ledger.replace("Goal initialized", "Tampered goal"),
                encoding="utf-8",
            )
            completed = run_without_manifest(
                project,
                base / "receipt.json",
                "--goal-state",
                str(state_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("invalid event hash", completed.stdout)

    def test_runtime_capability_needs_accepted_write_story(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project, _, state_path, _ = self.goal_fixture(
                base, runtime_capability="multi-agent-write"
            )
            completed = run_without_manifest(
                project,
                base / "receipt.json",
                "--goal-state",
                str(state_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "not active in the verified project or Goal context",
            completed.stdout,
        )

    def test_accepted_write_story_activates_runtime_overlay(self) -> None:
        from tests.test_goal_runtime import (
            command as goal_command,
            final_research_receipt,
            initialize,
            issue_envelope,
            make_repo,
            write_story_receipt,
        )

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project = make_repo(base)
            state_dir = base / "state"
            initialize(
                project,
                state_dir,
                capabilities=["repo-mutation"],
            )
            manifest_path = project / "project-manifest.json"
            envelope_path = base / "write-envelope.json"
            envelope = issue_envelope(
                project,
                state_dir,
                envelope_path,
                write_scope=["src/**"],
            )
            opened = goal_command(
                "story-issue",
                "--root",
                str(project),
                "--state-dir",
                str(state_dir),
                "--envelope",
                str(envelope_path),
            )
            self.assertEqual(opened.returncode, 0, opened.stdout)
            story_receipt = base / "story-receipt.json"
            write_story_receipt(
                project, state_dir, story_receipt, envelope
            )
            accepted = goal_command(
                "story-accept",
                "--root",
                str(project),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(story_receipt),
            )
            self.assertEqual(accepted.returncode, 0, accepted.stdout)
            receipt = final_research_receipt(project, state_dir)
            receipt["scope"]["capabilities"] = [
                "repo-mutation",
                "multi-agent-write",
            ]
            receipt["scope"]["assurance"] = "strict"
            receipt["completed_at"] = "2026-07-26T00:20:00Z"
            context = capability_model.resolve(
                {},
                capabilities=["repo-mutation", "multi-agent-write"],
                assurance="strict",
            )
            receipt["required_gates"] = context["required_gates"]
            receipt["gates"] = {
                name: {"status": "passed", "evidence": [evidence()]}
                for name in context["required_gates"]
            }
            claimed = receipt["gates"]["contract"]["evidence"][0]
            receipt["goal_binding"]["acceptance_claims"]["a1"][0][
                "evidence_sha256"
            ] = validate_evidence_v3.canonical_sha256(claimed)
            receipt["context"]["manifest_sha256"] = sha(manifest_path)
            receipt_path = base / "final.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(
                project,
                manifest_path,
                receipt_path,
                "--goal-state",
                str(state_dir / "goal-state.json"),
            )
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )

    def test_goal_acceptance_claim_must_match_passed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project, _, state_path, receipt = self.goal_fixture(base)
            receipt["goal_binding"]["acceptance_claims"]["a1"][0][
                "evidence_sha256"
            ] = "0" * 64
            receipt_path = base / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run_without_manifest(
                project,
                receipt_path,
                "--goal-state",
                str(state_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "evidence_sha256 does not match evidence", completed.stdout
        )

    def test_host_ledger_validator_rechecks_terminal_candidate_digest(
        self,
    ) -> None:
        from tests.test_goal_ledger import (
            current_snapshot,
            evidence_receipt,
            initialize,
            make_project,
            record_review,
        )

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project = make_project(base)
            state_dir, _state = initialize(
                base,
                project,
                assurance="strict",
            )
            for role, review_id in (
                ("architecture_review", "architect-validator"),
                ("adversarial_qa", "adversarial-validator"),
                ("terminal_critic", "terminal-validator"),
            ):
                reviewed = record_review(
                    base,
                    project,
                    state_dir,
                    role,
                    review_id,
                )
                self.assertEqual(
                    reviewed.returncode,
                    0,
                    reviewed.stdout + reviewed.stderr,
                )
            state, runtime_errors, current, events = (
                goal_ledger.load_and_verify(
                    project,
                    state_dir,
                    check_workspace=True,
                )
            )
            self.assertEqual(runtime_errors, [])
            self.assertIsNotNone(state)
            self.assertEqual(
                current,
                current_snapshot(project, state_dir),
            )
            receipt = evidence_receipt(project, state_dir)
            goal_info = {
                "state": state,
                "events": events,
                "current": current,
                "proven_runtime_capabilities": set(),
                "runtime_kind": "host-ledger-v1",
            }
            errors: list[str] = []
            validate_evidence_v3.validate_host_ledger_evidence_bindings(
                receipt,
                goal_info,
                receipt["gates"],
                errors,
            )
            self.assertEqual(errors, [])
            early_receipt = json.loads(json.dumps(receipt))
            early_receipt["completed_at"] = "2026-07-27T00:05:00Z"
            early_errors: list[str] = []
            validate_evidence_v3.validate_host_ledger_evidence_bindings(
                early_receipt,
                goal_info,
                early_receipt["gates"],
                early_errors,
            )
            self.assertTrue(
                any(
                    "current Review Verdict 'terminal_critic' was recorded "
                    "after receipt completed_at" in error
                    for error in early_errors
                ),
                early_errors,
            )
            receipt["gates"]["cleanup"]["evidence"][0][
                "summary"
            ] = "Changed after terminal review."
            changed_errors: list[str] = []
            validate_evidence_v3.validate_host_ledger_evidence_bindings(
                receipt,
                goal_info,
                receipt["gates"],
                changed_errors,
            )
        self.assertTrue(
            any(
                "does not match terminal critic" in error
                for error in changed_errors
            ),
            changed_errors,
        )

    def input_binding_fixture(
        self, root: Path
    ) -> tuple[Path, Path, Path, dict[str, object]]:
        analysis = root / "analysis"
        captures = root / "captures"
        analysis.mkdir()
        captures.mkdir()
        entrypoint = analysis / "run.py"
        entrypoint.write_text("print('fixture')\n", encoding="utf-8")

        baseline_input = captures / "base-input.json"
        repeat_input = captures / "repeat-input.json"
        variant_input = captures / "variant-input.json"
        baseline_result = captures / "base-result.json"
        repeat_result = captures / "repeat-result.json"
        variant_result = captures / "variant-result.json"
        baseline_input.write_text(
            json.dumps({"lookback_days": 20}), encoding="utf-8"
        )
        repeat_input.write_bytes(baseline_input.read_bytes())
        variant_input.write_text(
            json.dumps({"lookback_days": 60}), encoding="utf-8"
        )
        baseline_result.write_text(
            json.dumps(
                {
                    "project_id": "sample",
                    "run_id": "run-base",
                    "effective_config": {"lookback_days": 20},
                    "summary": {"score": 1.2},
                }
            ),
            encoding="utf-8",
        )
        repeat_result.write_text(
            json.dumps(
                {
                    "project_id": "sample",
                    "run_id": "run-repeat",
                    "effective_config": {"lookback_days": 20},
                    "summary": {"score": 1.2},
                }
            ),
            encoding="utf-8",
        )
        variant_result.write_text(
            json.dumps(
                {
                    "project_id": "sample",
                    "run_id": "run-variant",
                    "effective_config": {"lookback_days": 60},
                    "summary": {"score": 2.4},
                }
            ),
            encoding="utf-8",
        )
        runner = root / "tests" / "e2e" / "input-binding-runner"
        runner.parent.mkdir(parents=True)
        runner.write_text(
            "#!/bin/sh\nprintf '%s\\n' 'fixture UI runtime capture'\n",
            encoding="utf-8",
        )
        runner.chmod(0o755)
        baseline_dispatch = captures / "base-dispatch.json"
        variant_dispatch = captures / "variant-dispatch.json"
        baseline_adopted = captures / "base-adopted-result.json"
        variant_adopted = captures / "variant-adopted-result.json"
        baseline_view = captures / "base-bound-view.json"
        variant_view = captures / "variant-bound-view.json"
        baseline_trace = captures / "base-runtime-trace.bin"
        variant_trace = captures / "variant-runtime-trace.bin"
        baseline_invocation = captures / "base-invocation.json"
        repeat_invocation = captures / "repeat-invocation.json"
        variant_invocation = captures / "variant-invocation.json"
        baseline_analysis_trace = captures / "base-analysis-trace.bin"
        repeat_analysis_trace = captures / "repeat-analysis-trace.bin"
        variant_analysis_trace = captures / "variant-analysis-trace.bin"
        baseline_analysis_trace.write_bytes(b"baseline analysis trace\n")
        repeat_analysis_trace.write_bytes(b"repeat analysis trace\n")
        variant_analysis_trace.write_bytes(b"variant analysis trace\n")
        baseline_dispatch.write_text(
            json.dumps(
                {
                    "mapping": {
                        "frontend_field": "lookbackDays",
                        "canonical_field": "lookback_days",
                        "execution_mapping": "--lookback-days",
                        "entrypoint_sha256": sha(entrypoint),
                    },
                    "request": {
                        "body": {"config": {"lookback_days": 20}}
                    }
                }
            ),
            encoding="utf-8",
        )
        variant_dispatch.write_text(
            json.dumps(
                {
                    "mapping": {
                        "frontend_field": "lookbackDays",
                        "canonical_field": "lookback_days",
                        "execution_mapping": "--lookback-days",
                        "entrypoint_sha256": sha(entrypoint),
                    },
                    "request": {
                        "body": {"config": {"lookback_days": 60}}
                    }
                }
            ),
            encoding="utf-8",
        )
        baseline_adopted.write_bytes(baseline_result.read_bytes())
        variant_adopted.write_bytes(variant_result.read_bytes())
        baseline_view.write_text(
            json.dumps(
                {
                    "control": {
                        "field": "lookbackDays",
                        "applied_value": 20,
                    },
                    "binding": {
                        "status": "bound",
                        "project_id": "sample",
                        "run_id": "run-base",
                        "result_sha256": sha(baseline_result),
                        "result_values": {"/summary/score": 1.2},
                    },
                }
            ),
            encoding="utf-8",
        )
        variant_view.write_text(
            json.dumps(
                {
                    "control": {
                        "field": "lookbackDays",
                        "applied_value": 60,
                    },
                    "binding": {
                        "status": "bound",
                        "project_id": "sample",
                        "run_id": "run-variant",
                        "result_sha256": sha(variant_result),
                        "result_values": {"/summary/score": 2.4},
                    },
                }
            ),
            encoding="utf-8",
        )
        baseline_trace.write_bytes(b"baseline UI runtime trace\n")
        variant_trace.write_bytes(b"variant UI runtime trace\n")

        def write_invocation(
            path: Path,
            run_id: str,
            input_path: Path,
            result_path: Path,
            started_at: str,
            completed_at: str,
            value: int,
        ) -> None:
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project_id": "sample",
                        "run_id": run_id,
                        "entrypoint_path": "analysis/run.py",
                        "entrypoint_sha256": sha(entrypoint),
                        "input_path": input_path.relative_to(root).as_posix(),
                        "input_sha256": sha(input_path),
                        "result_path": result_path.relative_to(root).as_posix(),
                        "result_sha256": sha(result_path),
                        "started_at": started_at,
                        "completed_at": completed_at,
                        "exit_code": 0,
                        "binding": {
                            "kind": "argv-option",
                            "argv": [
                                "analysis/run.py",
                                "--lookback-days",
                                str(value),
                            ],
                            "entrypoint_argv_index": 0,
                        },
                    }
                ),
                encoding="utf-8",
            )

        write_invocation(
            baseline_invocation,
            "run-base",
            baseline_input,
            baseline_result,
            "2026-07-26T00:01:10Z",
            "2026-07-26T00:01:50Z",
            20,
        )
        write_invocation(
            repeat_invocation,
            "run-repeat",
            repeat_input,
            repeat_result,
            "2026-07-26T00:05:10Z",
            "2026-07-26T00:05:50Z",
            20,
        )
        write_invocation(
            variant_invocation,
            "run-variant",
            variant_input,
            variant_result,
            "2026-07-26T00:03:10Z",
            "2026-07-26T00:03:50Z",
            60,
        )

        def captured_artifact(
            path: Path, media_type: str
        ) -> dict[str, object]:
            return {
                "path": path.relative_to(root).as_posix(),
                "size": len(path.read_bytes()),
                "sha256": sha(path),
                "media_type": media_type,
            }

        manifest = manifest_base()
        manifest["assurance"] = "strict"
        manifest["capabilities"] = ["analysis-input-binding"]
        manifest["capability_config"] = {
            "analysis": {
                "authoritative_entrypoints": ["analysis/run.py"],
                "result_identity_fields": ["project_id", "run_id"],
                "result_identity_pointers": ["/project_id", "/run_id"],
            },
            "analysis-input-binding": {
                "controls": [
                    {
                        "id": "lookback-days",
                        "kind": "analysis",
                        "frontend_field": "lookbackDays",
                        "canonical_field": "lookback_days",
                        "execution_mapping": "--lookback-days",
                        "execution_binding": {
                            "kind": "argv-option",
                            "locator": "--lookback-days",
                        },
                        "default_source": "analysis default",
                        "input_pointer": "/lookback_days",
                        "effective_value_pointer": (
                            "/effective_config/lookback_days"
                        ),
                        "result_paths": ["/summary/score"],
                        "runtime_binding_contract": {
                            "dispatch_input_pointer": (
                                "/request/body/config"
                            ),
                            "dispatch_frontend_field_pointer": (
                                "/mapping/frontend_field"
                            ),
                            "dispatch_canonical_field_pointer": (
                                "/mapping/canonical_field"
                            ),
                            "dispatch_execution_mapping_pointer": (
                                "/mapping/execution_mapping"
                            ),
                            "dispatch_entrypoint_sha256_pointer": (
                                "/mapping/entrypoint_sha256"
                            ),
                            "view_control_field_pointer": "/control/field",
                            "view_applied_value_pointer": (
                                "/control/applied_value"
                            ),
                            "view_binding_status_pointer": "/binding/status",
                            "view_project_id_pointer": (
                                "/binding/project_id"
                            ),
                            "view_run_id_pointer": "/binding/run_id",
                            "view_result_sha256_pointer": (
                                "/binding/result_sha256"
                            ),
                            "view_result_values_pointer": (
                                "/binding/result_values"
                            ),
                        },
                    }
                ]
            },
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        capture: dict[str, object] = {
            "schema_version": 2,
            "project_id": "sample",
            "generated_at": "2026-07-26T00:08:00Z",
            "analysis_entrypoint": {
                "path": "analysis/run.py",
                "sha256": sha(entrypoint),
            },
            "capture_driver": {
                "adapter_id": "fixture-ui-driver",
                "tool": "fixture-driver",
                "tool_version": "1.0",
                "runner_path": "tests/e2e/input-binding-runner",
                "runner_sha256": sha(runner),
                "runner_argv_index": 0,
                "command_argv": [
                    "tests/e2e/input-binding-runner",
                ],
                "exit_code": 0,
            },
            "controls": [
                {
                    "control_id": "lookback-days",
                    "baseline": {
                        "entrypoint_sha256": sha(entrypoint),
                        "input_path": "captures/base-input.json",
                        "input_sha256": sha(baseline_input),
                        "result_path": "captures/base-result.json",
                        "result_sha256": sha(baseline_result),
                        "invocation_artifact": captured_artifact(
                            baseline_invocation, "application/json"
                        ),
                        "execution_trace_artifact": captured_artifact(
                            baseline_analysis_trace,
                            "application/octet-stream",
                        ),
                        "run_id": "run-base",
                        "started_at": "2026-07-26T00:01:00Z",
                        "completed_at": "2026-07-26T00:02:00Z",
                        "exit_code": 0,
                    },
                    "variant": {
                        "entrypoint_sha256": sha(entrypoint),
                        "input_path": "captures/variant-input.json",
                        "input_sha256": sha(variant_input),
                        "result_path": "captures/variant-result.json",
                        "result_sha256": sha(variant_result),
                        "invocation_artifact": captured_artifact(
                            variant_invocation, "application/json"
                        ),
                        "execution_trace_artifact": captured_artifact(
                            variant_analysis_trace,
                            "application/octet-stream",
                        ),
                        "run_id": "run-variant",
                        "started_at": "2026-07-26T00:03:00Z",
                        "completed_at": "2026-07-26T00:04:00Z",
                        "exit_code": 0,
                    },
                    "repeat": {
                        "entrypoint_sha256": sha(entrypoint),
                        "input_path": "captures/repeat-input.json",
                        "input_sha256": sha(repeat_input),
                        "result_path": "captures/repeat-result.json",
                        "result_sha256": sha(repeat_result),
                        "invocation_artifact": captured_artifact(
                            repeat_invocation, "application/json"
                        ),
                        "execution_trace_artifact": captured_artifact(
                            repeat_analysis_trace,
                            "application/octet-stream",
                        ),
                        "run_id": "run-repeat",
                        "started_at": "2026-07-26T00:05:00Z",
                        "completed_at": "2026-07-26T00:06:00Z",
                        "exit_code": 0,
                    },
                    "baseline_runtime": {
                        "capture_id": "lookback-base-runtime",
                        "session_id": "ui-session-base",
                        "started_at": "2026-07-26T00:00:00Z",
                        "control_committed_at": "2026-07-26T00:00:15Z",
                        "dispatch_observed_at": "2026-07-26T00:00:30Z",
                        "result_observed_at": "2026-07-26T00:02:10Z",
                        "view_bound_at": "2026-07-26T00:02:20Z",
                        "completed_at": "2026-07-26T00:02:30Z",
                        "dispatch_artifact": captured_artifact(
                            baseline_dispatch, "application/json"
                        ),
                        "adopted_result_artifact": captured_artifact(
                            baseline_adopted, "application/json"
                        ),
                        "view_artifact": captured_artifact(
                            baseline_view, "application/json"
                        ),
                        "trace_artifact": captured_artifact(
                            baseline_trace, "application/octet-stream"
                        ),
                    },
                    "variant_runtime": {
                        "capture_id": "lookback-variant-runtime",
                        "session_id": "ui-session-variant",
                        "started_at": "2026-07-26T00:02:40Z",
                        "control_committed_at": "2026-07-26T00:02:45Z",
                        "dispatch_observed_at": "2026-07-26T00:02:50Z",
                        "result_observed_at": "2026-07-26T00:04:10Z",
                        "view_bound_at": "2026-07-26T00:04:20Z",
                        "completed_at": "2026-07-26T00:04:30Z",
                        "dispatch_artifact": captured_artifact(
                            variant_dispatch, "application/json"
                        ),
                        "adopted_result_artifact": captured_artifact(
                            variant_adopted, "application/json"
                        ),
                        "view_artifact": captured_artifact(
                            variant_view, "application/json"
                        ),
                        "trace_artifact": captured_artifact(
                            variant_trace, "application/octet-stream"
                        ),
                    },
                }
            ],
        }
        capture_path = root / "capture.json"
        capture_path.write_text(json.dumps(capture), encoding="utf-8")
        receipt = receipt_base(manifest_path)
        receipt["scope"] = {
            "capabilities": ["analysis-input-binding"],
            "assurance": "strict",
            "remote_actions": False,
            "analysis_control_ids": ["lookback-days"],
        }
        context = capability_model.resolve(
            {
                "capabilities": ["analysis-input-binding"],
                "profiles": [],
                "assurance": "strict",
                "adapters": {},
                "capability_config": manifest["capability_config"],
            }
        )
        required = context["required_gates"]
        receipt["required_gates"] = required
        receipt["gates"] = {
            name: {
                "status": "passed",
                "evidence": [evidence()],
            }
            for name in required
        }
        receipt["gates"]["input_binding"]["evidence"][0][
            "capture_sha256"
        ] = sha(capture_path)
        receipt["gates"]["input_binding"]["evidence"][0].update(
            {
                "artifact_path": "capture.json",
                "artifact_sha256": sha(capture_path),
            }
        )
        for invocation_path, trace_path in (
            (baseline_invocation, baseline_analysis_trace),
            (repeat_invocation, repeat_analysis_trace),
            (variant_invocation, variant_analysis_trace),
        ):
            invocation = json.loads(
                invocation_path.read_text(encoding="utf-8")
            )
            receipt["gates"]["input_binding"]["evidence"].append(
                {
                    "kind": "command",
                    "status": "verified",
                    "summary": (
                        "Authoritative analysis command completed and "
                        "produced the bound result."
                    ),
                    "source": invocation["entrypoint_path"],
                    "checked_at": "2026-07-26T00:08:00Z",
                    "command": invocation["binding"]["argv"][0],
                    "command_argv": invocation["binding"]["argv"],
                    "exit_code": 0,
                    "artifact_path": trace_path.relative_to(root).as_posix(),
                    "artifact_sha256": sha(trace_path),
                    "extensions": {
                        "analysis_execution": {
                            "run_id": invocation["run_id"],
                            "entrypoint_sha256": invocation[
                                "entrypoint_sha256"
                            ],
                            "input_sha256": invocation["input_sha256"],
                            "result_sha256": invocation["result_sha256"],
                        }
                    },
                }
            )
        for trace_path in (baseline_trace, variant_trace):
            receipt["gates"]["input_binding"]["evidence"].append(
                {
                    "kind": "command",
                    "status": "verified",
                    "summary": "UI driver captured dispatch and bound view.",
                    "source": "fixture-ui-driver",
                    "checked_at": "2026-07-26T00:08:00Z",
                    "command": "tests/e2e/input-binding-runner",
                    "command_argv": [
                        "tests/e2e/input-binding-runner",
                    ],
                    "exit_code": 0,
                    "artifact_path": trace_path.relative_to(root).as_posix(),
                    "artifact_sha256": sha(trace_path),
                }
            )
        receipt["context"]["manifest_sha256"] = sha(manifest_path)
        receipt_path = root / "receipt.json"
        receipt_path.write_text(
            json.dumps(receipt), encoding="utf-8"
        )
        return (
            manifest_path,
            capture_path,
            receipt_path,
            capture,
        )

    def test_input_binding_capture_proves_authoritative_a_b(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (
                manifest_path,
                capture_path,
                receipt_path,
                _,
            ) = self.input_binding_fixture(root)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
                "--require-capability",
                "analysis-input-binding",
                "--minimum-assurance",
                "strict",
            )
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )

    def test_input_binding_driver_argv_must_invoke_declared_runner(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            capture["capture_driver"]["command_argv"] = [
                "true",
                "tests/e2e/input-binding-runner",
            ]
            capture["capture_driver"]["runner_argv_index"] = 0
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            for item in receipt["gates"]["input_binding"]["evidence"][1:]:
                item["command"] = "true"
                item["command_argv"] = [
                    "true",
                    "tests/e2e/input-binding-runner",
                ]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "command_argv must directly execute runner_path",
            completed.stdout,
        )

    def test_input_binding_driver_runner_must_be_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, _ = (
                self.input_binding_fixture(root)
            )
            runner = root / "tests" / "e2e" / "input-binding-runner"
            runner.chmod(0o644)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("runner_path must be executable", completed.stdout)

    def test_runtime_trace_evidence_must_follow_runtime_completion(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, _ = (
                self.input_binding_fixture(root)
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            runtime_evidence = next(
                item
                for item in receipt["gates"]["input_binding"]["evidence"]
                if item.get("artifact_path")
                == "captures/base-runtime-trace.bin"
            )
            runtime_evidence["checked_at"] = "2025-07-26T00:08:00Z"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "trace must be bound to passed runtime_trace evidence",
            completed.stdout,
        )

    def test_runtime_artifact_paths_must_be_canonical_and_independent(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            adopted = capture["controls"][0]["baseline_runtime"][
                "adopted_result_artifact"
            ]
            adopted["path"] = "captures/./base-result.json"
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "must be a canonical project-relative path",
            completed.stdout,
        )

    def test_runtime_trace_cannot_reuse_runner_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            runner = root / "tests" / "e2e" / "input-binding-runner"
            trace = capture["controls"][0]["baseline_runtime"][
                "trace_artifact"
            ]
            trace["path"] = "tests/e2e/input-binding-runner"
            trace["size"] = len(runner.read_bytes())
            trace["sha256"] = sha(runner)
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            evidence_item = receipt["gates"]["input_binding"]["evidence"][1]
            evidence_item["artifact_path"] = trace["path"]
            evidence_item["artifact_sha256"] = trace["sha256"]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "must not reuse a reserved or runtime artifact",
            completed.stdout,
        )

    def test_all_control_run_paths_are_reserved_before_runtime_validation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            future_input = root / "captures" / "future-control-input.json"
            future_input.write_text("{}", encoding="utf-8")
            capture["controls"].append(
                {
                    "control_id": "future-control",
                    "baseline": {
                        "input_path": "captures/future-control-input.json",
                        "result_path": "captures/future-control-input.json",
                    },
                    "repeat": {},
                    "variant": {},
                }
            )
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            receipt = json.loads(
                receipt_path.read_text(encoding="utf-8")
            )
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            observed: list[list[Path]] = []

            def record_runtime(**kwargs: object) -> None:
                observed.append(list(kwargs["used_artifact_paths"]))

            errors: list[str] = []
            with mock.patch.object(
                validate_evidence_v3,
                "validate_runtime_phase",
                side_effect=record_runtime,
            ):
                validate_evidence_v3.validate_input_binding_capture(
                    receipt,
                    manifest,
                    manifest_path,
                    root,
                    str(capture_path),
                    datetime.fromisoformat(
                        "2026-07-26T00:20:00+00:00"
                    ),
                    "strict",
                    errors,
                )
        self.assertTrue(observed)
        self.assertTrue(
            future_input.resolve() in observed[0]
        )

    def test_input_binding_capture_age_is_bounded_but_configurable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, _ = (
                self.input_binding_fixture(root)
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["completed_at"] = "2026-07-27T00:20:01Z"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            stale = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn(
                "older than maximum_capture_age_seconds",
                stale.stdout,
            )

            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            manifest["capability_config"]["analysis-input-binding"][
                "maximum_capture_age_seconds"
            ] = 172800
            manifest_path.write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            receipt["context"]["manifest_sha256"] = sha(manifest_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            configured = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertEqual(
            configured.returncode,
            0,
            configured.stdout + configured.stderr,
        )

    def test_input_binding_capture_rejects_paid_driver_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            capture["capture_driver"]["command_argv"] = [
                "bash",
                "-lc",
                "providerctl billing enable --payg",
            ]
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            for item in receipt["gates"]["input_binding"]["evidence"][1:]:
                item["command_argv"] = capture["capture_driver"][
                    "command_argv"
                ]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("prohibited paid action", completed.stdout)

    def test_input_binding_capture_rejects_secret_driver_argument(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            capture["capture_driver"]["command_argv"] = [
                "runner",
                "--api-key",
                "fixture-secret-value",
            ]
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            for item in receipt["gates"]["input_binding"]["evidence"][1:]:
                item["command_argv"] = capture["capture_driver"][
                    "command_argv"
                ]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("inline credential", completed.stdout)

    def test_runtime_trace_evidence_binds_exact_driver_argv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, _ = (
                self.input_binding_fixture(root)
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            runtime_evidence = next(
                item
                for item in receipt["gates"]["input_binding"]["evidence"]
                if item.get("artifact_path")
                == "captures/base-runtime-trace.bin"
            )
            runtime_evidence["command_argv"] = ["printf", "unrelated"]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "trace must be bound to passed runtime_trace evidence",
            completed.stdout,
        )

    def test_analysis_trace_evidence_binds_run_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, _ = (
                self.input_binding_fixture(root)
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            execution_evidence = next(
                item
                for item in receipt["gates"]["input_binding"]["evidence"]
                if item.get("artifact_path")
                == "captures/base-analysis-trace.bin"
            )
            execution_evidence["extensions"]["analysis_execution"][
                "entrypoint_sha256"
            ] = "0" * 64
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "baseline lacks matching authoritative analysis command-trace "
            "evidence",
            completed.stdout,
        )

    def test_input_binding_capture_rejects_unchanged_result_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (
                manifest_path,
                capture_path,
                receipt_path,
                capture,
            ) = self.input_binding_fixture(root)
            variant_result = root / "captures" / "variant-result.json"
            value = json.loads(variant_result.read_text())
            value["summary"]["score"] = 1.2
            variant_result.write_text(json.dumps(value), encoding="utf-8")
            capture["controls"][0]["variant"]["result_sha256"] = sha(
                variant_result
            )
            capture_path.write_text(
                json.dumps(capture), encoding="utf-8"
            )
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "no declared responsible result path changed",
            completed.stdout,
        )

    def test_input_binding_capture_requires_reproducible_repeat(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            repeat_result = root / "captures" / "repeat-result.json"
            value = json.loads(repeat_result.read_text())
            value["summary"]["score"] = 9.9
            repeat_result.write_text(json.dumps(value), encoding="utf-8")
            capture["controls"][0]["repeat"]["result_sha256"] = sha(
                repeat_result
            )
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("repeat changed core result path", completed.stdout)

    def test_input_binding_capture_isolates_the_target_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            variant_input = root / "captures" / "variant-input.json"
            value = json.loads(variant_input.read_text())
            value["unrelated_parameter"] = True
            variant_input.write_text(json.dumps(value), encoding="utf-8")
            capture["controls"][0]["variant"]["input_sha256"] = sha(
                variant_input
            )
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("variant changed undeclared input paths", completed.stdout)

    def test_input_binding_capture_binds_ui_runtime_to_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            variant_view = root / "captures" / "variant-bound-view.json"
            view = json.loads(variant_view.read_text(encoding="utf-8"))
            view["binding"]["run_id"] = "wrong-run"
            variant_view.write_text(json.dumps(view), encoding="utf-8")
            runtime_artifact = capture["controls"][0]["variant_runtime"][
                "view_artifact"
            ]
            runtime_artifact["size"] = len(variant_view.read_bytes())
            runtime_artifact["sha256"] = sha(variant_view)
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "view value at view_run_id_pointer does not match",
            completed.stdout,
        )

    def test_input_binding_rejects_self_assertion_without_runtime_bundle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            control = capture["controls"][0]
            control.pop("baseline_runtime")
            control.pop("variant_runtime")
            control["frontend_binding"] = {
                "submitted_value": 60,
                "bound_run_id": "run-variant",
            }
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("frontend_binding", completed.stdout)
        self.assertIn("runtime lookback-days baseline must be", completed.stdout)

    def test_input_binding_rejects_runtime_dispatch_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            dispatch = root / "captures" / "variant-dispatch.json"
            value = json.loads(dispatch.read_text(encoding="utf-8"))
            value["request"]["body"]["config"]["lookback_days"] = 999
            dispatch.write_text(json.dumps(value), encoding="utf-8")
            artifact = capture["controls"][0]["variant_runtime"][
                "dispatch_artifact"
            ]
            artifact["size"] = len(dispatch.read_bytes())
            artifact["sha256"] = sha(dispatch)
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "dispatched canonical input does not match run input",
            completed.stdout,
        )

    def test_input_binding_dispatch_binds_declared_mapping_contract(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, _ = (
                self.input_binding_fixture(root)
            )
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            control = manifest["capability_config"][
                "analysis-input-binding"
            ]["controls"][0]
            control["canonical_field"] = "unrelated_field"
            control["execution_mapping"] = "--unrelated"
            control["execution_binding"]["locator"] = "--unrelated"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["context"]["manifest_sha256"] = sha(manifest_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "dispatch value at dispatch_canonical_field_pointer does not match",
            completed.stdout,
        )
        self.assertIn(
            "dispatch value at dispatch_execution_mapping_pointer does not "
            "match",
            completed.stdout,
        )

    def test_coordinated_false_mapping_cannot_override_executed_argv(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            control = manifest["capability_config"][
                "analysis-input-binding"
            ]["controls"][0]
            control["canonical_field"] = "coordinated_false_field"
            control["execution_mapping"] = "--coordinated-false-option"
            control["execution_binding"]["locator"] = (
                "--coordinated-false-option"
            )
            for phase in ("baseline", "variant"):
                dispatch = root / "captures" / f"{phase}-dispatch.json"
                if phase == "baseline":
                    dispatch = root / "captures" / "base-dispatch.json"
                value = json.loads(dispatch.read_text(encoding="utf-8"))
                value["mapping"]["canonical_field"] = (
                    "coordinated_false_field"
                )
                value["mapping"]["execution_mapping"] = (
                    "--coordinated-false-option"
                )
                dispatch.write_text(json.dumps(value), encoding="utf-8")
                artifact = capture["controls"][0][
                    f"{phase}_runtime"
                ]["dispatch_artifact"]
                artifact["size"] = len(dispatch.read_bytes())
                artifact["sha256"] = sha(dispatch)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["context"]["manifest_sha256"] = sha(manifest_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "argv must contain the declared option exactly once",
            completed.stdout,
        )

    def test_declared_entrypoint_cannot_hide_the_invoked_entrypoint(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            dead_entrypoint = root / "analysis" / "dead.py"
            dead_entrypoint.write_text("print('dead')\n", encoding="utf-8")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["capability_config"]["analysis"][
                "authoritative_entrypoints"
            ] = ["analysis/dead.py"]
            capture["analysis_entrypoint"] = {
                "path": "analysis/dead.py",
                "sha256": sha(dead_entrypoint),
            }
            control = capture["controls"][0]
            for phase in ("baseline", "repeat", "variant"):
                run_item = control[phase]
                run_item["entrypoint_sha256"] = sha(dead_entrypoint)
                invocation = root / run_item["invocation_artifact"]["path"]
                document = json.loads(
                    invocation.read_text(encoding="utf-8")
                )
                document["entrypoint_path"] = "analysis/dead.py"
                document["entrypoint_sha256"] = sha(dead_entrypoint)
                invocation.write_text(json.dumps(document), encoding="utf-8")
                run_item["invocation_artifact"]["size"] = len(
                    invocation.read_bytes()
                )
                run_item["invocation_artifact"]["sha256"] = sha(invocation)
            for phase, filename in (
                ("baseline", "base-dispatch.json"),
                ("variant", "variant-dispatch.json"),
            ):
                dispatch = root / "captures" / filename
                value = json.loads(dispatch.read_text(encoding="utf-8"))
                value["mapping"]["entrypoint_sha256"] = sha(dead_entrypoint)
                dispatch.write_text(json.dumps(value), encoding="utf-8")
                artifact = control[f"{phase}_runtime"][
                    "dispatch_artifact"
                ]
                artifact["size"] = len(dispatch.read_bytes())
                artifact["sha256"] = sha(dispatch)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["context"]["manifest_sha256"] = sha(manifest_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "binding argv does not invoke analysis_entrypoint.path",
            completed.stdout,
        )

    def test_json_execution_bindings_use_hashed_source_bytes(self) -> None:
        for kind in ("json-payload", "config-json"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest_path, capture_path, receipt_path, capture = (
                    self.input_binding_fixture(root)
                )
                manifest = json.loads(
                    manifest_path.read_text(encoding="utf-8")
                )
                definition = manifest["capability_config"][
                    "analysis-input-binding"
                ]["controls"][0]
                definition["execution_mapping"] = "/lookback_days"
                definition["execution_binding"] = {
                    "kind": kind,
                    "locator": "/lookback_days",
                }
                control = capture["controls"][0]
                phase_values = {
                    "baseline": 20,
                    "repeat": 20,
                    "variant": 60,
                }
                source_paths: dict[str, Path] = {}
                for phase, value in phase_values.items():
                    source = root / "captures" / (
                        f"{phase}-{kind}-source.json"
                    )
                    source.write_text(
                        json.dumps({"lookback_days": value}),
                        encoding="utf-8",
                    )
                    source_paths[phase] = source
                    run_item = control[phase]
                    invocation = (
                        root / run_item["invocation_artifact"]["path"]
                    )
                    document = json.loads(
                        invocation.read_text(encoding="utf-8")
                    )
                    document["binding"] = {
                        "kind": kind,
                        "argv": ["analysis/run.py"],
                        "entrypoint_argv_index": 0,
                        "source_artifact": {
                            "path": source.relative_to(root).as_posix(),
                            "size": len(source.read_bytes()),
                            "sha256": sha(source),
                            "media_type": "application/json",
                        },
                    }
                    invocation.write_text(
                        json.dumps(document), encoding="utf-8"
                    )
                    run_item["invocation_artifact"]["size"] = len(
                        invocation.read_bytes()
                    )
                    run_item["invocation_artifact"]["sha256"] = sha(
                        invocation
                    )
                for phase, filename in (
                    ("baseline", "base-dispatch.json"),
                    ("variant", "variant-dispatch.json"),
                ):
                    dispatch = root / "captures" / filename
                    value = json.loads(
                        dispatch.read_text(encoding="utf-8")
                    )
                    value["mapping"]["execution_mapping"] = "/lookback_days"
                    dispatch.write_text(json.dumps(value), encoding="utf-8")
                    artifact = control[f"{phase}_runtime"][
                        "dispatch_artifact"
                    ]
                    artifact["size"] = len(dispatch.read_bytes())
                    artifact["sha256"] = sha(dispatch)
                manifest_path.write_text(
                    json.dumps(manifest), encoding="utf-8"
                )
                capture_path.write_text(
                    json.dumps(capture), encoding="utf-8"
                )
                receipt = json.loads(
                    receipt_path.read_text(encoding="utf-8")
                )
                receipt["context"]["manifest_sha256"] = sha(manifest_path)
                receipt_path.write_text(
                    json.dumps(receipt), encoding="utf-8"
                )
                rebind_capture_receipt(receipt_path, capture_path)
                rebind_analysis_execution_evidence(
                    receipt_path, capture_path, root
                )
                valid = run(
                    root,
                    manifest_path,
                    receipt_path,
                    "--input-binding-capture",
                    str(capture_path),
                )
                self.assertEqual(
                    valid.returncode,
                    0,
                    valid.stdout + valid.stderr,
                )
                source_paths["variant"].write_text(
                    json.dumps({"lookback_days": 999}),
                    encoding="utf-8",
                )
                tampered = run(
                    root,
                    manifest_path,
                    receipt_path,
                    "--input-binding-capture",
                    str(capture_path),
                )
                self.assertNotEqual(tampered.returncode, 0)
                self.assertTrue(
                    "sha256 does not match bytes" in tampered.stdout
                    or "size does not match bytes" in tampered.stdout,
                    tampered.stdout,
                )

    def test_input_binding_each_run_binds_analysis_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            capture["controls"][0]["variant"]["entrypoint_sha256"] = "0" * 64
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "variant.entrypoint_sha256 must match analysis_entrypoint.sha256",
            completed.stdout,
        )

    def test_result_paths_cannot_claim_effective_input_echo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, _ = (
                self.input_binding_fixture(root)
            )
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            control = manifest["capability_config"][
                "analysis-input-binding"
            ]["controls"][0]
            control["result_paths"] = [
                control["effective_value_pointer"]
            ]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["context"]["manifest_sha256"] = sha(manifest_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "result_paths must not overlap effective configuration or result "
            "identity pointers",
            completed.stdout,
        )

    def test_result_paths_cannot_claim_declared_result_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, _ = (
                self.input_binding_fixture(root)
            )
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            analysis = manifest["capability_config"]["analysis"]
            analysis["result_identity_fields"].append("config_hash")
            analysis["result_identity_pointers"].append("/config_hash")
            control = manifest["capability_config"][
                "analysis-input-binding"
            ]["controls"][0]
            control["result_paths"] = ["/config_hash"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["context"]["manifest_sha256"] = sha(manifest_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "result_paths must not overlap effective configuration or result "
            "identity pointers",
            completed.stdout,
        )

    def test_declared_result_identity_pointers_must_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, _ = (
                self.input_binding_fixture(root)
            )
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            manifest["capability_config"]["analysis"][
                "result_identity_pointers"
            ][1] = "/run_iid"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["context"]["manifest_sha256"] = sha(manifest_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "result identity pointer '/run_iid' failed",
            completed.stdout,
        )

    def test_input_binding_json_values_are_type_strict(self) -> None:
        cases = (
            ("dispatch", "dispatched canonical input does not match run input"),
            (
                "view",
                "view result value '/summary/score' does not match "
                "authoritative result",
            ),
        )
        for surface, expected_error in cases:
            with self.subTest(surface=surface), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest_path, capture_path, receipt_path, capture = (
                    self.input_binding_fixture(root)
                )
                if surface == "dispatch":
                    artifact_path = (
                        root / "captures" / "variant-dispatch.json"
                    )
                    document = json.loads(
                        artifact_path.read_text(encoding="utf-8")
                    )
                    document["request"]["body"]["config"][
                        "lookback_days"
                    ] = True
                    artifact = capture["controls"][0][
                        "variant_runtime"
                    ]["dispatch_artifact"]
                else:
                    artifact_path = (
                        root / "captures" / "variant-bound-view.json"
                    )
                    document = json.loads(
                        artifact_path.read_text(encoding="utf-8")
                    )
                    document["binding"]["result_values"][
                        "/summary/score"
                    ] = True
                    artifact = capture["controls"][0][
                        "variant_runtime"
                    ]["view_artifact"]
                artifact_path.write_text(
                    json.dumps(document), encoding="utf-8"
                )
                artifact["size"] = len(artifact_path.read_bytes())
                artifact["sha256"] = sha(artifact_path)
                capture_path.write_text(
                    json.dumps(capture), encoding="utf-8"
                )
                rebind_capture_receipt(receipt_path, capture_path)
                completed = run(
                    root,
                    manifest_path,
                    receipt_path,
                    "--input-binding-capture",
                    str(capture_path),
                )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(expected_error, completed.stdout)

    def test_invocation_constants_are_type_strict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            control = capture["controls"][0]
            for phase in ("baseline", "repeat", "variant"):
                run_item = control[phase]
                invocation_path = (
                    root / run_item["invocation_artifact"]["path"]
                )
                document = json.loads(
                    invocation_path.read_text(encoding="utf-8")
                )
                document["schema_version"] = True
                document["exit_code"] = False
                invocation_path.write_text(
                    json.dumps(document), encoding="utf-8"
                )
                run_item["invocation_artifact"]["size"] = len(
                    invocation_path.read_bytes()
                )
                run_item["invocation_artifact"]["sha256"] = sha(
                    invocation_path
                )
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "schema_version does not match the authoritative run",
            completed.stdout,
        )
        self.assertIn(
            "exit_code does not match the authoritative run",
            completed.stdout,
        )

    def test_authoritative_run_artifacts_cannot_be_reused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            control = capture["controls"][0]
            baseline = control["baseline"]
            repeat = control["repeat"]
            repeat["input_path"] = baseline["input_path"]
            repeat["input_sha256"] = baseline["input_sha256"]
            invocation_path = root / repeat["invocation_artifact"]["path"]
            document = json.loads(
                invocation_path.read_text(encoding="utf-8")
            )
            document["input_path"] = baseline["input_path"]
            document["input_sha256"] = baseline["input_sha256"]
            invocation_path.write_text(
                json.dumps(document), encoding="utf-8"
            )
            repeat["invocation_artifact"]["size"] = len(
                invocation_path.read_bytes()
            )
            repeat["invocation_artifact"]["sha256"] = sha(invocation_path)
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "repeat.input_path must not reuse a reserved or authoritative "
            "run artifact",
            completed.stdout,
        )

    def test_input_binding_requires_byte_identical_adopted_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            adopted = root / "captures" / "variant-adopted-result.json"
            value = json.loads(adopted.read_text(encoding="utf-8"))
            adopted.write_text(
                json.dumps(value, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            artifact = capture["controls"][0]["variant_runtime"][
                "adopted_result_artifact"
            ]
            artifact["size"] = len(adopted.read_bytes())
            artifact["sha256"] = sha(adopted)
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "adopted result is not byte-identical", completed.stdout
        )

    def test_input_binding_rejects_runtime_artifact_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            root.mkdir()
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            trace = root / "captures" / "variant-runtime-trace.bin"
            outside = base / "outside-runtime-trace.bin"
            outside.write_bytes(b"outside runtime trace\n")
            trace.unlink()
            trace.symlink_to(outside)
            artifact = capture["controls"][0]["variant_runtime"][
                "trace_artifact"
            ]
            artifact["size"] = len(outside.read_bytes())
            artifact["sha256"] = sha(outside)
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["gates"]["input_binding"]["evidence"][2][
                "artifact_sha256"
            ] = sha(outside)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("resolves outside project root", completed.stdout)

    def test_input_binding_rejects_reused_session_and_run_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            control = capture["controls"][0]
            control["variant_runtime"]["session_id"] = control[
                "baseline_runtime"
            ]["session_id"]
            control["repeat"]["run_id"] = control["variant"]["run_id"]
            repeat_result = root / "captures" / "repeat-result.json"
            result = json.loads(repeat_result.read_text(encoding="utf-8"))
            result["run_id"] = control["variant"]["run_id"]
            repeat_result.write_text(json.dumps(result), encoding="utf-8")
            control["repeat"]["result_sha256"] = sha(repeat_result)
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("repeat and variant run_id must differ", completed.stdout)
        self.assertIn("session_id must be unique", completed.stdout)

    def test_input_binding_rejects_runtime_time_reversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, capture = (
                self.input_binding_fixture(root)
            )
            capture["controls"][0]["variant_runtime"]["view_bound_at"] = (
                "2026-07-26T00:03:30Z"
            )
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            rebind_capture_receipt(receipt_path, capture_path)
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("timestamps are out of causal order", completed.stdout)

    def test_input_binding_rejects_missing_manifest_runtime_pointer(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, capture_path, receipt_path, _ = (
                self.input_binding_fixture(root)
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            contract = manifest["capability_config"][
                "analysis-input-binding"
            ]["controls"][0]["runtime_binding_contract"]
            contract.pop("view_run_id_pointer")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["context"]["manifest_sha256"] = sha(manifest_path)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = run(
                root,
                manifest_path,
                receipt_path,
                "--input-binding-capture",
                str(capture_path),
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "view_run_id_pointer must be a JSON Pointer",
            completed.stdout,
        )


if __name__ == "__main__":
    unittest.main()
