import {
  hashCanonicalInputsForAlgorithm,
  sha256Hex,
  stableJsonSerialize,
  type ControlManifest,
  type InputMap,
  type RunRecord,
  type RunResultEnvelope,
  type RunSubmission,
} from "@quant-research/contracts";
import type { AnalysisTransport } from "@quant-research/data-client";
import { z } from "zod";

export const referenceSchemaHash = "6".repeat(64);

export const referenceManifest: ControlManifest = {
  schemaVersion: 1,
  projectId: "reference-dashboard",
  inputSchemaVersion: "reference-dashboard/v1",
  inputSchemaHash: referenceSchemaHash,
  configHashAlgorithm: "js-stable-json-v1",
  controls: [
    {
      id: "lookback_days",
      label: "분석 기간",
      controlKind: "analysis",
      valueType: "number",
      defaultValue: 90,
      defaultSource: "current-result",
      unit: "일",
      minimum: 30,
      maximum: 365,
      step: 30,
      transportKey: "lookback_days",
      pythonParameter: "--lookback-days",
      resultEvidencePath: "metadata.effectiveInputs.lookback_days",
    },
    {
      id: "threshold",
      label: "참조 임계값",
      controlKind: "analysis",
      valueType: "number",
      defaultValue: 1,
      defaultSource: "current-result",
      minimum: 0.5,
      maximum: 2,
      step: 0.1,
      transportKey: "threshold",
      pythonParameter: "--threshold",
      resultEvidencePath: "metadata.effectiveInputs.threshold",
    },
    {
      id: "visible_rows",
      label: "차트 관측",
      controlKind: "display",
      valueType: "number",
      defaultValue: 8,
      defaultSource: "html-constant",
      unit: "개",
      minimum: 4,
      maximum: 12,
      step: 1,
    },
  ],
};

const chartPointSchema = z.object({
  x: z.string(),
  values: z.record(z.number().nullable()),
});

export const referencePayloadSchema = z.object({
  headline: z.string(),
  score: z.number(),
  points: z.array(chartPointSchema),
});
export type ReferencePayload = z.infer<typeof referencePayloadSchema>;

function payloadFor(inputs: InputMap): ReferencePayload {
  const lookback =
    typeof inputs.lookback_days === "number" ? inputs.lookback_days : 90;
  const threshold = typeof inputs.threshold === "number" ? inputs.threshold : 1;
  const offset = lookback / 180 + threshold;
  return {
    headline: "입력 계약과 결과 바인딩이 연결됨",
    score: Number((70 + offset).toFixed(1)),
    points: Array.from({ length: 12 }, (_, index) => ({
      x: `07.${String(index + 1).padStart(2, "0")}`,
      values: {
        focal: Number((60 + index * 1.1 + offset).toFixed(2)),
        benchmark: Number((61 + index * 0.55).toFixed(2)),
      },
    })),
  };
}

async function createIdentity(
  runId: string,
  submission: RunSubmission,
  source: "computed" | "static-snapshot",
): Promise<{
  run: RunRecord;
  result: RunResultEnvelope<ReferencePayload>;
}> {
  const fingerprint = await hashCanonicalInputsForAlgorithm(
    submission.inputs,
    "js-stable-json-v1",
  );
  const payload = payloadFor(submission.inputs);
  const payloadText = stableJsonSerialize(payload);
  const artifactHash = await sha256Hex(payloadText);
  const calculatedAt = new Date().toISOString();
  const common: Omit<
    RunResultEnvelope<ReferencePayload>,
    "status" | "payload"
  > = {
    projectId: referenceManifest.projectId,
    runId,
    inputSchemaVersion: referenceManifest.inputSchemaVersion,
    inputSchemaHash: referenceSchemaHash,
    configHashAlgorithm: fingerprint.algorithm,
    configHash: fingerprint.digest,
    effectiveConfigHash: fingerprint.digest,
    requestedInputs: submission.inputs,
    normalizedInputs: submission.inputs,
    effectiveInputs: submission.inputs,
    ignoredInputs: [],
    allowFallback: submission.allowFallback,
    fallbackUsed: false,
    fallbacks: [],
    dataAsOf: "2026-07-23",
    calculatedAt,
    codeVersion: "reference-adapter/v1",
    dataIdentity: {
      source,
      sourceHash: "1234567890abcdef",
      dataAsOf: "2026-07-23",
    },
    artifact: {
      url: `https://example.test/reference/${runId}.json`,
      sha256: artifactHash,
      byteSize: new TextEncoder().encode(payloadText).byteLength,
      contractVersion: "reference-result/v1",
    },
  };
  return {
    run: {
      ...common,
      status: "published",
      provider: source === "computed" ? "reference-adapter" : "static-snapshot",
      replayed: source === "static-snapshot",
      createdAt: calculatedAt,
      updatedAt: calculatedAt,
    },
    result: {
      ...common,
      status: "published",
      payload,
    },
  };
}

export class ReferenceTransport implements AnalysisTransport {
  private runs = new Map<
    string,
    { run: RunRecord; result: RunResultEnvelope<ReferencePayload> }
  >();
  private sequence = 0;

  async getCapabilities() {
    return {
      projectId: referenceManifest.projectId,
      projectName: "Reference Dashboard",
      inputSchemaVersion: referenceManifest.inputSchemaVersion,
      inputSchemaHash: referenceSchemaHash,
      configHashAlgorithm: referenceManifest.configHashAlgorithm,
      acceptsRuns: true,
      defaultInputs: { lookback_days: 90, threshold: 1 },
      defaultConfigHash: "0".repeat(64),
      inputs: [
        {
          key: "lookback_days",
          label: "분석 기간",
          type: "integer" as const,
          required: true,
          default: 90,
          minimum: 30,
          maximum: 365,
          unit: "일",
          cliArgument: "--lookback-days",
          workflowInput: "lookback_days",
        },
        {
          key: "threshold",
          label: "참조 임계값",
          type: "number" as const,
          required: true,
          default: 1,
          minimum: 0.5,
          maximum: 2,
          cliArgument: "--threshold",
          workflowInput: "threshold",
        },
      ],
      fallback: {
        defaultAllowed: false,
        analysisRunAllowFallback: false,
        scheduledOwnerOperationMayFallback: false,
        possibleWhen: "없음",
        reason: "참조 adapter는 fallback을 사용하지 않습니다.",
        providerCanEnforceRejection: true,
      },
      provider: {
        name: "reference-adapter",
        runCreationEnabled: true,
        executesHeavyAnalysisInApi: false,
        statusTracking: "native" as const,
        resultBinding: "manifest-required" as const,
      },
      endpoints: {
        createRun: "/v1/projects/reference-dashboard/runs",
      },
      staticFallbackUrl: "https://example.test/reference/latest.json",
    };
  }

  async createRun(
    _projectId: string,
    submission: RunSubmission,
    _idempotencyKey: string,
  ) {
    const runId = `reference-run-${++this.sequence}`;
    const pair = await createIdentity(runId, submission, "computed");
    this.runs.set(runId, pair);
    return pair.run;
  }

  async getRun(runId: string) {
    const pair = this.runs.get(runId);
    if (!pair) throw new Error(`Unknown reference run: ${runId}`);
    return pair.run;
  }

  async getResult(runId: string) {
    const pair = this.runs.get(runId);
    if (!pair) throw new Error(`Unknown reference run: ${runId}`);
    return pair.result;
  }
}

export async function createReferenceStaticSnapshot() {
  return (
    await createIdentity(
      "reference-static-001",
      {
        inputSchemaVersion: referenceManifest.inputSchemaVersion,
        inputs: { lookback_days: 90, threshold: 1 },
        allowFallback: false,
      },
      "static-snapshot",
    )
  ).result;
}
