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
ROLE_DESCRIPTION_CONCEPTS = {
    "quant-plan": (
        r"\b(?:audit|plan)\b",
        r"\bread-only\b",
        r"\badapt\w*",
    ),
    "quant-goal": (
        r"\bnative goal\b",
        r"\b(?:complete|completion|blocker|blocked)\b",
        r"\badapt\w*",
    ),
    "quant-developer": (
        r"\b(?:implementation|change|deliver)\b",
        r"\b(?:verify|verification|surface)\b",
        r"\badapt\w*",
    ),
}
ADAPTIVE_REFERENCE = "adaptive-workflow.md"
ORDINARY_CAPABILITY_ROUTES = {
    "capabilities/analysis.md": (
        r"\b(?:analysis|calculation|compute|result)\b",
        r"\b(?:display|result|output)\b",
    ),
    "capabilities/external-data.md": (
        r"\b(?:external|provider|api|feed|file)\b",
        r"\b(?:data|source)\b",
    ),
    "capabilities/analysis-input-flow.md": (
        r"\b(?:ui|control|input)\b",
        r"\b(?:analysis|calculation|compute|result)\b",
    ),
    "capabilities/web-ui.md": (
        r"\b(?:layout|interaction|responsive|ui)\b",
    ),
    "capabilities/interactive-chart.md": (
        r"\bchart\b",
        r"\binteraction\b",
    ),
    "capabilities/backend.md": (
        r"\b(?:api|state|authentication|secrets?)\b",
    ),
    "capabilities/scheduled-automation.md": (
        r"\b(?:recurring|event|schedule|scheduled|automation)\b",
    ),
    "capabilities/public-web.md": (
        r"\bpublic\b",
        r"\b(?:url|route|web|page)\b",
    ),
    "capabilities/publication.md": (
        r"\b(?:artifact|pointer|current)\b",
        r"\b(?:publish|publication|update)\b",
    ),
    "capabilities/remote-release.md": (
        r"\b(?:push|pr|release|deployment|remote)\b",
    ),
}


def skill_text(skill: str) -> str:
    return (
        ROOT / "skills" / skill / "SKILL.md"
    ).read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return validate_suite.normalized_policy_text(text)


def normalized_skill_text(skill: str) -> str:
    return normalized(skill_text(skill))


def agent_metadata(skill: str) -> dict[str, object]:
    raw = (
        ROOT / "skills" / skill / "agents" / "openai.yaml"
    ).read_text(encoding="utf-8")
    value = validate_suite.agent_metadata(raw)
    if value is None:
        raise AssertionError(f"missing agent metadata for {skill}")
    return value


def markdown_table_rows(text: str) -> list[str]:
    rows: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(normalized(" | ".join(cells)))
    return rows


class SkillRoutingTests(unittest.TestCase):
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

    def assert_excluded_activation_context(
        self,
        text: str,
        label: str,
        context_pattern: str,
    ) -> None:
        clauses = re.split(r"(?<=[.!?;])\s+", normalized(text))
        matched = [
            clause
            for clause in clauses
            if re.search(context_pattern, clause)
            and re.search(r"\b(?:activat|select|invok)", clause)
        ]
        self.assertTrue(matched, f"missing invocation context {label!r}")
        self.assertTrue(
            any(
                re.search(
                    r"\b(?:not|never|does not|do not|isn't|cannot)\b",
                    clause,
                )
                for clause in matched
            ),
            f"{label!r} is mentioned without an explicit non-activation rule",
        )

    def test_exactly_three_public_skills_with_semantic_descriptions(
        self,
    ) -> None:
        discovered = {
            path.parent.name
            for path in (ROOT / "skills").glob("*/SKILL.md")
        }
        self.assertEqual(discovered, set(EXPECTED_SKILLS))
        self.assertEqual(tuple(validate_suite.SKILLS), EXPECTED_SKILLS)
        self.assertFalse((ROOT / "shared" / "SKILL.md").exists())

        for skill, patterns in ROLE_DESCRIPTION_CONCEPTS.items():
            metadata = validate_suite.frontmatter(skill_text(skill))
            description = normalized(metadata.get("description", ""))
            with self.subTest(skill=skill):
                self.assertEqual(metadata.get("name"), skill)
                self.assertIn(f"${skill}", description)
                self.assertRegex(description, r"\b(?:explicit|only when)\b")
                for pattern in patterns:
                    self.assertRegex(description, pattern)

    def test_public_skills_share_one_canonical_manual_invocation_contract(
        self,
    ) -> None:
        for skill in EXPECTED_SKILLS:
            text = skill_text(skill)
            body = normalized(text)
            metadata = agent_metadata(skill)

            with self.subTest(skill=skill):
                self.assertIs(
                    metadata["allow_implicit_invocation"],
                    False,
                )
                self.assertIn(f"${skill}", body)
                self.assertRegex(body, r"\bcurrent[- ]user\b")
                self.assertRegex(body, r"\bsame[- ]request\b")
                self.assertRegex(body, r"\b(?:trusted\b.{0,80})?metadata\b")
                self.assertRegex(
                    body,
                    r"\b(?:produced|derived|generated)\b.{0,120}"
                    r"\b(?:select|selector|invocation)\b",
                )
                self.assertTrue(
                    validate_suite.has_selector_metadata_clause(text, skill)
                )

                for label, pattern in {
                    "semantic match": r"\bsemantic match\b",
                    "quoted selector": r"\bquoted\b",
                    "negated selector": r"\bnegated\b",
                    "prior request": r"\b(?:earlier|prior|previous)\b",
                    "worker instruction": r"\b(?:worker|another agent)\b",
                }.items():
                    self.assert_excluded_activation_context(
                        text,
                        label,
                        pattern,
                    )

    def test_selector_metadata_trust_dimensions_cannot_be_decoupled(
        self,
    ) -> None:
        mutations = (
            (r"trusted current-user", "untrusted current-user"),
            (r"current-user, same-request", "request"),
            (
                r"metadata generated by that\s+selector",
                "metadata not generated by that selector",
            ),
            (
                r"metadata generated by that\s+selector",
                "metadata never generated by that selector",
            ),
            (
                r"metadata generated by that\s+selector",
                "metadata not reliably generated by that selector",
            ),
            (
                r"metadata generated by that\s+selector",
                "metadata generated by a different selector",
            ),
            (
                r"metadata generated by that\s+selector",
                "metadata generated independently of that selector",
            ),
            (
                r"metadata generated by that\s+selector",
                "metadata generated by any selector",
            ),
            (
                r"metadata generated by that\s+selector",
                "metadata generated by no selector",
            ),
            (
                r"metadata generated by that\s+selector",
                (
                    "metadata generated by a selector other than the current "
                    "user's selector"
                ),
            ),
            (
                r"metadata generated by that\s+selector",
                "metadata generated by any current-user selector",
            ),
            (
                r"metadata generated by that\s+selector",
                "metadata generated by that selector or another selector",
            ),
            (
                r"metadata generated by that\s+selector",
                (
                    "metadata generated by that selector and an unrelated "
                    "selector"
                ),
            ),
            (
                r"metadata generated by that\s+selector",
                "metadata generated by that selector or a second selector",
            ),
            (r"generated by that\s+selector", "provided by the host"),
            (r"same-request", "prior-request"),
            (r"same-request metadata", "not same-request metadata"),
            (r"trusted current-user", "trusted not-current-user"),
            (
                r"same-request metadata",
                "same-request metadata from a prior request",
            ),
        )
        expected = (
            "selector metadata must be trusted, current-user, same-request, "
            "and selector-derived"
        )
        for skill in EXPECTED_SKILLS:
            original = skill_text(skill)
            for pattern, replacement in mutations:
                with self.subTest(skill=skill, mutation=pattern):
                    mutated, count = re.subn(
                        pattern,
                        replacement,
                        original,
                        count=1,
                    )
                    self.assertEqual(count, 1)
                    errors = validate_suite._validate_public_skill(
                        skill,
                        mutated,
                    )
                    self.assertTrue(
                        any(expected in error for error in errors),
                        errors,
                    )

    def test_trusted_same_unfinished_task_continuation_is_bounded(
        self,
    ) -> None:
        for skill in EXPECTED_SKILLS:
            raw = skill_text(skill)
            body = normalized(raw)
            with self.subTest(skill=skill):
                self.assertTrue(
                    validate_suite.has_trusted_same_task_continuation(raw)
                )
                self.assertTrue(
                    validate_suite.has_bounded_continuation_exclusion(raw)
                )
                self.assertRegex(
                    body,
                    r"\btrusted\b.{0,80}\bmetadata\b.{0,240}"
                    r"\bsame\b.{0,40}\bunfinished\b.{0,60}\btask\b",
                )
                self.assertRegex(body, r"\b(?:clarification|steering)\b")
                self.assertRegex(body, r"\bcontinu\w*\b")
                self.assertRegex(body, r"\bordinary prior-turn\b")
                self.assertRegex(body, r"\bcompleted\b")
                self.assertRegex(body, r"\bunrelated\b")
                self.assertRegex(body, r"\bworker\b")

            unsafe_mutations = (
                ("trusted host metadata", "untrusted host metadata"),
                (
                    r"(without (?:a new|another) selector) only\s+when",
                    r"\1 even without",
                ),
                (
                    r"same unfinished,\s+already-active task",
                    "any prior task",
                ),
            )
            for pattern, replacement in unsafe_mutations:
                with self.subTest(skill=skill, mutation=pattern):
                    mutated, count = re.subn(
                        pattern,
                        replacement,
                        raw,
                        count=1,
                    )
                    self.assertEqual(count, 1)
                    self.assertIn(
                        f"{skill}: continuation must require trusted host "
                        "metadata for current-user clarification or steering "
                        "in the same unfinished already-active task",
                        validate_suite._validate_public_skill(skill, mutated),
                    )

            without_completed = raw.replace("completed", "active", 1)
            self.assertIn(
                f"{skill}: continuation must exclude completed, unrelated, "
                "and worker tasks",
                validate_suite._validate_public_skill(
                    skill,
                    without_completed,
                ),
            )

            appended_expansion = (
                raw
                + "\nTrusted host metadata may continue this role from any "
                "prior task without a selector.\n"
            )
            self.assertIn(
                f"{skill}: permissive continuation of prior, completed, "
                "unrelated, or worker tasks is prohibited",
                validate_suite._validate_public_skill(
                    skill,
                    appended_expansion,
                ),
            )

    def test_safe_selector_metadata_paraphrase_is_accepted(self) -> None:
        pattern = (
            r"trusted current-user, same-request metadata generated by that"
            r"\s+selector"
        )
        safe_paraphrases = (
            (
                "trusted metadata produced from the current user's selector "
                "in the same request"
            ),
            (
                "trusted metadata that the current user's selector generated "
                "in the same request"
            ),
            (
                "trusted current-user, same-request metadata emitted by that "
                "selector"
            ),
        )
        for skill in EXPECTED_SKILLS:
            original = skill_text(skill)
            for paraphrase in safe_paraphrases:
                paraphrased, count = re.subn(
                    pattern,
                    paraphrase,
                    original,
                    count=1,
                )
                self.assertEqual(count, 1)
                with self.subTest(skill=skill, paraphrase=paraphrase):
                    self.assertEqual(
                        validate_suite._validate_public_skill(
                            skill,
                            paraphrased,
                        ),
                        [],
                    )

    def test_safe_kernel_skip_paraphrase_is_accepted(self) -> None:
        pattern = (
            r"If\s+uncertain,\s+read\s+the\s+kernel's\s+routing\s+table"
            r"\s+before\s+deciding\s+to\s+skip\s+it\."
        )
        safe_paraphrases = (
            "When unsure, consult the kernel router before skipping it.",
            (
                "When unsure, do not skip without consulting the kernel "
                "router."
            ),
            (
                "When unsure, skip only after consulting the kernel router."
            ),
        )
        for skill in EXPECTED_SKILLS:
            original = skill_text(skill)
            for paraphrase in safe_paraphrases:
                paraphrased, count = re.subn(
                    pattern,
                    paraphrase,
                    original,
                    count=1,
                )
                self.assertEqual(count, 1)
                with self.subTest(skill=skill, paraphrase=paraphrase):
                    self.assertEqual(
                        validate_suite._validate_public_skill(
                            skill,
                            paraphrased,
                        ),
                        [],
                    )

    def test_kernel_skip_policy_inversions_are_rejected(self) -> None:
        pattern = (
            r"If\s+uncertain,\s+read\s+the\s+kernel's\s+routing\s+table"
            r"\s+before\s+deciding\s+to\s+skip\s+it\."
        )
        inversions = (
            (
                "If uncertain, do not read the kernel's routing table before "
                "deciding to skip it."
            ),
            (
                "If uncertain, skip without checking the kernel router."
            ),
            "If uncertain, skip before checking the kernel router.",
            (
                "If uncertain, avoid reading the kernel's routing table "
                "before deciding to skip it."
            ),
            (
                "If uncertain, refrain from consulting the kernel router "
                "before skipping it."
            ),
        )
        expected = "uncertain narrow work must consult routing before skip"
        for skill in EXPECTED_SKILLS:
            original = skill_text(skill)
            for inversion in inversions:
                mutated, count = re.subn(
                    pattern,
                    inversion,
                    original,
                    count=1,
                )
                self.assertEqual(count, 1)
                with self.subTest(skill=skill, inversion=inversion):
                    self.assertTrue(
                        any(
                            expected in error
                            for error in validate_suite._validate_public_skill(
                                skill,
                                mutated,
                            )
                        )
                    )

    def test_agent_prompts_are_small_manual_role_summaries(self) -> None:
        for skill in EXPECTED_SKILLS:
            metadata = agent_metadata(skill)
            prompt = metadata["default_prompt"]
            self.assertIsInstance(prompt, str)
            assert isinstance(prompt, str)
            mentioned_skills = re.findall(
                r"\$(quant-(?:plan|goal|developer))",
                prompt,
            )

            with self.subTest(skill=skill):
                self.assertEqual(mentioned_skills, [skill])
                self.assertFalse("\n" in prompt)
                self.assertTrue(prompt.strip())
                self.assertLessEqual(len(prompt.split()), 60)
                self.assertIs(
                    metadata["allow_implicit_invocation"],
                    False,
                )
                selector_copy = normalized(
                    f"{metadata['short_description']} {prompt}"
                )
                self.assertRegex(
                    selector_copy,
                    r"\badapt\w*|\bcapability[- ]aware\b",
                )
                if skill == "quant-plan":
                    self.assertRegex(prompt.lower(), r"\baudit\b")
                    self.assertRegex(prompt.lower(), r"\bquick plan\b")
                    self.assertRegex(
                        prompt.lower(),
                        r"\bdecision-complete implementation plan\b",
                    )

    def test_native_goal_continuation_is_not_a_new_skill_invocation(
        self,
    ) -> None:
        goal = normalized_skill_text("quant-goal")
        router = normalized(
            (
                ROOT / "shared" / "core" / "context-routing.md"
            ).read_text(encoding="utf-8")
        )
        self.assertRegex(
            goal,
            r"\bnative goal\b.{0,180}\b(?:continu|follow-up|resume)\b",
        )
        self.assertRegex(
            goal,
            r"\b(?:continu\w*|follow-up|resume)\b.{0,180}"
            r"\bnot\b.{0,60}\b(?:activation|invocation)\b",
        )
        self.assertRegex(
            goal,
            r"\bnever\b.{0,80}\bgoal state\b.{0,120}\bordinary\b"
            r".{0,120}\bworker task\b",
        )
        self.assertIn("already-active quant goal", router)
        self.assertIn("native lifecycle work", router)

    def test_agent_policy_is_required_and_fails_closed(self) -> None:
        policy = "policy:\n  allow_implicit_invocation: false\n"
        raw = (
            ROOT / "skills" / "quant-plan" / "agents" / "openai.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn(policy, raw)
        self.assertIsNone(validate_suite.agent_metadata(raw.replace(policy, "")))

        with tempfile.TemporaryDirectory() as tmp:
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
            agent_file.write_text(
                raw.replace(
                    "allow_implicit_invocation: false",
                    "allow_implicit_invocation: true",
                ),
                encoding="utf-8",
            )

            with mock.patch.object(validate_suite, "ROOT", copied_root):
                errors = validate_suite.validate()

            self.assertTrue(
                any("implicit invocation" in error for error in errors),
                errors,
            )

    def test_multi_skill_composition_preserves_role_boundaries(self) -> None:
        plan = normalized_skill_text("quant-plan")
        goal = normalized_skill_text("quant-goal")
        developer = normalized_skill_text("quant-developer")
        router = normalized((
            ROOT / "shared" / "core" / "context-routing.md"
        ).read_text(encoding="utf-8"))

        self.assertRegex(
            plan,
            r"\bread-only\b.{0,180}\bimplementation\b",
        )
        self.assertRegex(
            goal,
            r"\bgoal lifecycle\b.{0,180}\bintegration\b"
            r"|\bintegration\b.{0,180}\bgoal lifecycle\b",
        )
        self.assertRegex(
            developer,
            r"\b(?:does not|never)\b.{0,100}\b(?:chang\w*|complet\w*)\b"
            r".{0,80}\b(?:parent )?goal\b",
        )
        self.assertRegex(
            router,
            r"\bread-only planning\b.{0,180}"
            r"\b(?:authorized|later) implementation\b",
        )
        self.assertRegex(
            router,
            r"\b(?:never|does not)\b.{0,80}\b(?:broaden|expand)"
            r".{0,60}\bauthority\b"
            r"|\bcomposition\b.{0,80}\bnever\b.{0,80}"
            r"\b(?:broaden|expand)\b.{0,60}\bauthority\b",
        )

    def test_familiar_single_surface_work_uses_generic_safe_skip(
        self,
    ) -> None:
        kernel = ROOT / "shared" / "references" / ADAPTIVE_REFERENCE
        self.assertTrue(kernel.is_file())

        for skill in EXPECTED_SKILLS:
            raw = skill_text(skill)
            body = normalized(raw)
            with self.subTest(skill=skill):
                self.assertIn(ADAPTIVE_REFERENCE, raw)
                self.assertRegex(
                    body,
                    r"\bfamiliar\b.{0,80}\bsingle-surface\b"
                    r"|\bsingle-surface\b.{0,80}\bfamiliar\b",
                )
                self.assertRegex(
                    body,
                    r"\botherwise\b.{0,80}\bread\b.{0,80}\bshared kernel\b",
                )
                self.assertRegex(
                    body,
                    r"\bno shared capability rail\b.{0,160}"
                    r"\bapproach\b.{0,80}\bmethod\b.{0,80}\bauthority\b"
                    r".{0,80}\bfailure handling\b.{0,80}\bproof\b",
                )
                for forbidden in (
                    "Run `validate_installed.py` before",
                    "Run `quantctl.py doctor` before",
                    "Run `quantctl.py context` before",
                ):
                    self.assertNotIn(forbidden, raw)
                self.assertRegex(
                    body,
                    r"\buncertain\b.{0,140}\brouting table\b"
                    r".{0,140}\bskip\b",
                )

        concrete_routes = [
            row.split(" | ", 1)[0]
            for row in markdown_table_rows(
                kernel.read_text(encoding="utf-8")
            )
            if "capabilities/" in row
        ]
        self.assertGreaterEqual(len(concrete_routes), 9)
        public_bodies = tuple(
            normalized_skill_text(skill) for skill in EXPECTED_SKILLS
        )
        for route in concrete_routes:
            with self.subTest(route=route):
                for body in public_bodies:
                    self.assertNotIn(route, body)

    def test_ordinary_capability_router_maps_triggers_to_selected_rails(
        self,
    ) -> None:
        routing_documents = (
            ROOT / "shared" / "core" / "context-routing.md",
            ROOT / "shared" / "references" / ADAPTIVE_REFERENCE,
        )
        rows = [
            row
            for document in routing_documents
            for row in markdown_table_rows(
                document.read_text(encoding="utf-8")
            )
        ]

        for reference, trigger_patterns in ORDINARY_CAPABILITY_ROUTES.items():
            matching_rows = [row for row in rows if reference in row]
            with self.subTest(reference=reference):
                self.assertTrue(
                    matching_rows,
                    f"missing ordinary capability route for {reference}",
                )
                route = matching_rows[0]
                for pattern in trigger_patterns:
                    self.assertRegex(route, pattern)
                self.assertTrue((ROOT / "shared" / reference).is_file())

        routing_text = " ".join(
            normalized(document.read_text(encoding="utf-8"))
            for document in routing_documents
        )
        self.assertRegex(
            routing_text,
            r"\bonly\b.{0,100}\b(?:needed|selected|applicable)\b"
            r".{0,120}\b(?:capabilit|rails?|documents?)\b"
            r"|\b(?:capabilit|rails?|documents?)\b.{0,120}"
            r"\bonly\b.{0,100}\b(?:needed|selected|applicable)\b",
        )

    def test_one_off_wait_routes_to_host_lifecycle_not_automation(
        self,
    ) -> None:
        kernel = normalized(
            (
                ROOT / "shared/references/adaptive-workflow.md"
            ).read_text(encoding="utf-8")
        )
        wait_row = next(
            row
            for row in markdown_table_rows(
                (
                    ROOT / "shared/references/adaptive-workflow.md"
                ).read_text(encoding="utf-8")
            )
            if "one-off wait" in row
        )
        self.assertIn("host lifecycle", wait_row)
        self.assertIn("do not select scheduled automation", wait_row)
        self.assertIn("creation or enablement", wait_row)
        self.assertIn("persistent recurring or provider-triggered", wait_row)
        self.assertRegex(
            kernel,
            r"\bif no wait surface exists\b.{0,140}\bbounded serial\b",
        )
        router = normalized(
            (
                ROOT / "shared/core/context-routing.md"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("host-lifecycle continuation follows", router)

    def test_legacy_structured_runtime_is_source_compatibility_only(
        self,
    ) -> None:
        expected_legacy = (
            "shared/references/goal-and-subagents.md",
            "shared/references/agent-orchestration.md",
            "shared/references/durable-runtime.md",
            "shared/scripts/goal_runtime.py",
            "shared/scripts/goal_ledger.py",
            "shared/scripts/team_protocol.py",
        )
        for relative in expected_legacy:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

        for skill in EXPECTED_SKILLS:
            text = normalized_skill_text(skill)
            with self.subTest(skill=skill):
                self.assertRegex(text, r"\blegacy\b|\bcompatibility\b")
                self.assertRegex(text, r"\bexplicit")
                self.assertRegex(
                    text,
                    r"\bexisting\b.{0,100}\b(?:contract|depends)\b",
                )
                self.assertRegex(
                    text,
                    r"\bordinary\b.{0,180}"
                    r"\b(?:do not|does not|must not|never|off "
                    r"(?:the )?(?:ordinary|default) path)\b"
                    r".{0,180}\b(?:legacy|manifest|ledger|receipt)\b"
                    r"|\b(?:legacy|manifest|ledger|receipt)\b.{0,180}"
                    r"\b(?:do not|does not|must not|never|off "
                    r"(?:the )?(?:ordinary|default) path)\b"
                    r".{0,180}\bordinary\b"
                    r"|\b(?:do not|does not|must not|never)\b.{0,180}"
                    r"\b(?:legacy|manifest|ledger|receipt)\b.{0,180}"
                    r"\bordinary\b"
                    r"|\b(?:legacy|manifest|ledger|receipt)\b.{0,180}"
                    r"\boff the ordinary path\b",
                )

        context_routing = normalized((
            ROOT / "shared" / "core" / "context-routing.md"
        ).read_text(encoding="utf-8"))
        self.assertRegex(
            context_routing,
            r"\blegacy\b.{0,180}\b(?:existing|explicit)\b"
            r"|\b(?:existing|explicit)\b.{0,180}\blegacy\b",
        )
        self.assertRegex(
            context_routing,
            r"\b(?:do not|does not|never)\b.{0,120}"
            r"\b(?:automatically |auto[- ]?)?(?:load|select|create)\b"
            r".{0,120}\b(?:ledger|structured runtime|legacy)\b",
        )

    def test_typed_module_extensions_do_not_open_root_package_surface(
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
        self.assertTrue(
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
