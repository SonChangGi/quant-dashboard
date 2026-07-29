from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

import capability_model


def normalized(relative: str) -> str:
    return " ".join(
        (ROOT / relative).read_text(encoding="utf-8").lower().split()
    )


class FreeDataPolicyTests(unittest.TestCase):
    def test_paid_data_and_free_to_paid_paths_are_ineligible(self) -> None:
        authority = normalized("shared/core/authority.md")
        for phrase in (
            "paid data is ineligible",
            "time-limited free trial",
            "expiring credit",
            "automatic free-to-paid conversion",
            "card, billing account",
            "payg",
            "overage",
            "paid tier",
            "no approval escape hatch",
        ):
            self.assertIn(phrase, authority)

        for field in (
            "paid_data_enabled",
            "paid_data_source_enabled",
            "paid_dataset_enabled",
        ):
            with self.subTest(field=field):
                errors = capability_model.policy_violations({field: True})
                self.assertTrue(errors)
                self.assertIn("must be false", "\n".join(errors))

        for command in (
            ["providerctl", "--paid-data=true"],
            ["providerctl", "enable", "paid", "dataset"],
        ):
            with self.subTest(command=command):
                self.assertTrue(
                    capability_model.paid_action_text_reasons(command)
                )

    def test_external_data_evidence_tracks_use_and_claim(self) -> None:
        contract = normalized(
            "shared/capabilities/external-data.md"
        )
        for phrase in (
            "`private_analysis`",
            "`derived_output`",
            "`raw_redistribution`",
            "unclear redistribution language is not by itself a blocker",
            "historical point-in-time provenance is required only when",
            "otherwise a non-pit",
            "separate corporate-actions feed",
            "only when acceptance depends on dividends",
        ):
            self.assertIn(phrase, contract)

    def test_free_fallbacks_precede_blocked_state(self) -> None:
        external = normalized(
            "shared/capabilities/external-data.md"
        )
        workflow = normalized(
            "shared/references/goal-and-subagents.md"
        )
        for phrase in (
            "official, regulator, exchange, or public-sector",
            "another eligible free provider",
            "free public filings",
            "defensible free proxy",
            "narrower period/universe/method",
        ):
            self.assertIn(phrase, external)
        self.assertIn(
            "use `blocked` only after safe in-scope free alternatives",
            workflow,
        )

    def test_release_delivery_is_separate_from_risk_assurance(self) -> None:
        workflow = normalized(
            "shared/references/goal-and-subagents.md"
        )
        self.assertIn(
            "risk assurance is `light`, `standard`, or `strict`; delivery is "
            "`local` or `release`",
            workflow,
        )
        self.assertIn(
            "it uses the selected `light`, `standard`, or `strict` local proof",
            workflow,
        )
        self.assertIn(
            "it does not automatically import the strict review stack",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
