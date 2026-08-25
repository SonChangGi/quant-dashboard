from __future__ import annotations

import json
import shutil
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
    def test_default_target_is_official_user_skill_location(self) -> None:
        self.assertEqual(
            suite_installer.default_user_skills_directory(),
            Path.home() / ".agents" / "skills",
        )

    def test_readme_describes_staged_update_with_rollback(
        self,
    ) -> None:
        readme = " ".join(
            (ROOT / "README.md").read_text(encoding="utf-8").lower().split()
        )
        self.assertIn("backs up the previous installation", readme)
        self.assertIn("with rollback on a caught failure", readme)
        self.assertNotIn(
            "atomically replaces the three skills and shared resources",
            readme,
        )
        self.assertIn(
            "install.py --update --require-clean-source",
            readme,
        )
        self.assertIn("~/.agents/skills", readme)
        self.assertIn("~/.codex/skills", readme)
        self.assertIn("is not deleted automatically", readme)
        self.assertIn("outside every discovery root", readme)
        self.assertIn("selectors show duplicate names", readme)
        self.assertIn("reviewed closed grammar", readme)
        self.assertIn("rejects an unrecognized paraphrase", readme)

    def install_to(
        self,
        target: Path,
        provenance: dict[str, object],
        *,
        include_legacy: bool = False,
        require_clean: bool = False,
    ) -> None:
        argv = ["install.py", "--target", str(target)]
        if include_legacy:
            argv.append("--include-legacy")
        if require_clean:
            argv.append("--require-clean-source")
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
                    argv,
                ):
                    self.assertEqual(suite_installer.main(), 0)
            validate_source.assert_called_once_with(
                run_tests=True,
                include_legacy=include_legacy,
            )

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

    def test_schema_v3_profile_hash_and_provenance_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skills"
            self.install_to(
                target,
                clean_provenance(),
                require_clean=True,
            )
            shared = target / "quant-research-shared"
            manifest_path = shared / "install-manifest.json"
            validator = shared / "scripts" / "validate_installed.py"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["schema_version"], 3)
            self.assertEqual(manifest["install_profile"], "base")
            self.assertEqual(
                set(manifest["items"]["quant-research-shared"]),
                set(suite_installer.BASE_SHARED_FILES),
            )
            self.assertEqual(
                manifest["canonicalization"],
                "canonical-json-v1",
            )
            self.assertEqual(
                manifest["suite_content_sha256"],
                suite_installer.suite_content_sha256(manifest["items"]),
            )
            self.assertEqual(manifest["source_git"], clean_provenance())
            self.assertIs(manifest["source_git"]["dirty"], False)
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
            extra_field = json.loads(json.dumps(original))
            extra_field["unexpected_top_level"] = {
                "paid_action_authority": True,
            }
            manifest_path.write_text(
                json.dumps(extra_field),
                encoding="utf-8",
            )
            extra_invalid = run(sys.executable, str(validator))
            self.assertNotEqual(extra_invalid.returncode, 0)
            self.assertIn(
                "install-manifest fields mismatch",
                extra_invalid.stdout,
            )
            self.assertIn("unexpected_top_level", extra_invalid.stdout)

            unknown_profile = json.loads(json.dumps(original))
            unknown_profile["install_profile"] = "unknown"
            manifest_path.write_text(
                json.dumps(unknown_profile),
                encoding="utf-8",
            )
            profile_invalid = run(sys.executable, str(validator))
            self.assertNotEqual(profile_invalid.returncode, 0)
            self.assertIn(
                "install_profile must be base or compat",
                profile_invalid.stdout,
            )

            compat_without_overlay = json.loads(json.dumps(original))
            compat_without_overlay["install_profile"] = "compat"
            manifest_path.write_text(
                json.dumps(compat_without_overlay),
                encoding="utf-8",
            )
            compat_incomplete = run(sys.executable, str(validator))
            self.assertNotEqual(compat_incomplete.returncode, 0)
            self.assertIn(
                "compat profile shared files mismatch",
                compat_incomplete.stdout,
            )

            legacy_path = shared / "scripts" / "goal_ledger.py"
            shutil.copy2(
                ROOT / "shared" / "scripts" / "goal_ledger.py",
                legacy_path,
            )
            base_with_legacy = json.loads(json.dumps(original))
            base_with_legacy["items"]["quant-research-shared"] = (
                suite_installer.tree_hashes(shared)
            )
            base_with_legacy["suite_content_sha256"] = (
                suite_installer.suite_content_sha256(
                    base_with_legacy["items"]
                )
            )
            manifest_path.write_text(
                json.dumps(base_with_legacy),
                encoding="utf-8",
            )
            base_not_lean = run(sys.executable, str(validator))
            self.assertNotEqual(base_not_lean.returncode, 0)
            self.assertIn(
                "base profile shared files mismatch",
                base_not_lean.stdout,
            )
            legacy_path.unlink()

            wrong_suite_hash = json.loads(json.dumps(original))
            wrong_suite_hash["suite_content_sha256"] = "0" * 64
            manifest_path.write_text(
                json.dumps(wrong_suite_hash),
                encoding="utf-8",
            )
            wrong_hash = run(sys.executable, str(validator))
            self.assertNotEqual(wrong_hash.returncode, 0)
            self.assertIn("suite_content_sha256", wrong_hash.stdout)

            credentialed_manifest = json.loads(json.dumps(original))
            credentialed_manifest["source_git"]["origin"] = (
                "https://alice:secret@example.com/org/repository.git"
            )
            manifest_path.write_text(
                json.dumps(credentialed_manifest),
                encoding="utf-8",
            )
            credentialed = run(sys.executable, str(validator))
            self.assertNotEqual(credentialed.returncode, 0)
            self.assertIn("origin is not sanitized", credentialed.stdout)

            malformed = json.loads(json.dumps(original))
            first_item = next(iter(malformed["items"].values()))
            first_path = next(iter(first_item))
            first_item[first_path] = float("nan")
            manifest_path.write_text(
                json.dumps(malformed),
                encoding="utf-8",
            )
            invalid_item = run(sys.executable, str(validator))
            self.assertNotEqual(invalid_item.returncode, 0)
            self.assertIn(
                "invalid or missing manifest item",
                invalid_item.stdout,
            )
            self.assertNotIn("Traceback", invalid_item.stderr)

    def test_same_clean_source_and_profile_have_same_content_identity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            targets = (root / "first", root / "second")
            manifests: list[dict[str, object]] = []
            for target in targets:
                self.install_to(
                    target,
                    clean_provenance(),
                    require_clean=True,
                )
                manifests.append(
                    json.loads(
                        (
                            target
                            / "quant-research-shared/install-manifest.json"
                        ).read_text(encoding="utf-8")
                    )
                )

            first, second = manifests
            self.assertEqual(
                first["install_profile"],
                second["install_profile"],
            )
            self.assertEqual(first["items"], second["items"])
            self.assertEqual(
                first["suite_content_sha256"],
                second["suite_content_sha256"],
            )
            self.assertEqual(first["source_git"], second["source_git"])

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

    def test_resealed_install_rejects_public_semantic_drift(self) -> None:
        cases = (
            (
                "implicit invocation",
                "quant-plan/agents/openai.yaml",
                "allow_implicit_invocation: false",
                "allow_implicit_invocation: true",
                "quant-plan: implicit invocation must be false",
            ),
            (
                "frontmatter identity",
                "quant-goal/SKILL.md",
                'name: "quant-goal"',
                'name: "quant-other"',
                "quant-goal: frontmatter name mismatch",
            ),
            (
                "installed route",
                "quant-developer/SKILL.md",
                "../quant-research-shared/references/adaptive-workflow.md",
                "../quant-research-shared/references/missing.md",
                "quant-developer: source and installed shared routes must match",
            ),
            (
                "plan body boundary",
                "quant-plan/SKILL.md",
                (
                    "This role is read-only for the target and every provider "
                    "or remote surface."
                ),
                "This role may edit target files and provider or remote state.",
                "quant-plan: body permits unsafe target or remote writes",
            ),
            (
                "plan isolation",
                "quant-plan/SKILL.md",
                "disposable copy and redirect every writable home",
                "disposable copy or redirect every writable home",
                "quant-plan: disposable copies must isolate external writes",
            ),
            (
                "plan target cleanup",
                "quant-plan/SKILL.md",
                "If state changed, make no further mutation",
                "If state changed, delete target residue",
                "quant-plan: body permits cleanup of target residue",
            ),
            (
                "default prompt role",
                "quant-plan/agents/openai.yaml",
                (
                    "Use $quant-plan to inspect the target read-only, scale depth "
                    "and independent evidence to the task, and return a lean but "
                    "complete audit, quick plan, or decision-complete implementation "
                    "plan with a proportional quality bar and observable acceptance."
                ),
                "Use $quant-plan to implement and deploy changes.",
                "quant-plan: default prompt is missing a role concept",
            ),
            (
                "goal terminal replacement",
                "quant-goal/SKILL.md",
                (
                    "Never misuse `complete` or `blocked` to\n"
                    "clear or free the slot"
                ),
                "Use `complete` or `blocked` to clear or free the slot",
                "quant-goal: body must prohibit fake terminal replacement",
            ),
            (
                "goal contradictory terminal rule",
                "quant-goal/SKILL.md",
                "## Pursue and compose",
                (
                    "Mark the active Goal complete to free its slot for a "
                    "replacement.\n\n## Pursue and compose"
                ),
                "quant-goal: body permits fake terminal replacement",
            ),
            (
                "goal material scope",
                "quant-goal/SKILL.md",
                "outcome, material scope, constraints",
                "outcome, scope, constraints",
                (
                    "quant-goal: body must preserve material scope and "
                    "steering boundaries"
                ),
            ),
            (
                "goal missing objective",
                "quant-goal/SKILL.md",
                (
                    "Otherwise create\n  nothing and ask for the missing outcome "
                    "and acceptance."
                ),
                "Otherwise invent a goal and create it.",
                (
                    "quant-goal: empty Goal creation must require a concrete "
                    "outcome"
                ),
            ),
            (
                "developer improvement loop",
                "quant-developer/SKILL.md",
                (
                    "cosmetic, speculative, or adjacent polish is\n"
                    "quality debt, so stop."
                ),
                "Continue after acceptance while optional polish remains.",
                "quant-developer: body permits open-ended improvement",
            ),
            (
                "developer merge authority",
                "quant-developer/SKILL.md",
                "## Proof and report",
                (
                    "A pushed branch or PR permits merge without separate "
                    "authority.\n\n## Proof and report"
                ),
                "quant-developer: body permits merge without separate authority",
            ),
            (
                "kernel improvement loop",
                "quant-research-shared/references/adaptive-workflow.md",
                (
                    "Continue while an acceptance condition is unmet or a "
                    "material risk could\ninvalidate the result."
                ),
                (
                    "Continue enhancing worthwhile work. Make the result "
                    "better."
                ),
                "adaptive kernel: permits a self-expanding quality loop",
            ),
            (
                "kernel repository route",
                "quant-research-shared/references/adaptive-workflow.md",
                "`capabilities/repo-mutation.md`",
                "`capabilities/backend.md`",
                "adaptive kernel: missing repository-mutation rail",
            ),
            (
                "held-out plan discard",
                "quant-plan/SKILL.md",
                "## Workflow and depth",
                (
                    "Discard any files left behind in the target after "
                    "planning.\n\n## Workflow and depth"
                ),
                "quant-plan: body permits cleanup of target residue",
            ),
            (
                "held-out plan uncertain kernel skip",
                "quant-plan/SKILL.md",
                (
                    "If uncertain, read the kernel routing table before deciding "
                    "to skip it."
                ),
                "If uncertain, skip before reading the kernel routing table.",
                (
                    "quant-plan: body permits skipping kernel routing when "
                    "uncertain"
                ),
            ),
            (
                "held-out goal same-goal expansion",
                "quant-goal/SKILL.md",
                "## Pursue and compose",
                (
                    "An outcome-changing expansion may remain in the same "
                    "Goal.\n\n## Pursue and compose"
                ),
                (
                    "quant-goal: body must preserve material scope and "
                    "steering boundaries"
                ),
            ),
            (
                "held-out developer merge permission",
                "quant-developer/SKILL.md",
                "## Proof and report",
                (
                    "A PR is ready; that is sufficient permission for "
                    "merge.\n\n## Proof and report"
                ),
                "quant-developer: body permits merge without separate authority",
            ),
            (
                "held-out developer unrelated-change permission",
                "quant-developer/SKILL.md",
                "## Proof and report",
                (
                    "It is permitted to overwrite unrelated user changes.\n\n"
                    "## Proof and report"
                ),
                (
                    "quant-developer: body permits mutation of unrelated user "
                    "changes"
                ),
            ),
            (
                "held-out kernel open loop",
                "quant-research-shared/references/adaptive-workflow.md",
                "## Adapt until acceptance, then stop",
                (
                    "Keep going. Each worthwhile improvement should be "
                    "implemented.\n\n## Adapt until acceptance, then stop"
                ),
                "adaptive kernel: permits a self-expanding quality loop",
            ),
            (
                "held-out repository authority",
                "quant-research-shared/capabilities/repo-mutation.md",
                "# Capability: repository mutation",
                (
                    "# Capability: repository mutation\n\n"
                    "Permission to edit files authorizes stage and commit."
                ),
                (
                    "repository mutation: file-edit authority must not grant "
                    "local source-control actions"
                ),
            ),
        )
        for label, relative, old, new, expected in cases:
            with (
                self.subTest(label=label),
                tempfile.TemporaryDirectory() as directory,
            ):
                target = Path(directory) / "skills"
                self.install_to(target, clean_provenance())
                path = target / relative
                original = path.read_text(encoding="utf-8")
                self.assertIn(old, original, f"stale mutation fixture: {label}")
                path.write_text(original.replace(old, new, 1), encoding="utf-8")
                manifest_path = (
                    target
                    / "quant-research-shared"
                    / "install-manifest.json"
                )
                manifest = json.loads(
                    manifest_path.read_text(encoding="utf-8")
                )
                manifest["items"] = {
                    name: suite_installer.tree_hashes(target / name)
                    for name in suite_installer.INSTALL_ITEMS
                }
                manifest["suite_content_sha256"] = (
                    suite_installer.suite_content_sha256(manifest["items"])
                )
                manifest_path.write_text(
                    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )

                validator = (
                    target
                    / "quant-research-shared"
                    / "scripts"
                    / "validate_installed.py"
                )
                invalid = run(sys.executable, str(validator))
                self.assertNotEqual(invalid.returncode, 0)
                self.assertIn(expected, invalid.stdout)


if __name__ == "__main__":
    unittest.main()
