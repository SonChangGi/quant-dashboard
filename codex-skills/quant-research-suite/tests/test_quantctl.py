from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "shared" / "scripts" / "quantctl.py"
GOAL_SCRIPT = ROOT / "shared" / "scripts" / "goal_runtime.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda value: value.as_posix(),
    ):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class QuantCtlTests(unittest.TestCase):
    def test_doctor_without_manifest_is_read_only_and_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            (root / "README.md").write_text("sample\n", encoding="utf-8")
            before = tree_hash(root)
            completed = run("doctor", "--root", str(root))
            after = tree_hash(root)
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertIsNone(payload["result"]["manifest"]["valid"])
        self.assertFalse(payload["result"]["writes_performed"])
        self.assertEqual(before, after)

    def test_doctor_state_check_does_not_modify_state_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            state = base / "goal-state"
            root.mkdir()
            (root / "README.md").write_text("sample\n", encoding="utf-8")
            initialized = subprocess.run(
                [
                    sys.executable,
                    str(GOAL_SCRIPT),
                    "init",
                    "--root",
                    str(root),
                    "--state-dir",
                    str(state),
                    "--goal-id",
                    "doctor-read-only",
                    "--project-id",
                    "sample",
                    "--objective",
                    "Verify doctor without mutation.",
                    "--acceptance",
                    "a1=Doctor reports valid state.",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                initialized.returncode,
                0,
                initialized.stdout + initialized.stderr,
            )
            before = tree_hash(state)
            completed = run(
                "doctor",
                "--root",
                str(root),
                "--state-dir",
                str(state),
            )
            after = tree_hash(state)
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["result"]["goal_state"]["ok"])
        self.assertFalse(payload["result"]["writes_performed"])
        self.assertEqual(before, after)

    def test_doctor_does_not_recover_or_delete_pending_goal_transaction(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            state = base / "goal-state"
            root.mkdir()
            (root / "README.md").write_text("sample\n", encoding="utf-8")
            initialized = subprocess.run(
                [
                    sys.executable,
                    str(GOAL_SCRIPT),
                    "init",
                    "--root",
                    str(root),
                    "--state-dir",
                    str(state),
                    "--goal-id",
                    "doctor-pending",
                    "--project-id",
                    "sample",
                    "--objective",
                    "Preserve pending state during diagnosis.",
                    "--acceptance",
                    "a1=Pending state remains unchanged.",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                initialized.returncode,
                0,
                initialized.stdout + initialized.stderr,
            )
            pending = state / "pending-event.json"
            pending.write_text('{"fixture":"pending"}\n', encoding="utf-8")
            before = tree_hash(state)
            completed = run(
                "doctor",
                "--root",
                str(root),
                "--state-dir",
                str(state),
            )
            after = tree_hash(state)
            pending_after = pending.read_text(encoding="utf-8")
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertIn(
            "pending transaction",
            " ".join(payload["issues"]),
        )
        self.assertEqual(before, after)
        self.assertEqual(pending_after, '{"fixture":"pending"}\n')

    def test_onboard_requires_literal_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            completed = run("onboard", "--root", directory)
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertIn("--dry-run", payload["issues"][0])

    def test_onboard_detects_without_creating_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                '{"dependencies":{"react":"fixture"},'
                '"devDependencies":{"typescript":"fixture"}}',
                encoding="utf-8",
            )
            workflow = root / ".github" / "workflows"
            workflow.mkdir(parents=True)
            (workflow / "refresh.yml").write_text(
                "on:\n  schedule:\n    - cron: '0 0 * * *'\n",
                encoding="utf-8",
            )
            before = tree_hash(root)
            completed = run(
                "onboard", "--root", str(root), "--dry-run"
            )
            after = tree_hash(root)
            manifest = root / ".codex" / "quant-project.json"
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )
        payload = json.loads(completed.stdout)
        candidates = {
            item["id"]
            for item in payload["result"]["capability_candidates"]
        }
        self.assertIn("web-ui", candidates)
        self.assertIn("scheduled-automation", candidates)
        self.assertEqual(
            payload["result"]["recommended_assurance"],
            "standard",
        )
        self.assertFalse(payload["result"]["writes_performed"])
        self.assertFalse(payload["result"]["network_used"])
        self.assertEqual(before, after)
        self.assertFalse(manifest.exists())

    def test_onboard_skips_external_symlinks_and_reports_partial_scan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            external = base / "outside"
            root.mkdir()
            external.mkdir()
            external_package = external / "package.json"
            external_package.write_text(
                '{"dependencies":{"react":"external-only"}}',
                encoding="utf-8",
            )
            (root / "package.json").symlink_to(external_package)
            before = external_package.read_bytes()
            completed = run(
                "onboard", "--root", str(root), "--dry-run"
            )
            after = external_package.read_bytes()
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )
        payload = json.loads(completed.stdout)
        candidates = {
            item["id"]
            for item in payload["result"]["capability_candidates"]
        }
        self.assertNotIn("web-ui", candidates)
        self.assertEqual(payload["result"]["candidate_coverage"], "partial")
        scan = payload["result"]["scan"]
        self.assertFalse(scan["complete"])
        self.assertIn("symlinks_skipped", scan["incomplete_reasons"])
        self.assertEqual(scan["symlink_paths"], ["package.json"])
        self.assertEqual(before, after)

    def test_context_loads_quant_design_only_with_profile(self) -> None:
        generic = run("context", "--capability", "web-ui")
        profiled = run(
            "context",
            "--capability",
            "web-ui",
            "--profile",
            "quant-research-web",
        )
        self.assertEqual(generic.returncode, 0)
        self.assertEqual(profiled.returncode, 0)
        generic_refs = json.loads(generic.stdout)["result"][
            "required_references"
        ]
        profiled_refs = json.loads(profiled.stdout)["result"][
            "required_references"
        ]
        self.assertNotIn("references/web-design-source.md", generic_refs)
        self.assertIn("references/web-design-source.md", profiled_refs)

    def test_context_keeps_standard_release_on_separate_axes(self) -> None:
        completed = run(
            "context",
            "--capability",
            "remote-release",
            "--assurance",
            "standard",
            "--delivery",
            "release",
        )
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )
        result = json.loads(completed.stdout)["result"]
        self.assertEqual(result["assurance"], "standard")
        self.assertEqual(result["delivery"], "release")
        self.assertIn("release", result["required_gates"])
        self.assertNotIn(
            "independent_reaudit", result["required_gates"]
        )

    def test_context_rejects_mutually_exclusive_runtime_cli_selection(
        self,
    ) -> None:
        completed = run(
            "context",
            "--capability",
            "multi-agent-write",
            "--capability",
            "agent-team-execution",
        )
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        message = " ".join(payload["issues"])
        self.assertIn("mutually exclusive", message)
        self.assertIn("host-native concurrent team", message)
        self.assertIn("legacy single-root Story", message)

    def test_context_rejects_runtime_conflict_after_manifest_merge(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "quant-project.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "capabilities": ["multi-agent-write"],
                    }
                ),
                encoding="utf-8",
            )
            completed = run(
                "context",
                "--manifest",
                str(manifest),
                "--capability",
                "agent-team-execution",
            )
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        message = " ".join(payload["issues"])
        self.assertIn("mutually exclusive", message)
        self.assertIn("agent-team-execution", message)
        self.assertIn("multi-agent-write", message)

    def test_context_routes_manifest_v1_to_legacy_strict_references(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "quant-project.json"
            manifest.write_text(
                json.dumps({"schema_version": 1}),
                encoding="utf-8",
            )
            completed = run("context", "--manifest", str(manifest))
        self.assertEqual(
            completed.returncode, 0, completed.stdout + completed.stderr
        )
        result = json.loads(completed.stdout)["result"]
        self.assertEqual(
            result["compatibility"]["mode"],
            "manifest-v1-strict",
        )
        self.assertEqual(
            result["compatibility"]["evidence_receipt_schema_version"],
            2,
        )
        for reference in (
            "references/cost-and-authority.md",
            "references/data-automation.md",
            "references/developer-runbook.md",
        ):
            self.assertIn(reference, result["required_references"])

    def test_context_rejects_non_integer_manifest_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "quant-project.json"
            manifest.write_text(
                json.dumps({"schema_version": True}),
                encoding="utf-8",
            )
            completed = run("context", "--manifest", str(manifest))
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertIn("schema_version", payload["issues"][0])


if __name__ == "__main__":
    unittest.main()
