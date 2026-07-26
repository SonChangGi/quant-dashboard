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

    def test_all_release_surfaces_carry_canonical_guard(self) -> None:
        surfaces = [
            ROOT / "README.md",
            ROOT / "shared" / "references" / "operating-principles.md",
            ROOT / "shared" / "references" / "cost-and-authority.md",
        ]
        for skill in validate_suite.SKILLS:
            surfaces.extend(
                [
                    ROOT / "skills" / skill / "SKILL.md",
                    ROOT / "skills" / skill / "agents" / "openai.yaml",
                ]
            )
        for path in surfaces:
            with self.subTest(path=path):
                self.assertTrue(
                    validate_suite.has_canonical_zero_spend_guard(
                        path.read_text(encoding="utf-8")
                    )
                )


if __name__ == "__main__":
    unittest.main()
