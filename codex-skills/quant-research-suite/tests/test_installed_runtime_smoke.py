from __future__ import annotations

import hashlib
import json
import os
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


def install_suite(
    target: Path,
    *,
    include_legacy: bool = False,
    update: bool = False,
) -> None:
    provenance = {
        "available": False,
        "origin": None,
        "branch": None,
        "commit": None,
        "tree": None,
        "dirty": None,
        "captured_at": "2026-07-26T00:00:00Z",
    }
    argv = ["install.py", "--target", str(target)]
    if include_legacy:
        argv.append("--include-legacy")
    if update:
        argv.append("--update")
    with mock.patch.object(suite_installer, "validate_source"):
        with mock.patch.object(
            suite_installer,
            "capture_source_git_provenance",
            return_value=provenance,
        ):
            with mock.patch.object(sys, "argv", argv):
                if suite_installer.main() != 0:
                    raise AssertionError("suite installer returned non-zero")


class InstalledRuntimeSmokeTests(unittest.TestCase):
    def test_default_install_contains_only_lean_shared_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skills"
            install_suite(target)

            shared = target / "quant-research-shared"
            manifest = json.loads(
                (shared / "install-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["schema_version"], 3)
            self.assertEqual(manifest["install_profile"], "base")
            self.assertEqual(
                set(manifest["items"]["quant-research-shared"]),
                set(suite_installer.BASE_SHARED_FILES),
            )
            for relative in suite_installer.BASE_SHARED_FILES:
                with self.subTest(relative=relative):
                    self.assertTrue((shared / relative).is_file())
            for skill_name in (
                "quant-plan",
                "quant-goal",
                "quant-developer",
            ):
                skill_dir = target / skill_name
                with self.subTest(skill=skill_name, reference="kernel"):
                    self.assertTrue(
                        (
                            skill_dir
                            / "../quant-research-shared/references/"
                            "adaptive-workflow.md"
                        ).resolve().is_file()
                    )
                with self.subTest(skill=skill_name, reference="router"):
                    self.assertTrue(
                        (
                            skill_dir
                            / "../quant-research-shared/core/"
                            "context-routing.md"
                        ).resolve().is_file()
                    )
            for relative in (
                "scripts/goal_ledger.py",
                "scripts/quantctl.py",
                "scripts/validate_project.py",
                "schemas/quant-project-v2.schema.json",
                "schemas/evidence-receipt-v3.schema.json",
                "templates/team-run-packet.example.json",
            ):
                with self.subTest(relative=relative):
                    self.assertFalse((shared / relative).exists())

            external_data = (
                shared / "capabilities/external-data.md"
            ).read_text(encoding="utf-8")
            self.assertIn("`scheduled-automation.md`", external_data)
            self.assertIn("`publication.md`", external_data)
            self.assertIn("`../core/context-routing.md`", external_data)
            self.assertNotIn(
                "`../references/data-automation.md`",
                external_data,
            )
            self.assertFalse(
                (shared / "references/data-automation.md").exists()
            )
            self.assertTrue(
                (shared / "capabilities/analysis-input-flow.md").is_file()
            )
            self.assertTrue(
                (shared / "capabilities/long-running-recovery.md").is_file()
            )
            self.assertTrue(
                (shared / "scripts/recovery_checkpoint.py").is_file()
            )
            self.assertFalse(
                (shared / "capabilities/analysis-input-binding.md").exists()
            )

            validated = run(
                sys.executable,
                str(shared / "scripts" / "validate_installed.py"),
            )
            self.assertEqual(
                validated.returncode,
                0,
                validated.stdout + validated.stderr,
            )

    def test_installed_base_recovery_helper_round_trip_from_unrelated_cwd(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "skills"
            install_suite(target)
            helper = (
                target
                / "quant-research-shared"
                / "scripts"
                / "recovery_checkpoint.py"
            )
            project = base / "project"
            project.mkdir()
            initialized = subprocess.run(
                ["git", "-C", str(project), "init", "-q"],
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(
                initialized.returncode,
                0,
                initialized.stdout + initialized.stderr,
            )
            unrelated = base / "unrelated"
            unrelated.mkdir()
            environment = dict(os.environ)
            environment["CODEX_HOME"] = str(base / "codex-home")
            capsule = {
                "objective_summary": "Verify the installed helper.",
                "phase": "installed-smoke",
                "completion_conditions": [],
                "workers": [],
                "evidence_refs": [],
                "blockers": [],
                "pending_authority": [],
                "next_action": "Read the candidate and retire exact state.",
                "no_repeat": [],
            }
            checkpoint = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(helper),
                    "checkpoint",
                    "--root",
                    str(project),
                    "--capsule",
                    "-",
                ],
                cwd=unrelated,
                env=environment,
                input=json.dumps(capsule),
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(
                checkpoint.returncode,
                0,
                checkpoint.stdout + checkpoint.stderr,
            )
            created = json.loads(checkpoint.stdout)
            recovery_id = created["recovery_id"]

            resumed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(helper),
                    "resume",
                    "--root",
                    str(project),
                    "--recovery-id",
                    recovery_id,
                ],
                cwd=unrelated,
                env=environment,
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
            self.assertEqual(
                json.loads(resumed.stdout)["reconciliation"]["authority"]["status"],
                "not_recorded",
            )

            retired = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(helper),
                    "retire",
                    "--root",
                    str(project),
                    "--recovery-id",
                    recovery_id,
                    "--expected-sequence",
                    str(created["sequence"]),
                ],
                cwd=unrelated,
                env=environment,
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(retired.returncode, 0, retired.stdout + retired.stderr)
            self.assertEqual(json.loads(retired.stdout)["status"], "retired")

    def test_base_update_removes_previous_compatibility_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skills"
            install_suite(target, include_legacy=True)
            shared = target / "quant-research-shared"
            self.assertTrue((shared / "scripts" / "goal_ledger.py").is_file())

            install_suite(target, update=True)

            self.assertFalse((shared / "scripts" / "goal_ledger.py").exists())
            self.assertFalse((shared / "scripts" / "quantctl.py").exists())
            self.assertTrue(
                (shared / "scripts" / "recovery_checkpoint.py").is_file()
            )
            self.assertTrue(
                (shared / "capabilities" / "long-running-recovery.md").is_file()
            )
            manifest = json.loads(
                (shared / "install-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["install_profile"], "base")
            validated = run(
                sys.executable,
                str(shared / "scripts" / "validate_installed.py"),
            )
            self.assertEqual(
                validated.returncode,
                0,
                validated.stdout + validated.stderr,
            )

    def test_compat_manifest_requires_contract_reference_closure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skills"
            install_suite(target, include_legacy=True)
            shared = target / "quant-research-shared"
            manifest_path = shared / "install-manifest.json"
            validator = shared / "scripts/validate_installed.py"
            original_manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )

            for relative in (
                "references/data-automation.md",
                "capabilities/analysis-input-binding.md",
                "capabilities/agent-team-execution.md",
                "capabilities/long-running-recovery.md",
                "core/invariants.md",
                "core/evidence-semantics.md",
                "references/operating-principles.md",
                "references/goal-and-subagents.md",
                "profiles/quant-research-web.md",
                "adapters/github.md",
                "scripts/goal_primitives.py",
                "scripts/capability_model.py",
                "scripts/project_inventory.py",
                "scripts/recovery_checkpoint.py",
                "schemas/analysis-input-binding-capture.schema.json",
                "schemas/analysis-invocation.schema.json",
                "templates/analysis-input-binding-capture.example.json",
                "templates/analysis-invocation.example.json",
            ):
                with self.subTest(relative=relative):
                    child = shared / relative
                    original_bytes = child.read_bytes()
                    child.unlink()
                    mutated = json.loads(json.dumps(original_manifest))
                    del mutated["items"]["quant-research-shared"][relative]
                    mutated["suite_content_sha256"] = (
                        suite_installer.suite_content_sha256(
                            mutated["items"]
                        )
                    )
                    manifest_path.write_text(
                        json.dumps(mutated),
                        encoding="utf-8",
                    )

                    invalid = run(sys.executable, str(validator))
                    self.assertNotEqual(invalid.returncode, 0)
                    self.assertIn(
                        "compat profile shared files mismatch",
                        invalid.stdout,
                    )
                    self.assertIn(relative, invalid.stdout)

                    child.parent.mkdir(parents=True, exist_ok=True)
                    child.write_bytes(original_bytes)
                    manifest_path.write_text(
                        json.dumps(original_manifest),
                        encoding="utf-8",
                    )

    def test_public_manifest_requires_exact_skill_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skills"
            install_suite(target)
            shared = target / "quant-research-shared"
            manifest_path = shared / "install-manifest.json"
            validator = shared / "scripts/validate_installed.py"
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )

            skill_file = target / "quant-developer" / "SKILL.md"
            skill_file.unlink()
            del manifest["items"]["quant-developer"]["SKILL.md"]
            manifest["suite_content_sha256"] = (
                suite_installer.suite_content_sha256(manifest["items"])
            )
            manifest_path.write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )

            invalid = run(sys.executable, str(validator))
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn(
                "quant-developer manifest files mismatch",
                invalid.stdout,
            )
            self.assertIn("SKILL.md", invalid.stdout)

    def test_installed_item_root_symlinks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "skills"
            install_suite(target)
            validator = (
                target
                / "quant-research-shared"
                / "scripts"
                / "validate_installed.py"
            )

            skill = target / "quant-developer"
            moved_skill = target / "quant-developer-real"
            skill.rename(moved_skill)
            skill.symlink_to(moved_skill, target_is_directory=True)
            single_invalid = run(sys.executable, str(validator))
            self.assertNotEqual(single_invalid.returncode, 0)
            self.assertIn(
                "quant-developer installed item is a symlink",
                single_invalid.stdout,
            )
            skill.unlink()
            moved_skill.rename(skill)

            mirror = base / "mirror"
            mirror.mkdir()
            for name in (
                "quant-plan",
                "quant-goal",
                "quant-developer",
                "quant-research-shared",
            ):
                source = target / name
                destination = mirror / name
                source.rename(destination)
                source.symlink_to(destination, target_is_directory=True)

            mirrored_validator = (
                target
                / "quant-research-shared"
                / "scripts"
                / "validate_installed.py"
            )
            mirrored_invalid = run(
                sys.executable,
                str(mirrored_validator),
            )
            self.assertNotEqual(mirrored_invalid.returncode, 0)
            for name in (
                "quant-plan",
                "quant-goal",
                "quant-developer",
                "quant-research-shared",
            ):
                with self.subTest(root_symlink=name):
                    self.assertIn(
                        f"{name} installed item is a symlink",
                        mirrored_invalid.stdout,
                    )

    def test_installed_copy_runs_optional_strict_and_legacy_entrypoints(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "skills"
            install_suite(target, include_legacy=True)

            shared = target / "quant-research-shared"
            scripts = shared / "scripts"
            install_manifest = json.loads(
                (shared / "install-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(install_manifest["schema_version"], 3)
            self.assertEqual(install_manifest["install_profile"], "compat")
            authority = (shared / "core" / "authority.md").resolve()
            expected_shared_children = (
                "core/context-routing.md",
                "core/authority.md",
                "references/data-automation.md",
                "references/goal-and-subagents.md",
                "references/agent-orchestration.md",
                "references/durable-runtime.md",
                "references/web-design-source.md",
                "references/web-design-v2.4.2.md",
                "scripts/goal_ledger.py",
                "scripts/team_protocol.py",
                "schemas/analysis-input-binding-capture.schema.json",
                "schemas/analysis-invocation.schema.json",
                "templates/analysis-input-binding-capture.example.json",
                "templates/analysis-invocation.example.json",
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
