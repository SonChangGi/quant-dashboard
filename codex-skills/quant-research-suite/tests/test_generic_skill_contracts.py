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

    def test_plan_treats_generated_probe_artifacts_as_target_writes(self) -> None:
        plan = skill("quant-plan")
        self.assert_concepts(
            plan,
            {
                "ordinary checks are not presumed read-only": (
                    r"\bdo not assume\b.{0,100}"
                    r"\b(?:test|linter|import|build|preview)\b.{0,120}"
                    r"\bnon-writing\b",
                ),
                "generated artifacts count as writes": (
                    r"\bbytecode\b.{0,80}\bcaches\b.{0,80}"
                    r"\b(?:coverage|snapshots|lockfiles)\b.{0,100}"
                    r"\bwrites\b",
                ),
                "unknown checks are redirected or copied": (
                    r"\buncertain check\b.{0,160}\bredirected\b"
                    r".{0,100}\bdisposable copy\b",
                ),
                "cleanup stays outside the target": (
                    r"\bremove only exact\b.{0,80}\bartifacts\b"
                    r".{0,100}\btask-scoped disposable path\b",
                ),
                "target drift is reported not repaired": (
                    r"\bif target state changed\b.{0,100}"
                    r"\bdo not mutate it further\b.{0,120}"
                    r"\bdisclose the exact residue\b",
                ),
            },
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
                    r"\b(?:do not|does not|must not|never)\b.{0,80}"
                    r"\b(?:create|use|load)\b.{0,60}\bledger\b",
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
                "material scope is recorded": (
                    r"\bmaterial scope\b.{0,100}"
                    r"\bobservable completion conditions?\b",
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
                "steering reports scope and quality-bar changes": (
                    r"\bafter steering\b.{0,120}\bscope\b.{0,80}"
                    r"\bcondition\b.{0,80}\bquality-bar\b.{0,80}"
                    r"\bstale proof\b",
                ),
                "compatible scope changes invalidate proof": (
                    r"\bwithin the stored outcome\b.{0,100}\bscope\b"
                    r".{0,100}\bconditions\b.{0,100}\binvalidate\b"
                    r".{0,80}\bproof\b",
                ),
                "outcome change becomes a different Goal": (
                    r"\boutcome-changing expansion\b.{0,80}"
                    r"\bdifferent goal\b",
                ),
            },
        )
        self.assertTrue(
            validate_suite.has_optional_condition_id_policy(goal)
        )
        self.assertTrue(
            validate_suite.has_conditional_condition_evidence_map(goal)
        )
        self.assertTrue(
            validate_suite.has_goal_scope_steering_contract(goal)
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
            "When useful, keep a compact\ncondition-to-evidence map in "
            "conversation rather than a separate ledger."
        )
        after_map = (
            "When ambiguity, partial invalidation, or machine audit makes it "
            "useful, keep a small mapping from conditions to evidence in "
            "conversation."
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
                "replacement observes an empty native slot": (
                    r"\bfresh\b.{0,40}`get_goal`.{0,120}"
                    r"\bno unfinished goal\b",
                ),
                "replacement asks only when ambiguous": (
                    r"\bif the request is ambiguous\b.{0,80}"
                    r"\bask which goal\b",
                ),
                "replacement never fakes a terminal state": (
                    r"\bnever misuse\b.{0,60}`complete`.{0,40}"
                    r"`blocked`.{0,60}\bclear the slot\b",
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
                "complete requested outcome": (
                    r"\bcomplete\b.{0,50}\brequested outcome\b",
                    r"\brequested outcome\b.{0,50}\bcomplete\b",
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
                "least-churn bounded change": (
                    r"\bbounded coherent (?:change|patch)\b.{0,100}"
                    r"\bleast unrelated churn\b",
                ),
                "extra scope needs request or target evidence": (
                    r"\badd new\b.{0,180}\bonly when\b.{0,80}"
                    r"\brequest or target evidence\b",
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
        for unsafe_expansion in (
            "Continue after acceptance while optional polish remains.",
            "Continue while any improvement could still be useful.",
            "Continue for hypothetical risks after the requested result works.",
            "Continue after acceptance, but do not skip tests.",
        ):
            with self.subTest(unsafe_expansion=unsafe_expansion):
                errors = validate_suite._validate_public_skill(
                    "quant-developer",
                    developer + f"\n{unsafe_expansion}\n",
                )
                self.assertIn(
                    "quant-developer: open-ended improvement loop is prohibited",
                    errors,
                )

    def test_quality_frontier_is_complete_without_becoming_open_ended(
        self,
    ) -> None:
        kernel = read("shared/references/adaptive-workflow.md")
        plan = skill("quant-plan")
        goal = skill("quant-goal")
        developer = skill("quant-developer")

        self.assert_concepts(
            kernel,
            {
                "strongest complete result": (
                    r"\bstrongest complete result\b.{0,140}"
                    r"\brequest\b.{0,100}\bconstraints\b",
                ),
                "proportionality is not minimum effort": (
                    r"\bproportionality\b.{0,100}\bnot least effort\b",
                ),
                "quality bar is stable rather than self-expanding": (
                    r"\bset the proportional quality bar\b.{0,160}"
                    r"\bbefore substantial action\b.{0,180}"
                    r"\bdo not repeatedly raise it\b",
                ),
                "material quality is established-bar bounded": (
                    r"\bmaterial gap against the established quality bar\b"
                    r".{0,200}\bnot permission to expand the bar\b",
                ),
                "quality debt stays bounded": (
                    r"\bquality debt\b.{0,160}"
                    r"\b(?:cosmetic|speculative|adjacent)\b",
                ),
                "quality-bar stop": (
                    r"\bstop once\b.{0,120}\bproportional quality bar\b"
                    r".{0,100}\bquality debt\b",
                ),
            },
        )
        self.assertRegex(
            normalized(plan),
            r"\bleanest communication form\b.{0,120}"
            r"\bbrevity\b.{0,80}\bnot reduce\b",
        )
        self.assertIn("minimal churn is not minimum effort", normalized(developer))
        for role in (goal, developer):
            with self.subTest(role=role.splitlines()[1]):
                body = normalized(role)
                self.assertIn(
                    "material gap against the established quality bar",
                    body,
                )
                self.assertIn("proportional quality bar", body)
                self.assertRegex(
                    body,
                    r"\b(?:cosmetic|speculative|adjacent)\b.{0,120}"
                    r"\bquality debt\b",
                )

    def test_orchestration_is_early_visible_and_integrated_not_ceremonial(
        self,
    ) -> None:
        kernel = read("shared/references/adaptive-workflow.md")
        body = normalized(kernel)
        self.assert_concepts(
            kernel,
            {
                "dependency-shaped coordination": (
                    r"\bderive the dependency shape\b",
                ),
                "delegation can influence route": (
                    r"\bbounded subagents\b.{0,160}"
                    r"\bearly enough\b.{0,80}\binfluence the route\b",
                ),
                "parent keeps progressing": (
                    r"\bparent continues\b.{0,80}\bnon-overlapping work\b",
                ),
                "native status visibility": (
                    r"\bhost-native plan or status\b.{0,140}"
                    r"\bownership\b.{0,80}\bdependencies\b",
                ),
                "one integrated state": (
                    r"\bone integrated state\b.{0,100}"
                    r"\bjudging the whole result\b",
                ),
                "conflicts are tested": (
                    r"\bfindings conflict\b.{0,120}"
                    r"\btest the competing claims\b",
                ),
                "retry is classified": (
                    r"\bretry only\b.{0,160}\btransient\b"
                    r".{0,100}\bsafe to repeat\b",
                ),
                "same-state independent review": (
                    r"\bfresh independent reviewer\b.{0,180}"
                    r"\bsame integrated state\b",
                ),
            },
        )
        self.assertIn("not a mandatory packet", body)
        self.assertIn("do not create a project file", body)
        self.assertIn("do not add a reviewer merely to satisfy a count", body)

    def test_flexible_recovery_and_authority_additions_are_bounded(self) -> None:
        plan = skill("quant-plan")
        goal = skill("quant-goal")
        developer = skill("quant-developer")
        kernel = read("shared/references/adaptive-workflow.md")

        self.assert_concepts(
            plan,
            {
                "isolated probe output": (
                    r"\btask-scoped temporary\b",
                ),
                "existing authenticated read-only access": (
                    r"\bexisting project-scoped\b.{0,180}"
                    r"\bauthenticated read-only\b",
                ),
                "secret-hiding unchanged authentication": (
                    r"\bsecrets stay hidden\b.{0,120}"
                    r"\b(?:login|scope|stored credentials)\b.{0,120}"
                    r"\bunchanged\b",
                ),
                "isolated lockfile dependencies": (
                    r"\blockfile\b.{0,100}\bdependencies\b.{0,100}"
                    r"\bisolation\b",
                ),
                "direct checks are known non-writing": (
                    r"\brun a check directly\b.{0,80}\bknown\b"
                    r".{0,40}\bnon-writing\b",
                ),
                "possible writes stay isolated": (
                    r"\bmay write\b.{0,120}\b(?:disposable copy|redirect)\b",
                ),
                "copy isolates external writable state": (
                    r"\bdisposable copy\b.{0,100}"
                    r"\bredirect writable home\b",
                ),
                "non-writing checks avoid isolation ceremony": (
                    r"\bskip isolation\b.{0,80}\bproven non-writing\b",
                ),
                "target stays unchanged and remote writes stay absent": (
                    r"\bconfirm target state\b.{0,80}\bunchanged\b"
                    r".{0,120}\bno remote mutation\b.{0,80}"
                    r"\b(?:occurred|requested or succeeded)\b",
                ),
                "no provider or remote writes": (
                    r"\bpermit no provider or remote writes\b",
                ),
                "unsafe probe is skipped": (
                    r"\bskip the probe\b",
                ),
            },
        )
        for unsafe_probe_expansion in (
            "Provider and remote writes are permitted during the probe.",
            (
                "Unlocked dependencies may be installed into the target "
                "environment during the probe."
            ),
            (
                "Ignored target-tree output may be written and cleaned after "
                "the probe."
            ),
            "Provider writes may be permitted, but do not log secrets.",
        ):
            with self.subTest(unsafe_probe_expansion=unsafe_probe_expansion):
                errors = validate_suite._validate_public_skill(
                    "quant-plan",
                    plan + f"\n{unsafe_probe_expansion}\n",
                )
                self.assertIn(
                    "quant-plan: probe must not permit provider writes or "
                    "unsafe dependency installation",
                    errors,
                )
        self.assert_concepts(
            goal,
            {
                "recovery after context loss": (
                    r"\b(?:long external wait|context compaction)\b.{0,180}"
                    r"\b(?:restate|recover|rebuild)\b",
                ),
                "retained evidence is rechecked": (
                    r"\bretained evidence\b.{0,100}\bavailable\b.{0,60}\bfresh\b",
                ),
                "no fixed recovery schema": (
                    r"\b(?:avoid|do not (?:introduce|require))\b.{0,60}"
                    r"\bfixed snapshot schema\b",
                ),
            },
        )
        self.assert_concepts(
            developer,
            {
                "remote execution needs explicit target authority": (
                    r"\bexplicit current-user request\b.{0,120}"
                    r"\bexecute\b.{0,120}\bidentified target\b"
                    r".{0,120}\bonly\b",
                ),
                "local preparation is not remote authority": (
                    r"\b(?:design\w*|implement\w*|prepar\w*)\b"
                    r".{0,160}\blocally\b"
                    r".{0,100}\bdoes not authorize\b.{0,80}\bremote\b",
                ),
                "paid data remains unavailable": (
                    r"\bpaid data\b.{0,60}\bno approval path\b",
                ),
            },
        )
        self.assert_concepts(
            kernel,
            {
                "worker reuse is context-dependent": (
                    r"\bsame role and domain\b.{0,120}\bcontext\b"
                    r".{0,120}\b(?:delta|changed scope|changed evidence)\b",
                ),
                "stale worker is replaced": (
                    r"\bfresh worker\b.{0,120}"
                    r"\b(?:cancellation|drift|off-track|unavailable context)\b",
                ),
                "one-off waits use host lifecycle": (
                    r"\bone-off\b.{0,100}\bwait\b.{0,120}"
                    r"\b(?:monitor|continuation)\b",
                ),
                "available host surfaces are negotiated": (
                    r"\bsurfaces the host actually exposes\b",
                ),
                "serial fallback": (
                    r"\botherwise serial work\b",
                ),
                "worker claim needs parent proof": (
                    r"\bworker completion claim is not proof\b",
                ),
                "persistent automation needs separate authority": (
                    r"\bpersistent automation\b.{0,120}\bseparate\b"
                    r".{0,120}\bmutation\b.{0,180}\bcurrent user requested\b",
                ),
                "repository mutation has a routed rail": (
                    r"\bproject file edits\b.{0,180}"
                    r"`capabilities/repo-mutation\.md`",
                ),
            },
        )

    def test_external_host_patterns_remain_bounded_and_host_neutral(self) -> None:
        kernel = read("shared/references/adaptive-workflow.md")
        scheduled = read("shared/capabilities/scheduled-automation.md")

        self.assert_concepts(
            kernel,
            {
                "isolation is not a security sandbox": (
                    r"\b(?:isolated root|worktree)\b.{0,120}\bnot\b"
                    r".{0,60}\bsecurity sandbox\b",
                ),
                "isolation does not expand authority": (
                    r"\b(?:isolated root|worktree)\b.{0,180}"
                    r"\bnever expands\b.{0,60}\bauthority\b",
                ),
                "isolated writer is bound to its integration context": (
                    r"\bexact root\b.{0,80}\bverified baseline\b.{0,80}"
                    r"\bintegration target\b.{0,80}\bacceptance\b",
                ),
                "duplicate implementation stays conditional": (
                    r"\bduplicate implementation\b.{0,80}\bonly\b"
                    r".{0,100}\b(?:explicit comparison|material uncertainty)\b",
                ),
                "one candidate is integrated and reverified": (
                    r"\bintegrate one coherent\b.{0,80}\bcandidate\b"
                    r".{0,180}\brerun affected proof\b",
                ),
            },
        )
        self.assert_concepts(
            scheduled,
            {
                "context-free runner gets a self-contained job": (
                    r"\brunner\b.{0,100}\bdoes not inherit\b.{0,100}"
                    r"\bconversation\b.{0,120}\bself-contained\b",
                ),
                "scheduled work does not rely on prior conversation": (
                    r"\bdo not rely on\b.{0,120}\b(?:memory|prior chat)\b",
                ),
            },
        )

        combined = normalized(kernel + "\n" + scheduled)
        for product_name in ("orca", "lobehub", "claude", "opencode"):
            with self.subTest(product_name=product_name):
                self.assertNotIn(product_name, combined)
        self.assertIn(
            "do not require fixed roles, models, worker counts, review counts, "
            "worktrees",
            combined,
        )

    def test_ordinary_base_rails_have_no_legacy_runtime_labels(self) -> None:
        for relative in validate_suite.ORDINARY_CAPABILITY_FILES:
            text = read(f"shared/capabilities/{relative}")
            with self.subTest(relative=relative):
                self.assertIsNone(
                    re.search(r"(?m)^Activate\b", text)
                )
                self.assertIsNone(
                    re.search(r"(?m)^Evidence gates?:", text)
                )

        analysis = read("shared/capabilities/analysis.md")
        external_data = read("shared/capabilities/external-data.md")
        self.assertNotIn("result_identity_fields", analysis)
        self.assertNotIn("result_identity_pointers", analysis)
        self.assertNotIn("access_eligibility", external_data)

        compatibility_source = (
            read("shared/templates/quant-project.schema.json")
            + read("shared/schemas/quant-project-v2.schema.json")
        )
        self.assertIn("result_identity_fields", compatibility_source)
        self.assertIn("access_eligibility", compatibility_source)

        self.assert_concepts(
            analysis,
            {
                "claim-proportional quant validity": (
                    r"\bempirical investment claim\b.{0,160}"
                    r"\bonly\b.{0,80}\bmaterial\b",
                ),
                "timing and universe validity": (
                    r"\b(?:timing|leakage)\b.{0,160}"
                    r"\b(?:universe|survivorship)\b",
                ),
                "cost and stability validity": (
                    r"\b(?:fees|slippage|turnover)\b.{0,180}"
                    r"\b(?:out-of-sample|overfitting|multiple-testing)\b",
                ),
                "no universal quant checklist": (
                    r"\bdo not\b.{0,60}\buniversal checklist\b",
                ),
            },
        )

        scheduled = read("shared/capabilities/scheduled-automation.md")
        publication = read("shared/capabilities/publication.md")
        chart = read("shared/capabilities/interactive-chart.md")
        public_web = read("shared/capabilities/public-web.md")
        remote_release = read("shared/capabilities/remote-release.md")
        self.assertRegex(
            normalized(scheduled),
            r"\bselect only\b.{0,80}\bmaterial\b.{0,100}\bactual runner\b",
        )
        self.assertRegex(
            normalized(publication),
            r"\bproject's native promotion model\b.{0,220}"
            r"\bwithout introducing pointer architecture\b",
        )
        chart_body = normalized(chart)
        self.assertIn("examples, not a universal checklist", chart_body)
        self.assertIn("when both states exist", chart_body)
        self.assertIn("adds no duplicate approval boundary", normalized(public_web))
        self.assertIn("only affected or applicable", normalized(public_web))
        release_body = normalized(remote_release)
        self.assertIn("relevant preflight and proof", release_body)
        self.assertIn("relevant target identities", release_body)
        self.assertIn("applicable authentication", release_body)
        self.assertNotIn("selection adds gates", release_body)

    def test_kernel_routes_data_policy_without_duplicating_details(
        self,
    ) -> None:
        kernel = read("shared/references/adaptive-workflow.md")
        external_data = read("shared/capabilities/external-data.md")
        authority = read("shared/core/authority.md")
        self.assert_concepts(
            kernel,
            {
                "external data owner": (
                    r"`capabilities/external-data\.md`",
                ),
                "authority owner": (
                    r"`core/authority\.md`",
                ),
                "selective loading": (
                    r"\bdo not\b.{0,100}\bload\b.{0,100}\bnon-data work\b",
                ),
            },
        )
        self.assert_concepts(
            external_data,
            {
                "claim-fit source selection": (
                    r"\bselect on\b.{0,120}\bclaim fitness\b",
                ),
                "freshness coverage and semantics": (
                    r"\bfreshness\b.{0,80}\bcoverage\b.{0,80}"
                    r"\bfield semantics\b",
                ),
                "rights and reproducibility": (
                    r"\brights\b.{0,100}\breliability\b.{0,80}"
                    r"\breproducibility\b",
                ),
                "degraded fallback": (
                    r"\bdegraded or unavailable\b",
                ),
            },
        )
        self.assertIn("hard-stop before any charge", normalized(authority))
        for duplicated_detail in (
            r"\bpayment method\b",
            r"\bpayg\b.{0,30}\boverage\b",
            r"\bchargeable fallback\b",
            r"\boptional paid tiers\b",
        ):
            self.assertIsNone(re.search(duplicated_detail, normalized(kernel)))

        duplicated_kernel = kernel + "\nPAYG, including overage charges.\n"
        self.assertTrue(
            any(
                "detailed data policy belongs in its selected rails"
                in error
                for error in validate_suite._validate_kernel(
                    duplicated_kernel
                )
            )
        )

    def test_developer_is_default_entry_and_names_the_base_input_flow(
        self,
    ) -> None:
        developer = normalized(skill("quant-developer"))
        self.assertIn("ordinary public entry", developer)
        self.assertIn("analysis-input flow", developer)
        self.assertNotIn("analysis-input binding", developer)

    def test_kernel_does_not_hard_code_product_or_scale_thresholds(
        self,
    ) -> None:
        kernel = normalized(read("shared/references/adaptive-workflow.md"))
        for token in (
            "multiagentv2",
            "multi_agent_v1",
            "multi_agent_v2",
            "gpt-5",
            "claude-",
            "spawn_agent",
            "create_thread",
            "wait_threads",
            "send_message_to_thread",
            "three workers",
            "3+ files",
            "200 loc",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, kernel)

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
