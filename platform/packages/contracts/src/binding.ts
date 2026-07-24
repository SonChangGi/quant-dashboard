import { sha256Hex, stableJsonSerialize } from "./canonical";
import {
  runRecordSchema,
  runResultEnvelopeSchema,
  type ArtifactIdentity,
  type RunRecord,
  type RunResultEnvelope,
} from "./schemas";

export type ResultBindingRejection =
  | "invalid-run"
  | "run-not-published"
  | "invalid-envelope"
  | "project-mismatch"
  | "run-mismatch"
  | "schema-mismatch"
  | "config-mismatch"
  | "data-mismatch"
  | "code-mismatch"
  | "artifact-mismatch";

export type ResultBindingAssessment<TPayload = unknown> =
  | {
      accepted: true;
      result: RunResultEnvelope<TPayload>;
    }
  | {
      accepted: false;
      reason: ResultBindingRejection;
      message: string;
    };

function reject(
  reason: ResultBindingRejection,
  message: string,
): ResultBindingAssessment<never> {
  return { accepted: false, reason, message };
}

export async function assessResultBinding<TPayload = unknown>(
  runInput: RunRecord,
  resultInput: unknown,
): Promise<ResultBindingAssessment<TPayload>> {
  const parsedRun = runRecordSchema.safeParse(runInput);
  if (!parsedRun.success) {
    return reject("invalid-run", "The expected run record is invalid.");
  }
  const run = parsedRun.data;
  if (run.status !== "published") {
    return reject(
      "run-not-published",
      "Only a published run can replace the official result.",
    );
  }

  const parsedResult = runResultEnvelopeSchema.safeParse(resultInput);
  if (!parsedResult.success) {
    return reject("invalid-envelope", "The result envelope is invalid.");
  }
  const result = parsedResult.data as RunResultEnvelope<TPayload>;

  if (result.projectId !== run.projectId) {
    return reject("project-mismatch", "The result belongs to another project.");
  }
  if (result.runId !== run.runId) {
    return reject("run-mismatch", "The result belongs to another run.");
  }
  if (
    result.inputSchemaVersion !== run.inputSchemaVersion ||
    result.inputSchemaHash !== run.inputSchemaHash ||
    result.configHashAlgorithm !== run.configHashAlgorithm
  ) {
    return reject(
      "schema-mismatch",
      "The result input schema differs from the submitted run.",
    );
  }
  if (
    result.configHash !== run.configHash ||
    result.effectiveConfigHash !== run.effectiveConfigHash
  ) {
    return reject(
      "config-mismatch",
      "The result was calculated with different inputs.",
    );
  }
  if (
    stableJsonSerialize(result.requestedInputs) !==
      stableJsonSerialize(run.requestedInputs) ||
    stableJsonSerialize(result.normalizedInputs) !==
      stableJsonSerialize(run.normalizedInputs) ||
    stableJsonSerialize(result.effectiveInputs) !==
      stableJsonSerialize(run.effectiveInputs) ||
    stableJsonSerialize(result.ignoredInputs) !==
      stableJsonSerialize(run.ignoredInputs) ||
    stableJsonSerialize(result.fallbacks) !== stableJsonSerialize(run.fallbacks) ||
    result.allowFallback !== run.allowFallback ||
    result.fallbackUsed !== run.fallbackUsed
  ) {
    return reject(
      "config-mismatch",
      "The result input audit differs from the published run.",
    );
  }
  if (
    result.dataAsOf !== run.dataAsOf ||
    result.dataIdentity.sourceHash !== run.dataIdentity?.sourceHash ||
    result.dataIdentity.dataAsOf !== run.dataIdentity?.dataAsOf
  ) {
    return reject(
      "data-mismatch",
      "The result data snapshot differs from the published run.",
    );
  }
  if (result.codeVersion !== run.codeVersion) {
    return reject(
      "code-mismatch",
      "The result code version differs from the published run.",
    );
  }
  if (
    result.artifact.sha256 !== run.artifact?.sha256 ||
    result.artifact.byteSize !== run.artifact?.byteSize ||
    result.artifact.contractVersion !== run.artifact?.contractVersion ||
    result.artifact.url !== run.artifact?.url
  ) {
    return reject(
      "artifact-mismatch",
      "The result artifact identity differs from the published run.",
    );
  }

  return { accepted: true, result };
}

export async function verifyArtifactBytes(
  bytes: Uint8Array,
  artifact: ArtifactIdentity,
): Promise<boolean> {
  if (bytes.byteLength !== artifact.byteSize) {
    return false;
  }
  return (await sha256Hex(bytes)) === artifact.sha256;
}
