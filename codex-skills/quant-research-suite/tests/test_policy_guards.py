from __future__ import annotations

import re
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
    def test_canonical_cost_guards_are_default_deny(self) -> None:
        authority = normalized("shared/core/authority.md")
        self.assertTrue(validate_suite.has_canonical_zero_spend_guard(authority))
        self.assertTrue(validate_suite.has_canonical_paid_data_guard(authority))

        weakened_spend = authority.replace(
            "requires a direct prior user request",
            "does not require a direct prior user request",
        )
        weakened_data = authority.replace(
            "paid data must not be proposed",
            "paid data may be proposed",
        )
        self.assertFalse(
            validate_suite.has_canonical_zero_spend_guard(weakened_spend)
        )
        self.assertFalse(
            validate_suite.has_canonical_paid_data_guard(weakened_data)
        )

    def test_detailed_cost_policy_has_one_owner(self) -> None:
        authority = ROOT / "shared/core/authority.md"
        duplicates: list[str] = []
        for path in ROOT.rglob("*"):
            if (
                path == authority
                or not path.is_file()
                or path.suffix not in {".md", ".yaml"}
            ):
                continue
            text = path.read_text(encoding="utf-8")
            if validate_suite.has_canonical_zero_spend_guard(text):
                duplicates.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(duplicates, [])

    def test_selected_data_route_is_sealed_from_optional_paid_tiers(
        self,
    ) -> None:
        authority = normalized("shared/core/authority.md")
        external_data = normalized("shared/capabilities/external-data.md")
        adaptive = normalized("shared/references/adaptive-workflow.md")
        for text in (authority, external_data):
            self.assertIn("zero charge", text)
            self.assertIn("payg", text)
            self.assertIn("overage", text)
            self.assertIn("optional paid tiers", text)
        self.assertIn("payment method", authority)
        self.assertIn("chargeable fallback", authority)
        self.assertIn("cannot enroll in, depend on, or fall through", external_data)
        self.assertIn("`capabilities/external-data.md`", adaptive)
        self.assertIn("`core/authority.md`", adaptive)
        self.assertIn("paid data has no approval path", adaptive)
        self.assertIn("no action-approval escape hatch", authority)
        for detailed_policy in (
            r"\bpayment method\b",
            r"\bpayg\b.{0,30}\boverage\b",
            r"\bchargeable fallback\b",
            r"\boptional paid tiers\b",
        ):
            self.assertIsNone(re.search(detailed_policy, adaptive))

    def test_public_skills_are_role_deltas_over_one_kernel(self) -> None:
        kernel = "../../shared/references/adaptive-workflow.md"
        installed_kernel = (
            "../quant-research-shared/references/adaptive-workflow.md"
        )
        limits = {
            "quant-plan": 880,
            "quant-goal": 1050,
            "quant-developer": 800,
        }
        for skill in validate_suite.SKILLS:
            path = ROOT / "skills" / skill / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=skill):
                self.assertIn(kernel, text)
                self.assertIn(installed_kernel, text)
                self.assertLessEqual(len(text.split()), limits[skill])
                self.assertFalse(
                    validate_suite.has_canonical_zero_spend_guard(text)
                )
                self.assertFalse(
                    validate_suite.has_canonical_paid_data_guard(text)
                )

            metadata = validate_suite.agent_metadata(
                (
                    ROOT / "skills" / skill / "agents/openai.yaml"
                ).read_text(encoding="utf-8")
            )
            self.assertIsNotNone(metadata)
            assert metadata is not None
            self.assertIs(metadata["allow_implicit_invocation"], False)
            self.assertLessEqual(
                len(str(metadata["default_prompt"]).split()),
                50,
            )

    def test_authority_dimensions_do_not_collapse(self) -> None:
        authority = normalized("shared/core/authority.md")
        ordered = (
            "read-only inspection",
            "local edits",
            "local source-control mutation",
            "remote source-control mutation",
            "provider or production mutation",
            "paid action",
        )
        positions = [authority.index(term) for term in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn(
            "authority in one dimension does not grant another",
            authority,
        )
        self.assertIn("existing project-owned connector", authority)
        self.assertIn("never put secret values", authority)

    def test_composed_roles_keep_stage_and_lifecycle_owners(self) -> None:
        plan = normalized("skills/quant-plan/SKILL.md")
        goal = normalized("skills/quant-goal/SKILL.md")
        developer = normalized("skills/quant-developer/SKILL.md")
        router = normalized("shared/core/context-routing.md")

        self.assertIn("read-only", plan)
        self.assertIn("planning does not authorize implementation", plan)
        self.assertIn("owns goal lifecycle", plan)
        self.assertIn("this role owns the goal", goal)
        self.assertIn("never changes the parent goal", developer)
        self.assertIn("composition never expands authority", router)

    def test_native_goal_and_ordinary_work_do_not_select_legacy_state(
        self,
    ) -> None:
        goal = normalized("skills/quant-goal/SKILL.md")
        router = normalized("shared/core/context-routing.md")
        self.assertIn("native goal and thread state are the default", goal)
        self.assertIn("do not create a ledger", goal)
        self.assertIn("do not auto-load a manifest", router)
        for reason in ("complexity", "duration", "failure", "`strict` label"):
            self.assertIn(reason, router)
        self.assertIn("alone does not select this path", router)

    def test_legacy_source_is_preserved_without_becoming_default(self) -> None:
        required = (
            "shared/scripts/goal_ledger.py",
            "shared/scripts/goal_runtime.py",
            "shared/scripts/team_protocol.py",
            "shared/schemas/goal-ledger-state.schema.json",
            "shared/schemas/team-run-packet.schema.json",
        )
        for relative in required:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())
        readme = normalized("README.md")
        self.assertRegex(
            readme,
            r"\bdefault\b.{0,40}\bbase\b.{0,80}"
            r"\b(?:omit|exclude)\w*\b.{0,80}\bpayload\b",
        )
        self.assertIn("existing exact project contract", readme)

    def test_web_design_reference_remains_hash_bound(self) -> None:
        source = (
            ROOT / "shared/references/web-design-source.md"
        ).read_text(encoding="utf-8")
        design = (
            ROOT / "shared/references/web-design-v2.4.2.md"
        ).read_text(encoding="utf-8")
        self.assertIn("web-design-v2.4.2.md", source)
        self.assertIn(
            f"version: `{validate_suite.EXPECTED_WEB_DESIGN_VERSION}`",
            source,
        )
        self.assertIn(
            f"source date: `{validate_suite.EXPECTED_WEB_DESIGN_SOURCE_DATE}`",
            source,
        )
        self.assertIn(validate_suite.EXPECTED_WEB_DESIGN_SHA, source)
        normalized_source = " ".join(source.split())
        self.assertIn("candidate contradicts itself", normalized_source)
        self.assertIn("continue to the next candidate", normalized_source)
        self.assertIn(
            f"> 버전: `{validate_suite.EXPECTED_WEB_DESIGN_VERSION}`",
            design,
        )
        self.assertIn(
            f"> 기준일: `{validate_suite.EXPECTED_WEB_DESIGN_SOURCE_DATE}`",
            design,
        )
        for stale in ("7개 메뉴", "7개 링크", "9개 메뉴", "9개 링크"):
            self.assertNotIn(stale, design)
        nav_heading = (
            f"## 4. {validate_suite.EXPECTED_WEB_DESIGN_MENU_COUNT}개 공통 메뉴"
        )
        nav_registry = design.split(nav_heading, 1)[1].split(
            "### 4.1 Canonical navigation", 1
        )[0]
        nav_rows = re.findall(
            r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*`([^`]+)`\s*\|$",
            nav_registry,
            re.MULTILINE,
        )
        self.assertEqual(
            tuple(nav_rows),
            validate_suite.EXPECTED_WEB_DESIGN_NAVIGATION,
        )


if __name__ == "__main__":
    unittest.main()
