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
    def test_selected_route_cannot_reach_billing(self) -> None:
        authority = normalized("shared/core/authority.md")
        for phrase in (
            "required scope at zero charge",
            "no card, billing account, subscription, trial, or expiring credit",
            "no payg, paid overage, automatic upgrade",
            "hard-stop before any charge",
            "no chargeable fallback",
            "optional paid tiers",
            "chosen route cannot enroll in, depend on, or fall through",
            "no action-approval escape hatch",
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

    def test_discovery_order_is_distinct_from_route_selection(self) -> None:
        external_data = normalized("shared/capabilities/external-data.md")
        discovery = external_data.split(
            "treat this order as a discovery aid", 1
        )[1]
        candidates = (
            "usable project source",
            "official, regulator",
            "another eligible free provider",
            "reproducible free derivation",
            "defensible free proxy",
            "explicit degraded or unavailable",
        )
        positions = [discovery.index(item) for item in candidates]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("select on claim fitness", external_data)
        for factor in (
            "claim fitness",
            "freshness",
            "coverage",
            "point-in-time",
            "rights",
            "reliability",
            "reproducibility",
        ):
            self.assertIn(factor, external_data)

        kernel = normalized("shared/references/adaptive-workflow.md")
        self.assertIn("`capabilities/external-data.md`", kernel)
        self.assertIn("`core/authority.md`", kernel)
        self.assertNotIn("treat this order as a discovery aid", kernel)

    def test_external_data_evidence_tracks_use_and_claim(self) -> None:
        contract = normalized("shared/capabilities/external-data.md")
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

    def test_external_data_rail_distinguishes_provider_from_selected_path(
        self,
    ) -> None:
        contract = normalized("shared/capabilities/external-data.md")
        self.assertIn("selected access path", contract)
        self.assertIn(
            "provider may offer separate optional paid tiers",
            contract,
        )
        self.assertIn(
            "cannot enroll in, depend on, or fall through",
            contract,
        )
        self.assertIn("hard-stops before any charge", contract)


if __name__ == "__main__":
    unittest.main()
