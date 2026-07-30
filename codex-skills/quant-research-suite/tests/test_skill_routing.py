from __future__ import annotations

import json
import re
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


EXPECTED_SKILLS = (
    "quant-plan",
    "quant-goal",
    "quant-developer",
)

EXPECTED_DESCRIPTIONS = {
    "quant-plan": (
        "Use only when the user explicitly invokes $quant-plan to audit "
        "current state or produce a quick or decision-complete "
        "implementation plan. Work read-only; never auto-activate or "
        "implement changes."
    ),
    "quant-goal": (
        "Use only when the user explicitly invokes $quant-goal to initialize, "
        "manually resume, or steer a native Goal through verified completion "
        "or a genuine blocker."
    ),
    "quant-developer": (
        "Use only when the user explicitly invokes $quant-developer to "
        "deliver a complete end-to-end change with adaptive implementation, "
        "selective delegation, and real-surface verification."
    ),
}


def skill_text(skill: str) -> str:
    return (
        ROOT / "skills" / skill / "SKILL.md"
    ).read_text(encoding="utf-8")


def normalized_skill_text(skill: str) -> str:
    return validate_suite.normalized_policy_text(skill_text(skill))


def agent_metadata(skill: str) -> dict[str, object]:
    raw = (
        ROOT / "skills" / skill / "agents" / "openai.yaml"
    ).read_text(encoding="utf-8")
    value = validate_suite.agent_metadata(raw)
    if value is None:
        raise AssertionError(f"missing agent metadata for {skill}")
    return value


class SkillRoutingTests(unittest.TestCase):
    def test_exactly_three_public_skills_with_stable_names_and_descriptions(
        self,
    ) -> None:
        discovered = {
            path.parent.name
            for path in (ROOT / "skills").glob("*/SKILL.md")
        }
        self.assertEqual(discovered, set(EXPECTED_SKILLS))
        self.assertEqual(tuple(validate_suite.SKILLS), EXPECTED_SKILLS)
        self.assertFalse((ROOT / "shared" / "SKILL.md").exists())

        for skill, expected_description in EXPECTED_DESCRIPTIONS.items():
            metadata = validate_suite.frontmatter(skill_text(skill))
            with self.subTest(skill=skill):
                self.assertEqual(metadata["name"], skill)
                self.assertEqual(
                    metadata["description"],
                    expected_description,
                )

    def test_public_skills_are_manual_and_do_not_cross_activate(self) -> None:
        for skill in EXPECTED_SKILLS:
            text = normalized_skill_text(skill)
            metadata = agent_metadata(skill)
            mentioned_skills = set(
                re.findall(r"\$(quant-(?:plan|goal|developer))", text)
            )

            with self.subTest(skill=skill):
                self.assertIs(
                    metadata["allow_implicit_invocation"],
                    False,
                )
                self.assertIn(f"${skill}", text)
                self.assertIn("explicit", text)
                self.assertTrue(
                    "current user" in text or "current-user" in text
                )
                self.assertTrue(
                    "not activation" in text
                    or "does not activate" in text
                    or "never auto-activate" in text
                )
                self.assertEqual(mentioned_skills, {skill})

    def test_agent_prompts_are_short_single_sentence_and_role_specific(
        self,
    ) -> None:
        for skill in EXPECTED_SKILLS:
            metadata = agent_metadata(skill)
            prompt = metadata["default_prompt"]
            self.assertIsInstance(prompt, str)
            assert isinstance(prompt, str)
            mentioned_skills = re.findall(
                r"\$(quant-(?:plan|goal|developer))",
                prompt,
            )
            sentence_endings = re.findall(r"[.!?]", prompt)

            with self.subTest(skill=skill):
                self.assertEqual(mentioned_skills, [skill])
                self.assertFalse("\n" in prompt)
                self.assertEqual(len(sentence_endings), 1)
                self.assertTrue(prompt.endswith((".", "!", "?")))
                self.assertGreaterEqual(len(prompt.split()), 12)
                self.assertLessEqual(len(prompt.split()), 45)
                self.assertIs(
                    metadata["allow_implicit_invocation"],
                    False,
                )

    def test_native_goal_continuation_is_not_implicit_skill_activation(
        self,
    ) -> None:
        goal = normalized_skill_text("quant-goal")
        self.assertIn("native goal lifecycle", goal)
        self.assertIn("not implicit skill invocation", goal)
        self.assertIn("automatic follow-up turns", goal)
        self.assertIn("without reactivating this skill", goal)
        self.assertIn(
            "do not create goal state for an ordinary request",
            goal,
        )
        self.assertIn("an active goal", goal)
        self.assertIn("is not activation", goal)

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

    def test_semantic_contracts_reject_reversed_meaning(self) -> None:
        cases = (
            (
                "skills/quant-plan/SKILL.md",
                "Plan read-only.",
                "It is forbidden to ever plan read-only.",
                "quant-plan: missing role concept 'read-only operation'",
            ),
            (
                "skills/quant-goal/SKILL.md",
                "Call `get_goal` before deciding whether to create or resume "
                "anything.",
                "Do not ever call `get_goal` before deciding whether to "
                "create or resume anything.",
                "quant-goal: missing role concept 'goal lookup first'",
            ),
            (
                "skills/quant-goal/SKILL.md",
                "the same blocking condition has recurred for three "
                "consecutive Goal turns;",
                "ignore whether the same blocking condition recurred across "
                "Goal turns;",
                "quant-goal: missing role concept 'three-turn blocker'",
            ),
            (
                "skills/quant-developer/SKILL.md",
                "Deliver the complete accepted outcome end to end while "
                "minimizing unrelated",
                "It is forbidden to ever deliver the complete accepted "
                "outcome end to end while minimizing unrelated",
                "quant-developer: missing role concept 'complete outcome'",
            ),
            (
                "shared/references/adaptive-workflow.md",
                "Add parallel lanes when at\nleast two independent questions "
                "or work units can make real progress at the\nsame time.",
                "Do not ever add parallel lanes when at\nleast two independent "
                "questions or work units can make real progress at the\nsame "
                "time.",
                "missing adaptive concept 'selective parallelism'",
            ),
            (
                "shared/core/authority.md",
                "Permission to implement locally includes reversible "
                "task-scoped temporary",
                "It is false that permission to implement locally includes "
                "reversible task-scoped temporary",
                "missing authority concept 'normal temporary isolation'",
            ),
            (
                "skills/quant-plan/SKILL.md",
                "This skill's read-only boundary always overrides shared "
                "`act`, edit, generated\nartifact, temporary-isolation, or "
                "mutation language.",
                "This skill's read-only boundary always overrides shared "
                "`act`, edit, generated\nartifact, temporary-isolation, or "
                "mutation language. It is false that this read-only boundary "
                "always overrides shared mutation language.",
                "quant-plan: missing role concept 'read-only shared precedence'",
            ),
            (
                "skills/quant-plan/SKILL.md",
                "keep this\nskill's phase read-only, finish and self-critique "
                "the selected plan first, then\nhand implementation ownership",
                "keep this\nskill's phase read-only, finish and self-critique "
                "the selected plan first, then\nhand implementation ownership. "
                "It is false that the phase read-only must precede "
                "implementation ownership",
                "quant-plan: missing role concept "
                "'staged implementation composition'",
            ),
            (
                "skills/quant-goal/SKILL.md",
                "Because `create_goal` has one\n   `objective` field and no "
                "separate success-condition field, serialize a\n   compact "
                "outcome, material scope boundaries, constraints, and the "
                "complete\n   `SC-*` list into that objective.",
                "Because `create_goal` has one\n   `objective` field and no "
                "separate success-condition field, serialize a\n   compact "
                "outcome, material scope boundaries, constraints, and the "
                "complete\n   `SC-*` list into that objective. Never serialize "
                "`create_goal` `objective` with the `SC-*` list.",
                "quant-goal: missing role concept "
                "'objective-bound success conditions'",
            ),
            (
                "skills/quant-goal/SKILL.md",
                "Mark evidence for\n"
                "every changed or dependent condition stale, and reverify the "
                "current set before\nreusing any conclusion.",
                "Mark evidence for\n"
                "every changed or dependent condition stale, and reverify the "
                "current set before\nreusing any conclusion. Never let stable "
                "IDs make dependent condition stale or reverify them.",
                "quant-goal: missing role concept "
                "'steering evidence invalidation'",
            ),
            (
                "shared/references/adaptive-workflow.md",
                "The invoking public skill's scope and mutation boundary always "
                "win.",
                "The invoking public skill's scope and mutation boundary always "
                "win. It is false that the invoking public skill boundary always "
                "win.",
                "missing adaptive concept 'invoking boundary precedence'",
            ),
            (
                "skills/quant-developer/SKILL.md",
                "Local source-control mutation\n(branch, worktree, stage, "
                "commit, cherry-pick, or rebase); remote source-control\n"
                "mutation",
                "Local source-control mutation\n(branch, worktree, stage, "
                "commit, cherry-pick, or rebase); remote source-control\n"
                "mutation. Never treat local source-control mutation and remote "
                "source-control mutation as separate authority boundaries",
                "quant-developer: missing role concept "
                "'separate authority boundaries'",
            ),
            (
                "shared/core/context-routing.md",
                "A `strict` label,\n   long duration, release delivery, task "
                "complexity, or repeated failure alone\n   does not select a "
                "ledger or structured runtime.",
                "A `strict` label,\n   long duration, release delivery, task "
                "complexity, or repeated failure alone\n   automatically "
                "selects a ledger and structured runtime.",
                "missing routed policy concept "
                "'native path does not auto-select structured state'",
            ),
            (
                "shared/references/durable-runtime.md",
                "`strict`,\nlong-running, release, complexity, or failure alone "
                "never selects either\nruntime.",
                "`strict`,\nlong-running, release, complexity, or failure alone "
                "always selects either\nruntime.",
                "missing routed policy concept "
                "'labels do not select durable runtime'",
            ),
        )

        for relative, old, new, expected_error in cases:
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as tmp:
                copied_root = Path(tmp) / "suite"
                shutil.copytree(
                    ROOT,
                    copied_root,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
                target = copied_root / relative
                raw = target.read_text(encoding="utf-8")
                self.assertIn(old, raw)
                target.write_text(raw.replace(old, new, 1), encoding="utf-8")

                with mock.patch.object(validate_suite, "ROOT", copied_root):
                    errors = validate_suite.validate()

                self.assertTrue(
                    any(expected_error in error for error in errors),
                    errors,
                )

    def test_ordinary_paths_are_self_contained_with_conditional_adaptation(
        self,
    ) -> None:
        shared_reference = (
            ROOT / "shared" / "references" / "adaptive-workflow.md"
        )
        self.assertTrue(shared_reference.is_file())

        installed_path = (
            "../quant-research-shared/references/adaptive-workflow.md"
        )
        source_path = "../../shared/references/adaptive-workflow.md"
        skip_or_continue_language = {
            "quant-plan": "do not load the reference for a narrow plan",
            "quant-goal": (
                "if that optional reference is unavailable, continue"
            ),
            "quant-developer": (
                "ordinary bounded changes should not need that reference"
            ),
        }

        for skill in EXPECTED_SKILLS:
            raw = skill_text(skill)
            text = normalized_skill_text(skill)
            with self.subTest(skill=skill):
                self.assertIn(installed_path, raw)
                self.assertIn(source_path, raw)
                self.assertIn("adaptive-workflow.md", raw)
                self.assertIn(skip_or_continue_language[skill], text)
                self.assertNotIn("Run `validate_installed.py` before", raw)
                self.assertNotIn("Run `quantctl.py doctor` before", raw)
                self.assertNotIn("Run `quantctl.py context` before", raw)

        plan = normalized_skill_text("quant-plan")
        goal = normalized_skill_text("quant-goal")
        developer = normalized_skill_text("quant-developer")
        self.assertIn("ordinary planning must not load or create", plan)
        self.assertIn(
            "do not create a ledger, manifest, plan packet, review stack",
            goal,
        )
        self.assertIn("they are off the default path", developer)

    def test_legacy_structured_runtime_is_explicitly_opt_in(self) -> None:
        expected_opt_in_meanings = {
            "quant-plan": (
                "optional legacy compatibility",
                "machine-audited legacy output",
                "existing project requires",
            ),
            "quant-goal": (
                "legacy compatibility",
                "machine audit",
                "existing goal already depends",
            ),
            "quant-developer": (
                "legacy compatibility",
                "explicit machine-audit request",
                "existing project contract",
            ),
        }
        for skill, meanings in expected_opt_in_meanings.items():
            text = normalized_skill_text(skill)
            with self.subTest(skill=skill):
                for meaning in meanings:
                    self.assertIn(meaning, text)
                self.assertIn("ordinary", text)

        context_routing = validate_suite.normalized_policy_text((
            ROOT / "shared" / "core" / "context-routing.md"
        ).read_text(encoding="utf-8"))
        self.assertIn("legacy structured assurance", context_routing)
        self.assertIn("only for an existing compatibility contract", context_routing)
        self.assertIn("ordinary host-native", context_routing)

    def test_safe_module_extension_does_not_open_root_package_surface(
        self,
    ) -> None:
        self.assertTrue(
            validate_suite.is_allowed_package_file(
                Path("shared/adapters/new-provider.md")
            )
        )
        self.assertTrue(
            validate_suite.is_allowed_package_file(
                Path("shared/references/new-workflow.md")
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

    def test_multi_agent_runtime_gate_matches_legacy_documentation(
        self,
    ) -> None:
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

    def test_goal_legacy_state_does_not_persist_authority(self) -> None:
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
