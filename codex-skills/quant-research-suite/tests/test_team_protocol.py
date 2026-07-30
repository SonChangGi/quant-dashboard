from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "shared" / "scripts"
TEMPLATES = ROOT / "shared" / "templates"
SCHEMAS = ROOT / "shared" / "schemas"
SCRIPT = SCRIPTS / "team_protocol.py"
sys.path.insert(0, str(SCRIPTS))

import team_protocol


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
DEFAULT_TEAM_OBJECTIVE = "Verify the bounded local deliverable."


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def seal_packet(packet: dict[str, object]) -> dict[str, object]:
    packet["packet_sha256"] = team_protocol.packet_hash(packet)
    return packet


def seal_receipt(receipt: dict[str, object]) -> dict[str, object]:
    receipt["receipt_sha256"] = team_protocol.receipt_hash(receipt)
    return receipt


def assignment(
    assignment_id: str,
    surface: str,
    *,
    mode: str = "isolated_write",
    required: bool = True,
    depends_on: list[str] | None = None,
    validation_group: str | None = None,
) -> dict[str, object]:
    return {
        "id": assignment_id,
        "role": "bounded-worker",
        "objective": f"Deliver {assignment_id}.",
        "non_goals": ["Do not change unrelated surfaces."],
        "required": required,
        "acceptance_ids": [f"a-{assignment_id}"],
        "depends_on": depends_on or [],
        "validation_group": validation_group,
        "workspace_binding_sha256": hashlib.sha256(
            f"workspace-binding-{assignment_id}".encode()
        ).hexdigest(),
        "baseline_binding": {
            "kind": "packet",
            "assignment_id": None,
        },
        "mode": mode,
        "write_scope": [] if mode == "read_only" else [f"src/{surface}/**"],
        "protected_scope": ["src/core/**"],
        "expected_checks": [f"check-{assignment_id}"],
        "expected_evidence": [f"evidence-{assignment_id}"],
        "stop_conditions": ["Stop at any authority boundary."],
    }


def make_packet(
    assignments: list[dict[str, object]],
    *,
    workspace_root: Path | None = None,
    assignment_roots: dict[str, Path] | None = None,
    objective: str = DEFAULT_TEAM_OBJECTIVE,
) -> dict[str, object]:
    packet = load_json(TEMPLATES / "team-run-packet.example.json")
    packet["team_run_id"] = "team-test"
    packet["owner"] = "standalone_developer"
    packet["goal_binding"] = None
    packet["objective_sha256"] = team_protocol.digest(objective)
    protected_patterns = sorted(
        {
            pattern
            for selected in assignments
            for pattern in selected["protected_scope"]
        }
    )
    packet["snapshot_policy"] = {
        "snapshot_version": 2,
        "excluded_root": None,
        "protected_patterns": protected_patterns,
    }
    for selected in assignments:
        selected_root = (assignment_roots or {}).get(str(selected["id"]))
        if selected_root is not None:
            selected["workspace_binding_sha256"] = (
                team_protocol.project_binding(selected_root)["identity_sha256"]
            )
    if workspace_root is not None:
        binding = team_protocol.project_binding(workspace_root)
        baseline = team_protocol.workspace_snapshot(
            workspace_root,
            None,
            protected_patterns,
            snapshot_version=2,
        )
        packet["project_binding_sha256"] = binding["identity_sha256"]
    else:
        body: dict[str, object] = {
            "kind": "directory",
            "head": None,
            "branch": None,
            "diff_sha256": None,
            "paths": {},
            "snapshot_version": 2,
            "protected_patterns": protected_patterns,
            "protected_paths": {},
        }
        baseline = {
            **body,
            "sha256": team_protocol.digest(body),
        }
    packet["baseline"] = {
        "workspace_sha256": baseline["sha256"],
        "head": baseline["head"],
        "branch": baseline["branch"],
    }
    packet["baseline_snapshot"] = baseline
    packet["assignments"] = assignments
    packet["join"] = {
        "integration_order": [
            item["id"] for item in assignments
        ],
        "verification": ["joined-project-native"],
        "review_boundary": "integrated_frozen_snapshot",
    }
    return seal_packet(packet)


def make_delivery(
    packet: dict[str, object],
    selected: dict[str, object],
    artifact_root: Path,
    *,
    worker_root: Path,
) -> dict[str, object]:
    assignment_id = str(selected["id"])
    artifact_ref = f"artifacts/{assignment_id}.artifact"
    artifact_path = artifact_root / artifact_ref
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_bytes = f"delivery artifact for {assignment_id}\n".encode()
    artifact_path.write_bytes(artifact_bytes)
    policy = packet["snapshot_policy"]
    excluded_root = (
        worker_root / policy["excluded_root"]
        if policy["excluded_root"] is not None
        else None
    )
    baseline_snapshot = team_protocol.workspace_snapshot(
        worker_root,
        excluded_root,
        policy["protected_patterns"],
        snapshot_version=2,
    )
    evidence_ids = list(selected["expected_evidence"])
    check_ids = list(selected["expected_checks"])
    paths = (
        []
        if selected["mode"] == "read_only"
        else [f"src/{assignment_id}/result.txt"]
    )
    for path in paths:
        destination = worker_root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            f"worker result for {assignment_id}\n",
            encoding="utf-8",
        )
    final_snapshot = team_protocol.workspace_snapshot(
        worker_root,
        excluded_root,
        policy["protected_patterns"],
        snapshot_version=2,
    )
    delivery: dict[str, object] = {
        "document_type": "quant_worker_delivery_receipt",
        "schema_version": 1,
        "team_run_id": packet["team_run_id"],
        "assignment_id": assignment_id,
        "packet_sha256": packet["packet_sha256"],
        "status": "ready_for_integration",
        "source": {
            "project_binding_sha256": packet["project_binding_sha256"],
            "workspace_binding_sha256": selected[
                "workspace_binding_sha256"
            ],
            "baseline_workspace_sha256": (
                baseline_snapshot["sha256"]
            ),
            "final_workspace_sha256": final_snapshot["sha256"],
        },
        "baseline_snapshot": baseline_snapshot,
        "final_snapshot": final_snapshot,
        "changed_paths": paths,
        "delivery_artifacts": [
            {
                "id": f"artifact-{assignment_id}",
                "kind": "report" if selected["mode"] == "read_only" else "patch",
                "ref": artifact_ref,
                "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
                "secret_scan": {
                    "mode": "validated_text",
                    "evidence_id": None,
                },
            }
        ],
        "claims": [
            {
                "acceptance_id": acceptance_id,
                "status": "passed",
                "evidence_ids": evidence_ids,
            }
            for acceptance_id in selected["acceptance_ids"]
        ],
        "evidence": [
            {
                "id": evidence_id,
                "kind": "artifact",
                "status": "passed",
                "summary": f"Direct evidence for {assignment_id}.",
                "artifact_ids": [f"artifact-{assignment_id}"],
            }
            for evidence_id in evidence_ids
        ],
        "checks": [
            {
                "id": check_id,
                "summary": f"Project-native check for {assignment_id}.",
                "status": "passed",
                "evidence_ids": evidence_ids,
            }
            for check_id in check_ids
        ],
        "cleanup": {
            "status": "passed",
            "summary": "The changed surface passed bounded cleanup.",
        },
        "unverified": [],
        "blockers": [],
        "completed_at": "2026-07-27T00:10:00Z",
        "receipt_sha256": "0" * 64,
    }
    return seal_receipt(delivery)


def make_integration(
    packet: dict[str, object],
    deliveries: list[dict[str, object]],
    *,
    workspace_root: Path | None = None,
) -> dict[str, object]:
    by_assignment = {
        str(item["assignment_id"]): item for item in deliveries
    }
    paths = sorted(
        {
            path
            for delivery in deliveries
            for path in delivery["changed_paths"]
        }
    )
    post_workspace_sha256 = (
        SHA_C if paths else packet["baseline"]["workspace_sha256"]
    )
    if workspace_root is not None:
        for path in paths:
            destination = workspace_root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                f"integrated result for {path}\n",
                encoding="utf-8",
            )
        post_workspace_sha256 = team_protocol.workspace_snapshot(
            workspace_root,
            None,
            packet["snapshot_policy"]["protected_patterns"],
            snapshot_version=2,
        )["sha256"]
    evidence = [
        {
            "id": f"join-{assignment_id}",
            "kind": "integration",
            "status": "passed",
            "summary": f"Integrated and verified {assignment_id}.",
            "source_sha256": post_workspace_sha256,
        }
        for assignment_id, delivery in by_assignment.items()
    ]
    evidence.extend(
        {
            "id": check_id,
            "kind": "verification",
            "status": "passed",
            "summary": f"Joined verification passed: {check_id}.",
            "source_sha256": post_workspace_sha256,
        }
        for check_id in packet["join"]["verification"]
    )
    results: list[dict[str, object]] = []
    claims: list[dict[str, object]] = []
    integrated_paths: set[str] = set()
    for selected in packet["assignments"]:
        assignment_id = str(selected["id"])
        delivery = by_assignment[assignment_id]
        read_only = selected["mode"] == "read_only"
        paths = [] if read_only else list(delivery["changed_paths"])
        integrated_paths.update(paths)
        results.append(
            {
                "assignment_id": assignment_id,
                "delivery_receipt_sha256": delivery["receipt_sha256"],
                "disposition": (
                    "accepted_read_only" if read_only else "integrated"
                ),
                "reason": "The bounded result passed joined verification.",
                "integrated_paths": paths,
                "evidence_ids": [f"join-{assignment_id}"],
            }
        )
        claims.extend(
            {
                "acceptance_id": acceptance_id,
                "status": "passed",
                "evidence_ids": [f"join-{assignment_id}"],
            }
            for acceptance_id in selected["acceptance_ids"]
        )
    paths = sorted(integrated_paths)
    integration: dict[str, object] = {
        "document_type": "quant_team_integration_receipt",
        "schema_version": 1,
        "team_run_id": packet["team_run_id"],
        "packet_sha256": packet["packet_sha256"],
        "integration_owner": packet["integration_owner"],
        "status": "ready_for_review",
        "delivery_results": results,
        "canonical_snapshot": {
            "pre_workspace_sha256": packet["baseline"]["workspace_sha256"],
            "post_workspace_sha256": post_workspace_sha256,
            "changed_paths": paths,
        },
        "acceptance_claims": claims,
        "evidence": evidence,
        "conflicts": [],
        "unverified": [],
        "blockers": [],
        "completed_at": "2026-07-27T00:20:00Z",
        "receipt_sha256": "0" * 64,
    }
    return seal_receipt(integration)


class TeamProtocolTests(unittest.TestCase):
    def test_schemas_and_examples_are_valid(self) -> None:
        for name in (
            "team-run-packet.schema.json",
            "worker-delivery-receipt.schema.json",
            "team-integration-receipt.schema.json",
        ):
            schema = load_json(SCHEMAS / name)
            self.assertEqual(
                schema["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )
        packet = load_json(TEMPLATES / "team-run-packet.example.json")
        delivery = load_json(
            TEMPLATES / "worker-delivery-receipt.example.json"
        )
        integration = load_json(
            TEMPLATES / "team-integration-receipt.example.json"
        )
        self.assertEqual(packet["packet_sha256"], team_protocol.packet_hash(packet))
        self.assertTrue(team_protocol.is_sha256(packet["objective_sha256"]))
        self.assertEqual(
            delivery["receipt_sha256"], team_protocol.receipt_hash(delivery)
        )
        self.assertEqual(
            integration["receipt_sha256"],
            team_protocol.receipt_hash(integration),
        )
        self.assertEqual(team_protocol.validate_packet(packet), [])
        with tempfile.TemporaryDirectory() as directory:
            artifact_root = Path(directory)
            artifact = artifact_root / "artifacts" / "implement-ui.patch"
            artifact.parent.mkdir()
            artifact.write_bytes(b"example patch\n")
            self.assertEqual(
                team_protocol.validate_delivery(
                    packet,
                    delivery,
                    artifact_root=artifact_root,
                    structural_only=True,
                ),
                [],
            )
            self.assertIn(
                "ready integration requires canonical workspace-root verification",
                team_protocol.validate_integration(
                    packet, [delivery], integration, artifact_root=artifact_root
                ),
            )

    def test_packet_v2_separates_risk_assurance_and_release_delivery(
        self,
    ) -> None:
        packet = make_packet([assignment("inspect", "inspect", mode="read_only")])
        packet["assurance"] = "standard"
        packet["delivery"] = "release"
        seal_packet(packet)
        self.assertEqual(team_protocol.validate_packet(packet), [])
        self.assertEqual(
            team_protocol.packet_risk_assurance(packet), "standard"
        )
        self.assertEqual(team_protocol.packet_delivery(packet), "release")

        packet["assurance"] = "release"
        seal_packet(packet)
        self.assertIn(
            "packet v2 assurance must be light, standard, or strict",
            team_protocol.validate_packet(packet),
        )

    def test_legacy_packet_v1_release_remains_explicitly_compatible(
        self,
    ) -> None:
        packet = make_packet([assignment("inspect", "inspect", mode="read_only")])
        packet["schema_version"] = 1
        packet.pop("delivery")
        packet["assurance"] = "release"
        seal_packet(packet)
        self.assertEqual(team_protocol.validate_packet(packet), [])
        self.assertEqual(team_protocol.packet_risk_assurance(packet), "strict")
        self.assertEqual(team_protocol.packet_delivery(packet), "release")

    def test_packet_rejects_paid_data_instruction_but_allows_refusal(
        self,
    ) -> None:
        selected = assignment("inspect", "inspect", mode="read_only")
        packet = make_packet([selected])
        for objective in (
            "Subscribe to a paid market-data API and integrate its price feed.",
            "Use paid data without delay.",
            "Download premium price data.",
            "Use a no-billing source and a premium price feed.",
            "Use a $10/month market data source.",
            "Buy an add-on for quote access.",
            "Use a free-only API until fees start.",
            "프리미엄 시세 API를 이용한다.",
        ):
            with self.subTest(objective=objective):
                selected["objective"] = objective
                seal_packet(packet)
                issues = team_protocol.validate_packet(packet)
                self.assertTrue(
                    any(
                        "prohibited paid data" in issue
                        for issue in issues
                    ),
                    issues,
                )

        selected["objective"] = "Do not use paid data."
        seal_packet(packet)
        self.assertFalse(
            any(
                "prohibited paid data" in issue
                for issue in team_protocol.validate_packet(packet)
            )
        )

    def test_resealed_delivery_and_integration_cannot_claim_paid_data_use(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project = base / "project"
            project.mkdir()
            (project / "src" / "core").mkdir(parents=True)
            (project / "src" / "core" / "contract.txt").write_text(
                "protected\n", encoding="utf-8"
            )
            artifact_root = base / "artifacts"
            artifact_root.mkdir()
            selected = assignment("inspect", "inspect", mode="read_only")
            packet = make_packet(
                [selected],
                workspace_root=project,
                assignment_roots={"inspect": project},
            )
            delivery = make_delivery(
                packet,
                selected,
                artifact_root,
                worker_root=project,
            )
            delivery["evidence"][0]["summary"] = (
                "Subscribed to a paid market-data API and integrated its "
                "price feed."
            )
            seal_receipt(delivery)
            delivery_issues = team_protocol.validate_delivery(
                packet,
                delivery,
                artifact_root=artifact_root,
                worker_root=project,
            )
            self.assertTrue(
                any("delivery proof prose" in issue for issue in delivery_issues),
                delivery_issues,
            )

            delivery["evidence"][0]["summary"] = (
                "Verified that paid data was not used."
            )
            seal_receipt(delivery)
            integration = make_integration(
                packet,
                [delivery],
                workspace_root=project,
            )
            integration["evidence"][0]["summary"] = (
                "Enable premium price feed and verify the joined result."
            )
            seal_receipt(integration)
            integration_issues = team_protocol.validate_integration(
                packet,
                [delivery],
                integration,
                artifact_root=artifact_root,
                workspace_root=project,
            )
            self.assertTrue(
                any(
                    "integration proof prose" in issue
                    for issue in integration_issues
                ),
                integration_issues,
            )

    def test_packet_rejects_unknown_dependency_and_cycle(self) -> None:
        first = assignment("first", "first", depends_on=["missing"])
        packet = make_packet([first])
        issues = team_protocol.validate_packet(packet)
        self.assertTrue(any("unknown dependencies" in issue for issue in issues))

        first["depends_on"] = ["second"]
        second = assignment("second", "second", depends_on=["first"])
        packet = make_packet([first, second])
        issues = team_protocol.validate_packet(packet)
        self.assertTrue(any("dependency cycle" in issue for issue in issues))

    def test_packet_requires_canonical_objective_digest(self) -> None:
        packet = make_packet([assignment("worker", "worker")])
        self.assertEqual(
            packet["objective_sha256"],
            team_protocol.digest(DEFAULT_TEAM_OBJECTIVE),
        )

        missing = copy.deepcopy(packet)
        del missing["objective_sha256"]
        seal_packet(missing)
        issues = team_protocol.validate_packet(missing)
        self.assertTrue(
            any("missing fields: objective_sha256" in issue for issue in issues)
        )

        invalid = copy.deepcopy(packet)
        invalid["objective_sha256"] = True
        seal_packet(invalid)
        self.assertIn(
            "packet objective_sha256 is invalid",
            team_protocol.validate_packet(invalid),
        )

    def test_goal_binding_rejects_boolean_revisions(self) -> None:
        for field in ("plan_revision", "acceptance_revision"):
            with self.subTest(field=field):
                packet = make_packet([assignment("worker", "worker")])
                packet["owner"] = "goal"
                packet["goal_binding"] = {
                    "goal_id": "goal-test",
                    "plan_revision": 1,
                    "acceptance_revision": 1,
                }
                packet["goal_binding"][field] = True
                seal_packet(packet)
                self.assertIn(
                    "packet goal_binding is invalid",
                    team_protocol.validate_packet(packet),
                )

    def test_writer_preflight_binds_live_root_baseline_and_isolation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "canonical"
            canonical.mkdir()
            first_root = root / "first-worker"
            first_root.mkdir()
            first = assignment("first", "first")
            packet = make_packet(
                [first],
                workspace_root=canonical,
                assignment_roots={"first": first_root},
            )
            self.assertEqual(
                team_protocol.validate_packet(
                    packet,
                    project_root=canonical,
                    workspace_root=canonical,
                    worker_roots={"first": first_root},
                    require_worker_preflight=True,
                ),
                [],
            )

            fake_binding = copy.deepcopy(packet)
            fake_binding["assignments"][0][
                "workspace_binding_sha256"
            ] = "0" * 64
            seal_packet(fake_binding)
            issues = team_protocol.validate_packet(
                fake_binding,
                project_root=canonical,
                workspace_root=canonical,
                worker_roots={"first": first_root},
                require_worker_preflight=True,
            )
            self.assertTrue(
                any(
                    "root binding does not match assignment" in issue
                    for issue in issues
                ),
                issues,
            )

            missing = team_protocol.validate_packet(
                packet,
                project_root=canonical,
                workspace_root=canonical,
                worker_roots={},
                require_worker_preflight=True,
            )
            self.assertTrue(
                any("missing writer roots: first" in issue for issue in missing),
                missing,
            )

            (first_root / "stale.txt").write_text(
                "not the issuance baseline\n",
                encoding="utf-8",
            )
            stale = team_protocol.validate_packet(
                packet,
                project_root=canonical,
                workspace_root=canonical,
                worker_roots={"first": first_root},
                require_worker_preflight=True,
            )
            self.assertTrue(
                any(
                    "baseline does not match packet issuance baseline" in issue
                    for issue in stale
                ),
                stale,
            )

            shared_root = root / "shared-worker"
            shared_root.mkdir()
            first = assignment("first", "first")
            second = assignment("second", "second")
            shared = make_packet(
                [first, second],
                workspace_root=canonical,
                assignment_roots={
                    "first": shared_root,
                    "second": shared_root,
                },
            )
            isolation = team_protocol.validate_packet(
                shared,
                project_root=canonical,
                workspace_root=canonical,
                worker_roots={
                    "first": shared_root,
                    "second": shared_root,
                },
                require_worker_preflight=True,
            )
            self.assertTrue(
                any(
                    "isolated writer roots must be physically distinct" in issue
                    for issue in isolation
                ),
                isolation,
            )

    def test_future_protocol_times_and_duplicate_json_keys_fail_closed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            artifacts = root / "artifacts"
            artifacts.mkdir()
            selected = assignment("inspect", "inspect", mode="read_only")
            packet = make_packet(
                [selected],
                workspace_root=workspace,
                assignment_roots={"inspect": workspace},
            )
            packet["created_at"] = "2099-01-01T00:00:00Z"
            seal_packet(packet)
            self.assertIn(
                "packet created_at exceeds allowed future clock skew",
                team_protocol.validate_packet(packet),
            )

            delivery = make_delivery(
                packet,
                selected,
                artifacts,
                worker_root=workspace,
            )
            delivery["completed_at"] = "2099-01-01T00:10:00Z"
            seal_receipt(delivery)
            delivery_issues = team_protocol.validate_delivery(
                packet,
                delivery,
                artifact_root=artifacts,
                structural_only=True,
            )
            self.assertIn(
                "delivery completed_at exceeds allowed future clock skew",
                delivery_issues,
            )

            integration = make_integration(
                packet,
                [delivery],
                workspace_root=workspace,
            )
            integration["completed_at"] = "2099-01-01T00:20:00Z"
            seal_receipt(integration)
            integration_issues = team_protocol.validate_integration(
                packet,
                [delivery],
                integration,
                artifact_root=artifacts,
                workspace_root=workspace,
            )
            self.assertIn(
                "integration completed_at exceeds allowed future clock skew",
                integration_issues,
            )

            duplicate = root / "duplicate.json"
            duplicate.write_text('{"value": 1, "value": 2}', encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "duplicate JSON object key",
            ):
                team_protocol.load(duplicate)

    def test_packet_rejects_unsafe_parallel_write_scopes(self) -> None:
        first = assignment("first", "first")
        second = assignment("second", "second")
        packet = make_packet([first, second])
        self.assertEqual(team_protocol.validate_packet(packet), [])

        second["write_scope"] = ["src/first/**"]
        packet = make_packet([first, second])
        self.assertTrue(
            any(
                "concurrent write scopes may overlap" in issue
                for issue in team_protocol.validate_packet(packet)
            )
        )

        second["write_scope"] = ["src/second/**"]
        second["mode"] = "same_workspace_sequential_write"
        packet = make_packet([first, second])
        self.assertTrue(
            any(
                "unordered same-workspace write assignments" in issue
                for issue in team_protocol.validate_packet(packet)
            )
        )

    def test_packet_rejects_reserved_case_overlap_and_policy_payloads(
        self,
    ) -> None:
        selected = assignment("worker", "worker")
        selected["write_scope"] = [".GiT/**"]
        issues = team_protocol.validate_packet(make_packet([selected]))
        self.assertTrue(
            any("escaping or reserved patterns" in issue for issue in issues)
        )
        for windows_scope in (
            "C:\\repo\\src\\**",
            "\\\\server\\share\\src\\**",
            "C:/repo/src/**",
        ):
            selected = assignment("worker", "worker")
            selected["write_scope"] = [windows_scope]
            issues = team_protocol.validate_packet(make_packet([selected]))
            self.assertTrue(
                any(
                    "escaping or reserved patterns" in issue
                    for issue in issues
                ),
                windows_scope,
            )

        first = assignment("first", "first")
        second = assignment("second", "second")
        first["write_scope"] = ["Src/API/**"]
        second["write_scope"] = ["src/api/private/**"]
        issues = team_protocol.validate_packet(make_packet([first, second]))
        self.assertTrue(
            any("concurrent write scopes may overlap" in issue for issue in issues)
        )

        selected = assignment("worker", "worker")
        selected["objective"] = "Use token=real-secret-value-12345."
        issues = team_protocol.validate_packet(make_packet([selected]))
        self.assertTrue(any("packet policy:" in issue for issue in issues))

        packet = make_packet([assignment("worker", "worker")])
        packet["payment_method_registration_required"] = True
        seal_packet(packet)
        issues = team_protocol.validate_packet(packet)
        self.assertTrue(
            any(
                issue.startswith("packet policy:")
                for issue in issues
            )
        )

    def test_packet_rejects_escaping_and_protected_scope(self) -> None:
        selected = assignment("worker", "worker")
        selected["write_scope"] = ["../secret/**"]
        packet = make_packet([selected])
        self.assertTrue(
            any(
                "escaping or reserved patterns" in issue
                for issue in team_protocol.validate_packet(packet)
            )
        )

        selected["write_scope"] = ["src/worker/**"]
        selected["protected_scope"] = ["src/worker/private/**"]
        packet = make_packet([selected])
        self.assertTrue(
            any(
                "may overlap its protected scope" in issue
                for issue in team_protocol.validate_packet(packet)
            )
        )

    def test_delivery_binds_project_scope_and_expected_proof(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = root / "artifacts"
            artifact_root.mkdir()
            worker_root = root / "worker"
            worker_root.mkdir()
            selected = assignment("worker", "worker")
            packet = make_packet(
                [selected],
                assignment_roots={"worker": worker_root},
            )
            delivery = make_delivery(
                packet,
                selected,
                artifact_root,
                worker_root=worker_root,
            )
            self.assertEqual(
                team_protocol.validate_delivery(
                    packet,
                    delivery,
                    artifact_root=artifact_root,
                    worker_root=worker_root,
                ),
                [],
            )

            changed = copy.deepcopy(delivery)
            changed["source"]["project_binding_sha256"] = "d" * 64
            seal_receipt(changed)
            issues = team_protocol.validate_delivery(
                packet,
                changed,
                artifact_root=artifact_root,
                worker_root=worker_root,
            )
            self.assertTrue(
                any("project binding does not match" in issue for issue in issues)
            )

            changed = copy.deepcopy(delivery)
            changed["source"]["workspace_binding_sha256"] = "e" * 64
            seal_receipt(changed)
            issues = team_protocol.validate_delivery(
                packet,
                changed,
                artifact_root=artifact_root,
                worker_root=worker_root,
            )
            self.assertTrue(
                any(
                    "workspace binding does not match assignment" in issue
                    for issue in issues
                )
            )

            changed = copy.deepcopy(delivery)
            changed["changed_paths"] = ["src/other/result.txt"]
            seal_receipt(changed)
            issues = team_protocol.validate_delivery(
                packet,
                changed,
                artifact_root=artifact_root,
                worker_root=worker_root,
            )
            self.assertTrue(
                any("outside assignment write scope" in issue for issue in issues)
            )

            expanded = copy.deepcopy(packet)
            expanded["assignments"][0]["expected_evidence"].append(
                "browser-proof"
            )
            expanded["assignments"][0]["expected_checks"].append("typecheck")
            seal_packet(expanded)
            changed = copy.deepcopy(delivery)
            changed["packet_sha256"] = expanded["packet_sha256"]
            seal_receipt(changed)
            issues = team_protocol.validate_delivery(
                expanded,
                changed,
                artifact_root=artifact_root,
                worker_root=worker_root,
            )
            self.assertTrue(
                any("missing expected evidence IDs" in issue for issue in issues)
            )
            self.assertTrue(
                any("missing expected check IDs" in issue for issue in issues)
            )

            unbound = copy.deepcopy(delivery)
            unbound["evidence"][0]["artifact_ids"] = []
            seal_receipt(unbound)
            issues = team_protocol.validate_delivery(
                packet,
                unbound,
                artifact_root=artifact_root,
                worker_root=worker_root,
            )
            self.assertTrue(
                any("expected evidence is not artifact-bound" in issue for issue in issues)
            )

            for windows_path in (
                "C:\\repo\\result.txt",
                "\\\\server\\share\\result.txt",
                "C:/repo/result.txt",
            ):
                changed = copy.deepcopy(delivery)
                changed["changed_paths"] = [windows_path]
                changed["delivery_artifacts"][0]["ref"] = windows_path
                seal_receipt(changed)
                issues = team_protocol.validate_delivery(
                    packet,
                    changed,
                    artifact_root=artifact_root,
                    worker_root=worker_root,
                )
                self.assertTrue(
                    any(
                        "reserved paths" in issue
                        or "portable artifact-relative path" in issue
                        for issue in issues
                    ),
                    windows_path,
                )

            wrong_worker = root / "other-worker"
            wrong_worker.mkdir()
            issues = team_protocol.validate_delivery(
                packet,
                delivery,
                artifact_root=artifact_root,
                worker_root=wrong_worker,
            )
            self.assertTrue(
                any("worker root binding does not match" in issue for issue in issues)
            )

            (worker_root / "unreported.txt").write_text(
                "not in the delivery snapshot\n",
                encoding="utf-8",
            )
            issues = team_protocol.validate_delivery(
                packet,
                delivery,
                artifact_root=artifact_root,
                worker_root=worker_root,
            )
            self.assertTrue(
                any("worker root snapshot does not match" in issue for issue in issues)
            )

    def test_ready_delivery_requires_verified_artifact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = root / "artifacts"
            artifact_root.mkdir()
            worker_root = root / "worker"
            worker_root.mkdir()
            selected = assignment("worker", "worker")
            packet = make_packet(
                [selected],
                assignment_roots={"worker": worker_root},
            )
            delivery = make_delivery(
                packet,
                selected,
                artifact_root,
                worker_root=worker_root,
            )
            alias = root / "artifact-root-link"
            alias.symlink_to(artifact_root, target_is_directory=True)
            issues = team_protocol.validate_delivery(
                packet,
                delivery,
                artifact_root=alias,
                worker_root=worker_root,
            )
            self.assertTrue(
                any("artifact root must not be a symbolic link" in issue for issue in issues)
            )
            issues = team_protocol.validate_delivery(packet, delivery)
            self.assertIn(
                "ready delivery requires artifact-root byte verification",
                issues,
            )
            self.assertIn(
                "ready delivery requires worker-root final snapshot verification",
                issues,
            )

            artifact = artifact_root / delivery["delivery_artifacts"][0]["ref"]
            artifact.write_bytes(b"tampered\n")
            issues = team_protocol.validate_delivery(
                packet,
                delivery,
                artifact_root=artifact_root,
                worker_root=worker_root,
            )
            self.assertTrue(
                any("does not match artifact bytes" in issue for issue in issues)
            )

            outside = root / "outside.patch"
            outside.write_bytes(b"outside\n")
            artifact.unlink()
            artifact.symlink_to(outside)
            issues = team_protocol.validate_delivery(
                packet,
                delivery,
                artifact_root=artifact_root,
                worker_root=worker_root,
            )
            self.assertTrue(
                any("must not traverse a symbolic link" in issue for issue in issues)
            )

    def test_ready_delivery_scans_text_and_blocks_unscannable_artifacts(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = root / "artifacts"
            artifact_root.mkdir()
            worker_root = root / "worker"
            worker_root.mkdir()
            selected = assignment("worker", "worker")
            packet = make_packet(
                [selected],
                assignment_roots={"worker": worker_root},
            )
            delivery = make_delivery(
                packet,
                selected,
                artifact_root,
                worker_root=worker_root,
            )
            artifact_record = delivery["delivery_artifacts"][0]
            artifact = artifact_root / artifact_record["ref"]

            secret_bytes = (
                b"token=" + b"sk" + b"-" + b"a" * 32 + b"\n"
            )
            artifact.write_bytes(secret_bytes)
            artifact_record["sha256"] = hashlib.sha256(secret_bytes).hexdigest()
            seal_receipt(delivery)
            issues = team_protocol.validate_delivery(
                packet,
                delivery,
                artifact_root=artifact_root,
                worker_root=worker_root,
            )
            self.assertTrue(
                any("artifact bytes" in issue for issue in issues)
            )

            binary_bytes = b"\xff\x00\x81"
            artifact.write_bytes(binary_bytes)
            artifact_record["sha256"] = hashlib.sha256(binary_bytes).hexdigest()
            artifact_record["secret_scan"] = {
                "mode": "external_scan",
                "evidence_id": "binary-secret-scan",
            }
            seal_receipt(delivery)
            issues = team_protocol.validate_delivery(
                packet,
                delivery,
                artifact_root=artifact_root,
                worker_root=worker_root,
            )
            self.assertTrue(
                any(
                    "unscannable artifact lacks passed external secret-scan"
                    in issue
                    for issue in issues
                )
            )

    def test_blocked_delivery_can_be_inspected_without_artifact_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = root / "artifacts"
            artifact_root.mkdir()
            worker_root = root / "worker"
            worker_root.mkdir()
            selected = assignment("worker", "worker")
            packet = make_packet(
                [selected],
                assignment_roots={"worker": worker_root},
            )
            delivery = make_delivery(
                packet,
                selected,
                artifact_root,
                worker_root=worker_root,
            )
        delivery["status"] = "blocked"
        delivery["changed_paths"] = []
        delivery["final_snapshot"] = copy.deepcopy(
            delivery["baseline_snapshot"]
        )
        delivery["source"]["final_workspace_sha256"] = delivery[
            "baseline_snapshot"
        ]["sha256"]
        delivery["delivery_artifacts"] = []
        delivery["claims"] = []
        delivery["evidence"] = []
        delivery["checks"] = []
        delivery["cleanup"] = {
            "status": "blocked",
            "summary": "A material dependency is unavailable.",
        }
        delivery["blockers"] = [
            "Blocking finding: the implementation uses paid data."
        ]
        seal_receipt(delivery)
        self.assertEqual(team_protocol.validate_delivery(packet, delivery), [])

    def test_receipt_tampering_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = root / "artifacts"
            artifact_root.mkdir()
            worker_root = root / "worker"
            worker_root.mkdir()
            selected = assignment("worker", "worker")
            packet = make_packet(
                [selected],
                assignment_roots={"worker": worker_root},
            )
            delivery = make_delivery(
                packet,
                selected,
                artifact_root,
                worker_root=worker_root,
            )
            delivery["cleanup"]["summary"] = "Rewritten after signing."
            issues = team_protocol.validate_delivery(
                packet,
                delivery,
                artifact_root=artifact_root,
                worker_root=worker_root,
            )
        self.assertIn("delivery receipt SHA-256 is invalid", issues)

    def test_packet_cli_separates_live_and_structural_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            worker = root / "worker"
            worker.mkdir()
            packet = make_packet(
                [assignment("worker", "worker")],
                workspace_root=workspace,
                assignment_roots={"worker": worker},
            )
            packet_path = root / "packet.json"
            packet_path.write_text(
                json.dumps(packet, sort_keys=True),
                encoding="utf-8",
            )

            missing_roots = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "packet",
                    "--packet",
                    str(packet_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(missing_roots.returncode, 1)
            self.assertIn(
                "requires --project-root",
                missing_roots.stdout,
            )

            structural = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "packet",
                    "--packet",
                    str(packet_path),
                    "--structural-only",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(structural.returncode, 0, structural.stdout)
            self.assertEqual(
                json.loads(structural.stdout)["status"], "structural_only"
            )

            missing_worker_root = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "packet",
                    "--packet",
                    str(packet_path),
                    "--project-root",
                    str(workspace),
                    "--workspace-root",
                    str(workspace),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(missing_worker_root.returncode, 1)
            self.assertIn(
                "worker preflight is missing writer roots",
                missing_worker_root.stdout,
            )

            live = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "packet",
                    "--packet",
                    str(packet_path),
                    "--project-root",
                    str(workspace),
                    "--workspace-root",
                    str(workspace),
                    "--worker-root",
                    f"worker={worker}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(live.returncode, 0, live.stdout)

            (workspace / "unexpected.txt").write_text(
                "changed after issuance\n",
                encoding="utf-8",
            )
            stale = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "packet",
                    "--packet",
                    str(packet_path),
                    "--project-root",
                    str(workspace),
                    "--workspace-root",
                    str(workspace),
                    "--worker-root",
                    f"worker={worker}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(stale.returncode, 1)
            self.assertIn("baseline does not match", stale.stdout)

    def test_installed_shared_root_command_runs_outside_suite_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed_skills = root / "installed-skills"
            installed_shared = (
                installed_skills / "quant-research-shared"
            )
            shutil.copytree(ROOT / "shared", installed_shared)
            unrelated_cwd = root / "unrelated-working-directory"
            unrelated_cwd.mkdir()
            workspace = root / "workspace"
            workspace.mkdir()
            selected = assignment(
                "inspect",
                "inspect",
                mode="read_only",
            )
            packet = make_packet(
                [selected],
                workspace_root=workspace,
                assignment_roots={"inspect": workspace},
            )
            packet_path = root / "packet.json"
            packet_path.write_text(
                json.dumps(packet, sort_keys=True),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(
                        installed_shared
                        / "scripts"
                        / "team_protocol.py"
                    ),
                    "packet",
                    "--packet",
                    str(packet_path),
                    "--structural-only",
                ],
                cwd=unrelated_cwd,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )
        self.assertEqual(
            json.loads(completed.stdout)["status"],
            "structural_only",
        )

    def test_live_handoff_binds_packet_worker_and_distinct_baseline_roots(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = root / "artifacts"
            artifact_root.mkdir()
            canonical_root = root / "canonical"
            canonical_root.mkdir()
            baseline_root = root / "baseline"
            baseline_root.mkdir()
            worker_root = root / "worker"
            worker_root.mkdir()
            selected = assignment("worker", "worker")
            packet = make_packet(
                [selected],
                workspace_root=canonical_root,
                assignment_roots={"worker": worker_root},
            )
            delivery = make_delivery(
                packet,
                selected,
                artifact_root,
                worker_root=worker_root,
            )
            integration = make_integration(
                packet,
                [delivery],
                workspace_root=canonical_root,
            )

            live_issues = team_protocol.validate_integration(
                packet,
                [delivery],
                integration,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
                project_root=canonical_root,
                baseline_root=baseline_root,
                worker_roots={"worker": worker_root},
                require_live_handoff=True,
            )
            self.assertEqual(live_issues, [])

            missing_worker = team_protocol.validate_integration(
                packet,
                [delivery],
                integration,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
                project_root=canonical_root,
                baseline_root=baseline_root,
                worker_roots={},
                require_live_handoff=True,
            )
            self.assertTrue(
                any("missing worker roots" in issue for issue in missing_worker)
            )

            wrong_worker_root = root / "wrong-worker"
            wrong_worker_root.mkdir()
            wrong_worker = team_protocol.validate_integration(
                packet,
                [delivery],
                integration,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
                project_root=canonical_root,
                baseline_root=baseline_root,
                worker_roots={"worker": wrong_worker_root},
                require_live_handoff=True,
            )
            self.assertTrue(
                any(
                    "worker root binding does not match assignment" in issue
                    for issue in wrong_worker
                )
            )

            reused_baseline = team_protocol.validate_integration(
                packet,
                [delivery],
                integration,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
                project_root=canonical_root,
                baseline_root=canonical_root,
                worker_roots={"worker": worker_root},
                require_live_handoff=True,
            )
            self.assertTrue(
                any(
                    "requires distinct physical baseline" in issue
                    for issue in reused_baseline
                )
            )

            packet_path = artifact_root / "packet.json"
            delivery_path = artifact_root / "delivery.json"
            integration_path = artifact_root / "integration.json"
            for path, document in (
                (packet_path, packet),
                (delivery_path, delivery),
                (integration_path, integration),
            ):
                path.write_text(
                    json.dumps(document, sort_keys=True),
                    encoding="utf-8",
                )
            command = [
                sys.executable,
                str(SCRIPT),
                "integration",
                "--packet",
                str(packet_path),
                "--delivery",
                str(delivery_path),
                "--integration",
                str(integration_path),
                "--artifact-root",
                str(artifact_root),
                "--workspace-root",
                str(canonical_root),
                "--project-root",
                str(canonical_root),
                "--baseline-root",
                str(baseline_root),
                "--require-live-handoff",
            ]
            live_cli = subprocess.run(
                [
                    *command,
                    "--worker-root",
                    f"worker={worker_root}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                live_cli.returncode,
                0,
                live_cli.stdout + live_cli.stderr,
            )

            missing_cli = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(missing_cli.returncode, 1)
            self.assertIn("missing worker roots", missing_cli.stdout)

            malformed_cli = subprocess.run(
                [*command, "--worker-root", "not-a-mapping"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(malformed_cli.returncode, 1)
            self.assertIn(
                "must use ASSIGNMENT_ID=PATH", malformed_cli.stdout
            )

            duplicate_cli = subprocess.run(
                [
                    *command,
                    "--worker-root",
                    f"worker={worker_root}",
                    "--worker-root",
                    f"worker={worker_root}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(duplicate_cli.returncode, 1)
            self.assertIn(
                "duplicate --worker-root assignment ID",
                duplicate_cli.stdout,
            )

    def test_causal_order_and_sequential_baseline_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = root / "artifacts"
            artifact_root.mkdir()
            canonical_root = root / "workspace"
            canonical_root.mkdir()
            sequential_root = root / "sequential-worker"
            sequential_root.mkdir()
            first = assignment(
                "first",
                "first",
                mode="same_workspace_sequential_write",
            )
            second = assignment(
                "second",
                "second",
                mode="same_workspace_sequential_write",
                depends_on=["first"],
            )
            second["baseline_binding"] = {
                "kind": "assignment_final",
                "assignment_id": "first",
            }
            packet = make_packet(
                [first, second],
                workspace_root=canonical_root,
                assignment_roots={
                    "first": sequential_root,
                    "second": sequential_root,
                },
            )
            first_delivery = make_delivery(
                packet,
                first,
                artifact_root,
                worker_root=sequential_root,
            )
            second_delivery = make_delivery(
                packet,
                second,
                artifact_root,
                worker_root=sequential_root,
            )
            second_delivery["completed_at"] = "2026-07-27T00:11:00Z"
            seal_receipt(second_delivery)
            deliveries = [first_delivery, second_delivery]
            integration = make_integration(
                packet, deliveries, workspace_root=canonical_root
            )
            self.assertEqual(
                team_protocol.validate_integration(
                    packet,
                    deliveries,
                    integration,
                    artifact_root=artifact_root,
                    workspace_root=canonical_root,
                ),
                [],
            )

            wrong_chain = copy.deepcopy(second_delivery)
            wrong_chain["source"]["baseline_workspace_sha256"] = packet[
                "baseline"
            ]["workspace_sha256"]
            seal_receipt(wrong_chain)
            issues = team_protocol.validate_integration(
                packet,
                [first_delivery, wrong_chain],
                integration,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any("hash-bound baseline reference" in issue for issue in issues)
            )

            predating = copy.deepcopy(first_delivery)
            predating["completed_at"] = "2026-07-26T23:59:00Z"
            seal_receipt(predating)
            issues = team_protocol.validate_delivery(
                packet,
                predating,
                artifact_root=artifact_root,
                structural_only=True,
            )
            self.assertIn(
                "delivery completion predates packet creation", issues
            )

            dependency_reversal = copy.deepcopy(second_delivery)
            dependency_reversal["completed_at"] = "2026-07-27T00:09:00Z"
            seal_receipt(dependency_reversal)
            reversed_integration = make_integration(
                packet,
                [first_delivery, dependency_reversal],
                workspace_root=canonical_root,
            )
            issues = team_protocol.validate_integration(
                packet,
                [first_delivery, dependency_reversal],
                reversed_integration,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any("predates dependency delivery" in issue for issue in issues)
            )

            early_integration = copy.deepcopy(integration)
            early_integration["completed_at"] = "2026-07-27T00:05:00Z"
            seal_receipt(early_integration)
            issues = team_protocol.validate_integration(
                packet,
                deliveries,
                early_integration,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertIn(
                "integration completion predates a worker delivery", issues
            )

            live_issues = team_protocol.validate_integration(
                packet,
                deliveries,
                integration,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
                project_root=canonical_root,
                baseline_root=canonical_root,
                worker_roots={
                    "first": sequential_root,
                    "second": sequential_root,
                },
                require_live_handoff=True,
            )
            self.assertIn(
                "completion-eligible live handoff cannot preserve multiple "
                "sequential final snapshots",
                "\n".join(live_issues),
            )

    def test_integration_is_complete_and_binds_known_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = root / "delivery-artifacts"
            artifact_root.mkdir()
            canonical_root = root / "canonical-workspace"
            canonical_root.mkdir()
            first_worker = root / "first-worker"
            first_worker.mkdir()
            second_worker = root / "second-worker"
            second_worker.mkdir()
            first = assignment(
                "first", "first", validation_group="joined-contract"
            )
            second = assignment(
                "second",
                "second",
                required=False,
                validation_group="joined-contract",
            )
            packet = make_packet(
                [first, second],
                workspace_root=canonical_root,
                assignment_roots={
                    "first": first_worker,
                    "second": second_worker,
                },
            )
            deliveries = [
                make_delivery(
                    packet,
                    first,
                    artifact_root,
                    worker_root=first_worker,
                ),
                make_delivery(
                    packet,
                    second,
                    artifact_root,
                    worker_root=second_worker,
                ),
            ]
            integration = make_integration(
                packet, deliveries, workspace_root=canonical_root
            )
            self.assertEqual(
                team_protocol.validate_integration(
                    packet,
                    deliveries,
                    integration,
                    artifact_root=artifact_root,
                    workspace_root=canonical_root,
                ),
                [],
            )

            never_run_packet = copy.deepcopy(packet)
            never_run_packet["join"]["verification"].append("never-run-xyz")
            seal_packet(never_run_packet)
            never_run_deliveries = copy.deepcopy(deliveries)
            for delivery in never_run_deliveries:
                delivery["packet_sha256"] = never_run_packet["packet_sha256"]
                seal_receipt(delivery)
            never_run = make_integration(
                never_run_packet,
                never_run_deliveries,
                workspace_root=canonical_root,
            )
            never_run["evidence"] = [
                item
                for item in never_run["evidence"]
                if item["id"] != "never-run-xyz"
            ]
            seal_receipt(never_run)
            issues = team_protocol.validate_integration(
                never_run_packet,
                never_run_deliveries,
                never_run,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any(
                    "missing join verification evidence: never-run-xyz"
                    in issue
                    for issue in issues
                ),
                issues,
            )

            stale_join = copy.deepcopy(integration)
            next(
                item
                for item in stale_join["evidence"]
                if item["id"] == "joined-project-native"
            )["source_sha256"] = packet["baseline"]["workspace_sha256"]
            seal_receipt(stale_join)
            issues = team_protocol.validate_integration(
                packet,
                deliveries,
                stale_join,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any(
                    "join verification evidence must pass on the current "
                    "integration snapshot: joined-project-native"
                    in issue
                    for issue in issues
                ),
                issues,
            )

            issues = team_protocol.validate_integration(
                packet, deliveries, integration
            )
            self.assertTrue(
                any(
                    "artifact-root byte verification" in issue
                    for issue in issues
                )
            )

            incomplete = copy.deepcopy(integration)
            incomplete["delivery_results"].pop()
            seal_receipt(incomplete)
            issues = team_protocol.validate_integration(
                packet,
                deliveries,
                incomplete,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any("missing assignment results" in issue for issue in issues)
            )

            arbitrary = copy.deepcopy(integration)
            arbitrary["evidence"][0]["source_sha256"] = "f" * 64
            seal_receipt(arbitrary)
            issues = team_protocol.validate_integration(
                packet,
                deliveries,
                arbitrary,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any("unknown source anchor" in issue for issue in issues)
            )

            uncoupled = copy.deepcopy(integration)
            result = uncoupled["delivery_results"][1]
            result["disposition"] = "rejected"
            result["integrated_paths"] = []
            uncoupled["canonical_snapshot"]["changed_paths"] = list(
                uncoupled["delivery_results"][0]["integrated_paths"]
            )
            seal_receipt(uncoupled)
            issues = team_protocol.validate_integration(
                packet,
                deliveries,
                uncoupled,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any(
                    "validation-coupled assignment is not accepted" in issue
                    for issue in issues
                )
            )

            stale = copy.deepcopy(deliveries[0])
            stale["cleanup"]["summary"] = "Mutated after integration."
            issues = team_protocol.validate_integration(
                packet,
                [stale, deliveries[1]],
                integration,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any("delivery receipt SHA-256 is invalid" in issue for issue in issues)
            )
            seal_receipt(stale)
            issues = team_protocol.validate_integration(
                packet,
                [stale, deliveries[1]],
                integration,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any("delivery receipt hash mismatch" in issue for issue in issues)
            )

            blocked = copy.deepcopy(integration)
            blocked["status"] = "blocked"
            blocked["blockers"] = []
            seal_receipt(blocked)
            issues = team_protocol.validate_integration(
                packet,
                deliveries,
                blocked,
                artifact_root=artifact_root,
            )
            self.assertIn(
                "blocked or failed integration requires a blocker", issues
            )

            ready_with_blocker = copy.deepcopy(integration)
            ready_with_blocker["blockers"] = ["Unresolved integration issue."]
            seal_receipt(ready_with_blocker)
            issues = team_protocol.validate_integration(
                packet,
                deliveries,
                ready_with_blocker,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertIn("ready integration cannot retain blockers", issues)

            wrong_owner = copy.deepcopy(integration)
            wrong_owner["integration_owner"] = "other-owner"
            seal_receipt(wrong_owner)
            issues = team_protocol.validate_integration(
                packet,
                deliveries,
                wrong_owner,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertIn("integration owner does not match packet", issues)

            wrong_pre = copy.deepcopy(integration)
            wrong_pre["canonical_snapshot"]["pre_workspace_sha256"] = "e" * 64
            seal_receipt(wrong_pre)
            issues = team_protocol.validate_integration(
                packet,
                deliveries,
                wrong_pre,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any("pre snapshot does not match packet baseline" in issue for issue in issues)
            )

            wrong_post = copy.deepcopy(integration)
            wrong_post["canonical_snapshot"]["post_workspace_sha256"] = "f" * 64
            wrong_post["evidence"][0]["source_sha256"] = "f" * 64
            wrong_post["evidence"][1]["source_sha256"] = "f" * 64
            seal_receipt(wrong_post)
            issues = team_protocol.validate_integration(
                packet,
                deliveries,
                wrong_post,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any("workspace snapshot does not match" in issue for issue in issues)
            )

            protected_file = canonical_root / "src" / "core" / "secret.txt"
            protected_file.parent.mkdir(parents=True, exist_ok=True)
            protected_file.write_text(
                "unreported protected change\n",
                encoding="utf-8",
            )
            forged_post = team_protocol.workspace_snapshot(
                canonical_root,
                None,
                packet["snapshot_policy"]["protected_patterns"],
                snapshot_version=2,
            )["sha256"]
            forged = copy.deepcopy(integration)
            forged["canonical_snapshot"]["post_workspace_sha256"] = forged_post
            for item in forged["evidence"]:
                item["source_sha256"] = forged_post
            seal_receipt(forged)
            issues = team_protocol.validate_integration(
                packet,
                deliveries,
                forged,
                artifact_root=artifact_root,
                workspace_root=canonical_root,
            )
            self.assertTrue(
                any(
                    "observed baseline-to-post delta" in issue
                    for issue in issues
                )
            )


if __name__ == "__main__":
    unittest.main()
