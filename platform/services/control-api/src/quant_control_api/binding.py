from __future__ import annotations

import json
import re
from datetime import datetime

from .best_factor import RESULT_CONTRACT_VERSION, canonical_sha256
from .models import WorkerResultManifest
from .store import RunRecord

ALLOWED_FALLBACK_CODES = {"market_cap_metadata_insufficient_preflight"}
BEST_CONTROL_SUMMARY_FIELDS = (
    "best_composite_score",
    "best_factor",
    "best_factor_holdout_cagr",
    "best_factor_holdout_rank",
    "best_factor_holdout_sharpe",
    "data_end_date",
    "effective_factor_count",
    "factor_library_size",
    "factor_preset",
    "fetched_at",
    "holding_count",
    "interpretation_label",
    "provider",
    "ranking_count",
    "selected_factor_count",
    "source_hash",
    "tested_factor_count",
    "universe_as_of_date",
)
MAX_BEST_CONTROL_SUMMARY_BYTES = 64 * 1024


class ResultBindingError(ValueError):
    pass


def bounded_best_result_payload(artifact_payload: dict[str, object]) -> dict[str, object]:
    summary = artifact_payload.get("summary")
    if not isinstance(summary, dict):
        raise ResultBindingError("Best Factor artifact summary is missing")
    bounded = {
        "schema_version": artifact_payload.get("schema_version"),
        "generated_at": artifact_payload.get("generated_at"),
        "summary": {
            key: summary[key]
            for key in BEST_CONTROL_SUMMARY_FIELDS
            if key in summary
        },
    }
    try:
        encoded = json.dumps(
            bounded,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ResultBindingError("Best Factor control summary is not strict JSON") from exc
    if len(encoded) > MAX_BEST_CONTROL_SUMMARY_BYTES:
        raise ResultBindingError("Best Factor control summary exceeds 64 KiB")
    return bounded


def validate_result_binding(record: RunRecord, manifest: WorkerResultManifest, artifact_bytes: bytes) -> None:
    errors: list[str] = []
    binding = manifest.binding
    expected_binding = {
        "projectId": record.project_id,
        "runId": record.run_id,
        "inputSchemaVersion": record.input_schema_version,
        "inputSchemaHash": record.input_schema_hash,
        "configHashAlgorithm": record.config_hash_algorithm,
        "configHash": record.config_hash,
    }
    actual_binding = binding.model_dump(mode="json", by_alias=True)
    if actual_binding != expected_binding:
        errors.append("binding identity does not match the requested run")

    if manifest.requested_inputs != record.requested_inputs:
        errors.append("worker requestedInputs do not exactly match the API requestedInputs")
    if manifest.normalized_inputs != record.normalized_inputs:
        errors.append("worker normalizedInputs do not exactly match the API normalizedInputs")
    if canonical_sha256(manifest.normalized_inputs) != record.config_hash:
        errors.append("worker normalizedInputs do not reproduce configHash")
    if manifest.ignored_inputs:
        errors.append("worker ignored one or more analysis inputs")
    if set(manifest.effective_inputs) != set(record.normalized_inputs):
        errors.append("worker effectiveInputs keys do not match the 11-field normalized contract")
    if canonical_sha256(manifest.effective_inputs) != manifest.effective_config_hash:
        errors.append("worker effectiveInputs do not reproduce effectiveConfigHash")

    differing_inputs = {
        key
        for key, normalized_value in record.normalized_inputs.items()
        if manifest.effective_inputs.get(key) != normalized_value
    }
    fallback_inputs = [event.input for event in manifest.fallbacks]
    if len(fallback_inputs) != len(set(fallback_inputs)):
        errors.append("each fallback input must appear exactly once")
    if set(fallback_inputs) != differing_inputs:
        errors.append("fallbacks must explain every and only requested/effective input difference")
    for event in manifest.fallbacks:
        if event.input not in record.normalized_inputs:
            errors.append("fallback references an unknown input")
            continue
        if event.requested != record.normalized_inputs[event.input]:
            errors.append(f"fallback requested value does not match normalizedInputs.{event.input}")
        if event.effective != manifest.effective_inputs.get(event.input):
            errors.append(f"fallback effective value does not match effectiveInputs.{event.input}")
        if event.code == "market_cap_metadata_insufficient_preflight" and (
            event.input != "min_market_cap" or event.effective not in (0, 0.0)
        ):
            errors.append("market-cap fallback must set min_market_cap to 0")
    fallback_codes = {event.code for event in manifest.fallbacks}
    if manifest.fallback_used != bool(differing_inputs):
        errors.append("fallbackUsed does not match requested/effective differences")
    if manifest.fallback_used and not manifest.fallback_reason:
        errors.append("fallbackReason is required when a fallback was used")
    if manifest.fallback_reason and not manifest.fallback_used:
        errors.append("fallbackReason is present without fallbackUsed")
    if fallback_codes - ALLOWED_FALLBACK_CODES:
        errors.append("worker reported an unknown fallback code")
    if manifest.fallback_used and not record.allow_fallback:
        errors.append("worker used a fallback without explicit consent")
    if not differing_inputs and manifest.effective_config_hash != record.config_hash:
        errors.append("effectiveConfigHash must equal configHash when no fallback changes an input")

    if manifest.data_identity.data_as_of != manifest.data_as_of:
        errors.append("dataIdentity.dataAsOf does not match dataAsOf")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.code_version):
        errors.append("codeVersion must be the exact 40-character worker commit SHA")
    if manifest.artifact.contract_version != RESULT_CONTRACT_VERSION:
        errors.append("artifact contractVersion is not the Best Factor v1 result contract")

    import hashlib

    if hashlib.sha256(artifact_bytes).hexdigest() != manifest.artifact.sha256:
        errors.append("artifact sha256 does not bind the exact fetched bytes")
    if len(artifact_bytes) != manifest.artifact.byte_size:
        errors.append("artifact byteSize does not bind the exact fetched bytes")
    try:
        fetched_payload = json.loads(
            artifact_bytes,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-standard JSON number: {value}")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        errors.append("artifact bytes are not valid UTF-8 JSON")
    else:
        if not isinstance(fetched_payload, dict):
            errors.append("artifact JSON root must be an object")
        else:
            try:
                bounded_payload = bounded_best_result_payload(fetched_payload)
            except ResultBindingError as exc:
                errors.append(str(exc))
            else:
                if manifest.payload != bounded_payload:
                    errors.append(
                        "callback payload is not the bounded summary of the fetched Best Factor artifact"
                    )
            if fetched_payload.get("schema_version") != 1:
                errors.append("artifact schema_version must be 1")
            summary = fetched_payload.get("summary")
            if not isinstance(summary, dict):
                errors.append("artifact summary is missing")
            else:
                if summary.get("data_end_date") != manifest.data_as_of.isoformat():
                    errors.append("artifact summary.data_end_date does not match dataAsOf")
                if (
                    str(summary.get("source_hash") or "").lower()
                    != manifest.data_identity.source_hash
                ):
                    errors.append(
                        "artifact summary.source_hash does not match dataIdentity.sourceHash"
                    )
            generated_at = fetched_payload.get("generated_at")
            try:
                parsed = datetime.fromisoformat(str(generated_at))
            except ValueError:
                errors.append("artifact generated_at is not an ISO-8601 timestamp")
            else:
                if parsed != manifest.calculated_at:
                    errors.append("artifact generated_at does not match calculatedAt")

    if errors:
        raise ResultBindingError("; ".join(errors))
