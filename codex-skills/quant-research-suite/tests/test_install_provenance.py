from __future__ import annotations

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


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        check=False,
        text=True,
    )


def clean_provenance() -> dict[str, object]:
    return {
        "available": True,
        "origin": "https://example.com/owner/repository.git",
        "branch": "main",
        "commit": "a" * 40,
        "tree": "b" * 40,
        "dirty": False,
        "captured_at": "2026-07-26T00:00:00Z",
    }


def unavailable_provenance() -> dict[str, object]:
    return {
        "available": False,
        "origin": None,
        "branch": None,
        "commit": None,
        "tree": None,
        "dirty": None,
        "captured_at": "2026-07-26T00:00:00Z",
    }


class InstallProvenanceTests(unittest.TestCase):
    def install_to(
        self,
        target: Path,
        provenance: dict[str, object],
    ) -> None:
        with mock.patch.object(
            suite_installer,
            "validate_source",
        ) as validate_source:
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
            validate_source.assert_called_once_with(run_tests=True)

    def test_origin_sanitization_removes_credentials_and_query(self) -> None:
        cases = {
            "https://alice:secret@example.com/org/repository.git": (
                "https://example.com/org/repository.git"
            ),
            "https://token@example.com/org/repository.git?access_token=hidden": (
                "https://example.com/org/repository.git"
            ),
            "ssh://git:secret@example.com/org/repository.git": (
                "ssh://example.com/org/repository.git"
            ),
            "file://alice:secret@example.com/source/repository.git": (
                "file://example.com/source/repository.git"
            ),
            "git@example.com:org/repository.git": (
                "example.com:org/repository.git"
            ),
        }
        for origin, expected in cases.items():
            with self.subTest(origin=origin):
                sanitized = suite_installer.sanitize_git_origin(origin)
                self.assertEqual(sanitized, expected)
                self.assertNotIn("secret", sanitized or "")
                self.assertNotIn("token", sanitized or "")
                self.assertNotIn("hidden", sanitized or "")

    def test_git_capture_records_commit_tree_branch_and_dirty_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            initialized = run("git", "init", "-q", cwd=repository)
            self.assertEqual(
                initialized.returncode,
                0,
                initialized.stdout + initialized.stderr,
            )
            for key, value in (
                ("user.name", "Test User"),
                ("user.email", "test@example.com"),
            ):
                configured = run(
                    "git",
                    "config",
                    key,
                    value,
                    cwd=repository,
                )
                self.assertEqual(configured.returncode, 0, configured.stderr)
            tracked = repository / "tracked.txt"
            tracked.write_text("clean\n", encoding="utf-8")
            added = run("git", "add", "tracked.txt", cwd=repository)
            self.assertEqual(added.returncode, 0, added.stderr)
            committed = run(
                "git",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-q",
                "-m",
                "fixture",
                cwd=repository,
            )
            self.assertEqual(committed.returncode, 0, committed.stderr)
            remote = run(
                "git",
                "remote",
                "add",
                "origin",
                (
                    "https://alice:secret@example.com/org/repository.git"
                    "?access_token=hidden"
                ),
                cwd=repository,
            )
            self.assertEqual(remote.returncode, 0, remote.stderr)

            clean = suite_installer.capture_source_git_provenance(repository)
            self.assertTrue(clean["available"])
            self.assertFalse(clean["dirty"])
            self.assertEqual(
                clean["origin"],
                "https://example.com/org/repository.git",
            )
            expected_commit = run(
                "git",
                "rev-parse",
                "HEAD",
                cwd=repository,
            ).stdout.strip()
            expected_tree = run(
                "git",
                "rev-parse",
                "HEAD^{tree}",
                cwd=repository,
            ).stdout.strip()
            self.assertEqual(clean["commit"], expected_commit)
            self.assertEqual(clean["tree"], expected_tree)
            self.assertTrue(clean["branch"])
            self.assertTrue(str(clean["captured_at"]).endswith("Z"))
            serialized = json.dumps(clean)
            self.assertNotIn("secret", serialized)
            self.assertNotIn("access_token", serialized)

            tracked.write_text("dirty\n", encoding="utf-8")
            dirty = suite_installer.capture_source_git_provenance(repository)
            self.assertTrue(dirty["available"])
            self.assertTrue(dirty["dirty"])

    def test_require_clean_source_fails_closed(self) -> None:
        suite_installer.require_clean_source(clean_provenance())
        with self.assertRaisesRegex(SystemExit, "provenance is unavailable"):
            suite_installer.require_clean_source(unavailable_provenance())
        dirty = clean_provenance()
        dirty["dirty"] = True
        with self.assertRaisesRegex(SystemExit, "dirty source"):
            suite_installer.require_clean_source(dirty)

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skills"
            with mock.patch.object(suite_installer, "validate_source"):
                with mock.patch.object(
                    suite_installer,
                    "capture_source_git_provenance",
                    return_value=dirty,
                ):
                    with mock.patch.object(
                        sys,
                        "argv",
                        [
                            "install.py",
                            "--target",
                            str(target),
                            "--dry-run",
                            "--skip-tests",
                            "--require-clean-source",
                        ],
                    ):
                        with self.assertRaisesRegex(SystemExit, "dirty source"):
                            suite_installer.main()
            self.assertFalse(target.exists())

    def test_schema_v2_manifest_hash_and_provenance_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skills"
            self.install_to(target, clean_provenance())
            shared = target / "quant-research-shared"
            manifest_path = shared / "install-manifest.json"
            validator = shared / "scripts" / "validate_installed.py"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(
                manifest["canonicalization"],
                "canonical-json-v1",
            )
            self.assertEqual(
                manifest["suite_content_sha256"],
                suite_installer.suite_content_sha256(manifest["items"]),
            )
            self.assertEqual(manifest["source_git"], clean_provenance())
            valid = run(sys.executable, str(validator))
            self.assertEqual(
                valid.returncode,
                0,
                valid.stdout + valid.stderr,
            )

            source_skill = target / "quant-plan" / "SKILL.md"
            linked_skill = target / "quant-plan" / "linked-skill.md"
            linked_skill.symlink_to(source_skill)
            symlinked = run(sys.executable, str(validator))
            self.assertNotEqual(symlinked.returncode, 0)
            self.assertIn("contains symlinks", symlinked.stdout)
            linked_skill.unlink()

            original = json.loads(json.dumps(manifest))
            manifest["suite_content_sha256"] = "0" * 64
            manifest_path.write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )
            wrong_hash = run(sys.executable, str(validator))
            self.assertNotEqual(wrong_hash.returncode, 0)
            self.assertIn("suite_content_sha256", wrong_hash.stdout)

            original["source_git"]["origin"] = (
                "https://alice:secret@example.com/org/repository.git"
            )
            manifest_path.write_text(
                json.dumps(original),
                encoding="utf-8",
            )
            credentialed = run(sys.executable, str(validator))
            self.assertNotEqual(credentialed.returncode, 0)
            self.assertIn("origin is not sanitized", credentialed.stdout)

            malformed = json.loads(json.dumps(manifest))
            first_item = next(iter(malformed["items"].values()))
            first_path = next(iter(first_item))
            first_item[first_path] = float("nan")
            manifest_path.write_text(
                json.dumps(malformed),
                encoding="utf-8",
            )
            invalid_item = run(sys.executable, str(validator))
            self.assertNotEqual(invalid_item.returncode, 0)
            self.assertIn("invalid or missing manifest item", invalid_item.stdout)
            self.assertNotIn("Traceback", invalid_item.stderr)

    def test_archive_source_provenance_remains_portable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skills"
            self.install_to(target, unavailable_provenance())
            validator = (
                target
                / "quant-research-shared"
                / "scripts"
                / "validate_installed.py"
            )
            valid = run(sys.executable, str(validator))
            self.assertEqual(
                valid.returncode,
                0,
                valid.stdout + valid.stderr,
            )


if __name__ == "__main__":
    unittest.main()
