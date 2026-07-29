from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import validate_suite


class PaidActionPolicyTests(unittest.TestCase):
    def test_canonical_guard_requires_default_deny_meaning(self) -> None:
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
        authority = ROOT / "shared" / "core" / "authority.md"
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

    def test_paid_data_is_permanently_ineligible(self) -> None:
        authority = (
            ROOT / "shared" / "core" / "authority.md"
        ).read_text(encoding="utf-8")
        self.assertTrue(
            validate_suite.has_canonical_paid_data_guard(authority)
        )
        normalized = validate_suite.normalized_policy_text(authority)
        for phrase in (
            "time-limited free trial",
            "expiring credit",
            "automatic free-to-paid conversion",
            "card, billing account",
            "payg",
            "overage",
            "paid tier",
            "no approval escape hatch",
        ):
            self.assertIn(phrase, normalized)

        for relative in (
            "shared/capabilities/external-data.md",
            "shared/references/data-automation.md",
            "shared/references/cost-and-authority.md",
        ):
            with self.subTest(path=relative):
                text = validate_suite.normalized_policy_text(
                    (ROOT / relative).read_text(encoding="utf-8")
                )
                self.assertIn("paid data", text)
                self.assertIn("free", text)
                self.assertIn("payg", text)

        for skill in validate_suite.SKILLS:
            with self.subTest(skill=skill):
                text = (
                    ROOT / "skills" / skill / "SKILL.md"
                ).read_text(encoding="utf-8").lower()
                self.assertIn("paid data", text)
                self.assertIn("never", text)

    def test_public_surfaces_use_concise_authority_boundary(self) -> None:
        documents = [
            ROOT / "README.md",
            ROOT / "shared" / "references" / "operating-principles.md",
            ROOT / "shared" / "references" / "cost-and-authority.md",
        ]
        for path in documents:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("shared/core/authority.md", text)
                self.assertIn("paid", text.lower())

        for skill in validate_suite.SKILLS:
            skill_path = ROOT / "skills" / skill / "SKILL.md"
            skill_text = skill_path.read_text(encoding="utf-8")
            with self.subTest(path=skill_path):
                self.assertIn(
                    "../quant-research-shared/core/authority.md",
                    skill_text,
                )
                self.assertIn(
                    "../../shared/core/authority.md", skill_text
                )
                self.assertIn("paid", skill_text.lower())

            path = ROOT / "skills" / skill / "agents" / "openai.yaml"
            prompt = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=path):
                self.assertIn("remote", prompt)
                self.assertIn("paid", prompt)


if __name__ == "__main__":
    unittest.main()
