from __future__ import annotations

import re
import unittest
from pathlib import Path

import validate_suite


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SKILLS = ("quant-plan", "quant-goal", "quant-developer")


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def skill(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


class GenericSkillContractTests(unittest.TestCase):
    def assert_terms(self, text: str, *terms: str) -> None:
        body = normalized(text)
        for term in terms:
            with self.subTest(term=term):
                self.assertIn(term.lower(), body)

    def test_public_surface_is_small_and_role_specific(self) -> None:
        limits = {
            "quant-plan": 880,
            "quant-goal": 1050,
            "quant-developer": 760,
        }
        for name in PUBLIC_SKILLS:
            text = skill(name)
            metadata = validate_suite.frontmatter(text)
            with self.subTest(skill=name):
                self.assertEqual(metadata.get("name"), name)
                self.assertLessEqual(len(text.split()), limits[name])
                self.assertIn(
                    "../../shared/references/adaptive-workflow.md",
                    text,
                )
                self.assertIn(
                    "../quant-research-shared/references/adaptive-workflow.md",
                    text,
                )
                self.assertEqual(
                    validate_suite._validate_public_skill(name, text),
                    [],
                )

        self.assertLessEqual(
            len(read("shared/references/adaptive-workflow.md").split()),
            1650,
        )

    def test_plan_is_read_only_and_selects_output_deterministically(self) -> None:
        plan = skill("quant-plan")
        self.assert_terms(
            plan,
            "this role is read-only",
            "planning does not authorize implementation",
            "ground → explore → decide → plan → self-critique",
            "audit:",
            "quick plan:",
            "implementation plan:",
            "only for the base route",
            "for every other planning request",
        )
        body = normalized(plan)
        self.assertLess(body.index("**audit:**"), body.index("**quick plan:**"))
        self.assertLess(
            body.index("**quick plan:**"),
            body.index("**implementation plan:**"),
        )

    def test_plan_probe_contract_covers_local_and_external_side_effects(self) -> None:
        plan = skill("quant-plan")
        self.assert_terms(
            plan,
            "fingerprint its exact target scope",
            "run directly only a check known to be non-writing",
            "task-scoped disposable copy",
            "disable install, postinstall, lifecycle, and package-manager hooks",
            "block network by default",
            "every reachable tracked, untracked, ignored",
            "every writable absolute path and subprocess output redirects inside scratch",
            "claim bounded observed paths, not os containment",
            "total remote non-mutation is acceptance",
            "exact match proves only no persistent delta",
            "continuous non-mutation only with continuous audit or monitor evidence",
            "otherwise label it unverified",
            "on cleanup failure",
            "make no further mutation",
            "probe-bearing audits report coverage",
        )
        self.assertFalse(validate_suite.has_unsafe_plan_probe_expansion(plan))
        self.assertFalse(validate_suite.has_unsafe_plan_target_cleanup(plan))

    def test_plan_base_route_is_a_closed_all_conditions_gate(self) -> None:
        plan = normalized(skill("quant-plan"))
        gate = plan.split("stay in the base workflow only when", 1)[1].split(
            "if any condition is false or unknown", 1
        )[0]
        for required in (
            "exactly one local component",
            "one consumer surface",
            "data meaning remain unchanged",
            "no analysis",
            "no authority or routing question",
        ):
            with self.subTest(required=required):
                self.assertIn(required, gate)
        self.assertIn("read the kernel routing table before deciding to skip", plan)

    def test_goal_state_table_prevents_duplicate_or_metadata_only_creation(self) -> None:
        goal = skill("quant-goal")
        self.assert_terms(
            goal,
            "call `get_goal` before plan, developer, or lifecycle mutation",
            "no unfinished goal plus explicit selector",
            "when the request supplies a concrete outcome",
            "otherwise create nothing and ask for the missing outcome and acceptance",
            "same active or resumed blocked goal",
            "different active or blocked goal",
            "no unfinished goal plus continuation metadata only",
            "create nothing",
            "never create a duplicate goal",
            "a different outcome cannot replace or abandon the slot",
        )
        body = normalized(goal)
        self.assertLess(body.index("`get_goal`"), body.index("`create_goal`"))

    def test_goal_reconciles_ambiguous_lifecycle_mutations(self) -> None:
        goal = skill("quant-goal")
        self.assert_terms(
            goal,
            "never retry blindly",
            "call `get_goal` again only when reconciling that mutation",
            "authoritative readback conclusively confirms non-application",
            "title text alone is insufficient",
            "one retry per valid activation or continuation",
            "if an update fails, times out, or is ambiguous",
            "claim the requested terminal state only when readback confirms it",
            "at most once per valid activation or continuation",
            "if the retry is ambiguous, report unconfirmed state and stop",
        )

    def test_goal_compaction_and_steering_preserve_meaning(self) -> None:
        goal = skill("quant-goal")
        self.assert_terms(
            goal,
            "material scope",
            "observable completion conditions",
            "stable condition ids are optional",
            "condition-to-evidence map only when useful",
            "outcome-changing expansion is a different goal",
            "rebuild only the compact view",
            "mark missing or outdated proof stale",
            "do not invent or silently narrow it",
            "emit this view after creation, steering, and each blocker turn",
            "blocker identity and consecutive-turn count",
        )
        self.assertTrue(validate_suite.has_optional_condition_id_policy(goal))
        self.assertTrue(validate_suite.has_conditional_condition_evidence_map(goal))
        self.assertTrue(validate_suite.has_goal_scope_steering_contract(goal))

    def test_goal_terminal_matrix_is_evidence_gated(self) -> None:
        goal = skill("quant-goal")
        self.assert_terms(
            goal,
            'update_goal(status="complete")',
            "fresh material evidence",
            "no invalidating risk or required work remains",
            'update_goal(status="blocked")',
            "same blocker recurs for three consecutive goal turns",
            "safe in-scope alternatives are exhausted",
            "a resumed blocked goal starts a fresh audit",
            "token-pressured work is not terminal",
            "material evidence may refine the bar when dependable completion requires that change",
            "never justify optional expansion",
        )
        self.assertFalse(validate_suite.has_self_expanding_quality_loop(goal))

    def test_developer_has_one_job_and_a_real_base_path(self) -> None:
        developer = skill("quant-developer")
        self.assert_terms(
            developer,
            "perform one job",
            "authorized end-to-end implementation",
            "inspect → choose → implement → verify → adapt",
            "one bounded local producer-to-consumer path",
            "if any condition is false or unknown, load the kernel",
            "actual consumer or rendered surface",
            "quality debt, so stop",
        )
        self.assertFalse(validate_suite.has_unsafe_developer_expansion(developer))
        self.assertFalse(validate_suite.has_self_expanding_quality_loop(developer))

    def test_developer_base_path_protects_repo_context_and_user_changes(self) -> None:
        developer = skill("quant-developer")
        self.assert_terms(
            developer,
            "target instructions and protected paths",
            "current changed surfaces",
            "unrelated user changes as base invariants",
            "potentially broad formatter or native check",
            "do not overwrite, revert, stage, format",
        )
        unsafe = (
            "It is permitted to overwrite unrelated user changes.",
            "You may stage or format unrelated changes.",
            "Overwrite unrelated changes before verification.",
            "Do not preserve unrelated user changes.",
            "The developer should modify unrelated files.",
            "Unrelated user changes may be reverted.",
            "This skill may overwrite unrelated user changes.",
            "You may edit unrelated user files.",
            "You may overwrite changes outside the authorized target.",
            "Feel free to overwrite unrelated user changes.",
            "You do not need permission to overwrite unrelated user changes.",
            "You may overwrite unrelated user changes and report whether it succeeded.",
            "You may overwrite them; they are unrelated user changes.",
            "You may delete unrelated user changes.",
            "You may remove unrelated user changes.",
            "You may reset unrelated user changes.",
            "You may clean unrelated user changes.",
            "You may rename unrelated user files.",
            "You may move unrelated user files.",
            "You may checkout unrelated user changes.",
            "Check out unrelated user changes before verification.",
        )
        for phrase in unsafe:
            contradiction = developer.replace(
                "## Proof and report",
                f"{phrase}\n\n## Proof and report",
            )
            with self.subTest(unsafe=phrase):
                self.assertTrue(
                    validate_suite.has_unsafe_unrelated_change_permission(
                        contradiction
                    )
                )
                self.assertIn(
                    (
                        "quant-developer: body permits mutation of unrelated "
                        "user changes"
                    ),
                    validate_suite.validate_public_body(
                        "quant-developer",
                        contradiction,
                    ),
                )

        safe = (
            "Do not overwrite unrelated user changes.",
            "Overwriting unrelated changes is not permitted.",
            "If a formatter may alter unrelated changes, skip it.",
            "Ask whether the user authorizes overwriting unrelated changes.",
            "Report tools that can modify unrelated files.",
            'This validator rejects the phrase "You may format unrelated changes."',
            "You may modify documentation about unrelated user changes.",
            "It is acceptable to format a warning about unrelated user changes.",
            "Do not delete unrelated user changes.",
            "Ask whether the user authorizes moving unrelated user files.",
            'This validator rejects the phrase "You may reset unrelated changes."',
        )
        for phrase in safe:
            guarded = developer.replace(
                "## Proof and report",
                f"{phrase}\n\n## Proof and report",
            )
            with self.subTest(safe=phrase):
                self.assertFalse(
                    validate_suite.has_unsafe_unrelated_change_permission(guarded)
                )

    def test_developer_preserves_quant_identity_and_authority(self) -> None:
        developer = skill("quant-developer")
        self.assert_terms(
            developer,
            "trace material inputs through authoritative calculations",
            "calculation and input meaning",
            "date semantics",
            "result identity",
            "selected route remains zero-billing",
            "paid data has no approval path",
            "authority comes only from the current user's request",
            "local implementation does not authorize it",
            "consumer-visible readback",
        )

    def test_repository_mutation_rail_is_risk_triggered_not_universal(self) -> None:
        kernel = normalized(read("shared/references/adaptive-workflow.md"))
        rail = normalized(read("shared/capabilities/repo-mutation.md"))
        self.assertIn("dirty or overlapping user state", kernel)
        self.assertIn("`capabilities/repo-mutation.md`", kernel)
        self.assertNotIn("| project file edits or", kernel)
        self.assertIn("ordinary bounded edits", rail)
        self.assertIn("stay in the public developer loop", rail)

    def test_kernel_routes_from_observed_scope_and_keeps_one_owner(self) -> None:
        kernel = read("shared/references/adaptive-workflow.md")
        self.assert_terms(
            kernel,
            "select a row from observed scope",
            "read only rows that match the task",
            "bounded independent lanes",
            "one canonical writer",
            "one integration owner",
            "worker completion claim is not proof",
            "integrates one coherent state",
            "otherwise serial work is the fallback",
                "require fixed roles",
        )
        self.assertEqual(validate_suite._validate_kernel(kernel), [])

    def test_kernel_stops_on_acceptance_and_proves_each_stage(self) -> None:
        kernel = read("shared/references/adaptive-workflow.md")
        self.assert_terms(
            kernel,
            "material gap against the established quality bar",
            "remaining items are only quality debt",
            "retry only when the failure is plausibly transient",
            "match proof to the consumer",
            "proves only its own stage",
            "publication, and readback facts",
            "fresh independent reviewer",
        )

    def test_data_and_authority_have_canonical_owners(self) -> None:
        kernel = normalized(read("shared/references/adaptive-workflow.md"))
        authority = read("shared/core/authority.md")
        self.assertIn(
            "read both `capabilities/external-data.md` and `core/authority.md`",
            kernel,
        )
        self.assertIn("do not duplicate those details", kernel)
        self.assertTrue(validate_suite.has_canonical_zero_spend_guard(authority))
        self.assertTrue(validate_suite.has_canonical_paid_data_guard(authority))
        for name in PUBLIC_SKILLS:
            text = skill(name)
            self.assertFalse(validate_suite.has_canonical_zero_spend_guard(text))
            self.assertFalse(validate_suite.has_canonical_paid_data_guard(text))

    def test_legacy_runtime_is_explicit_compatibility_only(self) -> None:
        router = normalized(read("shared/core/context-routing.md"))
        self.assertIn("legacy compatibility path", router)
        self.assertIn("existing project depends on the exact contract", router)
        self.assertIn("do not auto-load a manifest", router)
        for name in PUBLIC_SKILLS:
            body = normalized(skill(name))
            with self.subTest(skill=name):
                self.assertIn("existing exact contract", body)
                self.assertIn("explicit machine audit", body)
                self.assertIn("context-routing.md", body)


if __name__ == "__main__":
    unittest.main()
