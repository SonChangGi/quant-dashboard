from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import install as suite_installer


POLICY = "zero-spend-unless-user-first-requests-specific-paid-action"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        capture_output=True,
        check=False,
        text=True,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_manifest() -> dict[str, object]:
    return {
        "schema_version": 2,
        "project": {
            "id": "sample",
            "purpose": "Verify installed runtime routing.",
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


def local_receipt(manifest: Path) -> dict[str, object]:
    checked_at = "2026-07-26T00:00:00Z"
    evidence = {
        "kind": "inspection",
        "status": "verified",
        "summary": "The local fixture was inspected.",
        "source": "installed-runtime smoke fixture",
        "checked_at": checked_at,
    }
    return {
        "schema_version": 3,
        "project_id": "sample",
        "objective": "Verify installed runtime routing.",
        "scope": {
            "capabilities": [],
            "assurance": "light",
            "remote_actions": False,
            "analysis_control_ids": [],
        },
        "required_gates": ["contract", "cost"],
        "gates": {
            "contract": {"status": "passed", "evidence": [evidence]},
            "cost": {"status": "passed", "evidence": [evidence]},
        },
        "cost_authority": {
            "policy": POLICY,
            "classification": "no_billable_action",
            "decision": "allow",
            "paid_action_requested": False,
            "actions": [],
        },
        "context": {
            "manifest_sha256": sha256(manifest),
            "plan_sha256": "",
            "base_commit": "",
            "head_commit": "",
        },
        "goal_binding": None,
        "completed_at": "2026-07-26T00:01:00Z",
    }


class InstalledRuntimeSmokeTests(unittest.TestCase):
    def test_installed_copy_runs_optional_strict_and_legacy_entrypoints(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "skills"
            provenance = {
                "available": False,
                "origin": None,
                "branch": None,
                "commit": None,
                "tree": None,
                "dirty": None,
                "captured_at": "2026-07-26T00:00:00Z",
            }
            with mock.patch.object(suite_installer, "validate_source"):
                with mock.patch.object(
                    suite_installer,
                    "capture_source_git_provenance",
                    return_value=provenance,
                ):
                    with mock.patch.object(
                        sys,
                        "argv",
                        ["install.py", "--target", str(target)],
                    ):
                        self.assertEqual(suite_installer.main(), 0)

            shared = target / "quant-research-shared"
            scripts = shared / "scripts"
            authority = (shared / "core" / "authority.md").resolve()
            expected_shared_children = (
                "core/context-routing.md",
                "core/authority.md",
                "references/goal-and-subagents.md",
                "references/agent-orchestration.md",
                "references/durable-runtime.md",
                "references/web-design-source.md",
                "references/web-design-v2.4.1.md",
                "scripts/goal_ledger.py",
                "scripts/team_protocol.py",
            )
            for skill in (
                "quant-plan",
                "quant-goal",
                "quant-developer",
            ):
                skill_file = target / skill / "SKILL.md"
                resolved_shared = (
                    skill_file.parent / "../quant-research-shared"
                ).resolve()
                reference = (
                    skill_file.parent
                    / "../quant-research-shared/core/authority.md"
                ).resolve()
                with self.subTest(skill=skill):
                    self.assertEqual(resolved_shared, shared.resolve())
                    self.assertEqual(reference, authority)
                    self.assertTrue(reference.is_file())
                    for child in expected_shared_children:
                        self.assertTrue(
                            (resolved_shared / child).is_file(),
                            f"{skill}: missing installed shared child {child}",
                        )
            runtime_documents = (
                *sorted(target.glob("quant-*/SKILL.md")),
                *sorted((shared / "capabilities").glob("*.md")),
                *sorted((shared / "references").glob("*.md")),
            )
            for document in runtime_documents:
                with self.subTest(document=document):
                    document_text = document.read_text(encoding="utf-8")
                    self.assertNotIn(
                        "python3 shared/scripts/",
                        document_text,
                    )
                    self.assertNotIn(
                        "python3 <shared>/scripts/",
                        document_text,
                    )

            project = base / "project"
            project.mkdir()
            team_help = subprocess.run(
                [
                    sys.executable,
                    str(scripts / "team_protocol.py"),
                    "--help",
                ],
                cwd=project,
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(
                team_help.returncode,
                0,
                team_help.stdout + team_help.stderr,
            )
            manifest = project / "manifest.json"
            manifest.write_text(
                json.dumps(local_manifest()), encoding="utf-8"
            )

            context = run(
                sys.executable,
                str(scripts / "quantctl.py"),
                "context",
                "--manifest",
                str(manifest),
            )
            self.assertEqual(
                context.returncode, 0, context.stdout + context.stderr
            )
            self.assertIn("core/invariants.md", context.stdout)

            project_validation = run(
                sys.executable,
                str(scripts / "validate_project.py"),
                "--root",
                str(project),
                "--manifest",
                str(manifest),
            )
            self.assertEqual(
                project_validation.returncode,
                0,
                project_validation.stdout + project_validation.stderr,
            )

            receipt = project / "receipt.json"
            receipt.write_text(
                json.dumps(local_receipt(manifest)), encoding="utf-8"
            )
            evidence_validation = run(
                sys.executable,
                str(scripts / "validate_evidence.py"),
                str(receipt),
                "--project-root",
                str(project),
                "--manifest",
                str(manifest),
            )
            self.assertEqual(
                evidence_validation.returncode,
                0,
                evidence_validation.stdout + evidence_validation.stderr,
            )

            state = base / "goal-state"
            initialized = run(
                sys.executable,
                str(scripts / "goal_runtime.py"),
                "init",
                "--root",
                str(project),
                "--state-dir",
                str(state),
                "--goal-id",
                "installed-smoke",
                "--project-id",
                "sample",
                "--objective",
                "Verify installed runtime routing.",
                "--acceptance",
                "a1=Installed runtime verifies its state.",
                "--assurance",
                "light",
                "--manifest",
                str(manifest),
            )
            self.assertEqual(
                initialized.returncode,
                0,
                initialized.stdout + initialized.stderr,
            )
            verified = run(
                sys.executable,
                str(scripts / "goal_runtime.py"),
                "verify",
                "--root",
                str(project),
                "--state-dir",
                str(state),
            )
            self.assertEqual(
                verified.returncode, 0, verified.stdout + verified.stderr
            )

            acceptance = project / "host-ledger-acceptance.json"
            acceptance.write_text(
                json.dumps(
                    {
                        "acceptance": [
                            {
                                "id": "a1",
                                "text": (
                                    "Installed host-ledger routing resumes."
                                ),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            host_state = base / "host-goal-state"
            host_initialized = run(
                sys.executable,
                str(scripts / "goal_ledger.py"),
                "init",
                "--root",
                str(project),
                "--state-dir",
                str(host_state),
                "--goal-id",
                "installed-host-ledger",
                "--host-goal-id",
                "host-installed-smoke",
                "--project-id",
                "sample",
                "--objective",
                "Verify installed host-ledger routing.",
                "--acceptance",
                str(acceptance),
                "--assurance",
                "light",
                "--activation-reason",
                "recovery",
            )
            self.assertEqual(
                host_initialized.returncode,
                0,
                host_initialized.stdout + host_initialized.stderr,
            )
            host_resumed = run(
                sys.executable,
                str(scripts / "goal_ledger.py"),
                "resume",
                "--root",
                str(project),
                "--state-dir",
                str(host_state),
            )
            self.assertEqual(
                host_resumed.returncode,
                0,
                host_resumed.stdout + host_resumed.stderr,
            )

            legacy_manifest = json.loads(
                (
                    shared / "templates" / "quant-project.example.json"
                ).read_text(encoding="utf-8")
            )
            legacy_path = project / "legacy.json"
            legacy_path.write_text(
                json.dumps(legacy_manifest), encoding="utf-8"
            )
            legacy = run(
                sys.executable,
                str(scripts / "validate_project.py"),
                "--root",
                str(project),
                "--manifest",
                str(legacy_path),
            )
            self.assertNotIn("Traceback", legacy.stderr)
            self.assertNotIn("schema_version must equal 2", legacy.stdout)


if __name__ == "__main__":
    unittest.main()
