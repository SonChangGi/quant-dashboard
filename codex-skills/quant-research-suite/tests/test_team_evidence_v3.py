from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "shared" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import team_protocol
import validate_evidence_v3
from tests.test_evidence_v3 import (
    evidence,
    manifest_base,
    receipt_base,
    run as run_receipt,
    run_without_manifest,
)
from tests.test_team_protocol import (
    assignment,
    make_delivery,
    make_integration,
    make_packet,
    seal_packet,
    seal_receipt,
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> Path:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    return path


def team_extension(
    packet: dict[str, object],
    packet_path: Path,
    deliveries: list[dict[str, object]],
    delivery_paths: list[Path],
    integration: dict[str, object],
    integration_path: Path,
    *,
    goal_binding: dict[str, object] | None = None,
) -> dict[str, object]:
    delivery_by_id = {
        str(delivery["assignment_id"]): (delivery, path)
        for delivery, path in zip(deliveries, delivery_paths)
    }
    return {
        "schema_version": 1,
        "team_run_id": packet["team_run_id"],
        "packet_sha256": packet["packet_sha256"],
        "packet_file_sha256": file_sha256(packet_path),
        "deliveries": [
            {
                "assignment_id": assignment_id,
                "receipt_sha256": delivery_by_id[assignment_id][0][
                    "receipt_sha256"
                ],
                "file_sha256": file_sha256(
                    delivery_by_id[assignment_id][1]
                ),
            }
            for assignment_id in packet["join"]["integration_order"]
        ],
        "integration_receipt_sha256": integration["receipt_sha256"],
        "integration_file_sha256": file_sha256(integration_path),
        "integration_owner": integration["integration_owner"],
        "project_binding_sha256": packet["project_binding_sha256"],
        "current_workspace_sha256": integration["canonical_snapshot"][
            "post_workspace_sha256"
        ],
        "goal_binding": goal_binding,
        "integration_completed_at": integration["completed_at"],
    }


def build_standalone_bundle(base: Path) -> dict[str, object]:
    project = base / "project"
    project.mkdir()
    (project / "src" / "core").mkdir(parents=True)
    (project / "src" / "core" / "contract.txt").write_text(
        "protected\n", encoding="utf-8"
    )
    manifest_path = write_json(project / "manifest.json", manifest_base())

    proof_root = base / "proof"
    proof_root.mkdir()
    selected = assignment("inspect", "inspect", mode="read_only")
    packet = make_packet(
        [selected],
        workspace_root=project,
        assignment_roots={"inspect": project},
    )
    packet["objective_sha256"] = validate_evidence_v3.canonical_sha256(
        "Verify the bounded local deliverable."
    )
    packet["assurance"] = "light"
    seal_packet(packet)
    delivery = make_delivery(
        packet,
        selected,
        proof_root,
        worker_root=project,
    )
    integration = make_integration(
        packet,
        [delivery],
        workspace_root=project,
    )
    packet_path = write_json(proof_root / "packet.json", packet)
    delivery_path = write_json(proof_root / "delivery.json", delivery)
    integration_path = write_json(
        proof_root / "integration.json", integration
    )

    receipt = receipt_base(manifest_path)
    receipt["scope"]["capabilities"] = ["agent-team-execution"]
    receipt["required_gates"] = [
        "contract",
        "cost",
        "team_integration",
    ]
    receipt["gates"]["team_integration"] = {
        "status": "passed",
        "evidence": [
            {
                "kind": "artifact",
                "status": "verified",
                "summary": "The complete team bundle passed validation.",
                "source": validate_evidence_v3.TEAM_EVIDENCE_SOURCE,
                "checked_at": integration["completed_at"],
                "extensions": {
                    "agent_team_execution": team_extension(
                        packet,
                        packet_path,
                        [delivery],
                        [delivery_path],
                        integration,
                        integration_path,
                    )
                },
            }
        ],
    }
    receipt["completed_at"] = "2026-07-27T00:30:00Z"
    receipt_path = write_json(base / "receipt.json", receipt)
    cli = [
        "--team-packet",
        str(packet_path),
        "--team-delivery",
        str(delivery_path),
        "--team-integration",
        str(integration_path),
        "--team-artifact-root",
        str(proof_root),
        "--team-workspace-root",
        str(project),
        "--team-baseline-root",
        str(project),
        "--team-worker-root",
        f"inspect={project}",
    ]
    return {
        "project": project,
        "manifest_path": manifest_path,
        "proof_root": proof_root,
        "packet": packet,
        "packet_path": packet_path,
        "delivery": delivery,
        "delivery_path": delivery_path,
        "integration": integration,
        "integration_path": integration_path,
        "receipt": receipt,
        "receipt_path": receipt_path,
        "cli": cli,
    }


class TeamEvidenceV3Tests(unittest.TestCase):
    def test_standalone_typed_bundle_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_standalone_bundle(Path(directory))
            completed = run_receipt(
                bundle["project"],
                bundle["manifest_path"],
                bundle["receipt_path"],
                *bundle["cli"],
            )
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )

    def test_future_completion_and_duplicate_receipt_keys_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_standalone_bundle(Path(directory))
            receipt = copy.deepcopy(bundle["receipt"])
            receipt["completed_at"] = "2099-01-01T00:30:00Z"
            write_json(bundle["receipt_path"], receipt)
            future = run_receipt(
                bundle["project"],
                bundle["manifest_path"],
                bundle["receipt_path"],
                *bundle["cli"],
            )
            self.assertNotEqual(future.returncode, 0)
            self.assertIn(
                "completed_at exceeds allowed future clock skew",
                future.stdout,
            )

            receipt_path = bundle["receipt_path"]
            write_json(receipt_path, bundle["receipt"])
            raw = receipt_path.read_text(encoding="utf-8")
            marker = '"schema_version": 3'
            self.assertIn(marker, raw)
            receipt_path.write_text(
                raw.replace(
                    marker,
                    '"schema_version": 3, "schema_version": 3',
                    1,
                ),
                encoding="utf-8",
            )
            duplicate = run_receipt(
                bundle["project"],
                bundle["manifest_path"],
                receipt_path,
                *bundle["cli"],
            )
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn("duplicate JSON object key", duplicate.stdout)

    def test_generic_evidence_cannot_activate_team_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_standalone_bundle(Path(directory))
            receipt = bundle["receipt"]
            receipt["gates"]["team_integration"]["evidence"] = [
                evidence("A generic inspection claim.")
            ]
            write_json(bundle["receipt_path"], receipt)
            completed = run_receipt(
                bundle["project"],
                bundle["manifest_path"],
                bundle["receipt_path"],
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("requires --team-packet", completed.stdout)
        self.assertIn("typed evidence", completed.stdout)

    def test_team_bundle_cannot_be_replayed_for_a_different_objective(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_standalone_bundle(Path(directory))
            bundle["receipt"]["objective"] = (
                "A different objective that never issued this team run."
            )
            write_json(bundle["receipt_path"], bundle["receipt"])
            completed = run_receipt(
                bundle["project"],
                bundle["manifest_path"],
                bundle["receipt_path"],
                *bundle["cli"],
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "does not bind the completion objective",
            completed.stdout,
        )

    def test_team_cli_bundle_requires_explicit_runtime_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_standalone_bundle(Path(directory))
            receipt = bundle["receipt"]
            receipt["scope"]["capabilities"] = []
            receipt["required_gates"] = ["contract", "cost"]
            del receipt["gates"]["team_integration"]
            write_json(bundle["receipt_path"], receipt)
            completed = run_receipt(
                bundle["project"],
                bundle["manifest_path"],
                bundle["receipt_path"],
                *bundle["cli"],
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "CLI artifacts require agent-team-execution scope",
            completed.stdout,
        )

    def test_duplicate_and_symlinked_proof_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_standalone_bundle(Path(directory))
            duplicate_cli = [
                *bundle["cli"][:4],
                "--team-delivery",
                str(bundle["delivery_path"]),
                *bundle["cli"][4:],
            ]
            duplicate = run_receipt(
                bundle["project"],
                bundle["manifest_path"],
                bundle["receipt_path"],
                *duplicate_cli,
            )
            copied_delivery = bundle["proof_root"] / "delivery-copy.json"
            copied_delivery.write_bytes(bundle["delivery_path"].read_bytes())
            reused_cli = [
                *bundle["cli"][:4],
                "--team-delivery",
                str(copied_delivery),
                *bundle["cli"][4:],
            ]
            reused = run_receipt(
                bundle["project"],
                bundle["manifest_path"],
                bundle["receipt_path"],
                *reused_cli,
            )
            link = bundle["proof_root"] / "packet-link.json"
            link.symlink_to(bundle["packet_path"])
            symlink_cli = list(bundle["cli"])
            symlink_cli[1] = str(link)
            linked = run_receipt(
                bundle["project"],
                bundle["manifest_path"],
                bundle["receipt_path"],
                *symlink_cli,
            )
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("distinct physical files", duplicate.stdout)
        self.assertNotEqual(reused.returncode, 0)
        self.assertIn("Receipt hash is reused", reused.stdout)
        self.assertNotEqual(linked.returncode, 0)
        self.assertIn("must not be a symbolic link", linked.stdout)

    def test_tampered_but_resealed_integration_fails_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_standalone_bundle(Path(directory))
            integration = bundle["integration"]
            integration["integration_owner"] = "different-owner"
            seal_receipt(integration)
            write_json(bundle["integration_path"], integration)
            extension = team_extension(
                bundle["packet"],
                bundle["packet_path"],
                [bundle["delivery"]],
                [bundle["delivery_path"]],
                integration,
                bundle["integration_path"],
            )
            bundle["receipt"]["gates"]["team_integration"]["evidence"][0][
                "extensions"
            ]["agent_team_execution"] = extension
            write_json(bundle["receipt_path"], bundle["receipt"])
            completed = run_receipt(
                bundle["project"],
                bundle["manifest_path"],
                bundle["receipt_path"],
                *bundle["cli"],
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "integration owner does not match packet", completed.stdout
        )

    def test_resealed_worker_binding_requires_the_live_worker_root(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_standalone_bundle(Path(directory))
            packet = bundle["packet"]
            delivery = bundle["delivery"]
            integration = bundle["integration"]
            packet["assignments"][0]["workspace_binding_sha256"] = "f" * 64
            seal_packet(packet)
            delivery["packet_sha256"] = packet["packet_sha256"]
            delivery["source"]["workspace_binding_sha256"] = "f" * 64
            seal_receipt(delivery)
            integration["packet_sha256"] = packet["packet_sha256"]
            integration["delivery_results"][0][
                "delivery_receipt_sha256"
            ] = delivery["receipt_sha256"]
            seal_receipt(integration)
            write_json(bundle["packet_path"], packet)
            write_json(bundle["delivery_path"], delivery)
            write_json(bundle["integration_path"], integration)
            extension = team_extension(
                packet,
                bundle["packet_path"],
                [delivery],
                [bundle["delivery_path"]],
                integration,
                bundle["integration_path"],
            )
            bundle["receipt"]["gates"]["team_integration"]["evidence"][0][
                "extensions"
            ]["agent_team_execution"] = extension
            write_json(bundle["receipt_path"], bundle["receipt"])
            completed = run_receipt(
                bundle["project"],
                bundle["manifest_path"],
                bundle["receipt_path"],
                *bundle["cli"],
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "worker root binding does not match assignment",
            completed.stdout,
        )

    def test_exact_extension_hash_time_and_workspace_binding(self) -> None:
        mutations = {
            "type-confused schema version": ("schema_version", True),
            "packet hash": ("packet_file_sha256", "f" * 64),
            "project binding": ("project_binding_sha256", "f" * 64),
            "workspace binding": ("current_workspace_sha256", "f" * 64),
            "validation time": (
                "integration_completed_at",
                "2026-07-27T00:19:59Z",
            ),
            "standalone Goal binding": (
                "goal_binding",
                {
                    "goal_id": "forged",
                    "plan_revision": 1,
                    "acceptance_revision": 1,
                    "workspace_sha256": "f" * 64,
                },
            ),
        }
        for name, (field, value) in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                bundle = build_standalone_bundle(Path(directory))
                extension = bundle["receipt"]["gates"]["team_integration"][
                    "evidence"
                ][0]["extensions"]["agent_team_execution"]
                extension[field] = value
                write_json(bundle["receipt_path"], bundle["receipt"])
                completed = run_receipt(
                    bundle["project"],
                    bundle["manifest_path"],
                    bundle["receipt_path"],
                    *bundle["cli"],
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("does not exactly bind", completed.stdout)

    def test_goal_bound_bundle_supports_external_state_proof_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project = base / "project"
            project.mkdir()
            (project / "src" / "core").mkdir(parents=True)
            (project / "src" / "core" / "contract.txt").write_text(
                "protected\n", encoding="utf-8"
            )
            state_dir = base / "external-goal-state"
            state_dir.mkdir()
            selected = assignment("inspect", "inspect", mode="read_only")
            packet = make_packet(
                [selected],
                workspace_root=project,
                assignment_roots={"inspect": project},
            )
            packet["owner"] = "goal"
            packet["goal_binding"] = {
                "goal_id": "goal-test",
                "plan_revision": 2,
                "acceptance_revision": 3,
            }
            packet["objective_sha256"] = (
                validate_evidence_v3.canonical_sha256(
                    "Deliver the requested behavior."
                )
            )
            packet["assignments"][0]["acceptance_ids"] = ["a1"]
            seal_packet(packet)
            delivery = make_delivery(
                packet,
                selected,
                state_dir,
                worker_root=project,
            )
            integration = make_integration(
                packet,
                [delivery],
                workspace_root=project,
            )
            packet_path = write_json(state_dir / "packet.json", packet)
            delivery_path = write_json(state_dir / "delivery.json", delivery)
            integration_path = write_json(
                state_dir / "integration.json", integration
            )
            goal_binding = {
                "goal_id": "goal-test",
                "plan_revision": 2,
                "acceptance_revision": 3,
                "workspace_sha256": integration["canonical_snapshot"][
                    "post_workspace_sha256"
                ],
            }
            typed_extension = team_extension(
                packet,
                packet_path,
                [delivery],
                [delivery_path],
                integration,
                integration_path,
                goal_binding=goal_binding,
            )
            gate = {
                "status": "passed",
                "evidence": [
                    {
                        "kind": "artifact",
                        "status": "verified",
                        "summary": "The Goal-owned team bundle is current.",
                        "source": validate_evidence_v3.TEAM_EVIDENCE_SOURCE,
                        "checked_at": integration["completed_at"],
                        "extensions": {
                            "agent_team_execution": typed_extension,
                            "goal_ledger": copy.deepcopy(goal_binding),
                        },
                    }
                ],
            }
            args = Namespace(
                team_packet=str(packet_path),
                team_delivery=[str(delivery_path)],
                team_integration=str(integration_path),
                team_artifact_root=str(state_dir),
                team_workspace_root=str(project),
                team_baseline_root=str(project),
                team_worker_root=[f"inspect={project}"],
            )
            team_item = gate["evidence"][0]
            receipt = {
                "objective": "Deliver the requested behavior.",
                "scope": {"assurance": "standard"},
                "goal_binding": {
                    "acceptance_claims": {
                        "a1": [
                            {
                                "gate": "team_integration",
                                "evidence_index": 0,
                                "evidence_sha256": (
                                    validate_evidence_v3.canonical_sha256(
                                        team_item
                                    )
                                ),
                            }
                        ]
                    }
                },
            }
            errors: list[str] = []
            validate_evidence_v3.validate_agent_team_evidence(
                ["agent-team-execution"],
                {"team_integration": gate},
                receipt,
                project.resolve(),
                validate_evidence_v3.parse_time(
                    "2026-07-27T00:30:00Z"
                ).astimezone(timezone.utc),
                {
                    "runtime_kind": "host-ledger-v1",
                    "state_dir": state_dir.resolve(),
                        "state": {
                            "goal_id": "goal-test",
                            "objective_sha256": (
                                validate_evidence_v3.canonical_sha256(
                                    "Deliver the requested behavior."
                                )
                            ),
                            "plan": {"revision": 2},
                            "acceptance_revision": 3,
                            "acceptance": [{"id": "a1"}],
                            "assurance": "standard",
                        },
                    "current": {
                        "sha256": goal_binding["workspace_sha256"]
                    },
                },
                args,
                errors,
            )
            self.assertEqual(errors, [])
            stale_gate = copy.deepcopy(gate)
            stale_gate["evidence"][0]["extensions"]["agent_team_execution"][
                "goal_binding"
            ]["plan_revision"] = 1
            stale_gate["evidence"][0]["extensions"]["goal_ledger"][
                "workspace_sha256"
            ] = "f" * 64
            stale_errors: list[str] = []
            validate_evidence_v3.validate_agent_team_evidence(
                ["agent-team-execution"],
                {"team_integration": stale_gate},
                receipt,
                project.resolve(),
                validate_evidence_v3.parse_time(
                    "2026-07-27T00:30:00Z"
                ).astimezone(timezone.utc),
                {
                    "runtime_kind": "host-ledger-v1",
                    "state_dir": state_dir.resolve(),
                    "state": {
                        "goal_id": "goal-test",
                        "objective_sha256": (
                            validate_evidence_v3.canonical_sha256(
                                "Deliver the requested behavior."
                            )
                        ),
                        "plan": {"revision": 2},
                        "acceptance_revision": 3,
                        "acceptance": [{"id": "a1"}],
                        "assurance": "standard",
                    },
                    "current": {
                        "sha256": goal_binding["workspace_sha256"]
                    },
                },
                args,
                stale_errors,
            )
            self.assertTrue(
                any(
                    "does not exactly bind" in error
                    for error in stale_errors
                ),
                stale_errors,
            )
            self.assertTrue(
                any(
                    "does not exactly bind the current Goal snapshot" in error
                    for error in stale_errors
                ),
                stale_errors,
            )
            foreign_acceptance_errors: list[str] = []
            validate_evidence_v3.validate_agent_team_evidence(
                ["agent-team-execution"],
                {"team_integration": gate},
                receipt,
                project.resolve(),
                validate_evidence_v3.parse_time(
                    "2026-07-27T00:30:00Z"
                ).astimezone(timezone.utc),
                {
                    "runtime_kind": "host-ledger-v1",
                    "state_dir": state_dir.resolve(),
                    "state": {
                        "goal_id": "goal-test",
                        "objective_sha256": (
                            validate_evidence_v3.canonical_sha256(
                                "Deliver the requested behavior."
                            )
                        ),
                        "plan": {"revision": 2},
                        "acceptance_revision": 3,
                        "acceptance": [{"id": "different"}],
                        "assurance": "standard",
                    },
                    "current": {
                        "sha256": goal_binding["workspace_sha256"]
                    },
                },
                args,
                foreign_acceptance_errors,
            )
            self.assertTrue(
                any(
                    "outside the current Goal" in error
                    for error in foreign_acceptance_errors
                ),
                foreign_acceptance_errors,
            )

    def test_host_goal_validates_team_proofs_inside_external_state(self) -> None:
        from tests.test_goal_ledger import (
            command as goal_command,
            current_snapshot,
            evidence_receipt,
            make_project,
            record_review,
        )

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project = make_project(base)
            acceptance_path = write_json(
                base / "acceptance.json",
                {
                    "acceptance": [
                        {
                            "id": "a1",
                            "text": "The team result is directly verified.",
                        }
                    ]
                },
            )
            started = goal_command(
                "init",
                "--root",
                str(project),
                "--state-dir",
                str(base / "external-state"),
                "--goal-id",
                "goal-sample",
                "--host-goal-id",
                "host-goal-sample",
                "--project-id",
                "sample",
                "--objective",
                "Deliver the requested behavior.",
                "--acceptance",
                str(acceptance_path),
                "--assurance",
                "standard",
                "--activation-reason",
                "recovery",
                "--require-capability",
                "agent-team-execution",
            )
            self.assertEqual(
                started.returncode, 0, started.stdout + started.stderr
            )
            state_dir = Path(
                json.loads(started.stdout)["result"]["state_dir"]
            )

            selected = assignment("inspect", "inspect", mode="read_only")
            packet = make_packet(
                [selected],
                workspace_root=project,
                assignment_roots={"inspect": project},
            )
            packet["owner"] = "goal"
            packet["goal_binding"] = {
                "goal_id": "goal-sample",
                "plan_revision": 0,
                "acceptance_revision": 1,
            }
            packet["objective_sha256"] = (
                validate_evidence_v3.canonical_sha256(
                    "Deliver the requested behavior."
                )
            )
            packet["assurance"] = "standard"
            packet["assignments"][0]["acceptance_ids"] = ["a1"]
            seal_packet(packet)
            proof_root = state_dir / "team"
            proof_root.mkdir()
            delivery = make_delivery(
                packet,
                selected,
                proof_root,
                worker_root=project,
            )
            delivery["completed_at"] = "2026-07-27T00:04:00Z"
            seal_receipt(delivery)
            integration = make_integration(
                packet,
                [delivery],
                workspace_root=project,
            )
            integration["completed_at"] = "2026-07-27T00:05:00Z"
            integration["delivery_results"][0][
                "delivery_receipt_sha256"
            ] = delivery["receipt_sha256"]
            seal_receipt(integration)
            packet_path = write_json(proof_root / "packet.json", packet)
            delivery_path = write_json(
                proof_root / "delivery.json", delivery
            )
            integration_path = write_json(
                proof_root / "integration.json", integration
            )

            reviewed = record_review(
                base,
                project,
                state_dir,
                "integration_review",
                "integration-team-review",
            )
            self.assertEqual(
                reviewed.returncode, 0, reviewed.stdout + reviewed.stderr
            )
            receipt = evidence_receipt(project, state_dir)
            goal_workspace_sha256 = current_snapshot(
                project, state_dir
            )["sha256"]
            goal_binding = {
                "goal_id": "goal-sample",
                "plan_revision": 0,
                "acceptance_revision": 1,
                "workspace_sha256": goal_workspace_sha256,
            }
            receipt["gates"]["team_integration"]["evidence"] = [
                {
                    "kind": "artifact",
                    "status": "verified",
                    "summary": "The Goal-owned team bundle is current.",
                    "source": validate_evidence_v3.TEAM_EVIDENCE_SOURCE,
                    "checked_at": integration["completed_at"],
                    "extensions": {
                        "agent_team_execution": team_extension(
                            packet,
                            packet_path,
                            [delivery],
                            [delivery_path],
                            integration,
                            integration_path,
                            goal_binding=goal_binding,
                        ),
                        "goal_ledger": goal_binding,
                    },
                }
            ]
            team_item = receipt["gates"]["team_integration"]["evidence"][0]
            receipt["goal_binding"]["acceptance_claims"]["a1"].append(
                {
                    "gate": "team_integration",
                    "evidence_index": 0,
                    "evidence_sha256": (
                        validate_evidence_v3.canonical_sha256(team_item)
                    ),
                }
            )
            receipt_path = write_json(base / "receipt.json", receipt)
            validated = run_without_manifest(
                project,
                receipt_path,
                "--goal-state",
                str(state_dir / "goal-ledger-state.json"),
                "--team-packet",
                str(packet_path),
                "--team-delivery",
                str(delivery_path),
                "--team-integration",
                str(integration_path),
                "--team-artifact-root",
                str(proof_root),
                "--team-workspace-root",
                str(project),
                "--team-baseline-root",
                str(project),
                "--team-worker-root",
                f"inspect={project}",
            )
            completed = goal_command(
                "completion-ready",
                "--root",
                str(project),
                "--state-dir",
                str(state_dir),
                "--receipt",
                str(receipt_path),
                "--team-packet",
                str(packet_path),
                "--team-delivery",
                str(delivery_path),
                "--team-integration",
                str(integration_path),
                "--team-artifact-root",
                str(proof_root),
                "--team-workspace-root",
                str(project),
                "--team-baseline-root",
                str(project),
                "--team-worker-root",
                f"inspect={project}",
            )
        self.assertEqual(
            validated.returncode, 0, validated.stdout + validated.stderr
        )
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )

    def test_non_team_v3_receipt_remains_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = write_json(root / "manifest.json", manifest_base())
            receipt_path = write_json(
                root / "receipt.json", receipt_base(manifest_path)
            )
            completed = run_receipt(
                root,
                manifest_path,
                receipt_path,
            )
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )


if __name__ == "__main__":
    unittest.main()
