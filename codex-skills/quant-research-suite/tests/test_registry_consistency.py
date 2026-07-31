from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "shared"
SCRIPTS = SHARED / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capability_model


class RegistryConsistencyTests(unittest.TestCase):
    def test_every_builtin_capability_has_gates_and_a_readable_module(self) -> None:
        self.assertEqual(
            set(capability_model.CAPABILITIES),
            set(capability_model.CAPABILITY_GATES),
        )
        self.assertEqual(
            set(capability_model.CAPABILITIES),
            set(capability_model.CAPABILITY_REFERENCES),
        )
        for capability, references in sorted(
            capability_model.CAPABILITY_REFERENCES.items()
        ):
            with self.subTest(capability=capability):
                self.assertTrue(references)
                self.assertTrue(
                    capability_model.CAPABILITY_GATES[capability]
                )
                for reference in references:
                    path = SHARED / reference
                    self.assertTrue(path.is_file(), reference)
                    self.assertFalse(path.is_symlink(), reference)

    def test_profiles_reference_only_known_capabilities_and_files(self) -> None:
        self.assertEqual(
            set(capability_model.PROFILE_CAPABILITIES),
            set(capability_model.PROFILE_ASSURANCE),
        )
        self.assertEqual(
            set(capability_model.PROFILE_CAPABILITIES),
            set(capability_model.PROFILE_REFERENCES),
        )
        for profile, capabilities in sorted(
            capability_model.PROFILE_CAPABILITIES.items()
        ):
            with self.subTest(profile=profile):
                self.assertTrue(
                    set(capabilities).issubset(
                        capability_model.PROJECT_CAPABILITIES
                    )
                )
                for reference in capability_model.PROFILE_REFERENCES[profile]:
                    self.assertTrue((SHARED / reference).is_file(), reference)
        self.assertIn(
            "references/operating-principles.md",
            capability_model.PROFILE_REFERENCES[
                "quant-public-dashboard-strict"
            ],
        )

    def test_registered_adapter_references_exist(self) -> None:
        for adapter, reference in sorted(
            capability_model.ADAPTER_REFERENCES.items()
        ):
            with self.subTest(adapter=adapter):
                path = SHARED / reference
                self.assertTrue(path.is_file(), reference)
                self.assertFalse(path.is_symlink(), reference)

    def test_runtime_capabilities_are_not_project_capabilities(self) -> None:
        self.assertTrue(capability_model.RUNTIME_CAPABILITIES)
        self.assertTrue(
            capability_model.RUNTIME_CAPABILITIES.isdisjoint(
                capability_model.PROJECT_CAPABILITIES
            )
        )

    def test_runtime_capabilities_form_one_exclusive_registry_group(
        self,
    ) -> None:
        groups = capability_model.MUTUALLY_EXCLUSIVE_CAPABILITY_GROUPS
        self.assertEqual(set(groups), {"runtime-execution-mode"})
        self.assertEqual(
            groups["runtime-execution-mode"],
            capability_model.RUNTIME_CAPABILITIES,
        )
        for name, capabilities in groups.items():
            with self.subTest(group=name):
                self.assertIsInstance(capabilities, frozenset)
                self.assertGreaterEqual(len(capabilities), 2)
                self.assertTrue(
                    capabilities.issubset(capability_model.CAPABILITIES)
                )

    def test_agent_team_execution_is_optional_runtime_proof(self) -> None:
        capability = "agent-team-execution"
        self.assertIn(capability, capability_model.RUNTIME_CAPABILITIES)
        self.assertNotIn(
            capability,
            capability_model.CAPABILITY_ASSURANCE_FLOOR,
        )
        self.assertEqual(
            capability_model.CAPABILITY_GATES[capability],
            {"team_integration"},
        )
        self.assertIn(
            "capabilities/agent-team-execution.md",
            capability_model.CAPABILITY_REFERENCES[capability],
        )


if __name__ == "__main__":
    unittest.main()
