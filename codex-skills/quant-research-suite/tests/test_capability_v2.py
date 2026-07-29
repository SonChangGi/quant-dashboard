from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "shared" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capability_model
import validate_project


def base_manifest() -> dict[str, object]:
    return {
        "schema_version": 2,
        "project": {
            "id": "sample",
            "purpose": "Produce a user-visible result.",
        },
        "assurance": "light",
        "profiles": [],
        "capabilities": [],
        "adapters": {},
        "contracts": {"protected_paths": [], "test_commands": []},
        "capability_config": {},
        "authority": {
            "cost_policy": (
                "zero-spend-unless-user-first-requests-specific-paid-action"
            ),
            "paid_action_authority": None,
            "paid_fallback_enabled": False,
        },
        "extensions": {},
    }


class CapabilityModelTests(unittest.TestCase):
    def test_paid_data_prose_guard_is_refusal_aware_and_future_aware(
        self,
    ) -> None:
        prohibited = (
            "Subscribe to a paid market-data API and integrate its price feed.",
            "Use a freemium data API that becomes chargeable later.",
            "Use a free API now and pay later to continue.",
            "Use a free API now; pay later to continue.",
            "Use a free no-billing API that becomes chargeable later.",
            "Use a no-cost dataset; registration requires a payment card.",
            "Use free data today; it charges tomorrow.",
            "Use free data until quota, then buy credits.",
            "Use an API that is free but becomes paid.",
            "Use paid data without delay.",
            "Use paid data that cannot be replaced.",
            "Download premium price data.",
            "License a premium dataset.",
            "Use paid datasets.",
            "Use paid feeds.",
            "Use a no-billing source and a premium price feed.",
            "We will not buy paid data and will subscribe to a premium feed.",
            "Use a $10/month market data source.",
            "Register a credit card for the data API.",
            "Upgrade the provider plan to unlock data.",
            "Buy an add-on for quote access.",
            "Use 90-day promotional credits for the pricing API.",
            "Use a free-only API until fees start.",
            "Use a free-only data source that converts to a charged plan.",
            "Use a paid corporate-actions service.",
            "Subscribe to point-in-time fundamentals.",
            "유료 데이터를 활용한다.",
            "프리미엄 시세 API를 이용한다.",
            "월 10만원짜리 시세 API를 사용한다.",
            "무료 기간 종료 후 요금이 청구되는 시세 API를 사용한다.",
            "무료 체험 API를 사용한다.",
            "Access a paid data provider.",
            "Query a premium price API.",
            "Call a paid quotes API.",
            "Pull premium prices from this source.",
            "Scrape paid fundamentals.",
            "Stream paid quotes.",
            "Read a paid dataset.",
            "Consume a paid market-data feed.",
            "Rely on a premium data source.",
            "유료 API에 접속한다.",
            "프리미엄 가격 API를 호출한다.",
            "유료 데이터를 읽는다.",
            "Do not use paid data, then subscribe to a premium API.",
            "무료 유료전환 데이터는 사용하지 말고, "
            "프리미엄 가격 API를 구독한다.",
            "Enable premium price feed.",
            "Subscribe to Bloomberg Terminal for prices.",
            "Buy a market dataset.",
            "Purchase price data access.",
            "Pay for a quote feed.",
            "License a fundamentals dataset.",
            "Rent a price feed.",
            "Acquire market data for money.",
            "Use a data source that costs money.",
            "Use a data source with a nonzero cost.",
            "Buy access to corporate actions.",
            "Purchase historical prices.",
            "데이터를 구매한다.",
            "가격 API 사용권을 산다.",
            "시세 데이터 이용료를 낸다.",
            "데이터 비용을 지불한다.",
            "데이터 라이선스를 구매한다.",
            "Do not use paid data and access a premium API.",
            "Do not use paid data while accessing a premium API.",
            "Never subscribe to paid data except use a premium price API.",
            "Reject paid data, yet access a premium price feed.",
            "Paid data is prohibited—use a premium API instead.",
            "Analyze risk premium data from a permanently free source, "
            "then use a premium price API.",
            "Clinical trial data requires a payment card.",
            "Use risk premium data that becomes paid later.",
            "Replace free data with a paid API.",
        )
        for prose in prohibited:
            with self.subTest(prose=prose):
                self.assertTrue(
                    capability_model.prohibited_paid_data_reasons(prose)
                )

        allowed = (
            "Do not use paid data.",
            "Never subscribe to a premium price feed.",
            "Do not use a freemium API that becomes chargeable later.",
            "Use only a free no-billing source.",
            "Use data that requires no payment card.",
            "Use only a permanently free source with no card or billing.",
            "Paid data is outside the solution space.",
            "Paid data is ineligible and must remain out of scope.",
            "유료 데이터 사용은 불가하다.",
            "Use a free API with no overage.",
            "Paid data was not used.",
            "Paid data is not needed.",
            "Paid data is not an option.",
            "Reject a paid market-data API and use a free source instead.",
            "The plan rejects paid data, trials, credits, subscriptions, "
            "and future fees.",
            "Analyze equity risk premium data from a permanently free source.",
            "Analyze dividend payment dates from a permanently free dataset.",
            "Analyze credit-card transaction data from a permanently free "
            "dataset.",
            "Analyze clinical trial data from a permanently free source.",
            "Analyze mutual fund fee data from a permanently free filing.",
            "Use permanently free data about fund expense fees.",
            "Analyze subscription-rights corporate actions from a "
            "permanently free filing.",
            "Paid data is disallowed.",
            "Paid data may not be used.",
            "Paid data won't be used.",
            "Paid data is off limits.",
            "We excluded paid data.",
            "The paid data source is disabled.",
            "The paid API was removed.",
            "All billable data routes are disabled.",
            "No billable data route remains active.",
            "유료 데이터 안 써.",
            "유료 데이터는 필요 없다.",
            "유료 데이터는 절대로 안 쓴다.",
            "유료 데이터를 피하고 무료 소스만 쓴다.",
            "유료 데이터 사용을 거부한다.",
            "유료 데이터는 허용 대상이 아니다.",
            "결제 거래 데이터를 완전 무료 공공 소스에서 분석한다.",
            "Buy stock using permanently free price data.",
            "Do not buy market data.",
            "데이터를 구매하지 않는다.",
            "Replace the paid data source with a free source.",
            "Remove the premium API and use an eligible free source.",
            "Disable the paid feed.",
            "유료 데이터 소스를 제거하고 무료 소스로 교체한다.",
        )
        for prose in allowed:
            with self.subTest(prose=prose):
                self.assertEqual(
                    capability_model.prohibited_paid_data_reasons(prose),
                    [],
                )

    def test_paid_data_violation_reports_require_typed_opt_in(self) -> None:
        reports = (
            "Blocking finding: the implementation uses paid data.",
            "Paid data use was detected and must be removed.",
            "The premium API was accessed; replace it with a free source.",
            "Paid data was used; do not continue.",
            "Blocked: a paid dataset is the only currently configured source.",
        )
        for prose in reports:
            with self.subTest(prose=prose):
                self.assertTrue(
                    capability_model.prohibited_paid_data_reasons(prose)
                )
                self.assertEqual(
                    capability_model.prohibited_paid_data_reasons(
                        prose,
                        allow_reported_violation=True,
                    ),
                    [],
                )
        self.assertTrue(
            capability_model.prohibited_paid_data_reasons(
                "Blocking finding: use a paid data API next.",
                allow_reported_violation=True,
            )
        )

    def test_only_logical_capability_implications_apply(self) -> None:
        self.assertEqual(
            capability_model.expand_capabilities(["interactive-chart"]),
            ["interactive-chart", "web-ui"],
        )
        self.assertEqual(
            capability_model.expand_capabilities(
                ["analysis-input-binding"]
            ),
            ["analysis", "analysis-input-binding"],
        )
        self.assertEqual(
            capability_model.expand_capabilities(
                ["scheduled-automation"]
            ),
            ["scheduled-automation"],
        )
        self.assertEqual(
            capability_model.expand_capabilities(["remote-release"]),
            ["remote-release"],
        )

    def test_quant_web_profile_is_opt_in_and_narrow(self) -> None:
        generic = capability_model.resolve(
            {}, capabilities=["web-ui"]
        )
        profiled = capability_model.resolve(
            {}, profiles=["quant-research-web"]
        )
        self.assertNotIn(
            "references/web-design-source.md",
            generic["required_references"],
        )
        self.assertIn(
            "references/web-design-source.md",
            profiled["required_references"],
        )
        strict = capability_model.resolve(
            {}, profiles=["quant-public-dashboard-strict"]
        )
        self.assertEqual(strict["effective_capabilities"], [])
        self.assertEqual(strict["assurance"], "strict")
        for optional in (
            "backend",
            "interactive-chart",
            "analysis-input-binding",
        ):
            self.assertNotIn(optional, strict["effective_capabilities"])

    def test_capability_floor_raises_assurance_and_gates(self) -> None:
        resolved = capability_model.resolve(
            {},
            capabilities=["analysis-input-binding"],
            assurance="light",
        )
        self.assertEqual(resolved["assurance"], "strict")
        self.assertTrue(
            {
                "contract",
                "cost",
                "tests",
                "verification",
                "independent_reaudit",
                "analysis_result",
                "input_binding",
            }.issubset(resolved["required_gates"])
        )

    def test_standard_is_generic_until_a_capability_requires_tests(self) -> None:
        generic = capability_model.resolve({}, assurance="standard")
        self.assertIn("verification", generic["required_gates"])
        self.assertNotIn("tests", generic["required_gates"])
        analysis = capability_model.resolve(
            {}, capabilities=["analysis"], assurance="standard"
        )
        self.assertIn("verification", analysis["required_gates"])
        self.assertIn("tests", analysis["required_gates"])

    def test_multi_agent_does_not_raise_assurance_by_itself(self) -> None:
        light = capability_model.resolve(
            {},
            capabilities=["multi-agent-write"],
            assurance="light",
        )
        self.assertEqual(light["assurance"], "light")
        self.assertIn("handoff_review", light["required_gates"])
        self.assertNotIn(
            "independent_reaudit", light["required_gates"]
        )

        strict = capability_model.resolve(
            {},
            capabilities=["multi-agent-write"],
            assurance="strict",
        )
        self.assertIn(
            "independent_reaudit", strict["required_gates"]
        )

    def test_runtime_execution_modes_resolve_individually(self) -> None:
        cases = (
            (
                "multi-agent-write",
                "handoff_review",
                "team_integration",
            ),
            (
                "agent-team-execution",
                "team_integration",
                "handoff_review",
            ),
        )
        for capability, required_gate, excluded_gate in cases:
            with self.subTest(capability=capability):
                resolved = capability_model.resolve(
                    {},
                    capabilities=[capability],
                    assurance="light",
                )
                self.assertEqual(
                    resolved["effective_capabilities"],
                    [capability],
                )
                self.assertIn(required_gate, resolved["required_gates"])
                self.assertNotIn(
                    excluded_gate,
                    resolved["required_gates"],
                )

    def test_runtime_execution_modes_fail_closed_when_combined(self) -> None:
        cases = (
            (
                {},
                ["multi-agent-write", "agent-team-execution"],
            ),
            (
                {"capabilities": ["multi-agent-write"]},
                ["agent-team-execution"],
            ),
            (
                {
                    "capabilities": [
                        "multi-agent-write",
                        "agent-team-execution",
                    ]
                },
                [],
            ),
        )
        for manifest, selected in cases:
            with self.subTest(manifest=manifest, selected=selected):
                with self.assertRaises(
                    capability_model.CapabilityError
                ) as raised:
                    capability_model.resolve(
                        manifest,
                        capabilities=selected,
                    )
                message = str(raised.exception)
                self.assertIn("mutually exclusive", message)
                self.assertIn(
                    "host-native concurrent team", message
                )
                self.assertIn("legacy single-root Story", message)

    def test_delivery_does_not_raise_risk_assurance(self) -> None:
        for capability in (
            "external-data",
            "backend",
            "scheduled-automation",
            "publication",
            "public-web",
        ):
            with self.subTest(capability=capability):
                resolved = capability_model.resolve(
                    {}, capabilities=[capability], assurance="light"
                )
                self.assertEqual(resolved["assurance"], "standard")
        release = capability_model.resolve(
            {}, capabilities=["remote-release"], assurance="light"
        )
        self.assertEqual(release["assurance"], "light")
        self.assertEqual(release["delivery"], "release")
        self.assertIn("release", release["required_gates"])
        self.assertNotIn(
            "independent_reaudit", release["required_gates"]
        )
        standard_release = capability_model.resolve(
            {},
            capabilities=["remote-release"],
            assurance="standard",
        )
        self.assertEqual(standard_release["assurance"], "standard")
        self.assertEqual(standard_release["delivery"], "release")
        self.assertNotIn(
            "independent_reaudit",
            standard_release["required_gates"],
        )
        legacy = capability_model.resolve({}, assurance="release")
        self.assertEqual(legacy["assurance"], "release")
        self.assertEqual(legacy["delivery"], "release")
        self.assertIn("independent_reaudit", legacy["required_gates"])

    def test_delivery_conflicts_fail_closed(self) -> None:
        with self.assertRaises(capability_model.CapabilityError):
            capability_model.resolve(
                {},
                capabilities=["remote-release"],
                delivery="local",
            )
        with self.assertRaises(capability_model.CapabilityError):
            capability_model.resolve({}, delivery="release")

    def test_custom_capability_requires_custom_gate(self) -> None:
        with self.assertRaises(capability_model.CapabilityError):
            capability_model.resolve(
                {
                    "capabilities": ["x-domain-export"],
                    "capability_config": {},
                }
            )
        resolved = capability_model.resolve(
            {
                "capabilities": ["x-domain-export"],
                "capability_config": {
                    "x-domain-export": {
                        "required_gates": ["domain-export"]
                    }
                },
            }
        )
        self.assertIn("domain-export", resolved["required_gates"])


class ProjectManifestV2Tests(unittest.TestCase):
    def test_minimal_manifest_without_repository_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            errors, warnings = validate_project.validate(
                root, base_manifest()
            )
        self.assertEqual(errors, [])
        self.assertIn(
            "no optional project capabilities are active", warnings
        )

    def test_manifest_supports_standard_release_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = base_manifest()
            manifest["assurance"] = "standard"
            manifest["delivery"] = "release"
            manifest["capabilities"] = ["remote-release"]
            manifest["capability_config"] = {
                "remote-release": {
                    "kind": "provider",
                    "targets": [
                        {
                            "id": "public-host",
                            "provider": "free-static-host",
                            "account_or_project": "sample",
                            "action": "publish",
                        }
                    ],
                }
            }
            errors, _warnings = validate_project.validate(root, manifest)
        self.assertEqual(errors, [])
        resolved = capability_model.resolve(manifest)
        self.assertEqual(resolved["assurance"], "standard")
        self.assertEqual(resolved["delivery"], "release")
        self.assertNotIn(
            "independent_reaudit", resolved["required_gates"]
        )

    def test_external_data_requires_closed_free_access_eligibility(
        self,
    ) -> None:
        manifest = base_manifest()
        manifest["capabilities"] = ["external-data"]
        source = {
            "id": "prices",
            "provider": "Official open-data fixture",
            "role": "required",
            "rights_policy": "Public use with attribution",
            "access_eligibility": "permanently-free-no-billing",
            "paid_fallback_enabled": False,
        }
        manifest["capability_config"] = {
            "external-data": {"sources": [source]}
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            errors, warnings = validate_project.validate(root, manifest)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

            source.pop("access_eligibility")
            errors, _ = validate_project.validate(root, manifest)
            self.assertTrue(
                any("access_eligibility must equal" in item for item in errors),
                errors,
            )

            source["access_eligibility"] = (
                "permanently-free-no-billing"
            )
            source["provider"] = "Premium paid price feed"
            source["rights_policy"] = "Paid subscription license"
            errors, _ = validate_project.validate(root, manifest)
            self.assertTrue(
                any("paid data acquisition" in item for item in errors),
                errors,
            )

    def test_scheduled_automation_does_not_require_analysis_or_web(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow = root / "refresh.sh"
            workflow.write_text("#!/bin/sh\n", encoding="utf-8")
            manifest = base_manifest()
            manifest["capabilities"] = ["scheduled-automation"]
            manifest["capability_config"] = {
                "scheduled-automation": {
                    "schedules": [
                        {
                            "id": "refresh",
                            "entrypoint": "refresh.sh",
                            "schedule": "daily",
                            "timezone": "UTC",
                            "last_good_policy": "retain",
                            "retry_ceiling": 1,
                            "concurrency_ceiling": 1,
                            "cost_preflight": {
                                "precedes_remote_work": True
                            },
                        }
                    ]
                }
            }
            errors, _ = validate_project.validate(root, manifest)
        self.assertEqual(errors, [])
        resolved = capability_model.resolve(manifest)
        self.assertNotIn("analysis", resolved["effective_capabilities"])
        self.assertNotIn("publication", resolved["effective_capabilities"])

    def test_analysis_uses_project_owned_result_identity_vocabulary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "model.py").write_text(
                "print('fixture')\n", encoding="utf-8"
            )
            manifest = base_manifest()
            manifest["capabilities"] = ["analysis"]
            manifest["capability_config"] = {
                "analysis": {
                    "authoritative_entrypoints": ["model.py"],
                    "result_identity_fields": [
                        "dataset_revision",
                        "scenario",
                    ],
                }
            }
            errors, _ = validate_project.validate(root, manifest)
        self.assertEqual(errors, [])

    def test_runtime_capability_secret_and_paid_transition_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = base_manifest()
            manifest["capabilities"] = ["multi-agent-write"]
            manifest["extensions"] = {
                "api_token": ["not-a-real-secret"],
                "overage_enabled": True,
            }
            errors, _ = validate_project.validate(root, manifest)
        joined = "\n".join(errors)
        self.assertIn("runtime-only capabilities", joined)
        self.assertIn("must not contain a secret value", joined)
        self.assertIn("overage_enabled must be false", joined)

    def test_manifest_runtime_conflict_reports_mode_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = base_manifest()
            manifest["capabilities"] = [
                "multi-agent-write",
                "agent-team-execution",
            ]
            errors, _ = validate_project.validate(root, manifest)
        joined = "\n".join(errors)
        self.assertIn("mutually exclusive", joined)
        self.assertIn("host-native concurrent team", joined)
        self.assertIn("legacy single-root Story", joined)

    def test_all_paid_aliases_share_one_fail_closed_policy(self) -> None:
        for field in capability_model.PAID_TRANSITION_FIELDS:
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    manifest = base_manifest()
                    manifest["extensions"] = {field: True}
                    errors, _ = validate_project.validate(root, manifest)
                self.assertTrue(
                    any(f"{field} must be false" in error for error in errors),
                    errors,
                )

    def test_camel_case_and_free_text_credentials_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = base_manifest()
            manifest["extensions"] = {
                "apiToken": "fixture-secret",
                "overageEnabled": True,
                "callback": (
                    "https://example.test/callback?accessToken="
                    + "a" * 24
                ),
                "command": (
                    "curl -H 'Authorization: Bearer " + "b" * 24 + "'"
                ),
            }
            errors, _ = validate_project.validate(root, manifest)
        joined = "\n".join(errors)
        self.assertIn("extensions.apiToken must not contain", joined)
        self.assertIn("extensions.overageEnabled must be false", joined)
        self.assertIn("credential-bearing URL query", joined)
        self.assertIn("inline credential", joined)
        self.assertEqual(
            capability_model.literal_secret_reasons(
                "curl -H 'Authorization: Bearer $TOKEN'"
            ),
            [],
        )

    def test_policy_scanner_balances_generic_metadata_and_action_safety(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            benign = base_manifest()
            benign["extensions"] = {
                "token_count": 4096,
                "charge_density_unit": "C/cm2",
                "billing": True,
                "overage": 12.5,
                "database_upgrade_notes": "migrate SQLite to Postgres",
                "add_on_module": "optional visualizer",
                "apiToken": "$API_TOKEN",
                "research_note": "do not enable pay as you go",
                "provider_description": "paid fallback enabled",
                "nested_metadata": [
                    {"token_budget": 8192},
                    {"database_upgrade_notes": "research-only prose"},
                ],
            }
            benign_errors, _ = validate_project.validate(root, benign)

            unsafe = base_manifest()
            unsafe["extensions"] = {
                "command": "enable pay as you go",
                "PAYGEnabled": True,
                "APITokenValue": "fixture-secret-value",
                "note": "paid fallback enabled",
                "description": "disable spend cap",
                "observed_config": [
                    "serviceRole=" + "s" * 24,
                    "accessKey=" + "a" * 24,
                    "connectionString=" + "c" * 24,
                ],
            }
            unsafe_errors, _ = validate_project.validate(root, unsafe)

        self.assertEqual(benign_errors, [])
        joined = "\n".join(unsafe_errors)
        self.assertIn("prohibited paid action", joined)
        self.assertIn("contains an inline credential", joined)
        self.assertIn("PAYGEnabled must be false", joined)
        self.assertIn("APITokenValue must not contain", joined)
        self.assertTrue(
            capability_model.paid_action_text_reasons(
                "disable spend cap is prohibited"
            )
        )
        self.assertEqual(
            capability_model.policy_violations(
                {
                    "description": "disable spend cap is prohibited",
                    "research_note": "paid fallback enabled",
                }
            ),
            [],
        )

    def test_structured_paid_aliases_and_secret_material_fail_closed(
        self,
    ) -> None:
        unsafe_fields = {
            "enableBilling": True,
            "billingEnable": True,
            "paidFallback": True,
            "paidFallbackConfig": "metadata remains inert",
            "allowOverage": True,
            "spendCap": "disabled",
            "apiKeyMaterial": "fixture-api-key-material",
            "privateKeyPem": "fixture-private-key-pem",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = base_manifest()
            manifest["extensions"] = unsafe_fields
            errors, _ = validate_project.validate(root, manifest)
        joined = "\n".join(errors)
        for field in (
            set(unsafe_fields) - {"paidFallbackConfig"}
        ):
            with self.subTest(field=field):
                self.assertIn(f"extensions.{field}", joined)
        self.assertIn("must not enable a paid state", joined)
        self.assertIn("must not disable the spend cap", joined)
        self.assertIn("must not contain a secret value", joined)
        self.assertNotIn(
            "extensions.paidFallbackConfig", joined
        )

        nested = capability_model.policy_violations(
            {
                "paidFallback": {"enabled": True},
                "spendCap": {"disabled": True},
            }
        )
        self.assertTrue(
            any("paidFallback" in error for error in nested), nested
        )
        self.assertTrue(
            any("spendCap" in error for error in nested), nested
        )

    def test_executable_paid_commands_cannot_be_neutralized_by_prose(
        self,
    ) -> None:
        commands = (
            "providerctl billing enable --payg",
            "please enable pay as you go",
            "enable pay as you go; echo never",
            "providerctl enable-payg",
            "providerctl enable_billing=true",
            "providerctl disable-spend-cap",
            ["providerctl", "billing", "enable", "--payg"],
            ["bash", "-lc", "providerctl billing enable --payg"],
            ["enable", "pay as you go"],
            [
                "/usr/bin/env",
                "bash",
                "-lc",
                "providerctl billing enable --payg",
            ],
            [
                "bash",
                "-lc",
                'sh -c "providerctl billing enable --payg"',
            ],
            ["providerctl", "--payg=true"],
            ["providerctl", "--paid-fallback=true"],
            ["providerctl", "--paid-data=true"],
            ["providerctl", "enable", "paid", "dataset"],
            ["providerctl", "billing", "on"],
            [
                "/usr/bin/env",
                "-u",
                "SAFE_VAR",
                "bash",
                "-lc",
                "providerctl billing enable --payg",
            ],
            [
                "sudo",
                "--user",
                "root",
                "bash",
                "-lc",
                "providerctl billing enable --payg",
            ],
            [
                "powershell",
                "-Command",
                "providerctl billing enable --payg",
            ],
            [
                "cmd.exe",
                "/c",
                "providerctl billing enable --payg",
            ],
            ["providerctl", "--payg"],
            ["providerctl", "--payg=1"],
            ["providerctl", "--paid-fallback=yes"],
            [
                "python",
                "-c",
                "import os; os.system('providerctl billing enable --payg')",
            ],
            [
                "env",
                "-S",
                'bash -lc "providerctl billing enable --payg"',
            ],
            [
                "time",
                "-p",
                "bash",
                "-lc",
                "providerctl billing enable --payg",
            ],
            [
                "nice",
                "-n",
                "5",
                "bash",
                "-lc",
                "providerctl billing enable --payg",
            ],
            [
                "node",
                "-e",
                (
                    'require("child_process").execSync('
                    '"providerctl billing enable --payg")'
                ),
            ],
            [
                "python",
                "-c",
                (
                    "import subprocess; subprocess.call("
                    "['providerctl','billing','enable','--payg'])"
                ),
            ],
            ["providerctl", "--auto-renew=true"],
            ["providerctl", "--spend-cap=none"],
            ["providerctl", "--spend-cap=unlimited"],
            ["providerctl", "--payg=auto"],
            ["providerctl", "--auto-renew=default"],
            ["providerctl", "--payg=default"],
            ["providerctl", "--spend-cap=false"],
            ["providerctl", "--spend-cap=unbounded"],
            [
                "env",
                "--split-string=bash -lc "
                "'providerctl billing enable --payg'",
            ],
            [
                "env",
                "-Sbash -lc 'providerctl billing enable --payg'",
            ],
            [
                "nohup",
                "--",
                "bash",
                "-lc",
                "providerctl billing enable --payg",
            ],
            [
                "command",
                "--",
                "bash",
                "-lc",
                "providerctl billing enable --payg",
            ],
            [
                "node",
                "-p",
                (
                    'require("child_process").execFileSync('
                    '"providerctl",["billing","enable","--payg"])'
                ),
            ],
            [
                "node",
                "-e",
                (
                    'require("child_process").spawnSync('
                    '"providerctl",["billing","enable","--payg"])'
                ),
            ],
            [
                "python",
                "-c",
                (
                    "import os; os.execv('providerctl',"
                    "['providerctl','billing','enable','--payg'])"
                ),
            ],
            [
                "python",
                "-c",
                (
                    "import os; os.posix_spawn('providerctl',"
                    "['providerctl','billing','enable','--payg'],{})"
                ),
            ],
            [
                "python",
                "-c",
                (
                    "import asyncio; asyncio.create_subprocess_exec("
                    "'providerctl','billing','enable','--payg')"
                ),
            ],
        )
        for command in commands:
            with self.subTest(command=command):
                reasons = capability_model.paid_action_text_reasons(command)
                self.assertTrue(reasons)

        self.assertEqual(
            capability_model.paid_action_text_reasons(
                ["python", "-m", "unittest", "test_disable_spend_cap"]
            ),
            [],
        )
        benign_commands = (
            ["python", "analyze.py", "--use-billing-data"],
            "python simulate.py --allow-overage-simulation",
            "echo upgrade plan",
            ["grep", "upgrade", "plan", "records.txt"],
            ["logger", "upgrade", "plan"],
            ["python", "simulate.py", "--allow", "overage"],
            ["cat", "upgrade", "plan"],
            ["git", "diff", "upgrade", "plan"],
            ["cp", "upgrade", "plan"],
            ["diff", "upgrade", "plan"],
            ["ls", "upgrade", "plan"],
            ["mv", "upgrade", "plan"],
            ["head", "upgrade", "plan"],
            ["tail", "upgrade", "plan"],
            ["wc", "upgrade", "plan"],
            ["sort", "upgrade", "plan"],
            ["stat", "upgrade", "plan"],
            ["file", "upgrade", "plan"],
            ["touch", "upgrade", "plan"],
        )
        for command in benign_commands:
            with self.subTest(benign_command=command):
                self.assertEqual(
                    capability_model.paid_action_text_reasons(command),
                    [],
                )

        secret_errors = capability_model.policy_violations(
            {
                "command_argv": [
                    "runner",
                    "--api-key",
                    "fixture-secret-value",
                ]
            }
        )
        self.assertTrue(
            any("inline credential" in error for error in secret_errors),
            secret_errors,
        )
        for option in (
            "--private-key",
            "--service-role-key",
            "--connection-string",
            "--secret-key",
        ):
            with self.subTest(secret_option=option):
                errors = capability_model.policy_violations(
                    {
                        "command_argv": [
                            "runner",
                            option,
                            "fixture-secret-value",
                        ]
                    }
                )
                self.assertTrue(
                    any("inline credential" in error for error in errors),
                    errors,
                )
        short_secret_errors = capability_model.policy_violations(
            {
                "command_argv": [
                    "runner",
                    "--secret-key",
                    "s3cr3t",
                ]
            }
        )
        self.assertTrue(
            any(
                "explicit credential option value" in error
                for error in short_secret_errors
            ),
            short_secret_errors,
        )

    def test_unknown_core_fields_and_malformed_arrays_fail_without_crash(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = base_manifest()
            manifest["project"]["unexpected"] = "value"
            manifest["authority"]["allow_charges"] = True
            manifest["capabilities"] = [{}]
            errors, _ = validate_project.validate(root, manifest)
        joined = "\n".join(errors)
        self.assertIn("unknown project fields: unexpected", joined)
        self.assertIn("unknown authority fields: allow_charges", joined)
        self.assertIn("authority.allow_charges must be false", joined)
        self.assertIn("capabilities must be a string array", joined)

    def test_cli_explain_and_require_capability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(base_manifest()), encoding="utf-8"
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_project.py"),
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest_path),
                    "--require-capability",
                    "web-ui",
                    "--explain",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertIn(
            "required capability is not active: web-ui",
            payload["errors"],
        )
        self.assertIn("resolved", payload)


if __name__ == "__main__":
    unittest.main()
