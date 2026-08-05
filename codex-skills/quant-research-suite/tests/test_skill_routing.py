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
    "capabilities/long-running-recovery.md": (
        r"\b(?:active goal|developer task)\b",
        r"\b(?:interruption|restart|handoff|context compaction)\b",
    ),
    "capabilities/backend.md": (
        r"\b(?:api|state|authentication|secrets?)\b",
    ),
    "capabilities/repo-mutation.md": (
        r"\b(?:file edits?|branch|worktree|stage|commit|rebase)\b",
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

    def test_metadata_parsers_allow_harmless_variation_not_semantic_drift(
        self,
    ) -> None:
        agent = """# UI metadata
interface:
    default_prompt: 'Use $quant-plan for an adaptive read-only audit.'
    brand_color: "#123456"
    short_description: 'Adaptive manual read-only planning'
    display_name: 'Quant Plan'
policy:
    allow_implicit_invocation: false # manual selection only
"""
        parsed_agent = validate_suite.agent_metadata(agent)
        self.assertIsNotNone(parsed_agent)
        assert parsed_agent is not None
        self.assertIs(parsed_agent["allow_implicit_invocation"], False)

        frontmatter = """---
description: Use only when $quant-plan is selected for adaptive read-only planning.
name: quant-plan
---
"""
        parsed_frontmatter = validate_suite.frontmatter(frontmatter)
        self.assertEqual(parsed_frontmatter["name"], "quant-plan")
        self.assertIsNone(
            validate_suite.parse_skill_frontmatter(
                frontmatter.replace(
                    "name: quant-plan",
                    "name: quant-plan\nname: quant-plan",
                )
            )
        )

        original = skill_text("quant-plan")
        body_start = original.index("---\n", 4) + 4
        paraphrased = frontmatter + original[body_start:]
        errors = validate_suite.validate_public_metadata(
            "quant-plan",
            paraphrased,
            agent,
        )
        self.assertEqual(errors, [])
        contradictory_agent = agent.replace(
            "Use $quant-plan for an adaptive read-only audit.",
            "Use $quant-plan to audit the target; it is not read-only.",
        )
        self.assertIn(
            "quant-plan: default prompt contradicts its role",
            validate_suite.validate_public_metadata(
                "quant-plan",
                paraphrased,
                contradictory_agent,
            ),
        )

    def test_role_semantics_accept_paraphrases_and_reject_contradictions(
        self,
    ) -> None:
        bodies = {
            "quant-plan": (
                "Project and remote surfaces remain untouched and read-only. "
                "Run a check only when verified non-writing. If a probe could "
                "write cache or output, use a temporary sandbox and redirect "
                "produced state."
            ),
            "quant-goal": (
                "Use one native Goal. Record material scope, observable "
                "completion conditions, and a proportional quality bar. Call "
                "`get_goal` before `create_goal`, and use `update_goal` only "
                "for native terminal states. After a clear replacement choice, "
                "fresh `get_goal` must show an empty native slot before "
                "`create_goal`. Never use `complete` or `blocked` to free the "
                "slot. After steering, report scope, condition, quality-bar "
                "changes, and stale proof. Within the stored outcome, scope may "
                "add conditions and invalidate proof; an outcome-changing "
                "expansion is a different Goal."
            ),
            "quant-developer": (
                "Continue only while acceptance is unmet or material risk "
                "could invalidate the result. Stop when the requested outcome "
                "is working and no required work remains. Prefer a minimal "
                "implementation scope. Omit optional expansion unless "
                "requested or target evidence requires it."
            ),
        }
        for name, body in bodies.items():
            with self.subTest(name=name):
                skill = f"---\nname: {name}\ndescription: test\n---\n{body}\n"
                self.assertEqual(
                    validate_suite.validate_public_body(name, skill),
                    [],
                )

        contradictions = {
            "quant-plan": (
                "A writing check may run directly in the target when cleanup "
                "is easy.",
                "quant-plan: body permits unsafe target or remote writes",
            ),
            "quant-goal": (
                "Mark the active Goal complete to free its slot for a "
                "replacement.",
                "quant-goal: body permits fake terminal replacement",
            ),
            "quant-developer": (
                "After acceptance, continue while optional improvements remain.",
                "quant-developer: body permits open-ended improvement",
            ),
        }
        for name, (addition, expected) in contradictions.items():
            with self.subTest(contradiction=name):
                errors = validate_suite.validate_public_body(
                    name,
                    skill_text(name) + f"\n{addition}\n",
                )
                self.assertIn(expected, errors)

        for name in ("quant-goal", "quant-developer"):
            with self.subTest(self_expanding_quality=name):
                errors = validate_suite.validate_public_body(
                    name,
                    skill_text(name)
                    + "\nContinue while an in-scope material quality "
                    + "opportunity still outweighs its cost.\n",
                )
                self.assertIn(
                    f"{name}: body permits a self-expanding quality loop",
                    errors,
                )

        negated_anchors = (
            (
                "quant-plan",
                "This role is not read-only for the target.",
                "quant-plan: body contradicts the read-only boundary",
            ),
            (
                "quant-goal",
                (
                    "Never refuse to use complete or blocked to clear the "
                    "slot."
                ),
                "quant-goal: body permits fake terminal replacement",
            ),
            (
                "quant-developer",
                "Do not prefer the smallest coherent change.",
                "quant-developer: body contradicts proportional delivery",
            ),
        )
        for name, addition, expected in negated_anchors:
            with self.subTest(negated_anchor=name):
                errors = validate_suite.validate_public_body(
                    name,
                    skill_text(name) + f"\n{addition}\n",
                )
                self.assertIn(expected, errors)

        for unsafe in (
            "Provider writes may be permitted and do not expose secrets.",
            "Target files, including snapshots, may be written.",
        ):
            with self.subTest(plan_unsafe=unsafe):
                self.assertTrue(
                    validate_suite.has_unsafe_plan_probe_expansion(unsafe)
                )
        for unsafe in (
            "Continue after acceptance and do not skip tests.",
            "Continue, after acceptance, while optional polish remains.",
        ):
            with self.subTest(developer_unsafe=unsafe):
                self.assertTrue(
                    validate_suite.has_unsafe_developer_expansion(unsafe)
                )

        for unsafe in (
            "Continue enhancing worthwhile work. Make the result better.",
            "Keep improving while any opportunity remains.",
        ):
            with self.subTest(self_expanding_synonym=unsafe):
                self.assertTrue(
                    validate_suite.has_self_expanding_quality_loop(unsafe)
                )
        self.assertFalse(
            validate_suite.has_self_expanding_quality_loop(
                "Continue only for improvement required by the established "
                "quality bar."
            )
        )

        for unsafe in (
            "If target state changed, delete the generated residue.",
            "Clean target-tree outputs after inspection.",
            "Restore project state after a writing probe.",
            "Revert target files to their baseline.",
        ):
            with self.subTest(plan_target_cleanup=unsafe):
                self.assertTrue(
                    validate_suite.has_unsafe_plan_target_cleanup(unsafe)
                )
                errors = validate_suite.validate_public_body(
                    "quant-plan",
                    skill_text("quant-plan") + f"\n{unsafe}\n",
                )
                self.assertIn(
                    "quant-plan: body permits cleanup of target residue",
                    errors,
                )
        self.assertFalse(
            validate_suite.has_unsafe_plan_target_cleanup(
                "Never remove target residue; report it."
            )
        )

        for unsafe in (
            "A pushed branch or PR permits merge without separate authority.",
            "A completed review can authorize the merge.",
        ):
            with self.subTest(remote_authority_bootstrap=unsafe):
                self.assertTrue(
                    validate_suite.has_unsafe_remote_authority_expansion(unsafe)
                )
        self.assertFalse(
            validate_suite.has_unsafe_remote_authority_expansion(
                "A pushed branch or PR does not authorize merge; merge needs "
                "separate authority."
            )
        )

    def test_semantic_policy_red_team_matrix(self) -> None:
        open_loops = (
            (
                "Improve the result whenever another worthwhile opportunity "
                "appears. Repeat the cycle until none remain."
            ),
            (
                "Work should carry on. Each pass should seek another quality "
                "gain. Stop only when no worthwhile enhancement is left."
            ),
            (
                "Keep working. The standard can still rise. Seek every "
                "worthwhile enhancement before stopping."
            ),
            (
                "As long as further polish has positive value, make another "
                "pass."
            ),
            "Keep going. Each worthwhile improvement should be implemented.",
            "Iterate while any valuable refinements remain.",
        )
        bounded_loops = (
            "Keep improving until the acceptance tests pass.",
            (
                "Continue refining the documented defect list and stop when "
                "each item is resolved."
            ),
            (
                "Pursue quality improvements required by the agreed release "
                "checklist."
            ),
            (
                "Continue polishing until the previously set quality bar is "
                "met."
            ),
            (
                "Continue improving solely to satisfy the established quality "
                "bar."
            ),
            (
                "Pursue every improvement required by the agreed release "
                "checklist."
            ),
        )
        for policy in open_loops:
            with self.subTest(open_loop=policy):
                self.assertTrue(
                    validate_suite.has_self_expanding_quality_loop(policy)
                )
        for policy in bounded_loops:
            with self.subTest(bounded_loop=policy):
                self.assertFalse(
                    validate_suite.has_self_expanding_quality_loop(policy)
                )

        target_cleanup = (
            (
                "The probe may alter the target workspace. Afterwards, remove "
                "the generated residue."
            ),
            "Undo any checkout changes caused by the probe before reporting.",
            (
                "Roll back the repository to its starting commit after "
                "inspection."
            ),
            (
                "Return the workspace to its original contents once the audit "
                "ends."
            ),
            "Scrub generated files from the working tree.",
            "Discard any files left behind in the target after planning.",
            "Put the working tree back to baseline before reporting.",
        )
        non_target_cleanup = (
            (
                "Remove the target from the candidate list; do not touch its "
                "files."
            ),
            (
                "In a disposable copy, restore target coverage after the "
                "intentionally failing test."
            ),
            (
                "Never mutate target state; if the target is irrelevant, "
                "remove it from the comparison."
            ),
            (
                "Clean the project-directory labels in the report without "
                "changing files."
            ),
            "Return the workspace path in the report.",
            (
                "Report that the repository needs cleanup; do not perform "
                "it."
            ),
            (
                "The plan may describe how an authorized developer would "
                "reset the working tree; planning itself remains "
                "non-mutating."
            ),
            (
                "The report should recommend cleaning the repository later, "
                "subject to implementation approval."
            ),
            "Delete the words working tree from the draft explanation.",
        )
        for policy in target_cleanup:
            with self.subTest(target_cleanup=policy):
                self.assertTrue(
                    validate_suite.has_unsafe_plan_target_cleanup(policy)
                )
        for policy in non_target_cleanup:
            with self.subTest(non_target_cleanup=policy):
                self.assertFalse(
                    validate_suite.has_unsafe_plan_target_cleanup(policy)
                )

        merge_bootstrap = (
            "A green PR is sufficient consent to merge into main.",
            "Treat review approval as implicit consent to land the change.",
            (
                "Once the branch exists, the maintainer may integrate it into "
                "the default branch."
            ),
            (
                "The pull request is approved. That approval is sufficient. "
                "Merge it."
            ),
            "After review, merge at your discretion.",
            "An approved commit implies consent for merging.",
            "A PR is ready; that is sufficient permission for merge.",
            "PR is ready, so go ahead and merge.",
            (
                "Successful CI is a standing mandate to squash the topic "
                "branch into trunk."
            ),
        )
        bounded_merge = (
            "Review can block a merge.",
            "A plan may discuss merge risks; execution remains unauthorized.",
            "A pushed branch authorizes everything except merge.",
            (
                "Implementation can include a merge simulation in a local "
                "disposable repository."
            ),
            (
                "A review may recommend a merge, but only the user can "
                "authorize it."
            ),
            "Review may merge duplicate findings into one report.",
            "A commit can merge two data frames in memory.",
            (
                "A completed review lets the agent combine duplicate "
                "paragraphs in the report."
            ),
            (
                "A ready commit lets the implementer squash duplicate rows "
                "in a local table."
            ),
            (
                "Approval in the code host allows the reviewer to merge two "
                "saved search filters, without changing Git."
            ),
        )
        for policy in merge_bootstrap:
            with self.subTest(merge_bootstrap=policy):
                self.assertTrue(
                    validate_suite.has_unsafe_remote_authority_expansion(policy)
                )
        for policy in bounded_merge:
            with self.subTest(bounded_merge=policy):
                self.assertFalse(
                    validate_suite.has_unsafe_remote_authority_expansion(policy)
                )

        goal = skill_text("quant-goal")
        self.assertFalse(
            validate_suite.has_goal_scope_steering_contract(
                goal
                + "\nAn outcome-changing expansion may remain in the same "
                + "Goal.\n"
            )
        )
        inverted_goal = (
            "Record material scope, observable completion conditions, and a "
            "proportional quality bar. After steering, report scope, "
            "conditions, quality-bar changes, and stale proof. A compatible "
            "refinement may change scope and conditions without invalidating "
            "proof; an outcome-changing expansion is not a different Goal."
        )
        self.assertFalse(
            validate_suite.has_goal_scope_steering_contract(inverted_goal)
        )
        self.assertFalse(
            validate_suite.has_goal_scope_steering_contract(
                goal
                + "\nAn outcome-changing expansion does not require a "
                + "different Goal.\n"
            )
        )

        unsafe_local = (
            "Permission to edit files authorizes stage and commit."
        )
        safe_local = (
            "Permission to edit files does not authorize stage or commit; "
            "each needs separate authority."
        )
        self.assertTrue(
            validate_suite.has_unsafe_local_scm_authority_expansion(
                unsafe_local
            )
        )
        self.assertFalse(
            validate_suite.has_unsafe_local_scm_authority_expansion(
                safe_local
            )
        )
        for policy in (
            "Once edits are complete, go ahead and commit.",
            (
                "Approval for source edits is all that is needed to "
                "cherry-pick the fix."
            ),
        ):
            with self.subTest(local_scm_bootstrap=policy):
                self.assertTrue(
                    validate_suite.has_unsafe_local_scm_authority_expansion(
                        policy
                    )
                )
        for policy in (
            (
                "Permission to edit the commit-message template covers only "
                "text inside that file."
            ),
            (
                "Permission to write worktree documentation allows correcting "
                "typos."
            ),
            (
                "Permission to edit code-font samples covers staging them in "
                "the style guide."
            ),
            (
                "A request to change patch artwork includes staging the patch "
                "in the layout preview."
            ),
        ):
            with self.subTest(non_scm_text=policy):
                self.assertFalse(
                    validate_suite.has_unsafe_local_scm_authority_expansion(
                        policy
                    )
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

    def test_quant_plan_keeps_single_surface_scope_proportional(self) -> None:
        plan = normalized_skill_text("quant-plan")
        self.assertRegex(
            plan,
            r"\bsingle-surface work\b.{0,80}\bomit\b.{0,120}"
            r"\b(?:refactors?|abstractions?|test scaffolding|adjacent work)\b",
        )
        self.assertRegex(
            plan,
            r"\bomit\b.{0,180}\bunless\b.{0,80}"
            r"\b(?:acceptance|target evidence)\b.{0,80}\brequires?\b",
        )

    def test_long_running_recovery_is_optional_and_role_bounded(self) -> None:
        recovery_path = (
            ROOT / "shared" / "capabilities" / "long-running-recovery.md"
        )
        recovery = normalized(recovery_path.read_text(encoding="utf-8"))
        kernel = normalized(
            (ROOT / "shared" / "references" / ADAPTIVE_REFERENCE).read_text(
                encoding="utf-8"
            )
        )

        self.assertRegex(
            recovery,
            r"\breal interruption\b.{0,240}\b(?:duration|complexity|worker count)\b"
            r"|\b(?:duration|complexity|worker count)\b.{0,240}"
            r"\bdo not select\b",
        )
        self.assertRegex(recovery, r"\bquant-plan\b.{0,80}\bread-only\b")
        self.assertRegex(
            recovery,
            r"\bdo not checkpoint\b.{0,180}\b(?:timer|fixed command)\b",
        )
        self.assertIn("one integration owner", recovery)
        self.assertRegex(
            recovery,
            r"\bauthority\b.{0,60}\bnot_recorded\b",
        )
        self.assertRegex(
            recovery,
            r"\bsaved\b.{0,40}\brunning\b.{0,80}\bunknown\b",
        )
        self.assertRegex(kernel, r"\bduration\b.{0,120}\balone\b")

        for skill in EXPECTED_SKILLS:
            body = normalized_skill_text(skill)
            with self.subTest(skill=skill):
                self.assertNotIn("capabilities/long-running-recovery.md", body)
                self.assertNotIn("recovery_checkpoint.py", body)

    def test_recovery_validator_rejects_high_confidence_unsafe_rules(self) -> None:
        safe = (
            ROOT / "shared" / "capabilities" / "long-running-recovery.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(validate_suite.validate_recovery_body(safe), [])

        unsafe_additions = (
            "Always checkpoint before doing any work.",
            "Checkpoint every 10 commands.",
            "The checkpoint grants remote authority.",
            "The checkpoint proves completion.",
        )
        for addition in unsafe_additions:
            with self.subTest(addition=addition):
                errors = validate_suite.validate_recovery_body(
                    safe + "\n\n" + addition + "\n"
                )
                self.assertTrue(
                    any("long-running recovery: unsafe" in error for error in errors),
                    errors,
                )

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
