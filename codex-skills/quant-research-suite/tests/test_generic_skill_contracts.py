from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def skill_text(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(
        encoding="utf-8"
    )


def section(text: str, heading: str) -> str:
    body = text.split(heading, 1)[1]
    return body.split("\n## ", 1)[0]


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


class GenericSkillContractTests(unittest.TestCase):
    def test_plan_is_read_only_and_manifest_free_by_default(self) -> None:
        text = skill_text("quant-plan")
        default = section(text, "## Default path").lower()
        self.assertIn("default path is self-contained", default)
        self.assertIn("do not require", default)
        self.assertIn("discover", default)
        self.assertIn("non-git", default)
        self.assertNotIn("goal_runtime.py", default)

    def test_developer_is_repository_native_without_manifest(self) -> None:
        text = skill_text("quant-developer")
        default = section(text, "## Default path").lower()
        self.assertIn("repository-native", default)
        self.assertIn("entrypoints", default)
        self.assertIn("smallest coherent change", default)
        self.assertIn("self-review", default)
        self.assertIn("non-git", default)
        self.assertIn("do not require", default)

    def test_goal_activation_is_explicit_and_host_canonical(self) -> None:
        text = normalized(skill_text("quant-goal"))
        self.assertIn(
            "activate only when the current user request intentionally "
            "invokes this skill",
            text,
        )
        self.assertIn("literal token `$quant-goal`", text)
        self.assertIn(
            "active host goal state", text
        )
        self.assertIn("is not activation", text)
        self.assertIn(
            "do not create goal state for an ordinary", text
        )
        self.assertIn(
            "host application's goal state as canonical", text
        )
        for state in (
            "active",
            "waiting",
            "paused",
            "blocked",
            "completed",
            "cancelled",
            "superseded",
        ):
            self.assertIn(f"`{state}`", text)
        self.assertIn("without fabricating unsupported", text)

    def test_goal_revisions_do_not_force_a_new_goal(self) -> None:
        text = skill_text("quant-goal").lower()
        revision = section(
            text, "### 4. revise without rewriting history"
        )
        self.assertIn("refine wording or acceptance under the same goal", revision)
        self.assertIn("objective", revision)
        self.assertIn("authority", revision)
        self.assertIn("cost boundary", revision)
        self.assertIn("new or superseding goal", revision)
        self.assertNotIn("material scope", revision)

    def test_strict_goal_requires_reviewed_plan_without_rewriting_it(
        self,
    ) -> None:
        text = skill_text("quant-goal").lower()
        binding = normalized(
            section(text, "### 1. bind or resume intent")
        )
        self.assertIn("for `light` or `standard`", binding)
        self.assertIn(
            "for `strict`, and for legacy `assurance=release` compatibility",
            binding,
        )
        self.assertIn("require an approved immutable plan packet", binding)
        self.assertIn("independent plan-critic", binding)
        self.assertIn(
            "delivery alone does not create a strict planning prerequisite",
            binding,
        )
        self.assertIn(
            "do not activate that skill, recreate its plan, or review it here",
            binding,
        )

    def test_plan_review_depth_is_proportional_and_revision_bound(self) -> None:
        plan = normalized(skill_text("quant-plan"))
        shared = normalized((
            ROOT
            / "shared"
            / "references"
            / "goal-and-subagents.md"
        ).read_text(encoding="utf-8"))
        self.assertIn(
            "for `light` and `standard`, the primary planner performs one "
            "self-critique",
            plan,
        )
        self.assertIn(
            "do not commission an independent critic merely to add review count",
            plan,
        )
        self.assertIn("freeze the reviewed plan packet", plan)
        self.assertIn(
            "bind the exact plan revision or digest, the exact acceptance "
            "revision, and the critic verdict as one identity",
            plan,
        )
        self.assertIn(
            "if more than one independent high-risk surface requires its own "
            "reviewer, raise the workflow to `strict`",
            shared,
        )

    def test_decision_readiness_is_material_nonnumeric_and_freeze_gated(
        self,
    ) -> None:
        plan = normalized(skill_text("quant-plan"))
        shared = normalized((
            ROOT
            / "shared"
            / "references"
            / "goal-and-subagents.md"
        ).read_text(encoding="utf-8"))
        for text in (plan, shared):
            self.assertIn("`decision_readiness`", text)
            self.assertIn("material decision or contradiction", text)
            self.assertIn("nonnumeric", text)
            self.assertIn("omit", text)
            self.assertIn("do not", text)
            self.assertIn("threshold", text)
            self.assertIn("do not freeze", text)
        self.assertIn("fixed interview or review round", plan)
        self.assertIn("question count, or review-round count", shared)

    def test_typed_steering_and_resume_projection_preserve_authority(
        self,
    ) -> None:
        goal = normalized(skill_text("quant-goal"))
        shared = normalized((
            ROOT
            / "shared"
            / "references"
            / "goal-and-subagents.md"
        ).read_text(encoding="utf-8"))
        durable = normalized((
            ROOT
            / "shared"
            / "references"
            / "durable-runtime.md"
        ).read_text(encoding="utf-8"))
        orchestration = normalized((
            ROOT
            / "shared"
            / "references"
            / "agent-orchestration.md"
        ).read_text(encoding="utf-8"))
        for operation in (
            "`clarify`",
            "`add`",
            "`retire`",
            "`split`",
            "`merge`",
            "`reorder`",
            "`replace`",
        ):
            self.assertIn(operation, goal)
            self.assertIn(operation, shared)
            self.assertIn(
                operation.strip("`"),
                durable,
            )
        for text in (goal, shared, durable):
            self.assertIn("new or superseding", text)
            self.assertIn("objective", text)
            self.assertIn("authority", text)
            self.assertIn("cost", text)
        for text in (goal, shared, durable, orchestration):
            self.assertIn("continuation projection", text)
            self.assertIn("`not_recorded`", text)
            self.assertIn("cannot", text)
        for field in (
            "`checkpoint`",
            "`next_action`",
            "`stories_by_status`",
            "`current_blockers`",
            "`workspace_drift`",
            "`stale_review_roles`",
            "`completion_ready`",
            "`ledger`",
            "`workspace`",
            "`authority`",
        ):
            self.assertIn(field, durable)
            self.assertIn(field, orchestration)
        self.assertIn("`op`, `source_ids`, and `target_ids`", shared)
        self.assertIn("not persisted in the state schema", durable)

    def test_code_intelligence_is_local_read_only_and_opportunistic(
        self,
    ) -> None:
        plan = normalized(skill_text("quant-plan"))
        orchestration = normalized((
            ROOT
            / "shared"
            / "references"
            / "agent-orchestration.md"
        ).read_text(encoding="utf-8"))
        advisory = normalized((
            ROOT
            / "shared"
            / "advisory"
            / "external-comparisons.md"
        ).read_text(encoding="utf-8"))
        for text in (plan, orchestration, advisory):
            for phrase in (
                "already-installed",
                "lsp",
                "ast",
                "codegraph",
                "read-only",
                "`rg`",
                "project-native",
            ):
                self.assertIn(phrase, text)
        for phrase in (
            "do not install",
            "daemon",
            "mcp",
            "global configuration",
            "telemetry",
            "upload source",
        ):
            self.assertIn(phrase, orchestration)

    def test_shared_cleanup_and_parallel_write_contracts_are_bounded(
        self,
    ) -> None:
        shared = normalized((
            ROOT
            / "shared"
            / "references"
            / "goal-and-subagents.md"
        ).read_text(encoding="utf-8"))
        for phrase in (
            "cleanup is bounded to changed paths",
            "dead code",
            "masking fallbacks",
            "needless abstraction",
            "missing relevant tests",
            "multiple concurrent write workers require isolated worktrees",
            "one named integration owner",
            "overlapping write scopes remain under one owner",
            "companion ledger itself is deliberately single-root",
            "permits only one active write story",
            "records or accepts their structured evidence serially",
        ):
            self.assertIn(phrase, shared)

    def test_project_local_goal_state_is_truthful_about_portability(self) -> None:
        shared = normalized((
            ROOT
            / "shared"
            / "references"
            / "goal-and-subagents.md"
        ).read_text(encoding="utf-8"))
        durable = normalized((
            ROOT
            / "shared"
            / "references"
            / "durable-runtime.md"
        ).read_text(encoding="utf-8"))
        goal = normalized(skill_text("quant-goal"))
        for phrase in (
            "co-located evidence archive",
            "renaming, copying, moving to another path or machine",
            "intentionally unsupported and fails closed",
            "manual audit, not relocated execution",
            "separate explicit rebind protocol",
        ):
            self.assertIn(phrase, shared)
        for phrase in (
            "same verified project/state binding",
            "does not support rename, copy, cross-path, or cross-machine resume",
            "evidence portability for manual inspection",
        ):
            self.assertIn(phrase, durable)
        self.assertIn(
            "ledger-backed recovery, portability, machine audit, strict, or "
            "legacy release proof stays `unverified`",
            goal,
        )

    def test_review_scope_and_carry_forward_contract_is_explicit(self) -> None:
        shared = normalized((
            ROOT
            / "shared"
            / "references"
            / "goal-and-subagents.md"
        ).read_text(encoding="utf-8"))
        for phrase in (
            "exact portable path patterns",
            "latest relevant passed receipt",
            "intervening `needs_repair` or `blocked` verdict",
            "terminal critic is never carried forward",
            "declared ignored paths are rehashed",
        ):
            self.assertIn(phrase, shared)

    def test_plan_template_uses_lowercase_portable_acceptance_ids(self) -> None:
        template = (
            ROOT / "shared" / "templates" / "approved-plan.example.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Use lowercase portable IDs", template)
        self.assertIn("| a-1 |", template)
        self.assertNotIn("| A-1 |", template)

    def test_all_roles_define_proportional_assurance(self) -> None:
        combined = "\n".join(
            skill_text(name) for name in (
                "quant-plan",
                "quant-developer",
                "quant-goal",
            )
        ).lower()
        for level in ("`light`", "`standard`", "`strict`", "`release`"):
            self.assertGreaterEqual(combined.count(level), 3)
        developer = normalized(skill_text("quant-developer"))
        goal = normalized(skill_text("quant-goal"))
        self.assertIn(
            "do not raise assurance merely because a subagent or team was used",
            developer,
        )
        self.assertIn("subagent use alone does not raise assurance", goal)
        for text in (developer, goal):
            self.assertIn(
                "delivery as `local` or `release`",
                text,
            )
            self.assertIn(
                "does not raise assurance by itself",
                text,
            )

    def test_analysis_binding_has_basic_and_strict_paths(self) -> None:
        developer = skill_text("quant-developer").lower()
        capability = normalized((
            ROOT
            / "shared"
            / "capabilities"
            / "analysis-input-binding.md"
        ).read_text(encoding="utf-8"))
        self.assertIn("representative integration test", developer)
        self.assertIn("do not require", developer)
        self.assertIn("default repository-native check", capability)
        self.assertIn("strict compatibility contract", capability)
        for phrase in ("a/b capture", "raw runtime trace", "receipt"):
            self.assertIn(phrase, capability)

    def test_generic_defaults_do_not_inherit_dashboard_assumptions(self) -> None:
        plan_default = section(
            skill_text("quant-plan"), "## Default path"
        ).lower()
        developer_default = section(
            skill_text("quant-developer"), "## Default path"
        ).lower()
        for text in (plan_default, developer_default):
            for assumption in (
                "ctm",
                "coherent cutoff",
                "last-good publication",
                "fastapi",
                "supabase",
                "vercel",
            ):
                self.assertNotIn(assumption, text)

        web_ui = (
            ROOT / "shared" / "capabilities" / "web-ui.md"
        ).read_text(encoding="utf-8").lower()
        backend = (
            ROOT / "shared" / "capabilities" / "backend.md"
        ).read_text(encoding="utf-8").lower()
        self.assertNotIn("results-first", web_ui)
        self.assertNotIn("ctm", web_ui)
        self.assertIn("do not invent a static fallback", backend)

    def test_shared_runtime_failure_is_a_bounded_limitation(self) -> None:
        context = (
            ROOT / "shared" / "core" / "context-routing.md"
        ).read_text(encoding="utf-8").lower()
        self.assertIn(
            "missing or damaged shared runtime does not block", context
        )
        for name in ("quant-plan", "quant-developer", "quant-goal"):
            text = skill_text(name).lower()
            with self.subTest(skill=name):
                self.assertIn("unavailable", text)


if __name__ == "__main__":
    unittest.main()
