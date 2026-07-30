from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def skill(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


def between(text: str, start: str, end: str | None = None) -> str:
    body = text.split(start, 1)[1]
    return body.split(end, 1)[0] if end else body


class GenericSkillContractTests(unittest.TestCase):
    def assert_terms(self, text: str, *terms: str) -> None:
        body = normalized(text)
        for term in terms:
            with self.subTest(term=term):
                self.assertIn(term.lower(), body)

    def assert_order(self, text: str, *terms: str) -> None:
        body = normalized(text)
        positions = [body.index(term.lower()) for term in terms]
        self.assertEqual(positions, sorted(positions))

    def test_plan_is_read_only_and_decision_complete(self) -> None:
        plan = skill("quant-plan")
        self.assert_order(
            plan,
            "### 1. Ground",
            "### 2. Explore",
            "### 3. Decide",
            "### 4. Plan",
            "### 5. Self-critique",
        )
        scope = between(plan, "## Activation and scope", "## Workflow")
        self.assert_terms(
            scope,
            "read-only",
            "non-mutating checks",
            "do not edit files",
            "install dependencies",
            "create or update Goal state",
            "keep this skill's phase read-only",
            "finish and self-critique the selected plan first",
            "hand implementation ownership",
            "did not require plan approval first",
        )
        planning = between(plan, "### 4. Plan", "### 5. Self-critique")
        self.assert_terms(
            planning,
            "failure and degraded behavior",
            "observable acceptance",
            "compatibility",
            "approval boundaries",
        )

    def test_plan_shared_guidance_stays_read_only_and_audits_are_evidenced(
        self,
    ) -> None:
        plan = skill("quant-plan")
        explore = between(plan, "### 2. Explore", "### 3. Decide")
        output = between(
            plan,
            "## Output modes",
            "## Optional legacy compatibility",
        )
        self.assert_terms(
            explore,
            "read-only boundary always overrides",
            "inspection, comparison, simulation in memory, or proposed plan",
            "self-contained workflow",
            "do not search for another suite copy",
        )
        self.assert_terms(
            output,
            "reproducible evidence pointer",
            "file and line",
            "command result",
            "observation time",
            "`observed`, `inferred`, or `unverified`",
        )

    def test_plan_discovers_before_questions_and_selects_defaults(self) -> None:
        plan = skill("quant-plan")
        explore = between(plan, "### 2. Explore", "### 3. Decide")
        decide = between(plan, "### 3. Decide", "### 4. Plan")
        critique = between(
            plan, "### 5. Self-critique", "## Free data and evidence guardrails"
        )
        self.assert_terms(
            explore,
            "discover facts before asking questions",
            "source",
            "configuration",
            "tests",
            "real consumer",
        )
        self.assert_terms(
            decide,
            "materially changes the result",
            "cannot be discovered",
            "strongest reasonable default",
            "assumption",
            "one recommended approach",
        )
        self.assert_terms(
            critique,
            "missing decisions",
            "unsupported assumptions",
            "real consumer surface",
            "revise the plan",
        )

    def test_goal_uses_native_state_without_duplicate_or_ledger(self) -> None:
        goal = skill("quant-goal")
        activation = between(
            goal, "## Activation and continuation", "## Native Goal first"
        )
        native = between(goal, "## Native Goal first", "## Adaptive execution")
        self.assert_terms(
            activation,
            "explicitly invokes `$quant-goal`",
            "automatic follow-up turns",
            "without reactivating this skill",
            "native Goal lifecycle",
            "not implicit skill invocation",
            "ordinary request",
        )
        self.assert_order(native, "get_goal", "create_goal")
        self.assertGreaterEqual(normalized(native).count("get_goal"), 2)
        self.assert_terms(
            native,
            "source of truth",
            "unfinished Goal exists",
            "never create a duplicate Goal",
            "no unfinished Goal exists",
            "do not create a ledger",
            "manifest",
            "local state",
        )

    def test_goal_objective_and_steering_bind_current_success_conditions(
        self,
    ) -> None:
        native = between(
            skill("quant-goal"),
            "## Native Goal first",
            "## Adaptive execution",
        )
        self.assert_terms(
            native,
            "two to six observable success conditions",
            "stable IDs `SC-1` through `SC-6`",
            "`create_goal` has one `objective` field",
            "no separate success-condition field",
            "complete `SC-*` list into that objective",
            "stored objective contains every current `SC-*` ID",
            "do not proceed under a silently weakened binding",
            "retire rather than reuse an obsolete ID",
            "next unused ID",
            "two to six current conditions",
            "every changed or dependent condition stale",
            "reverify the current set",
        )
        self.assert_terms(
            native,
            "new objective pending",
            "ask whether to continue the unfinished Goal",
            "do not misuse `complete` or `blocked` to clear it",
            "do not invent a cancel or supersede transition",
        )

    def test_goal_budget_and_terminal_rules_match_native_lifecycle(self) -> None:
        goal = skill("quant-goal")
        native = between(goal, "## Native Goal first", "## Adaptive execution")
        terminal = between(
            goal, "## Verification and terminal state", "## Legacy compatibility"
        )
        self.assert_terms(
            native,
            "token_budget",
            "only when the user explicitly supplied",
            "positive token budget",
            "never a completion or blocking reason",
            "final token usage",
        )
        self.assert_terms(
            terminal,
            "update_goal",
            "complete",
            "every current `SC-*` success condition",
            "steering-invalidated evidence",
            "three consecutive Goal turns",
            "no meaningful progress",
            "first and second occurrence",
            "meaningful progress resets the count",
            "fresh three-turn audit",
            "not a steering operation",
            "accepts only `complete` and `blocked`",
        )
        for state in ("waiting", "paused", "cancelled", "superseded", "completed"):
            with self.subTest(state=state):
                self.assertIn(f"`{state}`", normalized(terminal))
        self.assert_terms(
            terminal,
            "never invent",
            "only lifecycle operations the host actually exposes",
        )

    def test_developer_pursues_completeness_and_switches_failed_routes(
        self,
    ) -> None:
        developer = skill("quant-developer")
        mission = between(
            developer, "## Mission", "## Adaptive implementation loop"
        )
        loop = between(
            developer,
            "## Adaptive implementation loop",
            "## Native subagents and teams",
        )
        self.assert_terms(
            mission,
            "complete accepted outcome end to end",
            "minimizing unrelated churn",
            "not necessarily the smallest patch",
            "make the requested result actually work",
            "integration owner",
        )
        self.assert_order(
            loop,
            "**Inspect.**",
            "**Inventory.**",
            "**Decompose.**",
            "**Implement.**",
            "**Verify the actual surface.**",
            "**Adapt and rerun.**",
        )
        self.assert_terms(
            loop,
            "diagnose failures",
            "switch the source, method, tool, or decomposition",
            "rather than repeating a failed route",
            "rerun affected checks",
            "safe, relevant next action",
        )

    def test_delegation_is_selective_bounded_and_integrated(self) -> None:
        adaptive = read("shared/references/adaptive-workflow.md")
        delegation = between(
            adaptive,
            "## Delegate for useful parallelism",
            "## Keep working through adaptable constraints",
        )
        self.assert_terms(
            delegation,
            "at least two independent",
            "real progress",
            "one canonical writer",
            "isolated writers",
            "integration owner",
            "outcome or question",
            "allowed scope",
            "constraints and protected surfaces",
            "evidence or artifact",
            "do not require fixed roles",
            "worker counts",
            "Team Run Packets",
            "receipts",
        )

        developer = between(
            skill("quant-developer"),
            "## Native subagents and teams",
            "## Free data and method adaptation",
        )
        self.assert_terms(
            developer,
            "at least two independent lanes",
            "four plain-language elements",
            "Outcome",
            "Scope",
            "Constraints",
            "Expected evidence",
            "demonstrably isolated",
            "one integration owner",
        )

    def test_free_data_ladder_excludes_paid_and_records_claim_evidence(
        self,
    ) -> None:
        data = between(
            read("shared/references/adaptive-workflow.md"),
            "## Use only zero-billing data",
            "## Prove the requested outcome",
        )
        self.assert_order(
            data,
            "project-owned source",
            "official no-billing",
            "another lawfully accessible no-billing public source",
            "derived from free inputs",
            "disclosed proxy",
        )
        self.assert_terms(
            data,
            "paid data is outside the solution space",
            "trials or credits",
            "payment-card setup",
            "pay-as-you-go",
            "overage",
            "paid add-ons",
            "source dates",
            "fields used",
            "adjustment",
            "point-in-time",
            "look-ahead",
            "public display",
            "redistribution",
        )

    def test_real_surface_proof_keeps_delivery_stages_distinct(self) -> None:
        proof = between(
            read("shared/references/adaptive-workflow.md"),
            "## Prove the requested outcome",
            "## Respect authority",
        )
        self.assert_terms(
            proof,
            "real consumer surface",
            "renderer",
            "publication",
            "readback",
            "final public or consumer-visible result",
            "proves only its own stage",
        )
        for intermediate in (
            "build",
            "health check",
            "workflow start",
            "HTTP status",
            "local artifact",
            "commit",
            "preview",
        ):
            with self.subTest(intermediate=intermediate):
                self.assertIn(intermediate.lower(), normalized(proof))

        developer = between(
            skill("quant-developer"),
            "## Verification and authority",
            "## Legacy compatibility",
        )
        self.assert_terms(
            developer,
            "actual renderer",
            "representative consumer",
            "meaningful inputs",
            "configuration",
            "execution",
            "artifact creation",
            "publication",
            "uncached public readback",
            "does not prove the downstream outcome",
        )

    def test_completion_report_is_short_and_evidence_based(self) -> None:
        report = between(skill("quant-developer"), "## Completion report")
        self.assert_terms(
            report,
            "Achieved outcome",
            "Changed areas",
            "Checks run",
            "Limits or unverified items",
            "structured evidence only",
            "explicit machine audit",
            "without claiming that parent work complete",
        )

    def test_legacy_runtime_is_preserved_but_opt_in(self) -> None:
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

        for name in ("quant-plan", "quant-goal", "quant-developer"):
            with self.subTest(skill=name):
                text = skill(name)
                marker = next(
                    heading
                    for heading in (
                        "## Legacy compatibility",
                        "## Optional legacy compatibility",
                    )
                    if heading in text
                )
                legacy = between(text, marker)
                self.assertTrue(
                    "explicit" in normalized(legacy)
                    or "existing project contract" in normalized(legacy)
                )
                default = normalized(text.split(marker, 1)[0])
                self.assertNotIn("require a team run packet", default)
                self.assertNotIn("require a goal ledger", default)


if __name__ == "__main__":
    unittest.main()
