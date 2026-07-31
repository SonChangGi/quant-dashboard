from __future__ import annotations

import re
import unittest
from pathlib import Path

import validate_suite


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SKILLS = ("quant-plan", "quant-goal", "quant-developer")
ADAPTIVE_REFERENCE = "adaptive-workflow.md"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def skill(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


class GenericSkillContractTests(unittest.TestCase):
    def assert_concept(
        self,
        text: str,
        label: str,
        *patterns: str,
    ) -> None:
        body = normalized(text)
        self.assertTrue(
            any(re.search(pattern, body) for pattern in patterns),
            f"missing {label}: expected one of {patterns!r}",
        )

    def assert_concepts(
        self,
        text: str,
        concepts: dict[str, tuple[str, ...]],
    ) -> None:
        for label, patterns in concepts.items():
            with self.subTest(concept=label):
                self.assert_concept(text, label, *patterns)

    def test_public_skills_are_role_deltas_over_one_adaptive_kernel(self) -> None:
        kernel_path = ROOT / "shared" / "references" / ADAPTIVE_REFERENCE
        self.assertTrue(kernel_path.is_file())
        kernel = kernel_path.read_text(encoding="utf-8")
        self.assert_concepts(
            kernel,
            {
                "environment discovery": (
                    r"\b(?:environment|workspace|target)\b.{0,100}"
                    r"\b(?:inspect|discover|inventory)\b",
                    r"\b(?:inspect|discover|inventory)\b.{0,100}"
                    r"\b(?:environment|workspace|target)\b",
                ),
                "selective delegation": (
                    r"\b(?:delegate|subagents?|agent team|parallel lanes?)\b",
                ),
                "free data": (
                    r"\b(?:zero[- ]billing|no[- ]billing|free data|free source)\b",
                ),
                "real-surface evidence": (
                    r"\b(?:real|actual) (?:consumer )?surface\b",
                    r"\bconsumer-visible result\b",
                    r"\bsurface\b.{0,100}\boutcome\b.{0,60}\bwork\b",
                    r"\bobserve\b.{0,80}\breal result\b",
                ),
            },
        )

        role_concepts = {
            "quant-plan": {
                "read-only role": (r"\bread-only\b",),
                "decision and plan": (
                    r"\b(?:decide|decision)\b.{0,160}\bplan\b",
                    r"\bplan\b.{0,160}\b(?:decide|decision)\b",
                ),
                "implementation boundary": (
                    r"\bplanning does not authorize implementation\b",
                    r"\bread-only\b.{0,160}\bimplementation\b",
                ),
            },
            "quant-goal": {
                "native lifecycle": (r"\bnative goal\b",),
                "host lookup": (r"`get_goal`",),
                "host creation": (r"`create_goal`",),
                "terminal transition": (r"`update_goal`",),
            },
            "quant-developer": {
                "implementation role": (
                    r"\b(?:implement|implementation|deliver)\b",
                ),
                "real-surface verification": (
                    r"\bverify\b.{0,100}\b(?:actual|real).{0,30}surface\b",
                    r"\b(?:actual|real).{0,30}surface\b.{0,100}\bverify\b",
                ),
                "route adaptation": (
                    r"\b(?:repair|switch|change)\b.{0,120}"
                    r"\b(?:route|source|method|tool|decomposition)\b",
                ),
            },
        }
        for name, concepts in role_concepts.items():
            text = skill(name)
            with self.subTest(skill=name, contract="kernel link"):
                self.assertIn(ADAPTIVE_REFERENCE, text)
            self.assert_concepts(text, concepts)

    def test_plan_is_read_only_fact_first_and_decision_complete(self) -> None:
        plan = skill("quant-plan")
        self.assert_concepts(
            plan,
            {
                "fact-first discovery": (
                    r"\bdiscover\w*\b.{0,80}\bbefore\b.{0,80}\bask",
                    r"\binspect\b.{0,100}\bbefore\b.{0,80}\bquestion",
                ),
                "material questions only": (
                    r"\bask\b.{0,120}\bmaterial",
                    r"\bmaterial\b.{0,120}\bask\b",
                ),
                "recommended default": (
                    r"\b(?:reasonable|supported) default\b",
                    r"\brecommend(?:ed)? approach\b",
                ),
                "observable acceptance": (
                    r"\bobservable\b.{0,40}\bacceptance\b",
                    r"\bacceptance\b.{0,40}\bobservable\b",
                ),
                "self critique": (
                    r"\bself[- ]critique\b",
                    r"\bchallenge\b.{0,80}\b(?:draft|plan)\b",
                ),
                "audit evidence": (
                    r"\b(?:observed|inferred|unverified)\b",
                    r"\breproducible evidence\b",
                ),
            },
        )
        self.assertNotRegex(
            normalized(plan),
            r"\b(?:edit|modify|write) files\b.{0,40}\b(?:during|in) planning\b",
        )

    def test_goal_uses_native_state_without_duplicate_or_default_ledger(
        self,
    ) -> None:
        goal = skill("quant-goal")
        self.assert_concepts(
            goal,
            {
                "host state is authoritative": (
                    r"\bhost\b.{0,80}\bsource of truth\b",
                    r"\bnative goal\b.{0,100}\bsource of truth\b",
                ),
                "lookup before creation": (
                    r"`get_goal`.{0,120}\bbefore\b.{0,120}"
                    r"(?:`create_goal`|creat)",
                ),
                "no duplicate goal": (
                    r"\b(?:never|do not)\b.{0,60}\bduplicate goal\b",
                    r"\b(?:never|do not)\b.{0,60}\bcreate\b.{0,40}"
                    r"\ba duplicate\b",
                ),
                "no ordinary ledger": (
                    r"\b(?:do not|must not|never)\b.{0,80}\b(?:create|use|load)\b"
                    r".{0,60}\bledger\b",
                    r"\bledger\b.{0,100}\boff (?:the )?default path\b",
                ),
            },
        )

    def test_goal_completion_conditions_scale_without_fixed_ids_or_counts(
        self,
    ) -> None:
        goal = skill("quant-goal")
        body = normalized(goal)
        self.assert_concepts(
            goal,
            {
                "observable completion conditions": (
                    r"\bobservable\b.{0,50}\b(?:completion|success) conditions?\b",
                    r"\b(?:completion|success) conditions?\b.{0,50}\bobservable\b",
                ),
                "stable IDs are conditional": (
                    r"\bstable (?:condition )?ids?\b.{0,180}"
                    r"\b(?:long|multi|steering|audit)\b",
                    r"\b(?:long-running|multi-surface|repeated steering|machine "
                    r"audit)\b.{0,180}\bstable (?:condition )?ids?\b",
                ),
                "independent condition tracking": (
                    r"\bcondition\b.{0,100}\breferenced independently\b"
                    r".{0,120}\b(?:turns?|consumer surfaces?)\b",
                ),
                "partial evidence invalidation": (
                    r"\bsteering\b.{0,100}\binvalidate\b.{0,100}"
                    r"\bpart\b.{0,80}\bevidence\b",
                ),
                "creation result can prove storage": (
                    r"`create_goal`.{0,160}\b(?:return|result|response)\b"
                    r".{0,180}\b(?:confirm|prove|show|contain|return)\w*\b",
                ),
                "follow-up lookup is conditional": (
                    r"\b(?:if|when|unless)\b.{0,180}\b(?:return|result|response)\b"
                    r".{0,220}`get_goal`",
                    r"`get_goal`.{0,160}\b(?:only if|when|unless)\b"
                    r".{0,180}\b(?:return|result|response)\b",
                ),
                "steering invalidates affected evidence": (
                    r"\b(?:changed|affected|dependent)\b.{0,100}"
                    r"\b(?:stale|reverify|refresh)\b",
                    r"\binvalidate\b.{0,80}\bevidence\b.{0,80}\baffected\b",
                ),
            },
        )
        self.assertTrue(
            validate_suite.has_optional_condition_id_policy(goal)
        )
        self.assertTrue(
            validate_suite.has_conditional_condition_evidence_map(goal)
        )
        optional_inversions = (
            "Stable condition IDs are compulsory.",
            "Stable condition IDs are required by default.",
            "Every Goal uses stable condition IDs.",
            "Stable condition IDs should be assigned to each condition.",
        )
        for mutation in optional_inversions:
            with self.subTest(optional_policy=mutation):
                mutated = goal.replace(
                    "Stable condition IDs are optional.",
                    mutation,
                    1,
                )
                self.assertIn(
                    "quant-goal: stable condition IDs must remain optional",
                    validate_suite._validate_public_skill(
                        "quant-goal",
                        mutated,
                    ),
                )
        for obsolete in (
            r"\btwo to six\b",
            r"\bsc-1\b.{0,80}\bsc-6\b",
            r"\bcomplete `?sc-\*`? list\b",
            r"\bevery current `?sc-\*`?",
            r"\bstable (?:condition )?ids?\b.{0,80}"
            r"\b(?:required|mandatory|always)\b",
            r"\bcondition-to-evidence map\b.{0,80}"
            r"\b(?:required|mandatory|always)\b",
        ):
            with self.subTest(obsolete=obsolete):
                self.assertNotRegex(body, obsolete)

        universal_mutations = (
            "Identifiers are mandatory for every completion condition.",
            "Every completion condition needs a stable identifier.",
            "Each success condition shall carry an ID.",
            "Assign an ID to every completion condition.",
            "Use stable IDs for all completion conditions.",
            "Every completion condition is assigned an identifier.",
            "Identifiers are compulsory for every completion condition.",
            "All completion conditions get identifiers.",
            (
                "Condition IDs are optional only when required for every "
                "completion condition."
            ),
            "Stable condition IDs are required by default.",
            "Condition IDs are optional but required by default.",
            "Each condition must have an ID.",
            "All current conditions require identifiers.",
            "Every Goal assigns stable condition IDs.",
        )
        for mutation in universal_mutations:
            with self.subTest(mutation=mutation):
                errors = validate_suite._validate_public_skill(
                    "quant-goal",
                    goal + f"\n{mutation}\n",
                )
                self.assertIn(
                    "quant-goal: universal completion-condition IDs are "
                    "prohibited",
                    errors,
                )

        safe_mutations = (
            "Do not require IDs for every completion condition.",
            "Every completion condition may have an ID.",
            "Each completion condition can have an identifier when useful.",
            "No ID is mandatory for every completion condition.",
            "It is false that every completion condition must have an ID.",
            "Each completion condition gets an optional ID.",
            "Each completion condition uses an ID only when needed.",
        )
        for mutation in safe_mutations:
            with self.subTest(safe_id_policy=mutation):
                self.assertNotIn(
                    "quant-goal: universal completion-condition IDs are "
                    "prohibited",
                    validate_suite._validate_public_skill(
                        "quant-goal",
                        goal + f"\n{mutation}\n",
                    ),
                )

        paraphrased = goal.replace(
            "Stable condition IDs are optional.",
            (
                "Identifiers for completion conditions are used only when "
                "useful."
            ),
            1,
        )
        before_map = (
            "When IDs\nare active, add a compact live condition-to-evidence "
            "map only when multiple\nconditions, partial evidence "
            "invalidation, or machine-audit proof would\notherwise be "
            "ambiguous."
        )
        after_map = (
            "When IDs are active, add a small current mapping from conditions "
            "to evidence only if several conditions, partial invalidation, or "
            "machine audit would otherwise cause ambiguity."
        )
        self.assertIn(before_map, paraphrased)
        paraphrased = paraphrased.replace(before_map, after_map, 1)
        self.assertEqual(
            validate_suite._validate_public_skill(
                "quant-goal",
                paraphrased,
            ),
            [],
        )

        safe_map_policies = (
            (
                "Use a condition-to-evidence map when ambiguity or partial "
                "invalidation makes it useful."
            ),
            (
                "A mapping from conditions to evidence is optional for "
                "partial invalidation or machine audit."
            ),
            (
                "A condition-to-evidence map may be used for partial "
                "invalidation."
            ),
            (
                "Use condition-to-evidence mapping selectively for multiple "
                "conditions."
            ),
        )
        for policy in safe_map_policies:
            with self.subTest(safe_map_policy=policy):
                mutated = goal.replace(before_map, policy, 1)
                self.assertEqual(
                    validate_suite._validate_public_skill(
                        "quant-goal",
                        mutated,
                    ),
                    [],
                )

        unconditional_map_policies = (
            "Always maintain a map from every condition to its evidence.",
            "A condition-to-evidence map is required for all Goals.",
            "Map every condition to evidence on every turn.",
            "A condition-to-evidence map is compulsory for all Goals.",
            "Every Goal gets a map from conditions to evidence.",
            (
                "A map from conditions to evidence is required only when no "
                "ambiguity exists."
            ),
            "Goals receive a condition-to-evidence map by default.",
        )
        for policy in unconditional_map_policies:
            with self.subTest(unconditional_map_policy=policy):
                self.assertIn(
                    "quant-goal: unconditional condition-evidence mapping "
                    "is prohibited",
                    validate_suite._validate_public_skill(
                        "quant-goal",
                        goal + f"\n{policy}\n",
                    ),
                )

        map_prohibitions = (
            (
                "Do not use a condition-to-evidence map when ambiguity or "
                "partial invalidation makes it useful."
            ),
            (
                "Never map conditions to evidence, even when ambiguity or "
                "partial invalidation makes it needed."
            ),
            (
                "Avoid using a condition-to-evidence map when ambiguity makes "
                "it useful."
            ),
            (
                "A condition-to-evidence map may not be used when partial "
                "invalidation makes it needed."
            ),
            (
                "Refrain from mapping conditions to evidence when ambiguity "
                "makes it useful."
            ),
            (
                "Do not ever use a condition-to-evidence map when ambiguity "
                "makes it useful."
            ),
            (
                "A condition-to-evidence map is forbidden even when partial "
                "invalidation makes it useful."
            ),
        )
        for policy in map_prohibitions:
            with self.subTest(map_prohibition=policy):
                self.assertIn(
                    "quant-goal: useful condition-evidence mapping must not "
                    "be prohibited",
                    validate_suite._validate_public_skill(
                        "quant-goal",
                        goal + f"\n{policy}\n",
                    ),
                )

    def test_goal_budget_and_terminal_rules_match_native_lifecycle(self) -> None:
        goal = skill("quant-goal")
        self.assert_concepts(
            goal,
            {
                "explicit positive token budget": (
                    r"`token_budget`.{0,100}\bexplicit",
                    r"\bexplicit\b.{0,100}`token_budget`",
                ),
                "budget is not terminal evidence": (
                    r"\btoken\b.{0,100}\bnever\b.{0,100}"
                    r"\b(?:completion|blocking) reason\b",
                    r"\btoken\b.{0,100}\bnot\b.{0,100}"
                    r"\b(?:completion|blocking) reason\b",
                    r"\bbudget\b.{0,120}\bnot\b.{0,80}"
                    r"\b(?:complete|blocked)\b",
                ),
                "completion conditions have fresh evidence": (
                    r"\b(?:completion|success) conditions?\b.{0,140}"
                    r"\bfresh\b.{0,80}\bevidence\b",
                    r"\bfresh\b.{0,80}\bevidence\b.{0,140}"
                    r"\b(?:completion|success) conditions?\b",
                ),
                "three-turn blocker": (
                    r"\bthree consecutive goal turns\b",
                ),
                "status-only update": (
                    r"`?update_goal\b.{0,180}\b(?:complete|blocked)\b",
                ),
            },
        )
        for state in ("waiting", "paused", "cancelled", "superseded"):
            with self.subTest(state=state):
                self.assertRegex(
                    normalized(goal),
                    rf"\b(?:never invent|does not invent|do not invent)\b"
                    rf".{{0,180}}\b{state}\b|\b{state}\b.{{0,180}}"
                    rf"\b(?:never invent|does not invent|do not invent)\b",
                )

    def test_developer_stops_on_acceptance_not_open_ended_polish(self) -> None:
        developer = skill("quant-developer")
        body = normalized(developer)
        self.assert_concepts(
            developer,
            {
                "complete accepted outcome": (
                    r"\bcomplete\b.{0,50}\baccepted outcome\b",
                    r"\baccepted outcome\b.{0,50}\bcomplete\b",
                ),
                "continue for unmet acceptance": (
                    r"\bunmet\b.{0,50}\bacceptance conditions?\b",
                    r"\bacceptance conditions?\b.{0,50}\b(?:remain|unmet)\b",
                ),
                "continue for material risk": (
                    r"\bmaterial risk\b.{0,120}\b(?:invalidate|undermine|remain)\b",
                    r"\b(?:invalidate|undermine)\b.{0,120}\bmaterial risk\b",
                ),
                "non-required work is quality debt": (
                    r"\bquality debt\b",
                ),
                "route switching": (
                    r"\b(?:repair|switch|change)\b.{0,120}"
                    r"\b(?:route|source|method|tool|decomposition)\b",
                ),
            },
        )
        self.assertNotIn(
            "continue this loop while a safe, relevant next action can improve "
            "the result",
            body,
        )

    def test_kernel_separates_free_route_discovery_from_final_selection(
        self,
    ) -> None:
        kernel = read("shared/references/adaptive-workflow.md")
        self.assert_concepts(
            kernel,
            {
                "free route discovery": (
                    r"\b(?:explore|discover)\b.{0,100}"
                    r"\b(?:candidates?|routes?|sources?)\b",
                ),
                "zero-billing eligibility": (
                    r"\bzero[- ]billing\b",
                    r"\bno[- ]billing\b",
                ),
                "claim-fit selection": (
                    r"\b(?:select|choose)\b.{0,160}\b(?:claim|fitness|fit)\b",
                    r"\b(?:claim|fitness|fit)\b.{0,160}\b(?:select|choose)\b",
                ),
                "freshness and coverage": (
                    r"\b(?:freshness|as-of)\b",
                    r"\bcoverage\b",
                ),
                "field and revision meaning": (
                    r"\bfield meaning\b",
                    r"\b(?:revision|point-in-time|pit)\b",
                ),
                "rights and reproducibility": (
                    r"\b(?:display|redistribution) rights\b",
                    r"\breproducib",
                ),
            },
        )
        self.assert_concept(
            kernel,
            "paid and free-to-paid data excluded",
            r"\bpaid data\b.{0,100}\b(?:outside|ineligible|prohibited)\b",
            r"\b(?:outside|ineligible|prohibited)\b.{0,100}\bpaid data\b",
            r"\bpaid data\b.{0,100}\bno approval path\b",
        )

    def test_real_surface_proof_keeps_delivery_stages_distinct(self) -> None:
        kernel = read("shared/references/adaptive-workflow.md")
        self.assert_concepts(
            kernel,
            {
                "consumer surface": (
                    r"\b(?:real|actual) consumer surface\b",
                    r"\bconsumer-visible result\b",
                    r"\bmatch proof to the consumer\b",
                    r"\bobserve\b.{0,80}\breal result\b",
                ),
                "stage-local evidence": (
                    r"\bproves only its own stage\b",
                    r"\bdoes not prove\b.{0,100}\bdownstream\b",
                ),
                "publication readback": (
                    r"\bpublication\b.{0,100}\breadback\b",
                ),
            },
        )

    def test_completion_report_is_reader_focused_and_evidence_based(self) -> None:
        developer = skill("quant-developer")
        self.assert_concepts(
            developer,
            {
                "achieved result": (
                    r"\bachieved (?:outcome|result)\b",
                    r"\bwhat (?:now )?works\b",
                ),
                "changed scope": (
                    r"\bchanged (?:areas?|scope|surfaces?)\b",
                    r"\b(?:areas?|scope|surfaces?) changed\b",
                ),
                "checks and observations": (
                    r"\bchecks?\b.{0,80}"
                    r"\b(?:run|observations?|evidence)\b",
                ),
                "honest limits": (
                    r"\b(?:limits?|limitations?|unverified items?)\b",
                ),
                "structured evidence is conditional": (
                    r"\bstructured evidence\b.{0,120}"
                    r"\b(?:only|when|requires?)\b",
                    r"\b(?:fixed|structured) evidence template\b"
                    r".{0,120}\b(?:not|rather than)\b",
                    r"\b(?:not|rather than)\b.{0,120}"
                    r"\b(?:fixed|structured) evidence template\b",
                    r"\bstructured receipts?\b.{0,180}\bexplicit\b",
                ),
            },
        )

    def test_legacy_runtime_is_source_compatibility_not_ordinary_work(
        self,
    ) -> None:
        expected_legacy = (
            "shared/references/goal-and-subagents.md",
            "shared/references/agent-orchestration.md",
            "shared/references/durable-runtime.md",
            "shared/scripts/goal_runtime.py",
            "shared/scripts/goal_ledger.py",
            "shared/scripts/team_protocol.py",
            "shared/schemas/goal-ledger-state.schema.json",
            "shared/schemas/team-run-packet.schema.json",
            "shared/schemas/worker-delivery-receipt.schema.json",
        )
        for relative in expected_legacy:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

        for name in PUBLIC_SKILLS:
            text = skill(name)
            with self.subTest(skill=name):
                self.assert_concepts(
                    text,
                    {
                        "legacy compatibility is explicit": (
                            r"\blegacy\b.{0,180}\bexplicit",
                            r"\bexplicit\b.{0,180}\blegacy\b",
                        ),
                        "existing contract is preserved": (
                            r"\bexisting\b.{0,100}\b(?:contract|depends)\b",
                        ),
                        "ordinary path does not auto-load legacy": (
                            r"\bordinary\b.{0,180}"
                            r"\b(?:do not|does not|must not|never|off "
                            r"(?:the )?(?:ordinary|default) path)\b"
                            r".{0,180}\b(?:manifest|ledger|receipt|legacy)\b",
                            r"\b(?:manifest|ledger|receipt|legacy)\b.{0,180}"
                            r"\b(?:off (?:the )?(?:ordinary|default) path|do not|"
                            r"does not|must not|never)\b"
                            r".{0,180}\bordinary\b",
                            r"\b(?:do not|does not|must not|never)\b.{0,180}"
                            r"\b(?:manifest|ledger|receipt|legacy)\b.{0,180}"
                            r"\bordinary\b",
                            r"\b(?:manifest|ledger|receipt|legacy)\b.{0,180}"
                            r"\boff the ordinary path\b",
                        ),
                    },
                )


if __name__ == "__main__":
    unittest.main()
