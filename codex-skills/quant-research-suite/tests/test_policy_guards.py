from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import validate_suite


def normalized(relative: str) -> str:
    return validate_suite.normalized_policy_text(
        (ROOT / relative).read_text(encoding="utf-8")
    )


class PolicyGuardTests(unittest.TestCase):
    def test_canonical_paid_action_guard_is_default_deny(self) -> None:
        guard = validate_suite.CANONICAL_ZERO_SPEND_GUARD
        self.assertTrue(validate_suite.has_canonical_zero_spend_guard(guard))
        reversed_meaning = guard.replace(
            "are prohibited unless a direct prior user request names",
            "are allowed even when no direct prior user request names",
        )
        self.assertFalse(
            validate_suite.has_canonical_zero_spend_guard(reversed_meaning)
        )

    def test_detailed_paid_policy_has_one_document_owner(self) -> None:
        authority = ROOT / "shared/core/authority.md"
        self.assertTrue(
            validate_suite.has_canonical_zero_spend_guard(
                authority.read_text(encoding="utf-8")
            )
        )
        duplicates = []
        for path in ROOT.rglob("*"):
            if (
                path == authority
                or not path.is_file()
                or path.suffix not in {".md", ".yaml"}
            ):
                continue
            if validate_suite.has_canonical_zero_spend_guard(
                path.read_text(encoding="utf-8")
            ):
                duplicates.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(duplicates, [])

    def test_paid_data_is_ineligible_and_free_fallbacks_remain_useful(
        self,
    ) -> None:
        authority = (ROOT / "shared/core/authority.md").read_text(
            encoding="utf-8"
        )
        self.assertTrue(validate_suite.has_canonical_paid_data_guard(authority))
        authority_text = validate_suite.normalized_policy_text(authority)
        for concept in (
            "time-limited free trial",
            "automatic free-to-paid conversion",
            "card, billing account",
            "payg",
            "overage",
            "no approval escape hatch",
        ):
            self.assertIn(concept, authority_text)

        adaptive = normalized("shared/references/adaptive-workflow.md")
        ladder_text = adaptive.split(
            "explore data routes in this order",
            maxsplit=1,
        )[1]
        ladder = (
            "project-owned source",
            "official no-billing",
            "another lawfully accessible no-billing",
            "derived from free inputs",
            "disclosed proxy",
        )
        positions = [ladder_text.index(item) for item in ladder]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("paid data is outside the solution space", adaptive)

        for skill in validate_suite.SKILLS:
            text = normalized(f"skills/{skill}/SKILL.md")
            with self.subTest(skill=skill):
                self.assertIn("paid", text)
                self.assertTrue(
                    any(
                        marker in text
                        for marker in (
                            "zero-billing",
                            "no-billing",
                            "free-only",
                        )
                    )
                )
                self.assertFalse(
                    validate_suite.has_canonical_zero_spend_guard(text)
                )

    def test_public_skills_keep_authority_concise_and_prompts_small(
        self,
    ) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("shared/core/authority.md", readme)

        authority_concepts = {
            "destructive": ("destructive",),
            "credentials": ("authentication", "secret"),
            "external": ("production", "remote"),
            "source control": ("commit", "push", "merge"),
            "cost": ("paid",),
        }
        for skill in validate_suite.SKILLS:
            skill_text = normalized(f"skills/{skill}/SKILL.md")
            with self.subTest(skill=skill):
                for label, alternatives in authority_concepts.items():
                    self.assertTrue(
                        any(item in skill_text for item in alternatives),
                        f"{skill} missing {label}",
                    )

            agent_path = ROOT / f"skills/{skill}/agents/openai.yaml"
            metadata = validate_suite.agent_metadata(
                agent_path.read_text(encoding="utf-8")
            )
            self.assertIsNotNone(metadata)
            assert metadata is not None
            prompt = metadata["default_prompt"]
            assert isinstance(prompt, str)
            with self.subTest(agent=skill):
                self.assertLessEqual(len(prompt.split()), 50)
                self.assertFalse(
                    validate_suite.has_canonical_zero_spend_guard(prompt)
                )

    def test_local_isolation_is_normal_but_durable_scm_is_separate(
        self,
    ) -> None:
        authority = normalized("shared/core/authority.md")
        for concept in (
            "task-scoped temporary isolation outside git",
            "does not include creating a git branch or worktree",
            "explicit integration owner",
            "branch, worktree, stage, commit",
            "remains dimension 3",
            "commit does not authorize push",
        ):
            self.assertIn(concept, authority)

        adaptive = normalized("shared/references/adaptive-workflow.md")
        self.assertIn(
            "reversible non-git task-scoped temporary isolation",
            adaptive,
        )
        self.assertIn("one canonical writer", adaptive)
        self.assertIn("isolated writers only when", adaptive)
        self.assertIn("integration owner", adaptive)
        for action in (
            "branch",
            "worktree",
            "stage",
            "commit",
            "cherry-pick",
            "rebase",
        ):
            self.assertIn(action, adaptive)

        repository = normalized("shared/capabilities/repo-mutation.md")
        for action in (
            "branch",
            "worktree",
            "stage",
            "commit",
            "cherry-pick",
            "rebase",
            "push",
            "pr",
            "merge",
        ):
            self.assertIn(action, repository)
        self.assertIn("permission to edit files is not enough", repository)

        for skill in validate_suite.SKILLS:
            text = normalized(f"skills/{skill}/SKILL.md")
            with self.subTest(skill=skill):
                self.assertIn("local source-control mutation", text)
                self.assertIn("remote source-control mutation", text)
                for action in (
                    "branch",
                    "worktree",
                    "stage",
                    "commit",
                    "cherry-pick",
                    "rebase",
                ):
                    self.assertIn(action, text)
        for skill in ("quant-goal", "quant-developer"):
            self.assertIn(
                "reversible non-git task-scoped temporary isolation",
                normalized(f"skills/{skill}/SKILL.md"),
            )

    def test_multi_skill_composition_is_staged_and_keeps_sole_owners(
        self,
    ) -> None:
        readme = normalized("README.md")
        plan = normalized("skills/quant-plan/SKILL.md")
        goal = normalized("skills/quant-goal/SKILL.md")
        developer = normalized("skills/quant-developer/SKILL.md")
        router = normalized("shared/core/context-routing.md")

        for text in (readme, router):
            self.assertIn("read-only planning", text)
            self.assertIn("later implementation", text)
            self.assertIn("goal lifecycle", text)
            self.assertIn("never broadens authority", text)
        self.assertIn("keep this skill's phase read-only", plan)
        self.assertIn("finish and self-critique the selected plan first", plan)
        self.assertIn("did not require plan approval first", plan)
        self.assertIn("that skill alone owns goal state", plan)
        self.assertIn("let its read-only phase finish before implementation", goal)
        self.assertIn("retains integration and goal lifecycle ownership", goal)
        self.assertIn("wait for its read-only, self-critiqued plan", developer)
        self.assertIn("owns goal lifecycle and overall integration", developer)
        self.assertIn("never changes or completes the parent goal", developer)

    def test_native_goal_never_auto_selects_structured_runtime(self) -> None:
        goal = normalized("skills/quant-goal/SKILL.md")
        router = normalized("shared/core/context-routing.md")
        contract = normalized("shared/references/goal-and-subagents.md")
        durable = normalized("shared/references/durable-runtime.md")

        self.assertIn("do not create a ledger", goal)
        self.assertIn(
            "a `strict` label, long duration, release delivery, or task "
            "complexity alone never selects a local ledger",
            goal,
        )
        self.assertIn(
            "a `strict` label, long duration, release delivery, task complexity, "
            "or repeated failure alone does not select",
            router,
        )
        self.assertIn(
            "outside an explicitly selected structured compatibility or "
            "machine-audit path, no local ledger is created automatically",
            contract,
        )
        self.assertIn(
            "`strict`, long-running, release, complexity, or failure alone "
            "never selects either runtime",
            durable,
        )
        for obsolete in (
            "local ledger only when long-running",
            "host lifecycle plus automatic ledger",
            "an automatic local ledger is required for",
            "goal_ledger.py is the host-aligned evidence companion for `strict`, "
            "clearly long-running",
        ):
            with self.subTest(obsolete=obsolete):
                self.assertNotIn(obsolete, contract)
                self.assertNotIn(obsolete, durable)

    def test_shared_root_and_legacy_runtime_paths_stay_valid(self) -> None:
        router = (ROOT / "shared/core/context-routing.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Shared-root resolution", router)
        self.assertIn("<suite-root>/shared", router)
        self.assertIn("quant-research-shared", router)
        self.assertIn("never from the current working directory", router)

        adaptive = ROOT / "shared/references/adaptive-workflow.md"
        authority = ROOT / "shared/core/authority.md"
        self.assertTrue(adaptive.is_file())
        self.assertTrue(authority.is_file())
        for skill in validate_suite.SKILLS:
            skill_dir = ROOT / "skills" / skill
            adaptive_ref = (
                skill_dir / "../../shared/references/adaptive-workflow.md"
            ).resolve()
            authority_ref = (
                skill_dir / "../../shared/core/authority.md"
            ).resolve()
            raw = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=skill):
                self.assertEqual(adaptive_ref, adaptive.resolve())
                self.assertTrue(adaptive_ref.is_file())
                self.assertEqual(authority_ref, authority.resolve())
                self.assertTrue(authority_ref.is_file())
                self.assertIn(
                    "../quant-research-shared/core/authority.md",
                    raw,
                )
                self.assertIn("../../shared/core/authority.md", raw)

        team = (
            ROOT / "shared/capabilities/agent-team-execution.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("python3 shared/scripts/", team)
        self.assertGreaterEqual(
            team.count(
                "python3 <quant-shared-root>/scripts/team_protocol.py"
            ),
            5,
        )

    def test_legacy_runtime_triggers_require_user_or_existing_contract(
        self,
    ) -> None:
        surfaces = (
            "README.md",
            "skills/quant-plan/SKILL.md",
            "skills/quant-goal/SKILL.md",
            "skills/quant-developer/SKILL.md",
            "shared/core/context-routing.md",
            "shared/advisory/external-comparisons.md",
        )
        for relative in surfaces:
            text = normalized(relative)
            with self.subTest(relative=relative):
                self.assertIn("high-risk recovery", text)
                recovery = text.split("high-risk recovery", maxsplit=1)[0]
                self.assertTrue(
                    "explicit" in recovery[-80:]
                    or "user" in recovery[-80:]
                )

        self.assertIn(
            "do not create a ledger",
            normalized("skills/quant-goal/SKILL.md"),
        )
        self.assertIn(
            "ordinary planning must not load or create",
            normalized("skills/quant-plan/SKILL.md"),
        )
        self.assertIn(
            "off the default path",
            normalized("skills/quant-developer/SKILL.md"),
        )

    def test_plan_goal_and_developer_keep_stage_and_authority_boundaries(
        self,
    ) -> None:
        plan = normalized("skills/quant-plan/SKILL.md")
        goal = normalized("skills/quant-goal/SKILL.md")
        developer = normalized("skills/quant-developer/SKILL.md")

        self.assertIn("planning does not authorize implementation", plan)
        self.assertIn(
            "non-git task-scoped temporary isolation are normal",
            goal,
        )
        self.assertIn(
            "non-git task-scoped temporary isolation are normal",
            developer,
        )
        for text in (goal, developer):
            self.assertIn("commit", text)
            self.assertIn("push", text)
            self.assertIn("deployment", text)
            self.assertIn("separate authority boundaries", text)

        self.assertIn("local test does not prove a remote", goal)
        for stage in (
            "configuration",
            "execution",
            "artifact creation",
            "publication",
            "public readback",
        ):
            self.assertIn(stage, developer)

        design_source = (
            ROOT / "shared/references/web-design-source.md"
        ).read_text(encoding="utf-8")
        self.assertIn("web-design-v2.4.1.md", design_source)
        self.assertIn("version: `2.4.1`", design_source)
        self.assertIn(
            f"SHA-256: `{validate_suite.EXPECTED_WEB_DESIGN_SHA}`",
            design_source,
        )


if __name__ == "__main__":
    unittest.main()
