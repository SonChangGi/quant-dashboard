from __future__ import annotations

import json
import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "shared"
sys.path.insert(0, str(ROOT))
import install as suite_installer
sys.path.insert(0, str(SHARED / "scripts"))
import validate_evidence as evidence_validator


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        check=False,
    )


def run_env(
    environment: dict[str, str],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


def gate_evidence(kind: str, **extra: object) -> dict[str, object]:
    value: dict[str, object] = {
        "kind": kind,
        "summary": f"{kind} passed",
        "source": "deterministic test fixture",
        "checked_at": "2026-07-25T12:00:00Z",
    }
    value.update(extra)
    return value


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def complete_cost_evidence(cost: dict[str, object]) -> dict[str, object]:
    envelope = cost["canonical_actions_envelope"]
    assert isinstance(envelope, dict)
    return gate_evidence(
        "cost_preflight",
        classification=cost["classification"],
        decision=cost["decision"],
        canonical_actions_envelope_sha256=envelope["sha256"],
        cost_evidence_sha256=cost.get("cost_evidence_sha256"),
        all_remote_or_provider_actions_enumerated=True,
        all_numeric_ceilings_validated=True,
        all_hard_stops_enabled=True,
        trusted_runtime_paid_authority_verified=False,
    )


def local_cost() -> dict[str, object]:
    actions: list[object] = []
    return {
        "policy": "zero-spend-unless-user-first-requests-specific-paid-action",
        "classification": "no_billable_action",
        "decision": "allow",
        "paid_action_requested": False,
        "authority_origin": "none",
        "actions": actions,
        "canonical_actions_envelope": {
            "canonicalization": "canonical-json-v1",
            "action_count": 0,
            "sha256": canonical_sha256(actions),
            "authoritative_for_cost_gate": True,
        },
    }


def make_verified_zero_cost(
    scope_groups: list[tuple[str, list[str]]],
    *,
    recurring: bool,
) -> dict[str, object]:
    maximum_runs = 30 if recurring else 1
    actions: list[object] = []
    for index, (provider, scope_ids) in enumerate(scope_groups):
        action: dict[str, object] = {
            "action_id": f"remote-action-{index + 1}",
            "scope_ids": scope_ids,
            "remote_or_provider_action": True,
            "provider": provider,
            "account_or_project": "sample",
            "resource_or_sku": "hard-free-fixture",
            "normalized_redacted_action": (
                "scheduled collection, automation, or publication"
            ),
            "classification": "verified_zero_charge",
            "decision": "allow",
            "pricing_and_quota": {
                "official_or_account_visible_evidence": "fixture plan record",
                "checked_at": "2026-07-25T09:00:00Z",
                "billing_mode": "hard-free-no-overage",
                "cap_unit": "provider calls",
                "hard_free_cap": 1000,
                "remaining_free_quota": 999,
                "planned_usage_per_run": 1,
                "trial_or_credit_required": False,
                "auto_renewing_trial_active": False,
                "payment_method_registration_required": False,
                "overage_possible": False,
                "automatic_upgrade_possible": False,
                "payment_method_change_required": False,
                "plan_upgrade_required": False,
                "pay_as_you_go_enabled": False,
                "free_quota_exceedance_allowed": False,
                "paid_add_on_active": False,
                "spend_cap_disabled": False,
            },
            "numeric_ceilings": {
                "maximum_cost_per_run": 0,
                "maximum_total_cost": 0,
                "maximum_runs": maximum_runs,
                "maximum_provider_calls_per_run": 1,
                "maximum_retry_attempts": 2,
                "maximum_concurrency": 1,
                "maximum_compute_seconds_per_run": 300,
                "maximum_storage_bytes": 1000000,
                "maximum_egress_bytes_per_run": 1000000,
                "maximum_retention_days": 30,
            },
            "schedule": {
                "recurring": recurring,
                "cadence": "daily" if recurring else "",
                "end_at": "2026-08-25T00:00:00Z" if recurring else "",
            },
            "hard_stop": {
                "enabled": True,
                "check_quota_before_each_run": True,
                "block_when_price_or_quota_unknown": True,
                "block_when_free_quota_exhausted": True,
                "block_when_projected_cost_exceeds_ceiling": True,
                "block_when_trial_or_credit_required": True,
                "block_when_auto_renewing_trial_active": True,
                "block_when_payment_method_registration_required": True,
                "block_when_plan_upgrade_required": True,
                "block_when_overage_possible": True,
                "block_when_pay_as_you_go_enabled": True,
                "block_when_free_quota_exceedance_possible": True,
                "block_when_paid_add_on_active": True,
                "require_spend_cap_enabled": True,
                "paid_fallback_enabled": False,
                "automatic_upgrade_enabled": False,
                "plan_upgrade_enabled": False,
                "paid_add_on_enabled": False,
                "spend_cap_disablement_enabled": False,
            },
        }
        action["canonical_action_envelope_sha256"] = canonical_sha256(action)
        actions.append(action)
    return {
        "policy": "zero-spend-unless-user-first-requests-specific-paid-action",
        "classification": "verified_zero_charge",
        "decision": "allow",
        "paid_action_requested": False,
        "authority_origin": "none",
        "actions": actions,
        "canonical_actions_envelope": {
            "canonicalization": "canonical-json-v1",
            "action_count": len(actions),
            "sha256": canonical_sha256(actions),
            "authoritative_for_cost_gate": True,
        },
    }


def verified_zero_cost() -> dict[str, object]:
    return make_verified_zero_cost(
        [
            ("fixture", ["source:primary"]),
            ("fixture", ["source:secondary"]),
            ("github", ["automation:.github/workflows/refresh.yml"]),
            ("example.invalid", ["publish:example.invalid"]),
            ("example.invalid", ["frontend:example.invalid"]),
        ],
        recurring=True,
    )


def verified_release_cost() -> dict[str, object]:
    return make_verified_zero_cost(
        [
            ("github", ["release:github"]),
            ("example.invalid", ["deploy:example.invalid"]),
            ("example.invalid", ["readback:example.invalid"]),
        ],
        recurring=False,
    )


def write_cost_capture(
    root: Path,
    cost: dict[str, object],
    *,
    workflow_run_id: str | None,
    release_ci_run_id: str | None,
) -> Path:
    actions = cost["actions"]
    assert isinstance(actions, list)
    captured_actions: list[object] = []
    for action in actions:
        assert isinstance(action, dict)
        captured_actions.append(
            {
                "action_id": action["action_id"],
                "provider": action["provider"],
                "account_or_project": action["account_or_project"],
                "resource_or_sku": action["resource_or_sku"],
                "pricing_and_quota": action["pricing_and_quota"],
            }
        )
    path = root / "captures" / "cost-evidence.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "capture_origin": "official-account-api",
                "capture_tool": "deterministic fixture",
                "source_reference": "fixture account plan endpoint",
                "captured_at": "2026-07-25T09:00:00Z",
                "workflow_run_id": workflow_run_id,
                "release_ci_run_id": release_ci_run_id,
                "automation_cost_preflight_completed_at": (
                    "2026-07-25T09:10:00Z"
                    if workflow_run_id is not None
                    else None
                ),
                "release_cost_preflight_completed_at": (
                    "2026-07-25T09:10:00Z"
                    if release_ci_run_id is not None
                    else None
                ),
                "actions": captured_actions,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    cost["cost_evidence_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path


def write_context(
    root: Path,
    *,
    automated: bool = False,
    released: bool = False,
) -> tuple[Path, Path, dict[str, bool]]:
    scope = {
        "automated_data_to_web": automated,
        "remote_release": released,
        "paid_action": False,
    }
    (root / "analysis").mkdir(exist_ok=True)
    (root / "analysis" / "run.py").write_text("", encoding="utf-8")
    (root / "pipeline.py").write_text(
        "import runpy\nrunpy.run_path('analysis/run.py')\n",
        encoding="utf-8",
    )
    (root / "collect.py").write_text("print('collect')\n", encoding="utf-8")
    (root / "cost_preflight.py").write_text(
        "print('quota checked')\n",
        encoding="utf-8",
    )
    (root / "schemas").mkdir(exist_ok=True)
    (root / "schemas" / "input.json").write_text("{}\n", encoding="utf-8")
    (root / "schemas" / "analysis-input.json").write_text(
        '{"type":"object"}\n',
        encoding="utf-8",
    )
    workflow = root / ".github" / "workflows" / "refresh.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(
        "concurrency:\n"
        "  group: sample-automation\n"
        "  cancel-in-progress: false\n"
        "on:\n"
        "  schedule:\n"
        "    - cron: '0 1 * * *'\n"
        "jobs:\n"
        "  refresh:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - id: cost-preflight\n"
        "        run: python cost_preflight.py\n"
        "      - id: collect-and-analyze\n"
        "        run: python pipeline.py\n",
        encoding="utf-8",
    )
    manifest = root / "project.json"
    manifest_value = valid_project_manifest()
    if not automated:
        manifest_value["automation"]["mode"] = "none"
        manifest_value["automation"]["workflows"] = []
        manifest_value["automation"]["schedules"] = []
    manifest.write_text(
        json.dumps(manifest_value),
        encoding="utf-8",
    )
    goal = root / "goal.json"
    goal.write_text(
        json.dumps(
            {
                "project_id": "sample",
                "objective": "Ship a verified result",
                "scope": scope,
                "required_outcomes": {
                    "automated_data_to_web": automated,
                    "remote_release": released,
                },
                "approval_gates": {
                    "release": "approved" if released else "pending",
                    "paid_action": (
                        "prohibited-unless-user-first-requests-specific-scope"
                    ),
                },
                "automation_state": {
                    "in_scope": automated,
                    "scope_status": (
                        "in-scope"
                        if automated
                        else "explicitly-out-of-scope"
                    ),
                    "scope_exclusion_reason": (
                        ""
                        if automated
                        else "This fixture performs no automation/provider action."
                    ),
                    "last_good_result_identity": (
                        {
                            "generation": 1,
                            "result_artifact_sha256": "a" * 64,
                            "data_as_of": "2026-07-23",
                            "published_result_key": "result-20260723",
                        }
                        if automated
                        else {}
                    ),
                },
                "cost_authority": {
                    "policy": (
                        "zero-spend-unless-user-first-requests-specific-paid-action"
                    ),
                    "paid_action_requested": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return manifest, goal, scope


def valid_project_manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "project": {
            "id": "sample",
            "name": "Sample",
            "purpose": "Publish a verified research result.",
            "repository": "example/sample",
            "public_url": "https://example.invalid/",
        },
        "protected": {"paths": ["analysis/**"]},
        "data": {
            "sources": [
                {
                    "id": "primary",
                    "provider": "fixture",
                    "role": "required",
                    "collector_entrypoint": "collect.py",
                    "rights_policy": "test fixture",
                    "secret_names": [],
                    "provider_timezone": "UTC",
                    "session_calendar": "daily",
                    "expected_release_window": "daily at 00:00 UTC",
                    "allowed_lag": "1 day",
                    "allowed_lag_seconds": 86400,
                    "maximum_source_age_seconds": 172800,
                    "rate_limit_policy": "one bounded fixture call",
                    "retry_policy": "two bounded retries",
                    "cache_policy": "project-local immutable fixture",
                    "raw_artifact": "data/raw.json",
                    "normalized_artifact": "data/input.json",
                    "schema_contract": "schemas/input.json",
                    "freshness_fields": [
                        "source_as_of",
                        "collected_at",
                        "artifact_sha256",
                    ],
                    "fallback_policy": "fail-closed",
                    "paid_fallback_enabled": False,
                }
            ],
            "coherent_cutoff_policy": "required source minimum",
            "data_manifest_path": "data/manifest.json",
            "provenance_fields": [
                "source_id",
                "source_as_of",
                "collected_at",
                "artifact_sha256",
            ],
            "source_last_good_policy": "retain",
        },
        "analysis": {
            "input_schema_contract": "schemas/analysis-input.json",
            "result_artifact_identity": [
                {
                    "id": "project",
                    "json_pointer": "/project_id",
                    "identity_field": "project_id",
                },
                {
                    "id": "run",
                    "json_pointer": "/run_id",
                    "identity_field": "run_id",
                },
            ],
            "authoritative_entrypoints": ["pipeline.py"],
            "controls": [{"id": "table-sort", "kind": "display"}],
            "result_identity_fields": [
                "project_id",
                "run_id",
                "data_as_of",
                "code_version",
                "data_manifest_sha256",
                "analysis_input_sha256",
                "analysis_input_validation_sha256",
                "analysis_entrypoint_sha256",
                "config_hash",
                "effective_config_hash",
                "input_schema_version",
                "data_schema_version",
                "result_schema_version",
                "artifact_sha256",
            ],
        },
        "frontend": {"type": "static", "test_commands": []},
        "backend": {"required": False, "test_commands": []},
        "automation": {
            "mode": "scheduled",
            "workflows": [".github/workflows/refresh.yml"],
            "schedules": [
                {
                    "id": "daily",
                    "workflow": ".github/workflows/refresh.yml",
                    "entrypoint": "pipeline.py",
                    "entrypoint_command": "python pipeline.py",
                    "job_id": "refresh",
                    "cost_preflight_step_id": "cost-preflight",
                    "entrypoint_step_id": "collect-and-analyze",
                    "cost_preflight_entrypoint": "cost_preflight.py",
                    "cost_preflight_command": "python cost_preflight.py",
                    "cron": "0 1 * * *",
                    "cron_timezone": "UTC",
                    "business_timezone": "UTC",
                    "calendar": "daily",
                    "availability_lag": "1 hour",
                    "idempotency_key": "date",
                    "concurrency_policy": "one writer",
                    "concurrency_group": "sample-automation",
                    "cancel_in_progress": False,
                    "timeout": "30 minutes",
                    "retry_policy": "2 bounded retries",
                    "manual_dispatch_mode": "backfill",
                    "retention_policy": "30 days",
                    "enabled_on_default_branch": True,
                }
            ],
            "pipeline_stages": [
                "collect",
                "validate",
                "normalize",
                "coherent_cutoff",
                "analyze",
                "validate_result",
                "stage",
                "publish",
                "deploy",
                "public_readback",
            ],
            "freshness_fields": [
                "source_as_of",
                "collected_at",
                "data_as_of",
                "calculated_at",
                "published_at",
                "verified_at",
            ],
            "publication_path": "docs/data/result.json",
            "public_readback_urls": ["https://example.invalid/data/result.json"],
            "last_good_policy": "atomic pointer",
            "failure_policy": "fail-closed",
            "cost_bounds": {
                "policy": "zero-spend",
                "retry_ceiling": 2,
                "concurrency_ceiling": 1,
                "retention_ceiling": 30,
                "overage_enabled": False,
                "paid_fallback_enabled": False,
                "trial_credit_or_overage_possible": False,
                "auto_renewing_trial_enabled": False,
                "automatic_upgrade_enabled": False,
                "payment_method_change_required": False,
                "payment_method_registration_required": False,
                "plan_upgrade_required": False,
                "pay_as_you_go_enabled": False,
                "free_quota_exceedance_allowed": False,
                "paid_add_on_enabled": False,
                "spend_cap_disabled": False,
                "spend_cap_enabled": True,
                "quota_hard_stop": True,
            },
        },
        "release": {
            "base_branch": "main",
            "approved_account": "example",
            "production": "https://example.invalid/",
            "cost_policy": (
                "zero-spend-unless-user-first-requests-specific-paid-action"
            ),
            "paid_action_authority": None,
            "paid_fallback_policy": "prohibited",
        },
        "quality": {"commands": []},
    }


class ToolTests(unittest.TestCase):
    def test_zero_cost_action_rejects_paid_state_transitions(self) -> None:
        cost = make_verified_zero_cost(
            [("fixture", ["source:primary"])],
            recurring=False,
        )
        base_action = cost["actions"][0]
        assert isinstance(base_action, dict)
        unsafe_cases = (
            ("pricing_and_quota", "auto_renewing_trial_active", True),
            (
                "pricing_and_quota",
                "payment_method_registration_required",
                True,
            ),
            ("pricing_and_quota", "plan_upgrade_required", True),
            ("pricing_and_quota", "pay_as_you_go_enabled", True),
            (
                "pricing_and_quota",
                "free_quota_exceedance_allowed",
                True,
            ),
            ("pricing_and_quota", "paid_add_on_active", True),
            ("pricing_and_quota", "spend_cap_disabled", True),
            (
                "hard_stop",
                "block_when_auto_renewing_trial_active",
                False,
            ),
            (
                "hard_stop",
                "block_when_payment_method_registration_required",
                False,
            ),
            ("hard_stop", "block_when_plan_upgrade_required", False),
            ("hard_stop", "block_when_pay_as_you_go_enabled", False),
            (
                "hard_stop",
                "block_when_free_quota_exceedance_possible",
                False,
            ),
            ("hard_stop", "block_when_paid_add_on_active", False),
            ("hard_stop", "require_spend_cap_enabled", False),
        )
        for section, field, unsafe_value in unsafe_cases:
            with self.subTest(section=section, field=field):
                action = json.loads(json.dumps(base_action))
                action[section][field] = unsafe_value
                unhashed = dict(action)
                unhashed.pop("canonical_action_envelope_sha256")
                action["canonical_action_envelope_sha256"] = canonical_sha256(
                    unhashed
                )
                errors: list[str] = []
                evidence_validator.validate_zero_cost_action(
                    action,
                    None,
                    errors,
                    "cost.actions[0]",
                )
                self.assertTrue(errors)
                self.assertTrue(
                    any(field in error for error in errors),
                    errors,
                )

        unexpected = json.loads(json.dumps(base_action))
        unexpected["pricing_and_quota"]["unreviewed_paid_state"] = True
        unhashed = dict(unexpected)
        unhashed.pop("canonical_action_envelope_sha256")
        unexpected["canonical_action_envelope_sha256"] = canonical_sha256(
            unhashed
        )
        unexpected_errors: list[str] = []
        evidence_validator.validate_zero_cost_action(
            unexpected,
            None,
            unexpected_errors,
            "cost.actions[0]",
        )
        self.assertTrue(
            any("unexpected fields" in error for error in unexpected_errors),
            unexpected_errors,
        )

    def test_project_cost_bounds_reject_paid_state_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, _, _ = write_context(root, automated=True)
            base_manifest = json.loads(manifest.read_text(encoding="utf-8"))
            script = str(SHARED / "scripts" / "validate_project.py")
            unsafe_cases = (
                ("auto_renewing_trial_enabled", True),
                ("payment_method_registration_required", True),
                ("plan_upgrade_required", True),
                ("pay_as_you_go_enabled", True),
                ("free_quota_exceedance_allowed", True),
                ("paid_add_on_enabled", True),
                ("spend_cap_disabled", True),
                ("spend_cap_enabled", False),
            )
            for field, unsafe_value in unsafe_cases:
                with self.subTest(field=field):
                    value = json.loads(json.dumps(base_manifest))
                    value["automation"]["cost_bounds"][field] = unsafe_value
                    manifest.write_text(
                        json.dumps(value),
                        encoding="utf-8",
                    )
                    result = run(
                        sys.executable,
                        script,
                        "--root",
                        str(root),
                        "--manifest",
                        str(manifest),
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(
                        f"automation.cost_bounds.{field}",
                        result.stdout,
                    )

            unexpected = json.loads(json.dumps(base_manifest))
            unexpected["automation"]["cost_bounds"][
                "unreviewed_paid_state"
            ] = True
            manifest.write_text(
                json.dumps(unexpected),
                encoding="utf-8",
            )
            unexpected_result = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(unexpected_result.returncode, 0)
            self.assertIn(
                "automation.cost_bounds has unexpected fields",
                unexpected_result.stdout,
            )

    def test_cross_scope_binds_workflow_commit_and_public_identity(self) -> None:
        receipt = {
            "scope": {
                "automated_data_to_web": True,
                "remote_release": True,
            },
            "automation_identity": {
                "head_sha": "a" * 40,
                "deployment_id": "deploy-1",
                "frontend_response_sha256": "b" * 64,
                "frontend_response_size": 100,
                "result_artifact_sha256": "c" * 64,
                "result_artifact_size": 200,
                "frontend_url": "https://example.invalid/?verify=1",
                "public_url": (
                    "https://example.invalid/data/result.json?verify=1"
                ),
            },
            "release_identity": {
                "commit_sha": "d" * 40,
                "deployment_id": "deploy-1",
                "frontend_response_sha256": "b" * 64,
                "frontend_response_size": 100,
                "authoritative_result_sha256": "c" * 64,
                "authoritative_result_size": 200,
                "production_url": "https://example.invalid/",
                "authoritative_result_url": (
                    "https://example.invalid/data/result.json"
                ),
            },
        }
        errors: list[str] = []
        evidence_validator.validate_cross_scope(receipt, errors)
        self.assertIn(
            "automation.head_sha does not match release.commit_sha",
            errors,
        )
        receipt["release_identity"]["commit_sha"] = "a" * 40
        errors = []
        evidence_validator.validate_cross_scope(receipt, errors)
        self.assertEqual(errors, [])

    def test_github_preflight_binds_repo_account_write_and_branch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            run("git", "-C", str(root), "init", "-b", "main")
            run("git", "-C", str(root), "config", "user.name", "Fixture")
            run(
                "git",
                "-C",
                str(root),
                "config",
                "user.email",
                "fixture@example.invalid",
            )
            (root / "README.md").write_text("fixture\n", encoding="utf-8")
            run("git", "-C", str(root), "add", "README.md")
            committed = run(
                "git",
                "-C",
                str(root),
                "commit",
                "-m",
                "fixture",
            )
            self.assertEqual(
                committed.returncode,
                0,
                committed.stdout + committed.stderr,
            )
            run(
                "git",
                "-C",
                str(root),
                "remote",
                "add",
                "origin",
                "https://github.com/example/sample.git",
            )
            fake_bin = Path(directory) / "bin"
            fake_bin.mkdir()
            real_git = shutil.which("git")
            assert real_git is not None
            (fake_bin / "git").write_text(
                "#!/bin/sh\n"
                "case \" $* \" in\n"
                "  *\" ls-remote \"*) exit 0 ;;\n"
                "esac\n"
                f"exec {shlex.quote(real_git)} \"$@\"\n",
                encoding="utf-8",
            )
            (fake_bin / "gh").write_text(
                "#!/bin/sh\n"
                "case \"$1 $2 $*\" in\n"
                "  \"auth status \"*) exit 0 ;;\n"
                "  \"api user \"*) echo example; exit 0 ;;\n"
                "  \"repo view \"*\"nameWithOwner\"*) "
                "echo example/sample; exit 0 ;;\n"
                "  \"repo view \"*\"defaultBranchRef\"*) echo main; exit 0 ;;\n"
                "  \"api repos/example/sample \"*) echo true; exit 0 ;;\n"
                "esac\n"
                "exit 1\n",
                encoding="utf-8",
            )
            (fake_bin / "git").chmod(0o755)
            (fake_bin / "gh").chmod(0o755)
            environment = dict(os.environ)
            environment["PATH"] = (
                str(fake_bin) + os.pathsep + environment.get("PATH", "")
            )
            script = str(SHARED / "scripts" / "github_preflight.sh")
            passed = run_env(
                environment,
                "bash",
                script,
                str(root),
                "example/sample",
                "example",
                "true",
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            self.assertIn("push_permission=true", passed.stdout)

            missing_target = run_env(
                environment,
                "bash",
                script,
                str(root),
            )
            self.assertNotEqual(missing_target.returncode, 0)
            self.assertIn("usage:", missing_target.stderr)

            wrong_account = run_env(
                environment,
                "bash",
                script,
                str(root),
                "example/sample",
                "someone-else",
                "true",
            )
            self.assertNotEqual(wrong_account.returncode, 0)

            run("git", "-C", str(root), "checkout", "--detach")
            detached = run_env(
                environment,
                "bash",
                script,
                str(root),
                "example/sample",
                "example",
                "true",
            )
            self.assertNotEqual(detached.returncode, 0)
            self.assertIn("detached HEAD", detached.stderr)

    def test_project_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text(
                "print('ok')\n", encoding="utf-8"
            )
            deep = root / "src" / "a" / "b" / "c" / "d"
            deep.mkdir(parents=True)
            (deep / "collector.py").write_text("", encoding="utf-8")
            run("git", "-C", str(root), "init")
            run(
                "git",
                "-C",
                str(root),
                "remote",
                "add",
                "origin",
                "https://user:token@github.com/example/sample.git",
            )
            result = run(
                sys.executable,
                str(SHARED / "scripts" / "project_inventory.py"),
                "--root",
                str(root),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("src/app.py", payload["source"]["python"])
            self.assertIn("src/a/b/c/d/collector.py", payload["source"]["python"])
            self.assertEqual(
                payload["git"]["remote_origin"]["value"],
                "https://github.com/example/sample.git",
            )

    def test_contract_guard_detects_and_clears_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protected = root / "analysis"
            protected.mkdir()
            file = protected / "model.py"
            file.write_text("VALUE = 1\n", encoding="utf-8")
            manifest = root / "project.json"
            manifest.write_text(
                json.dumps(
                    {
                        "project": {"id": "sample"},
                        "protected": {"paths": ["analysis/**"]},
                    }
                ),
                encoding="utf-8",
            )
            baseline = root / "baseline.json"
            script = SHARED / "scripts" / "contract_guard.py"

            created = run(
                sys.executable,
                str(script),
                "snapshot",
                "--root",
                str(root),
                "--manifest",
                str(manifest),
                "--output",
                str(baseline),
            )
            self.assertEqual(created.returncode, 0, created.stderr)

            unchanged = run(
                sys.executable,
                str(script),
                "verify",
                "--root",
                str(root),
                "--baseline",
                str(baseline),
                "--manifest",
                str(manifest),
            )
            self.assertEqual(
                unchanged.returncode, 0, unchanged.stdout + unchanged.stderr
            )

            file.write_text("VALUE = 2\n", encoding="utf-8")
            changed = run(
                sys.executable,
                str(script),
                "verify",
                "--root",
                str(root),
                "--baseline",
                str(baseline),
                "--manifest",
                str(manifest),
            )
            self.assertEqual(changed.returncode, 1)
            payload = json.loads(changed.stdout)
            self.assertEqual(payload["changed"], ["analysis/model.py"])

    def test_contract_guard_rejects_unmatched_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "project.json"
            manifest.write_text(
                json.dumps(
                    {
                        "project": {"id": "sample"},
                        "protected": {"paths": ["missing/**"]},
                    }
                ),
                encoding="utf-8",
            )
            result = run(
                sys.executable,
                str(SHARED / "scripts" / "contract_guard.py"),
                "snapshot",
                "--root",
                str(root),
                "--manifest",
                str(manifest),
                "--output",
                str(root / "baseline.json"),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("matched no files", result.stderr)

    def test_contract_guard_rejects_root_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            root.mkdir()
            (base / "outside.txt").write_text("secret\n", encoding="utf-8")
            manifest = root / "project.json"
            manifest.write_text(
                json.dumps(
                    {
                        "project": {"id": "sample"},
                        "protected": {"paths": ["../outside.txt"]},
                    }
                ),
                encoding="utf-8",
            )
            result = run(
                sys.executable,
                str(SHARED / "scripts" / "contract_guard.py"),
                "snapshot",
                "--root",
                str(root),
                "--manifest",
                str(manifest),
                "--output",
                str(root / "baseline.json"),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("stay within root", result.stderr)

    def test_project_contract_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "analysis").mkdir()
            (root / "analysis" / "run.py").write_text("", encoding="utf-8")
            (root / "pipeline.py").write_text(
                "import runpy\nrunpy.run_path('analysis/run.py')\n",
                encoding="utf-8",
            )
            (root / "collect.py").write_text("print('collect')\n", encoding="utf-8")
            (root / "cost_preflight.py").write_text(
                "print('quota checked')\n",
                encoding="utf-8",
            )
            (root / "schemas").mkdir()
            (root / "schemas" / "input.json").write_text("{}\n", encoding="utf-8")
            (root / "schemas" / "analysis-input.json").write_text(
                '{"type":"object"}\n',
                encoding="utf-8",
            )
            workflow = root / ".github" / "workflows" / "refresh.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                "concurrency:\n"
                "  group: sample-automation\n"
                "  cancel-in-progress: false\n"
                "on:\n"
                "  schedule:\n"
                "    - cron: '0 1 * * *'\n"
                "jobs:\n"
                "  refresh:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - id: cost-preflight\n"
                "        run: python cost_preflight.py\n"
                "      - id: collect-and-analyze\n"
                "        run: python pipeline.py\n",
                encoding="utf-8",
            )
            manifest = root / "project.json"
            manifest.write_text(
                json.dumps(valid_project_manifest()),
                encoding="utf-8",
            )
            script = str(SHARED / "scripts" / "validate_project.py")
            valid = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

            original_workflow = workflow.read_text(encoding="utf-8")
            pinned_checkout_workflow = original_workflow.replace(
                "      - id: cost-preflight\n",
                "      - uses: actions/checkout@"
                + "a" * 40
                + "\n"
                "      - id: cost-preflight\n",
            )
            workflow.write_text(
                pinned_checkout_workflow,
                encoding="utf-8",
            )
            pinned_checkout = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertEqual(
                pinned_checkout.returncode,
                0,
                pinned_checkout.stdout + pinned_checkout.stderr,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            generic_environment_bypasses = (
                (
                    "      - id: cost-preflight\n",
                    "      - id: cost-preflight\n"
                    "        env:\n"
                    "          SKIP_COST_CHECK: true\n",
                ),
                (
                    "  refresh:\n",
                    "  refresh:\n"
                    "    env:\n"
                    "      SKIP_COST_CHECK: true\n",
                ),
                (
                    "on:\n",
                    "env:\n"
                    "  SKIP_COST_CHECK: true\n"
                    "on:\n",
                ),
                (
                    "      - id: cost-preflight\n",
                    "      - id: cost-preflight\n"
                    "        env:\n"
                    "          LD_LIBRARY_PATH: bypass\n",
                ),
            )
            for old, replacement in generic_environment_bypasses:
                workflow.write_text(
                    original_workflow.replace(old, replacement),
                    encoding="utf-8",
                )
                generic_environment_bypass = run(
                    sys.executable,
                    script,
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                )
                self.assertNotEqual(generic_environment_bypass.returncode, 0)
                self.assertRegex(
                    generic_environment_bypass.stdout,
                    r"must not declare env",
                )
            workflow.write_text(original_workflow, encoding="utf-8")

            concurrency_contract_cases = (
                (
                    "concurrency:\n"
                    "  group: sample-automation\n"
                    "  cancel-in-progress: false\n",
                    "",
                    "must declare exactly one workflow-level concurrency",
                ),
                (
                    "  group: sample-automation\n",
                    "  group: another-project\n",
                    "concurrency group must exactly match",
                ),
                (
                    "  cancel-in-progress: false\n",
                    "  cancel-in-progress: true\n",
                    "cancel-in-progress must be the literal false",
                ),
            )
            for old, replacement, expected_error in concurrency_contract_cases:
                workflow.write_text(
                    original_workflow.replace(old, replacement),
                    encoding="utf-8",
                )
                invalid_concurrency = run(
                    sys.executable,
                    script,
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                )
                self.assertNotEqual(invalid_concurrency.returncode, 0)
                self.assertIn(expected_error, invalid_concurrency.stdout)
            workflow.write_text(original_workflow, encoding="utf-8")

            scope_multiplication_cases = (
                (
                    "    runs-on: ubuntu-latest\n",
                    "    runs-on: ubuntu-latest\n"
                    "    strategy:\n"
                    "      matrix:\n"
                    "        shard: [1, 2, 3, 4]\n",
                    "must not use strategy or matrix",
                ),
                (
                    "",
                    "  unguarded-paid:\n"
                    "    runs-on: ubuntu-latest\n"
                    "    steps:\n"
                    "      - run: python pipeline.py\n",
                    "jobs must contain only the declared required job",
                ),
                (
                    "    - cron: '0 1 * * *'\n",
                    "    - cron: '0 1 * * *'\n"
                    "    - cron: '0 2 * * *'\n",
                    "schedule crons must exactly match",
                ),
                (
                    "  schedule:\n",
                    "  push:\n"
                    "  schedule:\n",
                    "triggers must be limited",
                ),
            )
            for old, replacement, expected_error in scope_multiplication_cases:
                candidate = (
                    original_workflow + replacement
                    if old == ""
                    else original_workflow.replace(old, replacement)
                )
                workflow.write_text(candidate, encoding="utf-8")
                multiplied_scope = run(
                    sys.executable,
                    script,
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                )
                self.assertNotEqual(multiplied_scope.returncode, 0)
                self.assertIn(expected_error, multiplied_scope.stdout)
            workflow.write_text(original_workflow, encoding="utf-8")

            duplicate_mapping_cases = (
                (
                    "",
                    "jobs:\n"
                    "  refresh:\n"
                    "    runs-on: self-hosted\n"
                    "    steps:\n"
                    "      - run: python pipeline.py\n",
                    "top-level mapping keys must be unique",
                ),
                (
                    "",
                    "  refresh:\n"
                    "    runs-on: self-hosted\n"
                    "    steps:\n"
                    "      - run: python pipeline.py\n",
                    "job IDs must be unique",
                ),
                (
                    "  schedule:\n",
                    "  schedule:\n"
                    "  schedule:\n"
                    "    - cron: '* * * * *'\n",
                    "trigger mapping keys must be unique",
                ),
            )
            for index, (old, replacement, expected_error) in enumerate(
                duplicate_mapping_cases
            ):
                if index == 0:
                    candidate = original_workflow + replacement
                elif index == 1:
                    candidate = original_workflow + replacement
                else:
                    candidate = original_workflow.replace(old, replacement)
                workflow.write_text(candidate, encoding="utf-8")
                duplicate_mapping = run(
                    sys.executable,
                    script,
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                )
                self.assertNotEqual(duplicate_mapping.returncode, 0)
                self.assertIn(expected_error, duplicate_mapping.stdout)
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "        run: python pipeline.py\n",
                    "        run: python pipeline.py\n"
                    "      - id: extra-provider-call\n"
                    "        run: python collect.py\n",
                ),
                encoding="utf-8",
            )
            extra_step = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(extra_step.returncode, 0)
            self.assertIn(
                "steps must be an optional pinned checkout",
                extra_step.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "  refresh:\n",
                    '  refresh:\n    "if": false\n',
                ),
                encoding="utf-8",
            )
            conditional = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(conditional.returncode, 0)
            self.assertIn(
                "required job must not be conditional",
                conditional.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "      - id: cost-preflight\n",
                    '      - id: cost-preflight\n        "if": false\n',
                ),
                encoding="utf-8",
            )
            conditional_step = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(conditional_step.returncode, 0)
            self.assertIn(
                "must be unconditional and fail-closed",
                conditional_step.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "        run: python cost_preflight.py\n",
                    "        run: |\n"
                    "          if false; then\n"
                    "            python cost_preflight.py\n"
                    "          fi\n",
                ),
                encoding="utf-8",
            )
            dead_cost_command = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(dead_cost_command.returncode, 0)
            self.assertIn(
                "cost step must contain only the exact preflight command",
                dead_cost_command.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "        run: python cost_preflight.py\n",
                    "        run: python cost_preflight.py || true\n",
                ),
                encoding="utf-8",
            )
            ignored_cost_failure = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(ignored_cost_failure.returncode, 0)
            self.assertIn(
                "cost step must contain only the exact preflight command",
                ignored_cost_failure.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "        run: python cost_preflight.py\n",
                    "        shell: bash -c 'exit 0' -- {0}\n"
                    "        run: python cost_preflight.py\n",
                ),
                encoding="utf-8",
            )
            custom_shell_bypass = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(custom_shell_bypass.returncode, 0)
            self.assertIn(
                "must not override its shell",
                custom_shell_bypass.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            bypass_directory = root / "bypass"
            bypass_directory.mkdir()
            (bypass_directory / "cost_preflight.py").write_text(
                "print('unsafe no-op')\n",
                encoding="utf-8",
            )
            workflow.write_text(
                original_workflow.replace(
                    "        run: python cost_preflight.py\n",
                    "        working-directory: bypass\n"
                    "        run: python cost_preflight.py\n",
                ),
                encoding="utf-8",
            )
            working_directory_bypass = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(working_directory_bypass.returncode, 0)
            self.assertIn(
                "must not override its working-directory",
                working_directory_bypass.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "      - id: cost-preflight\n",
                    "      - id: cost-preflight\n"
                    "        env:\n"
                    "          BASH_ENV: bypass.sh\n",
                ),
                encoding="utf-8",
            )
            dangerous_step_environment = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(dangerous_step_environment.returncode, 0)
            self.assertIn(
                "env overrides execution context: BASH_ENV",
                dangerous_step_environment.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "  refresh:\n",
                    "  refresh:\n"
                    "    env:\n"
                    "      PATH: bypass-bin:/usr/bin:/bin\n",
                ),
                encoding="utf-8",
            )
            dangerous_job_environment = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(dangerous_job_environment.returncode, 0)
            self.assertIn(
                "required job env overrides execution context: PATH",
                dangerous_job_environment.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                "env:\n"
                "  PYTHONPATH: bypass\n"
                + original_workflow,
                encoding="utf-8",
            )
            dangerous_workflow_environment = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(dangerous_workflow_environment.returncode, 0)
            self.assertIn(
                "workflow env overrides execution context: PYTHONPATH",
                dangerous_workflow_environment.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "    runs-on: ubuntu-latest\n",
                    "    runs-on: self-hosted\n",
                ),
                encoding="utf-8",
            )
            untrusted_runner = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(untrusted_runner.returncode, 0)
            self.assertIn(
                "must use one literal trusted GitHub-hosted runner",
                untrusted_runner.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "    runs-on: ubuntu-latest\n",
                    "    runs-on: ubuntu-latest\n"
                    "    container: example.invalid/untrusted:latest\n",
                ),
                encoding="utf-8",
            )
            untrusted_container = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(untrusted_container.returncode, 0)
            self.assertIn(
                "required job must not use a container",
                untrusted_container.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "      - id: cost-preflight\n",
                    "      - id: mutate-context\n"
                    "        run: echo PATH=./bypass >> \"$GITHUB_ENV\"\n"
                    "      - id: cost-preflight\n",
                ),
                encoding="utf-8",
            )
            preceding_run_bypass = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(preceding_run_bypass.returncode, 0)
            self.assertIn(
                "only one pinned actions/checkout step",
                preceding_run_bypass.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            encoded_key_bypasses = (
                (
                    "      - id: cost-preflight\n",
                    "      - id: cost-preflight\n"
                    "        ? if\n"
                    "        : false\n",
                ),
                (
                    "      - id: cost-preflight\n",
                    "      - id: cost-preflight\n"
                    '        "i\\u0066": false\n',
                ),
                (
                    "      - id: cost-preflight\n",
                    "      - id: cost-preflight\n"
                    '        "s\\u0068ell": '
                    "bash -c 'exit 0' -- {0}\n",
                ),
                (
                    "      - id: cost-preflight\n",
                    "      - id: cost-preflight\n"
                    "        env:\n"
                    '          "BASH\\u005fENV": bypass.sh\n',
                ),
                (
                    "    runs-on: ubuntu-latest\n",
                    "    runs-on: ubuntu-latest\n"
                    '    "cont\\u0061iner": '
                    "example.invalid/untrusted:latest\n",
                ),
                (
                    "jobs:\n",
                    '"def\\u0061ults": '
                    "{run: {shell: bash -c 'exit 0' -- {0}}}\n"
                    "jobs:\n",
                ),
            )
            for old, replacement in encoded_key_bypasses:
                workflow.write_text(
                    original_workflow.replace(old, replacement),
                    encoding="utf-8",
                )
                encoded_key_bypass = run(
                    sys.executable,
                    script,
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                )
                self.assertNotEqual(encoded_key_bypass.returncode, 0)
                self.assertIn(
                    "must use simple literal YAML mapping keys",
                    encoded_key_bypass.stdout,
                )
            workflow.write_text(original_workflow, encoding="utf-8")

            anchored_key_bypasses = (
                (
                    "      - id: cost-preflight\n",
                    "      - id: cost-preflight\n"
                    "        !!str if: false\n",
                ),
                (
                    "      - id: cost-preflight\n",
                    "      - id: cost-preflight\n"
                    "        &guard if: false\n",
                ),
                (
                    "on:\n",
                    "env:\n"
                    "  SAFE_NAME: &guard if\n"
                    "on:\n",
                ),
            )
            for old, replacement in anchored_key_bypasses:
                candidate = original_workflow.replace(old, replacement)
                if "SAFE_NAME" in candidate:
                    candidate = candidate.replace(
                        "      - id: cost-preflight\n",
                        "      - id: cost-preflight\n"
                        "        *guard: false\n",
                    )
                workflow.write_text(candidate, encoding="utf-8")
                anchored_key_bypass = run(
                    sys.executable,
                    script,
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                )
                self.assertNotEqual(anchored_key_bypass.returncode, 0)
                self.assertIn(
                    "must use simple literal YAML mapping keys",
                    anchored_key_bypass.stdout,
                )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "jobs:\n",
                    "defaults:\n"
                    "  run:\n"
                    "    shell: bash -c 'exit 0' -- {0}\n"
                    "jobs:\n",
                ),
                encoding="utf-8",
            )
            workflow_default_shell_bypass = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(workflow_default_shell_bypass.returncode, 0)
            self.assertIn(
                "must not override shell or working-directory",
                workflow_default_shell_bypass.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "jobs:\n",
                    "defaults: {run: {shell: bash -c 'exit 0' -- {0}}}\n"
                    "jobs:\n",
                ),
                encoding="utf-8",
            )
            inline_default_shell_bypass = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(inline_default_shell_bypass.returncode, 0)
            self.assertIn(
                "must not override shell or working-directory",
                inline_default_shell_bypass.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "    steps:\n",
                    "    defaults:\n"
                    "      run:\n"
                    "        working-directory: bypass\n"
                    "    steps:\n",
                ),
                encoding="utf-8",
            )
            job_default_directory_bypass = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(job_default_directory_bypass.returncode, 0)
            self.assertIn(
                "must not override shell or working-directory",
                job_default_directory_bypass.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            workflow.write_text(
                original_workflow.replace(
                    "  refresh:\n",
                    "  refresh:\n"
                    '    "continue-on-error": ${{ true }}\n',
                ),
                encoding="utf-8",
            )
            permissive_job = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(permissive_job.returncode, 0)
            self.assertIn(
                "required job must not declare continue-on-error",
                permissive_job.stdout,
            )
            workflow.write_text(
                original_workflow.replace(
                    "      - id: cost-preflight\n",
                    "      - id: cost-preflight\n"
                    '        "continue-on-error": ${{ true }}\n',
                ),
                encoding="utf-8",
            )
            permissive_step = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(permissive_step.returncode, 0)
            self.assertIn(
                "must be unconditional and fail-closed",
                permissive_step.stdout,
            )
            workflow.write_text(original_workflow, encoding="utf-8")

            incomplete_artifact_identity = valid_project_manifest()
            incomplete_artifact_identity["analysis"][
                "result_artifact_identity"
            ] = [
                assertion
                for assertion in incomplete_artifact_identity["analysis"][
                    "result_artifact_identity"
                ]
                if assertion["identity_field"] != "run_id"
            ]
            manifest.write_text(
                json.dumps(incomplete_artifact_identity),
                encoding="utf-8",
            )
            incomplete_identity = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(incomplete_identity.returncode, 0)
            self.assertIn(
                "must bind both project_id and run_id",
                incomplete_identity.stdout,
            )

            missing_runtime_shape = valid_project_manifest()
            del missing_runtime_shape["frontend"]["type"]
            del missing_runtime_shape["backend"]["required"]
            manifest.write_text(
                json.dumps(missing_runtime_shape),
                encoding="utf-8",
            )
            invalid_runtime_shape = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(invalid_runtime_shape.returncode, 0)
            self.assertIn("frontend.type", invalid_runtime_shape.stdout)
            self.assertIn("backend.required", invalid_runtime_shape.stdout)

            payload = valid_project_manifest()
            payload["release"]["paid_action_authority"] = {"approved": True}
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            invalid = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("cannot grant paid-action authority", invalid.stdout)

            empty_manual = valid_project_manifest()
            empty_manual["data"]["sources"] = []
            empty_manual["analysis"]["authoritative_entrypoints"] = []
            empty_manual["automation"]["mode"] = "manual"
            empty_manual["automation"]["workflows"] = []
            empty_manual["automation"]["schedules"] = []
            manifest.write_text(json.dumps(empty_manual), encoding="utf-8")
            invalid_manual = run(
                sys.executable,
                script,
                "--root",
                str(root),
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(invalid_manual.returncode, 0)
            self.assertIn(
                "active automation requires a data source registry",
                invalid_manual.stdout,
            )

    def test_evidence_receipt_v2_local(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, goal, scope = write_context(root)
            cost = local_cost()
            receipt = root / "receipt.json"
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_id": "sample",
                        "objective": "Ship a verified result",
                        "scope": scope,
                        "cost_authority": cost,
                        "completed_at": "2026-07-25T12:01:00Z",
                        "required_gates": [
                            "contract",
                            "tests",
                            "product",
                            "cost",
                        ],
                        "gates": {
                            "contract": {
                                "status": "passed",
                                "evidence": [gate_evidence("contract_guard")],
                            },
                            "tests": {
                                "status": "passed",
                                "evidence": [gate_evidence("test_run")],
                            },
                            "product": {
                                "status": "passed",
                                "evidence": [gate_evidence("product_check")],
                            },
                            "cost": {
                                "status": "passed",
                                "evidence": [complete_cost_evidence(cost)],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = run(
                sys.executable,
                str(SHARED / "scripts" / "validate_evidence.py"),
                "--project-root",
                str(root),
                "--manifest",
                str(manifest),
                "--goal-state",
                str(goal),
                str(receipt),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_evidence_receipt_v1_blocked_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project_id": "sample",
                        "objective": "Historical receipt",
                        "required_gates": ["contract"],
                        "gates": {
                            "contract": {
                                "status": "passed",
                                "evidence": ["historical evidence"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            script = str(SHARED / "scripts" / "validate_evidence.py")
            blocked = run(sys.executable, script, str(receipt))
            self.assertNotEqual(blocked.returncode, 0)
            allowed = run(
                sys.executable,
                script,
                "--allow-legacy-v1",
                str(receipt),
            )
            self.assertEqual(allowed.returncode, 3, allowed.stdout + allowed.stderr)
            self.assertIn("historical-read-only-not-completion", allowed.stdout)

    def test_evidence_receipt_rejects_malformed_gate_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project_id": "sample",
                        "objective": "Historical receipt",
                        "required_gates": [{}],
                        "gates": {},
                    }
                ),
                encoding="utf-8",
            )
            result = run(
                sys.executable,
                str(SHARED / "scripts" / "validate_evidence.py"),
                "--allow-legacy-v1",
                str(receipt),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)

    def test_evidence_receipt_rejects_nonfinite_json_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            receipt.write_text(
                '{"schema_version":2,"project_id":"sample",'
                '"objective":"test","unsafe":NaN}',
                encoding="utf-8",
            )
            result = run(
                sys.executable,
                str(SHARED / "scripts" / "validate_evidence.py"),
                str(receipt),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("non-finite JSON number", result.stdout)
            self.assertNotIn("Traceback", result.stderr)

    def test_paid_action_requires_direct_prior_user_request(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scope = {
                "automated_data_to_web": False,
                "remote_release": False,
                "paid_action": True,
            }
            manifest, goal, _ = write_context(root)
            goal.write_text(
                json.dumps(
                    {
                        "project_id": "sample",
                        "objective": "Ship a verified result",
                        "scope": scope,
                        "required_outcomes": {
                            "automated_data_to_web": False,
                            "remote_release": False,
                        },
                        "approval_gates": {
                            "release": "pending",
                            "paid_action": "direct-user-prior-request-recorded",
                        },
                        "automation_state": {"in_scope": False},
                        "cost_authority": {
                            "policy": (
                                "zero-spend-unless-user-first-requests-specific-paid-action"
                            ),
                            "paid_action_requested": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            actions: list[object] = []
            cost = {
                "policy": (
                    "zero-spend-unless-user-first-requests-specific-paid-action"
                ),
                "classification": "explicit_user_paid_command",
                "decision": "allow",
                "paid_action_requested": True,
                "authority_origin": "direct-user-prior-request",
                "actions": actions,
                "canonical_actions_envelope": {
                    "canonicalization": "canonical-json-v1",
                    "action_count": 0,
                    "sha256": canonical_sha256(actions),
                    "authoritative_for_cost_gate": True,
                },
            }
            receipt = root / "receipt.json"
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_id": "sample",
                        "objective": "Ship a verified result",
                        "scope": scope,
                        "cost_authority": cost,
                        "completed_at": "2026-07-25T12:01:00Z",
                        "required_gates": [
                            "contract",
                            "tests",
                            "product",
                            "cost",
                        ],
                        "gates": {
                            "contract": {
                                "status": "passed",
                                "evidence": [gate_evidence("contract_guard")],
                            },
                            "tests": {
                                "status": "passed",
                                "evidence": [gate_evidence("test_run")],
                            },
                            "product": {
                                "status": "passed",
                                "evidence": [gate_evidence("product_check")],
                            },
                            "cost": {
                                "status": "passed",
                                "evidence": [
                                    gate_evidence(
                                        "cost_preflight",
                                        classification="explicit_user_paid_command",
                                        decision="allow",
                                        canonical_actions_envelope_sha256=(
                                            canonical_sha256(actions)
                                        ),
                                        all_remote_or_provider_actions_enumerated=True,
                                        all_numeric_ceilings_validated=True,
                                        all_hard_stops_enabled=True,
                                        trusted_runtime_paid_authority_verified=False,
                                    )
                                ],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            script = str(SHARED / "scripts" / "validate_evidence.py")
            blocked = run(
                sys.executable,
                script,
                "--project-root",
                str(root),
                "--manifest",
                str(manifest),
                "--goal-state",
                str(goal),
                str(receipt),
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn(
                "no trusted runtime authority envelope",
                blocked.stdout,
            )

    def test_automation_receipt_requires_matching_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, goal, scope = write_context(root, automated=True)
            manifest_value = json.loads(manifest.read_text(encoding="utf-8"))
            secondary_source = json.loads(
                json.dumps(manifest_value["data"]["sources"][0])
            )
            secondary_source["id"] = "secondary"
            secondary_source["role"] = "optional"
            secondary_source["fallback_policy"] = "explicit-degraded"
            secondary_source["raw_artifact"] = "data/raw-secondary.json"
            secondary_source["normalized_artifact"] = (
                "data/input-secondary.json"
            )
            manifest_value["data"]["sources"].append(secondary_source)
            manifest.write_text(json.dumps(manifest_value), encoding="utf-8")
            workflow_file = root / ".github" / "workflows" / "refresh.yml"
            workflow_file_hash = hashlib.sha256(
                workflow_file.read_bytes()
            ).hexdigest()
            analysis_entrypoint_hash = hashlib.sha256(
                (root / "pipeline.py").read_bytes()
            ).hexdigest()
            code_version = "f" * 40
            source_artifact = root / "data" / "raw-primary.json"
            source_artifact.parent.mkdir()
            source_artifact.write_bytes(b'{"source_as_of":"2026-07-24"}\n')
            source_artifact_hash = hashlib.sha256(
                source_artifact.read_bytes()
            ).hexdigest()
            analysis_input = root / "data" / "input.json"
            analysis_input.write_bytes(
                b'{"project_id":"sample","observations":[1,2,3]}\n'
            )
            analysis_input_hash = hashlib.sha256(
                analysis_input.read_bytes()
            ).hexdigest()
            source_manifest = root / "data" / "manifest.json"
            source_manifest.write_text(
                json.dumps(
                    {
                        "project_id": "sample",
                        "data_as_of": "2026-07-24",
                        "required_source_ids": ["primary"],
                        "analysis_input_path": "data/input.json",
                        "analysis_input_sha256": analysis_input_hash,
                        "analysis_input_size": analysis_input.stat().st_size,
                        "sources": [
                            {
                                "source_id": "primary",
                                "role": "required",
                                "artifact_path": "data/raw-primary.json",
                                "artifact_sha256": source_artifact_hash,
                                "artifact_size": source_artifact.stat().st_size,
                                "source_as_of": "2026-07-24",
                                "expected_source_as_of": "2026-07-24",
                                "coherent_through": "2026-07-24",
                                "observed_lag_seconds": 0,
                                "allowed_lag_seconds": 86400,
                                "observed_age_seconds": 122400,
                                "maximum_source_age_seconds": 172800,
                                "collected_at": "2026-07-25T09:30:00Z",
                            }
                        ],
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            source_hash = hashlib.sha256(source_manifest.read_bytes()).hexdigest()
            config_hash = canonical_sha256({})
            input_schema = root / "schemas" / "analysis-input.json"
            input_schema_hash = hashlib.sha256(
                input_schema.read_bytes()
            ).hexdigest()
            analysis_input_validation = (
                root / "data" / "analysis-input-validation.json"
            )
            analysis_input_validation.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project_id": "sample",
                        "run_id": "run-1",
                        "analysis_input_sha256": analysis_input_hash,
                        "input_schema_sha256": input_schema_hash,
                        "code_version": code_version,
                        "analysis_entrypoint_sha256": (
                            analysis_entrypoint_hash
                        ),
                        "valid": True,
                        "validator_name": "fixture-schema-validator",
                        "validator_version": "1",
                        "command": "python validate_input.py",
                        "checked_at": "2026-07-25T09:20:00Z",
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            analysis_input_validation_hash = hashlib.sha256(
                analysis_input_validation.read_bytes()
            ).hexdigest()
            analysis_request_manifest = (
                root / "data" / "analysis-request.json"
            )
            analysis_request_manifest.write_text(
                json.dumps(
                    {
                        "project_id": "sample",
                        "run_id": "run-1",
                        "code_version": code_version,
                        "analysis_entrypoint_sha256": (
                            analysis_entrypoint_hash
                        ),
                        "input_schema_version": "1",
                        "input_schema_sha256": input_schema_hash,
                        "data_manifest_sha256": source_hash,
                        "analysis_input_sha256": analysis_input_hash,
                        "analysis_input_validation_sha256": (
                            analysis_input_validation_hash
                        ),
                        "requested_config": {},
                        "effective_config": {},
                        "config_hash": config_hash,
                        "effective_config_hash": config_hash,
                        "fallback_applied": False,
                        "fallback_reason": "",
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            analysis_request_hash = hashlib.sha256(
                analysis_request_manifest.read_bytes()
            ).hexdigest()
            artifact = root / "docs" / "data" / "result.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b'{"project_id":"sample","run_id":"run-1"}\n')
            result_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
            result_manifest = root / "docs" / "data" / "result-manifest.json"
            result_manifest.write_text(
                json.dumps(
                    {
                        "project_id": "sample",
                        "run_id": "run-1",
                        "data_as_of": "2026-07-24",
                        "code_version": code_version,
                        "analysis_entrypoint_sha256": (
                            analysis_entrypoint_hash
                        ),
                        "data_manifest_sha256": source_hash,
                        "analysis_input_sha256": analysis_input_hash,
                        "analysis_input_validation_sha256": (
                            analysis_input_validation_hash
                        ),
                        "analysis_request_manifest_sha256": (
                            analysis_request_hash
                        ),
                        "config_hash": config_hash,
                        "effective_config_hash": config_hash,
                        "input_schema_version": "1",
                        "input_schema_sha256": input_schema_hash,
                        "data_schema_version": "1",
                        "result_schema_version": "1",
                        "artifact_path": "docs/data/result.json",
                        "artifact_sha256": result_hash,
                        "artifact_size": artifact.stat().st_size,
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            result_manifest_hash = hashlib.sha256(
                result_manifest.read_bytes()
            ).hexdigest()
            pointer_before = root / "captures" / "pointer-before.json"
            pointer_before.parent.mkdir()
            pointer_before.write_text(
                json.dumps(
                    {
                        "project_id": "sample",
                        "generation": 1,
                        "published_result_key": "result-20260723",
                        "data_as_of": "2026-07-23",
                        "result_artifact_sha256": "a" * 64,
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            pointer_before_hash = hashlib.sha256(
                pointer_before.read_bytes()
            ).hexdigest()
            pointer_after = root / "captures" / "pointer-after.json"
            pointer_after.write_text(
                json.dumps(
                    {
                        "project_id": "sample",
                        "generation": 2,
                        "published_result_key": "result-20260724",
                        "data_as_of": "2026-07-24",
                        "result_artifact_sha256": result_hash,
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            pointer_after_hash = hashlib.sha256(
                pointer_after.read_bytes()
            ).hexdigest()
            ordering_test_output = (
                root / "captures" / "publication-ordering-test.log"
            )
            ordering_test_output.write_text(
                "older candidate rejected\n"
                "failed candidate preserved previous pointer\n",
                encoding="utf-8",
            )
            ordering_test_output_hash = hashlib.sha256(
                ordering_test_output.read_bytes()
            ).hexdigest()
            ordering_evidence = root / "captures" / "publication-ordering.json"
            ordering_evidence.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project_id": "sample",
                        "candidate_run_id": "run-1",
                        "previous_generation": 1,
                        "candidate_generation": 2,
                        "previous_result_sha256": "a" * 64,
                        "candidate_result_sha256": result_hash,
                        "selected_generation": 2,
                        "older_candidate_rejected": True,
                        "failed_candidate_preserved_previous": True,
                        "test_source": "deterministic publication fixture",
                        "test_command": "python test_publication_ordering.py",
                        "test_exit_code": 0,
                        "isolated_test_namespace": "fixture-run-1",
                        "test_output_sha256": ordering_test_output_hash,
                        "test_output_size": ordering_test_output.stat().st_size,
                        "older_candidate_scenario": {
                            "newer_run_id": "run-1",
                            "older_run_id": "run-1-older",
                            "newer_generation": 2,
                            "older_generation": 1,
                            "pointer_before_sha256": pointer_after_hash,
                            "pointer_after_sha256": pointer_after_hash,
                            "selected_generation": 2,
                        },
                        "failed_candidate_scenario": {
                            "failed_run_id": "run-1-failed",
                            "failure_stage": "analysis-or-readback",
                            "pointer_before_sha256": pointer_before_hash,
                            "pointer_after_sha256": pointer_before_hash,
                            "preserved_result_sha256": "a" * 64,
                        },
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            ordering_evidence_hash = hashlib.sha256(
                ordering_evidence.read_bytes()
            ).hexdigest()
            public_result = root / "captures" / "public-result.json"
            public_result.write_bytes(artifact.read_bytes())
            frontend = root / "captures" / "frontend.html"
            frontend.write_bytes(b"<html><body>sample</body></html>\n")
            frontend_hash = hashlib.sha256(frontend.read_bytes()).hexdigest()
            frontend_dom = root / "captures" / "frontend-dom.html"
            frontend_dom.write_text(
                (
                    '<main data-quant-result-binding="bound" '
                    'data-quant-project-id="sample" '
                    'data-quant-run-id="run-1" '
                    'data-quant-as-of="2026-07-24" '
                    f'data-quant-result-sha="{result_hash}" '
                    f'data-quant-result-manifest-sha="{result_manifest_hash}" '
                    f'data-quant-config-sha="{config_hash}" '
                    f'data-quant-effective-config-sha="{config_hash}" '
                    'data-quant-input-schema-version="1" '
                    f'data-quant-analysis-entrypoint-sha="'
                    f'{analysis_entrypoint_hash}" '
                    'data-quant-publication-state="degraded"></main>'
                ),
                encoding="utf-8",
            )
            frontend_dom_hash = hashlib.sha256(
                frontend_dom.read_bytes()
            ).hexdigest()
            frontend_binding = root / "captures" / "frontend-binding.json"
            frontend_binding.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "binding_status": "bound",
                        "capture_origin": "browser-runtime",
                        "capture_tool": "deterministic browser fixture",
                        "dom_selector": "[data-quant-result-binding]",
                        "dom_snapshot_sha256": frontend_dom_hash,
                        "dom_snapshot_size": frontend_dom.stat().st_size,
                        "captured_at": "2026-07-25T10:05:00Z",
                        "frontend_url": "https://example.invalid/",
                        "frontend_response_sha256": frontend_hash,
                        "public_result_url": (
                            "https://example.invalid/data/result.json?verify=1"
                        ),
                        "public_result_sha256": result_hash,
                        "project_id": "sample",
                        "run_id": "run-1",
                        "data_as_of": "2026-07-24",
                        "code_version": code_version,
                        "analysis_entrypoint_sha256": (
                            analysis_entrypoint_hash
                        ),
                        "data_manifest_sha256": source_hash,
                        "result_manifest_sha256": result_manifest_hash,
                        "result_artifact_sha256": result_hash,
                        "analysis_input_sha256": analysis_input_hash,
                        "analysis_input_validation_sha256": (
                            analysis_input_validation_hash
                        ),
                        "analysis_request_manifest_sha256": (
                            analysis_request_hash
                        ),
                        "config_hash": config_hash,
                        "effective_config_hash": config_hash,
                        "input_schema_version": "1",
                        "input_schema_sha256": input_schema_hash,
                        "publication_state": "degraded",
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            frontend_binding_hash = hashlib.sha256(
                frontend_binding.read_bytes()
            ).hexdigest()
            workflow_run = root / "captures" / "workflow-run.json"
            workflow_run.write_text(
                json.dumps(
                    {
                        "run_id": "run-1",
                        "run_url": "https://example.invalid/run/1",
                        "event": "schedule",
                        "default_branch": "main",
                        "head_sha": "f" * 40,
                        "started_at": "2026-07-25T09:00:00Z",
                        "conclusion": "success",
                        "steps_completed": 2,
                        "workflow_file_sha256": workflow_file_hash,
                        "jobs": [
                            {
                                "job_id": "refresh",
                                "conclusion": "success",
                                "steps": [
                                    {
                                        "step_id": "cost-preflight",
                                        "outcome": "success",
                                        "conclusion": "success",
                                        "completed_at": (
                                            "2026-07-25T09:10:00Z"
                                        ),
                                    },
                                    {
                                        "step_id": "collect-and-analyze",
                                        "outcome": "success",
                                        "conclusion": "success",
                                        "started_at": (
                                            "2026-07-25T09:11:00Z"
                                        ),
                                    },
                                ],
                            }
                        ],
                        "completed_at": "2026-07-25T10:00:00Z",
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            workflow_run_hash = hashlib.sha256(
                workflow_run.read_bytes()
            ).hexdigest()
            identity = {
                "source_manifest_sha256": source_hash,
                "source_manifest_size": source_manifest.stat().st_size,
                "required_source_ids": ["primary"],
                "required_source_count": 1,
                "failed_required_source_count": 0,
                "data_as_of": "2026-07-24",
                "analysis_code_version": code_version,
                "analysis_entrypoint_sha256": analysis_entrypoint_hash,
                "analysis_input_sha256": analysis_input_hash,
                "analysis_input_size": analysis_input.stat().st_size,
                "analysis_input_validation_sha256": (
                    analysis_input_validation_hash
                ),
                "analysis_input_validation_size": (
                    analysis_input_validation.stat().st_size
                ),
                "analysis_request_manifest_sha256": analysis_request_hash,
                "analysis_request_manifest_size": (
                    analysis_request_manifest.stat().st_size
                ),
                "result_manifest_sha256": result_manifest_hash,
                "result_manifest_size": result_manifest.stat().st_size,
                "config_hash": config_hash,
                "effective_config_hash": config_hash,
                "input_schema_version": "1",
                "input_schema_sha256": input_schema_hash,
                "data_schema_version": "1",
                "result_schema_version": "1",
                "run_id": "run-1",
                "run_url": "https://example.invalid/run/1",
                "workflow_run_evidence_sha256": workflow_run_hash,
                "workflow_file_sha256": workflow_file_hash,
                "workflow_started_at": "2026-07-25T09:00:00Z",
                "cost_preflight_completed_at": "2026-07-25T09:10:00Z",
                "entrypoint_started_at": "2026-07-25T09:11:00Z",
                "default_branch": "main",
                "head_sha": "f" * 40,
                "job_id": "refresh",
                "cost_preflight_step_id": "cost-preflight",
                "entrypoint_step_id": "collect-and-analyze",
                "steps_completed": 2,
                "result_artifact_sha256": result_hash,
                "result_artifact_size": artifact.stat().st_size,
                "published_result_key": "result-20260724",
                "publication_state": "degraded",
                "previous_generation": 1,
                "candidate_generation": 2,
                "previous_public_result_sha256": "a" * 64,
                "previous_data_as_of": "2026-07-23",
                "previous_published_result_key": "result-20260723",
                "public_pointer_before_sha256": pointer_before_hash,
                "public_pointer_before_size": pointer_before.stat().st_size,
                "public_pointer_after_sha256": pointer_after_hash,
                "public_pointer_after_size": pointer_after.stat().st_size,
                "publication_ordering_evidence_sha256": (
                    ordering_evidence_hash
                ),
                "publication_ordering_evidence_size": (
                    ordering_evidence.stat().st_size
                ),
                "publication_ordering_test_output_sha256": (
                    ordering_test_output_hash
                ),
                "publication_ordering_test_output_size": (
                    ordering_test_output.stat().st_size
                ),
                "schedule_id": "daily",
                "workflow": ".github/workflows/refresh.yml",
                "schedule_last_success_at": "2026-07-25T10:00:00Z",
                "deployment_id": "deploy-1",
                "public_url": (
                    "https://example.invalid/data/result.json?verify=1"
                ),
                "public_http_status": 200,
                "public_response_sha256": result_hash,
                "public_response_size": public_result.stat().st_size,
                "frontend_url": "https://example.invalid/",
                "frontend_http_status": 200,
                "frontend_response_sha256": frontend_hash,
                "frontend_response_size": frontend.stat().st_size,
                "frontend_binding_evidence_sha256": frontend_binding_hash,
                "frontend_binding_evidence_size": (
                    frontend_binding.stat().st_size
                ),
                "frontend_dom_snapshot_sha256": frontend_dom_hash,
                "frontend_dom_snapshot_size": frontend_dom.stat().st_size,
                "public_verified_at": "2026-07-25T10:05:00Z",
            }
            cost = verified_zero_cost()
            cost_capture = write_cost_capture(
                root,
                cost,
                workflow_run_id="run-1",
                release_ci_run_id=None,
            )
            required = [
                "contract",
                "tests",
                "product",
                "cost",
                "collection",
                "freshness",
                "analysis_result",
                "schedule",
                "publication",
                "public_readback",
            ]
            gates = {
                "contract": {
                    "status": "passed",
                    "evidence": [gate_evidence("contract_guard")],
                },
                "tests": {
                    "status": "passed",
                    "evidence": [gate_evidence("test_run")],
                },
                "product": {
                    "status": "passed",
                    "evidence": [gate_evidence("product_check")],
                },
                "cost": {
                    "status": "passed",
                    "evidence": [complete_cost_evidence(cost)],
                },
                "collection": {
                    "status": "passed",
                    "evidence": [
                        gate_evidence(
                            "source_collection",
                            source_manifest_sha256=source_hash,
                            source_manifest_size=source_manifest.stat().st_size,
                            required_source_ids=["primary"],
                            required_source_count=1,
                            failed_required_source_count=0,
                            required_source_receipts=[
                                {
                                    "source_id": "primary",
                                    "role": "required",
                                    "status": "succeeded",
                                    "source_as_of": "2026-07-24",
                                    "expected_source_as_of": "2026-07-24",
                                    "coherent_through": "2026-07-24",
                                    "observed_lag_seconds": 0,
                                    "allowed_lag_seconds": 86400,
                                    "observed_age_seconds": 122400,
                                    "maximum_source_age_seconds": 172800,
                                    "collected_at": "2026-07-25T09:30:00Z",
                                    "artifact_path": "data/raw-primary.json",
                                    "artifact_sha256": source_artifact_hash,
                                    "artifact_size": source_artifact.stat().st_size,
                                }
                            ],
                            optional_source_receipts=[
                                {
                                    "source_id": "secondary",
                                    "role": "optional",
                                    "status": "unavailable",
                                    "reason": "fixture provider unavailable",
                                    "impact": "benchmark omitted",
                                    "fallback_applied": False,
                                }
                            ],
                        )
                    ],
                },
                "freshness": {
                    "status": "passed",
                    "evidence": [
                        gate_evidence(
                            "coherent_cutoff",
                            data_as_of="2026-07-24",
                            coherent_cutoff_policy="required source minimum",
                            publication_state="degraded",
                            cutoff_derivation=(
                                "minimum-required-coherent-through"
                            ),
                            calendar_evaluator="fixture calendar",
                            calendar_evaluated_at=(
                                "2026-07-25T09:40:00Z"
                            ),
                            required_source_freshness=[
                                {
                                    "source_id": "primary",
                                    "source_as_of": "2026-07-24",
                                    "expected_source_as_of": "2026-07-24",
                                    "coherent_through": "2026-07-24",
                                    "observed_lag_seconds": 0,
                                    "allowed_lag_seconds": 86400,
                                    "observed_age_seconds": 122400,
                                    "maximum_source_age_seconds": 172800,
                                }
                            ],
                        )
                    ],
                },
                "analysis_result": {
                    "status": "passed",
                    "evidence": [
                        gate_evidence(
                            "authoritative_analysis",
                            source_manifest_sha256=source_hash,
                            analysis_input_sha256=analysis_input_hash,
                            analysis_input_size=analysis_input.stat().st_size,
                            analysis_input_validation_sha256=(
                                analysis_input_validation_hash
                            ),
                            analysis_input_validation_size=(
                                analysis_input_validation.stat().st_size
                            ),
                            analysis_request_manifest_sha256=(
                                analysis_request_hash
                            ),
                            analysis_request_manifest_size=(
                                analysis_request_manifest.stat().st_size
                            ),
                            result_manifest_sha256=result_manifest_hash,
                            result_manifest_size=result_manifest.stat().st_size,
                            result_artifact_sha256=result_hash,
                            result_artifact_size=artifact.stat().st_size,
                            data_as_of="2026-07-24",
                            run_id="run-1",
                            code_version=code_version,
                            analysis_entrypoint_sha256=(
                                analysis_entrypoint_hash
                            ),
                            config_hash=config_hash,
                            effective_config_hash=config_hash,
                            input_schema_version="1",
                            input_schema_sha256=input_schema_hash,
                            data_schema_version="1",
                            result_schema_version="1",
                            calculated_at="2026-07-25T09:55:00Z",
                        )
                    ],
                },
                "schedule": {
                    "status": "passed",
                    "evidence": [
                        gate_evidence(
                            "workflow_schedule",
                            schedule_id="daily",
                            workflow=".github/workflows/refresh.yml",
                            event="schedule",
                            default_branch="main",
                            head_sha="f" * 40,
                            enabled_on_default_branch=True,
                            last_success_at="2026-07-25T10:00:00Z",
                            conclusion="success",
                            run_id="run-1",
                            run_url="https://example.invalid/run/1",
                            steps_completed=2,
                            workflow_run_evidence_sha256=workflow_run_hash,
                            workflow_file_sha256=workflow_file_hash,
                            job_id="refresh",
                            cost_preflight_step_id="cost-preflight",
                            entrypoint_step_id="collect-and-analyze",
                            workflow_started_at="2026-07-25T09:00:00Z",
                            cost_preflight_completed_at=(
                                "2026-07-25T09:10:00Z"
                            ),
                            entrypoint_started_at="2026-07-25T09:11:00Z",
                        )
                    ],
                },
                "publication": {
                    "status": "passed",
                    "evidence": [
                        gate_evidence(
                            "atomic_publication",
                            published_result_key="result-20260724",
                            publication_state="degraded",
                            result_artifact_sha256=result_hash,
                            deployment_id="deploy-1",
                            monotonic_generation_checked=True,
                            previous_generation=1,
                            candidate_generation=2,
                            previous_public_result_sha256="a" * 64,
                            public_pointer_before_sha256=pointer_before_hash,
                            public_pointer_after_sha256=pointer_after_hash,
                            publication_ordering_evidence_sha256=(
                                ordering_evidence_hash
                            ),
                            publication_ordering_test_output_sha256=(
                                ordering_test_output_hash
                            ),
                            published_at="2026-07-25T10:02:00Z",
                        )
                    ],
                },
                "public_readback": {
                    "status": "passed",
                    "evidence": [
                        gate_evidence(
                            "public_readback",
                            published_result_key="result-20260724",
                            publication_state="degraded",
                            result_artifact_sha256=result_hash,
                            data_as_of="2026-07-24",
                            public_url=(
                                "https://example.invalid/data/result.json?verify=1"
                            ),
                            http_status=200,
                            response_sha256=result_hash,
                            response_size=public_result.stat().st_size,
                            cache_busted=True,
                            frontend_url="https://example.invalid/",
                            frontend_http_status=200,
                            frontend_response_sha256=frontend_hash,
                            frontend_response_size=frontend.stat().st_size,
                            frontend_binding_evidence_sha256=(
                                frontend_binding_hash
                            ),
                            frontend_binding_evidence_size=(
                                frontend_binding.stat().st_size
                            ),
                            frontend_dom_snapshot_sha256=frontend_dom_hash,
                            frontend_dom_snapshot_size=(
                                frontend_dom.stat().st_size
                            ),
                            verified_at="2026-07-25T10:05:00Z",
                        )
                    ],
                },
            }
            receipt = root / "receipt.json"
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_id": "sample",
                        "objective": "Ship a verified result",
                        "scope": scope,
                        "cost_authority": cost,
                        "completed_at": "2026-07-25T12:01:00Z",
                        "required_gates": required,
                        "gates": gates,
                        "automation_identity": identity,
                        "result_identity": {
                            "project_id": "sample",
                            "run_id": "run-1",
                            "data_as_of": "2026-07-24",
                            "code_version": code_version,
                            "data_manifest_sha256": source_hash,
                            "analysis_input_sha256": analysis_input_hash,
                            "analysis_input_validation_sha256": (
                                analysis_input_validation_hash
                            ),
                            "analysis_entrypoint_sha256": (
                                analysis_entrypoint_hash
                            ),
                            "config_hash": config_hash,
                            "effective_config_hash": config_hash,
                            "input_schema_version": "1",
                            "data_schema_version": "1",
                            "result_schema_version": "1",
                            "artifact_sha256": result_hash,
                        },
                    }
                ),
                encoding="utf-8",
            )
            script = str(SHARED / "scripts" / "validate_evidence.py")
            validation_args = (
                sys.executable,
                script,
                "--project-root",
                str(root),
                "--manifest",
                str(manifest),
                "--goal-state",
                str(goal),
                "--workflow-run-evidence",
                str(workflow_run),
                "--source-manifest",
                str(source_manifest),
                "--analysis-input",
                str(analysis_input),
                "--analysis-input-validation",
                str(analysis_input_validation),
                "--analysis-request-manifest",
                str(analysis_request_manifest),
                "--result-manifest",
                str(result_manifest),
                "--public-pointer-before",
                str(pointer_before),
                "--public-pointer-after",
                str(pointer_after),
                "--publication-ordering-evidence",
                str(ordering_evidence),
                "--publication-ordering-test-output",
                str(ordering_test_output),
                "--result-artifact",
                str(artifact),
                "--public-result-body",
                str(public_result),
                "--frontend-body",
                str(frontend),
                "--frontend-binding-evidence",
                str(frontend_binding),
                "--frontend-dom-snapshot",
                str(frontend_dom),
                "--cost-evidence",
                str(cost_capture),
                str(receipt),
            )
            passed = run(*validation_args)
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)

            valid_payload = json.loads(receipt.read_text(encoding="utf-8"))
            valid_workflow_run = json.loads(
                workflow_run.read_text(encoding="utf-8")
            )
            swallowed_preflight = json.loads(json.dumps(valid_workflow_run))
            swallowed_preflight["jobs"][0]["steps"][0][
                "outcome"
            ] = "failure"
            workflow_run.write_text(
                json.dumps(swallowed_preflight, sort_keys=True),
                encoding="utf-8",
            )
            swallowed_hash = hashlib.sha256(
                workflow_run.read_bytes()
            ).hexdigest()
            swallowed_payload = json.loads(json.dumps(valid_payload))
            swallowed_payload["automation_identity"][
                "workflow_run_evidence_sha256"
            ] = swallowed_hash
            swallowed_payload["gates"]["schedule"]["evidence"][0][
                "workflow_run_evidence_sha256"
            ] = swallowed_hash
            receipt.write_text(
                json.dumps(swallowed_payload),
                encoding="utf-8",
            )
            swallowed = run(*validation_args)
            self.assertNotEqual(swallowed.returncode, 0)
            self.assertIn(
                "did not have successful outcome and conclusion",
                swallowed.stdout,
            )
            workflow_run.write_text(
                json.dumps(valid_workflow_run, sort_keys=True),
                encoding="utf-8",
            )
            receipt.write_text(json.dumps(valid_payload), encoding="utf-8")

            stale_payload = json.loads(json.dumps(valid_payload))
            stale_receipt = stale_payload["gates"]["collection"]["evidence"][0][
                "required_source_receipts"
            ][0]
            stale_receipt["source_as_of"] = "2026-07-20"
            stale_receipt["coherent_through"] = "2026-07-20"
            stale_receipt["observed_lag_seconds"] = 345600
            stale_receipt["observed_age_seconds"] = 468000
            stale_row = stale_payload["gates"]["freshness"]["evidence"][0][
                "required_source_freshness"
            ][0]
            stale_row["source_as_of"] = "2026-07-20"
            stale_row["coherent_through"] = "2026-07-20"
            stale_row["observed_lag_seconds"] = 345600
            stale_row["observed_age_seconds"] = 468000
            receipt.write_text(json.dumps(stale_payload), encoding="utf-8")
            stale = run(*validation_args)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("is stale:", stale.stdout)
            receipt.write_text(json.dumps(valid_payload), encoding="utf-8")

            forged_expected = json.loads(json.dumps(valid_payload))
            forged_receipt = forged_expected["gates"]["collection"][
                "evidence"
            ][0]["required_source_receipts"][0]
            forged_row = forged_expected["gates"]["freshness"]["evidence"][0][
                "required_source_freshness"
            ][0]
            for source in (forged_receipt, forged_row):
                source["source_as_of"] = "2025-01-01"
                source["expected_source_as_of"] = "2025-01-01"
                source["coherent_through"] = "2025-01-01"
                source["observed_lag_seconds"] = 0
                source["observed_age_seconds"] = 0
            receipt.write_text(json.dumps(forged_expected), encoding="utf-8")
            forged_latest = run(*validation_args)
            self.assertNotEqual(forged_latest.returncode, 0)
            self.assertIn("is too old for this run", forged_latest.stdout)
            receipt.write_text(json.dumps(valid_payload), encoding="utf-8")

            fail_closed_manifest = json.loads(
                manifest.read_text(encoding="utf-8")
            )
            fail_closed_manifest["data"]["sources"][1][
                "fallback_policy"
            ] = "fail-closed"
            manifest.write_text(
                json.dumps(fail_closed_manifest),
                encoding="utf-8",
            )
            fail_closed_optional = run(*validation_args)
            self.assertNotEqual(fail_closed_optional.returncode, 0)
            self.assertIn(
                "fallback_policy is fail-closed",
                fail_closed_optional.stdout,
            )
            manifest.write_text(json.dumps(manifest_value), encoding="utf-8")

            wrong_code = json.loads(json.dumps(valid_payload))
            wrong_code["automation_identity"][
                "analysis_code_version"
            ] = "e" * 40
            receipt.write_text(json.dumps(wrong_code), encoding="utf-8")
            code_mismatch = run(*validation_args)
            self.assertNotEqual(code_mismatch.returncode, 0)
            self.assertIn(
                "analysis_code_version must equal workflow head_sha",
                code_mismatch.stdout,
            )
            receipt.write_text(json.dumps(valid_payload), encoding="utf-8")

            valid_analysis_input_bytes = analysis_input.read_bytes()
            analysis_input.write_bytes(b"{not-json")
            malformed_input = run(*validation_args)
            self.assertNotEqual(malformed_input.returncode, 0)
            self.assertIn("analysis input is not valid JSON", malformed_input.stdout)
            analysis_input.write_bytes(valid_analysis_input_bytes)

            missing_optional = json.loads(json.dumps(valid_payload))
            missing_optional["gates"]["collection"]["evidence"][0][
                "optional_source_receipts"
            ] = []
            receipt.write_text(json.dumps(missing_optional), encoding="utf-8")
            omitted_optional = run(*validation_args)
            self.assertNotEqual(omitted_optional.returncode, 0)
            self.assertIn(
                "optional source receipts do not cover",
                omitted_optional.stdout,
            )

            valid_artifact_bytes = artifact.read_bytes()
            artifact.write_bytes(
                b'{"project_id":"other-project","run_id":"other-run"}\n'
            )
            wrong_artifact_hash = hashlib.sha256(
                artifact.read_bytes()
            ).hexdigest()
            wrong_artifact_payload = json.loads(json.dumps(valid_payload))
            wrong_artifact_payload["automation_identity"][
                "result_artifact_sha256"
            ] = wrong_artifact_hash
            wrong_artifact_payload["automation_identity"][
                "result_artifact_size"
            ] = artifact.stat().st_size
            wrong_artifact_payload["result_identity"][
                "artifact_sha256"
            ] = wrong_artifact_hash
            receipt.write_text(
                json.dumps(wrong_artifact_payload),
                encoding="utf-8",
            )
            wrong_artifact = run(*validation_args)
            self.assertNotEqual(wrong_artifact.returncode, 0)
            self.assertIn(
                "result artifact identity assertion",
                wrong_artifact.stdout,
            )
            artifact.write_bytes(valid_artifact_bytes)

            receipt.write_text(json.dumps(valid_payload), encoding="utf-8")
            valid_request_bytes = analysis_request_manifest.read_bytes()
            wrong_request = json.loads(valid_request_bytes.decode("utf-8"))
            wrong_request["requested_config"] = {"period": 42}
            analysis_request_manifest.write_text(
                json.dumps(wrong_request, sort_keys=True),
                encoding="utf-8",
            )
            wrong_config = run(*validation_args)
            self.assertNotEqual(wrong_config.returncode, 0)
            self.assertIn(
                "analysis request requested_config hash mismatch",
                wrong_config.stdout,
            )
            analysis_request_manifest.write_bytes(valid_request_bytes)

            valid_binding_bytes = frontend_binding.read_bytes()
            detached_binding = json.loads(
                valid_binding_bytes.decode("utf-8")
            )
            detached_binding["binding_status"] = "detached"
            frontend_binding.write_text(
                json.dumps(detached_binding, sort_keys=True),
                encoding="utf-8",
            )
            detached_binding_hash = hashlib.sha256(
                frontend_binding.read_bytes()
            ).hexdigest()
            detached_payload = json.loads(json.dumps(valid_payload))
            detached_payload["automation_identity"][
                "frontend_binding_evidence_sha256"
            ] = detached_binding_hash
            detached_payload["gates"]["public_readback"]["evidence"][0][
                "frontend_binding_evidence_sha256"
            ] = detached_binding_hash
            receipt.write_text(json.dumps(detached_payload), encoding="utf-8")
            detached = run(*validation_args)
            self.assertNotEqual(detached.returncode, 0)
            self.assertIn(
                "frontend binding evidence binding_status mismatch",
                detached.stdout,
            )
            frontend_binding.write_bytes(valid_binding_bytes)

            receipt.write_text(json.dumps(valid_payload), encoding="utf-8")
            payload = json.loads(json.dumps(valid_payload))
            payload["gates"]["public_readback"]["evidence"][0][
                "result_artifact_sha256"
            ] = "c" * 64
            receipt.write_text(json.dumps(payload), encoding="utf-8")
            failed = run(*validation_args)
            self.assertNotEqual(failed.returncode, 0)

            receipt.write_text(json.dumps(valid_payload), encoding="utf-8")
            valid_manifest = json.loads(manifest.read_text(encoding="utf-8"))
            disabled_manifest = json.loads(json.dumps(valid_manifest))
            disabled_manifest["automation"]["schedules"][0][
                "enabled_on_default_branch"
            ] = False
            manifest.write_text(json.dumps(disabled_manifest), encoding="utf-8")
            disabled = run(*validation_args)
            self.assertNotEqual(disabled.returncode, 0)
            self.assertIn("not enabled on default branch", disabled.stdout)
            manifest.write_text(json.dumps(valid_manifest), encoding="utf-8")

            manual_run = json.loads(workflow_run.read_text(encoding="utf-8"))
            manual_run["event"] = "manual_dispatch"
            workflow_run.write_text(
                json.dumps(manual_run, sort_keys=True),
                encoding="utf-8",
            )
            manual_hash = hashlib.sha256(workflow_run.read_bytes()).hexdigest()
            manual_payload = json.loads(json.dumps(valid_payload))
            manual_payload["automation_identity"][
                "workflow_run_evidence_sha256"
            ] = manual_hash
            manual_payload["gates"]["schedule"]["evidence"][0][
                "workflow_run_evidence_sha256"
            ] = manual_hash
            manual_payload["gates"]["schedule"]["evidence"][0][
                "event"
            ] = "manual_dispatch"
            receipt.write_text(json.dumps(manual_payload), encoding="utf-8")
            manual = run(*validation_args)
            self.assertNotEqual(manual.returncode, 0)

            workflow_run.write_text(
                json.dumps(
                    {
                        "run_id": "run-1",
                        "run_url": "https://example.invalid/run/1",
                        "event": "schedule",
                        "default_branch": "main",
                        "head_sha": "f" * 40,
                        "started_at": "2026-07-25T09:00:00Z",
                        "conclusion": "success",
                        "steps_completed": 2,
                        "workflow_file_sha256": workflow_file_hash,
                        "jobs": [
                            {
                                "job_id": "refresh",
                                "conclusion": "success",
                                "steps": [
                                    {
                                        "step_id": "cost-preflight",
                                        "outcome": "success",
                                        "conclusion": "success",
                                        "completed_at": (
                                            "2026-07-25T09:10:00Z"
                                        ),
                                    },
                                    {
                                        "step_id": "collect-and-analyze",
                                        "outcome": "success",
                                        "conclusion": "success",
                                        "started_at": (
                                            "2026-07-25T09:11:00Z"
                                        ),
                                    },
                                ],
                            }
                        ],
                        "completed_at": "2026-07-25T10:00:00Z",
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            future_payload = json.loads(json.dumps(valid_payload))
            future_payload["automation_identity"][
                "public_verified_at"
            ] = "2099-01-01T00:00:00Z"
            future_payload["gates"]["public_readback"]["evidence"][0][
                "verified_at"
            ] = "2099-01-01T00:00:00Z"
            receipt.write_text(json.dumps(future_payload), encoding="utf-8")
            future = run(*validation_args)
            self.assertNotEqual(future.returncode, 0)
            self.assertIn("after receipt completion", future.stdout)

            unlimited_payload = json.loads(json.dumps(valid_payload))
            action = unlimited_payload["cost_authority"]["actions"][0]
            action["numeric_ceilings"][
                "maximum_retry_attempts"
            ] = "unlimited"
            action_without_hash = dict(action)
            action_without_hash.pop("canonical_action_envelope_sha256")
            action["canonical_action_envelope_sha256"] = canonical_sha256(
                action_without_hash
            )
            actions = unlimited_payload["cost_authority"]["actions"]
            actions_sha = canonical_sha256(actions)
            unlimited_payload["cost_authority"]["canonical_actions_envelope"][
                "sha256"
            ] = actions_sha
            unlimited_payload["gates"]["cost"]["evidence"][0][
                "canonical_actions_envelope_sha256"
            ] = actions_sha
            receipt.write_text(json.dumps(unlimited_payload), encoding="utf-8")
            unlimited = run(*validation_args)
            self.assertNotEqual(unlimited.returncode, 0)

    def test_required_automation_cannot_be_downgraded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, goal, scope = write_context(root)
            cost = local_cost()
            receipt = root / "receipt.json"
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_id": "sample",
                        "objective": "Ship a verified result",
                        "scope": scope,
                        "cost_authority": cost,
                        "completed_at": "2026-07-25T12:01:00Z",
                        "required_gates": [
                            "contract",
                            "tests",
                            "product",
                            "cost",
                        ],
                        "gates": {
                            "contract": {
                                "status": "passed",
                                "evidence": [gate_evidence("contract_guard")],
                            },
                            "tests": {
                                "status": "passed",
                                "evidence": [gate_evidence("test_run")],
                            },
                            "product": {
                                "status": "passed",
                                "evidence": [gate_evidence("product_check")],
                            },
                            "cost": {
                                "status": "passed",
                                "evidence": [complete_cost_evidence(cost)],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = run(
                sys.executable,
                str(SHARED / "scripts" / "validate_evidence.py"),
                "--require-automation",
                "--project-root",
                str(root),
                "--manifest",
                str(manifest),
                "--goal-state",
                str(goal),
                str(receipt),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "--require-automation requires automation scope",
                result.stdout,
            )

    def test_remote_release_requires_identity_bytes_and_zero_cost_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, goal, scope = write_context(root, released=True)
            result_body = root / "captures" / "release-result.json"
            result_body.parent.mkdir()
            result_body.write_bytes(b'{"project_id":"sample","released":true}\n')
            result_hash = hashlib.sha256(result_body.read_bytes()).hexdigest()
            frontend = root / "captures" / "release-index.html"
            frontend.write_bytes(b"<html><body>released</body></html>\n")
            frontend_hash = hashlib.sha256(frontend.read_bytes()).hexdigest()
            release_run = root / "captures" / "release-run.json"
            release_run.write_text(
                json.dumps(
                    {
                        "repository": "example/sample",
                        "account": "example",
                        "branch": "main",
                        "commit_sha": "a" * 40,
                        "ci_run_id": "ci-1",
                        "ci_run_url": "https://example.invalid/actions/runs/1",
                        "conclusion": "success",
                        "deployment_id": "deploy-1",
                        "steps_completed": 2,
                        "cost_preflight_completed_at": (
                            "2026-07-25T09:10:00Z"
                        ),
                        "remote_write_started_at": "2026-07-25T09:11:00Z",
                        "jobs": [
                            {
                                "job_id": "release",
                                "conclusion": "success",
                                "steps": [
                                    {
                                        "step_id": "cost-preflight",
                                        "outcome": "success",
                                        "conclusion": "success",
                                        "completed_at": (
                                            "2026-07-25T09:10:00Z"
                                        ),
                                    },
                                    {
                                        "step_id": "remote-write",
                                        "outcome": "success",
                                        "conclusion": "success",
                                        "started_at": (
                                            "2026-07-25T09:11:00Z"
                                        ),
                                    },
                                ],
                            }
                        ],
                        "completed_at": "2026-07-25T10:00:00Z",
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            release_run_hash = hashlib.sha256(
                release_run.read_bytes()
            ).hexdigest()
            cost = verified_release_cost()
            cost_capture = write_cost_capture(
                root,
                cost,
                workflow_run_id=None,
                release_ci_run_id="ci-1",
            )
            identity = {
                "repository": "example/sample",
                "account": "example",
                "branch": "main",
                "commit_sha": "a" * 40,
                "ci_run_id": "ci-1",
                "ci_run_url": "https://example.invalid/actions/runs/1",
                "release_run_evidence_sha256": release_run_hash,
                "job_id": "release",
                "steps_completed": 2,
                "cost_preflight_step_id": "cost-preflight",
                "cost_preflight_completed_at": "2026-07-25T09:10:00Z",
                "remote_write_step_id": "remote-write",
                "remote_write_started_at": "2026-07-25T09:11:00Z",
                "run_completed_at": "2026-07-25T10:00:00Z",
                "deployment_id": "deploy-1",
                "production_url": "https://example.invalid/",
                "frontend_response_sha256": frontend_hash,
                "frontend_response_size": frontend.stat().st_size,
                "authoritative_result_url": (
                    "https://example.invalid/data/result.json"
                ),
                "authoritative_result_sha256": result_hash,
                "authoritative_result_size": result_body.stat().st_size,
                "public_verified_at": "2026-07-25T10:05:00Z",
            }
            receipt = root / "release-receipt.json"
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_id": "sample",
                        "objective": "Ship a verified result",
                        "scope": scope,
                        "cost_authority": cost,
                        "completed_at": "2026-07-25T12:01:00Z",
                        "required_gates": [
                            "contract",
                            "tests",
                            "product",
                            "cost",
                            "release",
                            "public_readback",
                        ],
                        "gates": {
                            "contract": {
                                "status": "passed",
                                "evidence": [gate_evidence("contract_guard")],
                            },
                            "tests": {
                                "status": "passed",
                                "evidence": [gate_evidence("test_run")],
                            },
                            "product": {
                                "status": "passed",
                                "evidence": [gate_evidence("product_check")],
                            },
                            "cost": {
                                "status": "passed",
                                "evidence": [complete_cost_evidence(cost)],
                            },
                            "release": {
                                "status": "passed",
                                "evidence": [
                                    gate_evidence(
                                        "github_release",
                                        repository="example/sample",
                                        account="example",
                                        branch="main",
                                        commit_sha="a" * 40,
                                        ci_run_id="ci-1",
                                        ci_run_url=(
                                            "https://example.invalid/actions/runs/1"
                                        ),
                                        deployment_id="deploy-1",
                                        production_url=(
                                            "https://example.invalid/"
                                        ),
                                        conclusion="success",
                                        release_run_evidence_sha256=(
                                            release_run_hash
                                        ),
                                        job_id="release",
                                        steps_completed=2,
                                        cost_preflight_step_id=(
                                            "cost-preflight"
                                        ),
                                        cost_preflight_completed_at=(
                                            "2026-07-25T09:10:00Z"
                                        ),
                                        remote_write_step_id="remote-write",
                                        remote_write_started_at=(
                                            "2026-07-25T09:11:00Z"
                                        ),
                                        run_completed_at=(
                                            "2026-07-25T10:00:00Z"
                                        ),
                                    )
                                ],
                            },
                            "public_readback": {
                                "status": "passed",
                                "evidence": [
                                    gate_evidence(
                                        "public_readback",
                                        frontend_url=(
                                            "https://example.invalid/"
                                        ),
                                        frontend_http_status=200,
                                        frontend_response_sha256=frontend_hash,
                                        frontend_response_size=(
                                            frontend.stat().st_size
                                        ),
                                        authoritative_result_url=(
                                            "https://example.invalid/data/result.json"
                                        ),
                                        authoritative_result_http_status=200,
                                        authoritative_result_sha256=result_hash,
                                        authoritative_result_size=(
                                            result_body.stat().st_size
                                        ),
                                        cache_busted=True,
                                        verified_at=(
                                            "2026-07-25T10:05:00Z"
                                        ),
                                    )
                                ],
                            },
                        },
                        "release_identity": identity,
                    }
                ),
                encoding="utf-8",
            )
            command = (
                sys.executable,
                str(SHARED / "scripts" / "validate_evidence.py"),
                "--require-release",
                "--project-root",
                str(root),
                "--manifest",
                str(manifest),
                "--goal-state",
                str(goal),
                "--release-run-evidence",
                str(release_run),
                "--public-result-body",
                str(result_body),
                "--frontend-body",
                str(frontend),
                "--cost-evidence",
                str(cost_capture),
                str(receipt),
            )
            passed = run(*command)
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)

            valid_receipt_bytes = receipt.read_bytes()
            valid_release_run = json.loads(
                release_run.read_text(encoding="utf-8")
            )
            failed_step_run = json.loads(json.dumps(valid_release_run))
            failed_step_run["jobs"][0]["steps"][0]["outcome"] = "failure"
            release_run.write_text(
                json.dumps(failed_step_run, sort_keys=True),
                encoding="utf-8",
            )
            failed_step_hash = hashlib.sha256(
                release_run.read_bytes()
            ).hexdigest()
            failed_step_receipt = json.loads(valid_receipt_bytes)
            failed_step_receipt["release_identity"][
                "release_run_evidence_sha256"
            ] = failed_step_hash
            failed_step_receipt["gates"]["release"]["evidence"][0][
                "release_run_evidence_sha256"
            ] = failed_step_hash
            receipt.write_text(
                json.dumps(failed_step_receipt),
                encoding="utf-8",
            )
            failed_preflight_step = run(*command)
            self.assertNotEqual(failed_preflight_step.returncode, 0)
            self.assertIn(
                "release cost preflight step success",
                failed_preflight_step.stdout,
            )
            release_run.write_text(
                json.dumps(valid_release_run, sort_keys=True),
                encoding="utf-8",
            )
            receipt.write_bytes(valid_receipt_bytes)

            valid_manifest = json.loads(manifest.read_text(encoding="utf-8"))
            wrong_target = json.loads(json.dumps(valid_manifest))
            wrong_target["project"]["repository"] = "someone-else/other"
            manifest.write_text(json.dumps(wrong_target), encoding="utf-8")
            wrong_repository = run(*command)
            self.assertNotEqual(wrong_repository.returncode, 0)
            self.assertIn(
                "release repository does not match manifest",
                wrong_repository.stdout,
            )
            manifest.write_text(json.dumps(valid_manifest), encoding="utf-8")

            payload = json.loads(receipt.read_text(encoding="utf-8"))
            payload["release_identity"]["commit_sha"] = "b" * 40
            receipt.write_text(json.dumps(payload), encoding="utf-8")
            failed = run(*command)
            self.assertNotEqual(failed.returncode, 0)

            payload["release_identity"]["commit_sha"] = "a" * 40
            local = local_cost()
            payload["cost_authority"] = local
            payload["gates"]["cost"]["evidence"] = [
                complete_cost_evidence(local)
            ]
            receipt.write_text(json.dumps(payload), encoding="utf-8")
            unverified_remote = run(*command)
            self.assertNotEqual(unverified_remote.returncode, 0)
            self.assertIn(
                "remote/provider scope cannot use no_billable_action",
                unverified_remote.stdout,
            )

    def test_installer_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run(
                sys.executable,
                str(ROOT / "install.py"),
                "--target",
                directory,
                "--dry-run",
                "--skip-tests",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("quant-plan", result.stdout)
            self.assertIn("quant-goal", result.stdout)
            self.assertIn("quant-developer", result.stdout)
            blocked = run(
                sys.executable,
                str(ROOT / "install.py"),
                "--target",
                directory,
                "--skip-tests",
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("only with --dry-run", blocked.stderr)

    def test_installer_update_hash_parity_and_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "skills"
            with mock.patch.object(
                suite_installer,
                "validate_source",
            ) as validate_source:
                with mock.patch.object(
                    sys,
                    "argv",
                    ["install.py", "--target", str(target)],
                ):
                    self.assertEqual(suite_installer.main(), 0)
                validate_source.assert_called_once_with(
                    run_tests=True,
                    include_legacy=False,
                )
            integrity = (
                target
                / "quant-research-shared"
                / "scripts"
                / "validate_installed.py"
            )
            verified = run(sys.executable, str(integrity))
            self.assertEqual(
                verified.returncode,
                0,
                verified.stdout + verified.stderr,
            )
            installed_skill = target / "quant-plan" / "SKILL.md"
            installed_skill.write_text("corrupt\n", encoding="utf-8")
            corrupted = run(sys.executable, str(integrity))
            self.assertNotEqual(corrupted.returncode, 0)

            with mock.patch.object(
                suite_installer,
                "validate_source",
            ) as validate_source:
                with mock.patch.object(
                    sys,
                    "argv",
                    ["install.py", "--target", str(target), "--update"],
                ):
                    self.assertEqual(suite_installer.main(), 0)
                validate_source.assert_called_once_with(
                    run_tests=True,
                    include_legacy=False,
                )
            source_skill = ROOT / "skills" / "quant-plan" / "SKILL.md"
            self.assertEqual(
                installed_skill.read_bytes(),
                source_skill.read_bytes(),
            )
            self.assertTrue(list(target.glob(".quant-plan.backup-pointer-*")))
            self.assertTrue(list((base / "skill-backups").glob("*")))
            repaired = run(sys.executable, str(integrity))
            self.assertEqual(
                repaired.returncode,
                0,
                repaired.stdout + repaired.stderr,
            )
            self.assertFalse(list(target.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
