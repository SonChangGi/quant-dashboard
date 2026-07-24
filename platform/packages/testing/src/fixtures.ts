import type {
  ControlManifest,
  InputMap,
  RunRecord,
  RunResultEnvelope,
} from "@quant-research/contracts";

export const testInputSchemaHash = "1".repeat(64);
export const testConfigHash = "2".repeat(64);
export const testArtifactHash = "3".repeat(64);

export const testManifest: ControlManifest = {
  schemaVersion: 1,
  projectId: "test-dashboard",
  inputSchemaVersion: "test-dashboard/v1",
  inputSchemaHash: testInputSchemaHash,
  configHashAlgorithm: "test-python-json-v1",
  controls: [
    {
      id: "lookback_days",
      label: "분석 기간",
      controlKind: "analysis",
      valueType: "number",
      defaultValue: 90,
      defaultSource: "current-result",
      unit: "일",
      minimum: 20,
      maximum: 365,
      step: 1,
      transportKey: "lookback_days",
      pythonParameter: "--lookback-days",
      resultEvidencePath: "metadata.effectiveInputs.lookback_days",
    },
    {
      id: "visible_rows",
      label: "표시 행",
      controlKind: "display",
      valueType: "number",
      defaultValue: 20,
      defaultSource: "html-constant",
      unit: "행",
      minimum: 5,
      maximum: 100,
      step: 5,
    },
    {
      id: "saved_result",
      label: "저장 결과",
      controlKind: "result_selector",
      valueType: "string",
      defaultValue: "latest",
      defaultSource: "current-result",
      options: [{ value: "latest", label: "최신" }],
      resultIdentityKey: "runId",
    },
    {
      id: "force_refresh",
      label: "강제 갱신",
      controlKind: "operation",
      valueType: "boolean",
      defaultValue: false,
      defaultSource: "html-constant",
      operationKey: "force_refresh",
      requiresAuthentication: true,
    },
  ],
};

export function createPublishedPair<TPayload>(
  inputs: InputMap,
  payload: TPayload,
  overrides: Partial<RunRecord> = {},
): {
  run: RunRecord;
  result: RunResultEnvelope<TPayload>;
} {
  const common: Omit<RunResultEnvelope<TPayload>, "status" | "payload"> = {
    projectId: testManifest.projectId,
    runId: "run-test-001",
    inputSchemaVersion: testManifest.inputSchemaVersion,
    inputSchemaHash: testInputSchemaHash,
    configHashAlgorithm: testManifest.configHashAlgorithm,
    configHash: testConfigHash,
    effectiveConfigHash: testConfigHash,
    requestedInputs: inputs,
    normalizedInputs: inputs,
    effectiveInputs: inputs,
    ignoredInputs: [],
    allowFallback: false,
    fallbackUsed: false,
    fallbacks: [],
    dataAsOf: "2026-07-23",
    calculatedAt: "2026-07-24T00:00:00.000Z",
    codeVersion: "test-code-v1",
    dataIdentity: {
      source: "fixture",
      sourceHash: "abcdef1234567890",
      dataAsOf: "2026-07-23",
    },
    artifact: {
      url: "https://example.test/results/run-test-001.json",
      sha256: testArtifactHash,
      byteSize: 128,
      contractVersion: "test-result/v1",
    },
  };

  const run: RunRecord = {
    ...common,
    status: "published",
    provider: "test",
    replayed: false,
    createdAt: "2026-07-24T00:00:00.000Z",
    updatedAt: "2026-07-24T00:00:00.000Z",
    ...overrides,
  };
  const result: RunResultEnvelope<TPayload> = {
    ...common,
    status: "published",
    payload,
  };
  return { run, result };
}
