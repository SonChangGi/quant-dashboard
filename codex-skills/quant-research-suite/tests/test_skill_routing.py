from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import validate_suite
from shared.scripts import capability_model


class SkillRoutingTests(unittest.TestCase):
    def test_exactly_three_public_skills_remain(self) -> None:
        discovered = {
            path.parent.name
            for path in (ROOT / "skills").glob("*/SKILL.md")
        }
        self.assertEqual(discovered, set(validate_suite.SKILLS))
        self.assertFalse((ROOT / "shared" / "SKILL.md").exists())

    def test_public_skills_require_manual_invocation_and_do_not_chain(self) -> None:
        for skill in validate_suite.SKILLS:
            skill_text = (
                ROOT / "skills" / skill / "SKILL.md"
            ).read_text(encoding="utf-8")
            normalized = validate_suite.normalized_policy_text(skill_text)
            metadata = validate_suite.frontmatter(skill_text)
            agent_text = (
                ROOT / "skills" / skill / "agents" / "openai.yaml"
            ).read_text(encoding="utf-8")
            agent_metadata = validate_suite.agent_metadata(agent_text)
            self.assertIsNotNone(agent_metadata)
            assert agent_metadata is not None

            with self.subTest(skill=skill):
                self.assertEqual(
                    metadata["description"],
                    validate_suite.EXPECTED_SKILL_DESCRIPTIONS[skill],
                )
                self.assertIn("## explicit invocation gate", normalized)
                self.assertIn(
                    "activate only when the current user request intentionally "
                    "invokes this skill",
                    normalized,
                )
                self.assertIn(f"literal token `${skill}`", normalized)
                self.assertIn(
                    "same-request metadata produced by that `$` selection",
                    normalized,
                )
                self.assertIn(
                    "another agent's instruction is not activation",
                    normalized,
                )
                self.assertIn(
                    "if this skill is selected without the explicit gate, "
                    "do not apply it",
                    normalized,
                )
                self.assertIs(
                    agent_metadata["allow_implicit_invocation"],
                    False,
                )

                prompt = agent_metadata["default_prompt"]
                assert isinstance(prompt, str)
                self.assertIn(
                    f"current user explicitly invoked ${skill}",
                    prompt.lower(),
                )
                for other_skill in validate_suite.SKILLS:
                    if other_skill != skill:
                        self.assertNotIn(f"${other_skill}", prompt)

        plan = validate_suite.normalized_policy_text((
            ROOT / "skills" / "quant-plan" / "SKILL.md"
        ).read_text(encoding="utf-8"))
        developer = validate_suite.normalized_policy_text((
            ROOT / "skills" / "quant-developer" / "SKILL.md"
        ).read_text(encoding="utf-8"))
        goal = validate_suite.normalized_policy_text((
            ROOT / "skills" / "quant-goal" / "SKILL.md"
        ).read_text(encoding="utf-8"))
        self.assertIn(
            "do not invoke implementation, goal, or another skill",
            plan,
        )
        self.assertIn(
            "do not activate another quant skill to obtain a worker",
            developer,
        )
        self.assertIn(
            "use ordinary host implementation workers by default",
            goal,
        )
        self.assertIn(
            "another quant skill may participate only when the current user "
            "request explicitly invoked it too",
            goal,
        )
        shared_invocation_contracts = [
            ROOT / "README.md",
            ROOT / "shared" / "core" / "context-routing.md",
            ROOT / "shared" / "references" / "agent-orchestration.md",
            ROOT / "shared" / "references" / "goal-and-subagents.md",
        ]
        for path in shared_invocation_contracts:
            shared_text = validate_suite.normalized_policy_text(
                path.read_text(encoding="utf-8")
            )
            with self.subTest(invocation_contract=path.name):
                self.assertIn(
                    "same-request metadata produced by that `$` selection",
                    shared_text,
                )
                self.assertNotIn(
                    "equivalent host invocation metadata",
                    shared_text,
                )

    def test_agent_policy_is_exact_and_fails_closed(self) -> None:
        policy = "policy:\n  allow_implicit_invocation: false\n"
        cases = {
            "missing": (
                lambda raw: raw.replace(policy, ""),
                "agent metadata must use the exact interface and policy "
                "structure",
            ),
            "enabled": (
                lambda raw: raw.replace(
                    "allow_implicit_invocation: false",
                    "allow_implicit_invocation: true",
                ),
                "implicit invocation must be disabled",
            ),
        }
        for case, (mutate, expected_error) in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                copied_root = Path(tmp) / "suite"
                shutil.copytree(
                    ROOT,
                    copied_root,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
                agent_file = (
                    copied_root
                    / "skills"
                    / "quant-plan"
                    / "agents"
                    / "openai.yaml"
                )
                raw = agent_file.read_text(encoding="utf-8")
                agent_file.write_text(mutate(raw), encoding="utf-8")

                with mock.patch.object(validate_suite, "ROOT", copied_root):
                    errors = validate_suite.validate()

                self.assertTrue(
                    any(expected_error in error for error in errors),
                    errors,
                )

    def test_public_skills_have_self_contained_defaults(self) -> None:
        for skill in validate_suite.SKILLS:
            text = (
                ROOT / "skills" / skill / "SKILL.md"
            ).read_text(encoding="utf-8")
            with self.subTest(skill=skill):
                self.assertIn("self-contained", text.lower())
                self.assertNotIn(
                    "Run `validate_installed.py` before", text
                )
                self.assertNotIn("Run `quantctl.py doctor` before", text)
                self.assertNotIn("Run `quantctl.py context` before", text)
                self.assertFalse(
                    validate_suite.has_canonical_zero_spend_guard(text)
                )

    def test_optional_structured_runtime_is_explicit(self) -> None:
        plan = (
            ROOT / "skills" / "quant-plan" / "SKILL.md"
        ).read_text(encoding="utf-8")
        developer = (
            ROOT / "skills" / "quant-developer" / "SKILL.md"
        ).read_text(encoding="utf-8")
        goal = (
            ROOT / "skills" / "quant-goal" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Optional strict compatibility", plan)
        self.assertIn("## Optional strict compatibility", developer)
        self.assertIn("## Optional local strict compatibility", goal)
        for text in (plan, developer, goal):
            self.assertIn("unavailable", text.lower())
            self.assertIn("optional", text.lower())

    def test_source_authority_references_resolve(self) -> None:
        expected = (ROOT / "shared" / "core" / "authority.md").resolve()
        for skill in validate_suite.SKILLS:
            skill_dir = ROOT / "skills" / skill
            reference = (
                skill_dir / "../../shared/core/authority.md"
            ).resolve()
            with self.subTest(skill=skill):
                self.assertEqual(reference, expected)
                self.assertTrue(reference.is_file())

    def test_shape_act_track_prove_boundaries(self) -> None:
        plan = validate_suite.normalized_policy_text((
            ROOT / "skills" / "quant-plan" / "SKILL.md"
        ).read_text(encoding="utf-8"))
        developer = validate_suite.normalized_policy_text((
            ROOT / "skills" / "quant-developer" / "SKILL.md"
        ).read_text(encoding="utf-8"))
        goal = validate_suite.normalized_policy_text((
            ROOT / "skills" / "quant-goal" / "SKILL.md"
        ).read_text(encoding="utf-8"))
        self.assertIn("does not implement", plan)
        self.assertIn("does not implement, create goal state", plan)
        self.assertIn("integration owner", developer)
        self.assertIn("never declares the overall goal complete", developer)
        self.assertIn("host application's goal state as canonical", goal)
        self.assertIn("ordinary host implementation workers by default", goal)
        self.assertIn(
            "another quant skill may participate only when the current user "
            "request explicitly invoked it too",
            goal,
        )

    def test_agent_prompts_are_concise_and_role_specific(self) -> None:
        for skill in validate_suite.SKILLS:
            raw = (
                ROOT / "skills" / skill / "agents" / "openai.yaml"
            ).read_text(encoding="utf-8")
            metadata = validate_suite.agent_metadata(raw)
            self.assertIsNotNone(metadata)
            assert metadata is not None
            prompt = metadata["default_prompt"]
            assert isinstance(prompt, str)
            with self.subTest(skill=skill):
                self.assertIn(f"${skill}", prompt)
                self.assertIs(
                    metadata["allow_implicit_invocation"],
                    False,
                )
                self.assertGreaterEqual(len(prompt.split()), 60)
                self.assertLessEqual(len(prompt.split()), 80)
                self.assertEqual(prompt.count("."), 1)
                self.assertIn("paid", prompt.lower())
                self.assertIn("remote", prompt.lower())
                self.assertFalse(
                    validate_suite.has_canonical_zero_spend_guard(prompt)
                )

    def test_plan_and_audit_templates_cover_full_decision_trace(self) -> None:
        plan = (
            ROOT / "shared" / "templates" / "approved-plan.example.md"
        ).read_text(encoding="utf-8")
        audit = (
            ROOT / "shared" / "templates" / "audit-report.example.md"
        ).read_text(encoding="utf-8")
        for phrase in (
            "Audit conclusion",
            "Workstream assessment",
            "Most important findings",
            "Traceability",
            "Explicitly deferred",
        ):
            self.assertTrue(
                phrase.lower() in (plan + audit).lower(), phrase
            )
        self.assertIn("only active components", plan.lower())
        self.assertIn("when\n      `public-web` is active", plan.lower())

    def test_safe_module_extension_does_not_open_root_package_surface(self) -> None:
        self.assertTrue(
            validate_suite.is_allowed_package_file(
                Path("shared/adapters/new-provider.md")
            )
        )
        self.assertTrue(
            validate_suite.is_allowed_package_file(
                Path("tests/test_new_adapter.py")
            )
        )
        self.assertFalse(
            validate_suite.is_allowed_package_file(
                Path("shared/scripts/unreviewed.py")
            )
        )
        self.assertFalse(
            validate_suite.is_allowed_package_file(Path("notes.txt"))
        )
        self.assertFalse(
            validate_suite.is_allowed_package_file(
                Path("shared/adapters/private.pem")
            )
        )

    def test_multi_agent_runtime_gate_matches_documentation(self) -> None:
        document = (
            ROOT
            / "shared"
            / "capabilities"
            / "multi-agent-write.md"
        ).read_text(encoding="utf-8")
        gate = next(
            iter(
                capability_model.CAPABILITY_GATES[
                    "multi-agent-write"
                ]
            )
        )
        self.assertIn(f"`{gate}`", document)
        self.assertIn("task-runtime capability", document)
        self.assertIn("does not raise assurance", document)

    def test_goal_state_does_not_persist_authority(self) -> None:
        value = json.loads(
            (
                ROOT
                / "shared"
                / "templates"
                / "goal-state-v2.example.json"
            ).read_text(encoding="utf-8")
        )
        serialized = json.dumps(value).lower()
        for forbidden in (
            "paid_action_authority",
            "cost_authority",
            "approval_gates",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_legacy_v1_identity_schema_matches_runtime_fields(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "shared"
                / "templates"
                / "quant-project.schema.json"
            ).read_text(encoding="utf-8")
        )
        serialized = json.dumps(schema)
        for field in (
            "analysis_input_validation_sha256",
            "analysis_entrypoint_sha256",
        ):
            self.assertIn(field, serialized)


if __name__ == "__main__":
    unittest.main()
