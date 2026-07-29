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

import validate_project


class V1CompatibilityTests(unittest.TestCase):
    def test_dispatch_is_byte_for_byte_equivalent_to_v1_validator(self) -> None:
        template = json.loads(
            (
                ROOT
                / "shared"
                / "templates"
                / "quant-project.example.json"
            ).read_text(encoding="utf-8")
        )
        fixtures = [
            template,
            {
                "schema_version": 1,
                "project": {},
                "protected": {},
                "inputs": {},
                "analysis": {},
                "results": {},
                "frontend": {},
                "automation": {},
                "release": {},
            },
            {"schema_version": 1},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for fixture in fixtures:
                with self.subTest(keys=sorted(fixture)):
                    expected = validate_project.validate_v1(root, fixture)
                    dispatched = validate_project.validate(root, fixture)
                    self.assertEqual(dispatched, expected)

    def test_v2_only_receipt_flags_fail_closed_for_v1_and_v2(self) -> None:
        for schema_version in (1, 2):
            with self.subTest(schema_version=schema_version):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    receipt = root / "receipt.json"
                    receipt.write_text(
                        json.dumps(
                            {
                                "schema_version": schema_version,
                                "project_id": "sample",
                                "objective": "Historical fixture.",
                            }
                        ),
                        encoding="utf-8",
                    )
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(SCRIPTS / "validate_evidence.py"),
                            str(receipt),
                            "--project-root",
                            str(root),
                            "--minimum-assurance",
                            "strict",
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                self.assertNotEqual(completed.returncode, 0)
                if schema_version == 1:
                    self.assertIn("legacy v1 is blocked", completed.stdout)
                else:
                    self.assertIn(
                        "options require receipt schema_version 3",
                        completed.stdout,
                    )
                self.assertNotIn("Traceback", completed.stderr)

    def test_v2_future_completion_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = root / "receipt.json"
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "project_id": "sample",
                        "objective": "Reject future-dated completion.",
                        "completed_at": "2099-01-01T00:00:00Z",
                        "required_gates": [],
                        "gates": {},
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_evidence.py"),
                    str(receipt),
                    "--project-root",
                    str(root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "completed_at exceeds allowed future clock skew",
            completed.stdout,
        )


if __name__ == "__main__":
    unittest.main()
