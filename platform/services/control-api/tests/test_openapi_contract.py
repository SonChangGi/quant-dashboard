from __future__ import annotations

import json
from pathlib import Path

from quant_control_api.app import create_app
from quant_control_api.artifacts import MappingArtifactFetcher
from quant_control_api.dual_write import NullDualWritePublisher
from quant_control_api.providers.fake import FakeWorkerProvider
from quant_control_api.settings import Settings
from quant_control_api.store import InMemoryRunStore


def test_openapi_route_and_worker_failure_contract_matches_golden() -> None:
    app = create_app(
        settings=Settings(),
        provider=FakeWorkerProvider(auto_complete=False),
        store=InMemoryRunStore(),
        publisher=NullDualWritePublisher(),
        artifact_fetcher=MappingArtifactFetcher(),
    )
    schema = app.openapi()
    actual_paths = {
        path: sorted(
            method
            for method in operations
            if method in {"get", "post", "put", "patch", "delete"}
        )
        for path, operations in schema["paths"].items()
    }
    golden_path = Path(__file__).parent / "golden" / "openapi-paths.json"
    expected_paths = json.loads(golden_path.read_text(encoding="utf-8"))
    assert actual_paths == expected_paths

    components = schema["components"]["schemas"]
    create_schema = components["RunCreateRequest"]
    version_schema = create_schema["properties"]["inputSchemaVersion"]
    assert version_schema["enum"] == [
        "best-factor/v1",
        "momentum/v1",
        "fear-greed/control-inputs-v1",
    ]

    failure_schema = components["WorkerFailureManifest"]
    error_code = failure_schema["properties"]["errorCode"]
    assert error_code["enum"] == [
        "worker_workflow_failed",
        "worker_analysis_failed",
        "worker_publication_failed",
    ]
    assert failure_schema["required"] == [
        "binding",
        "errorCode",
        "errorMessage",
        "providerRunId",
        "occurredAt",
    ]
