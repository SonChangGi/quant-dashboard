import { describe, expect, it } from "vitest";
import type {
  ProjectCapabilities,
  RunRecord,
  RunResultEnvelope,
  RunSubmission,
} from "@quant-research/contracts";
import { sha256Hex, stableJsonSerialize } from "@quant-research/contracts";
import {
  AnalysisSession,
  type AnalysisTransport,
} from "@quant-research/data-client";
import {
  createPublishedPair,
  testInputSchemaHash,
  testManifest,
} from "./fixtures";

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function pairFor(
  lookbackDays: number,
  runId: string,
  configHash: string,
): {
  run: RunRecord;
  result: RunResultEnvelope<{ value: number }>;
} {
  const pair = createPublishedPair(
    { lookback_days: lookbackDays },
    { value: lookbackDays },
  );
  pair.run.runId = runId;
  pair.result.runId = runId;
  pair.run.configHash = configHash;
  pair.run.effectiveConfigHash = configHash;
  pair.result.configHash = configHash;
  pair.result.effectiveConfigHash = configHash;
  return pair;
}

async function bindVerifiedStaticSnapshot<TPayload>(
  session: AnalysisSession<TPayload>,
  result: RunResultEnvelope<TPayload>,
) {
  const verified = await verifiedStaticSnapshot(result);
  return session.bindStaticSnapshot(verified.result, async () =>
    new Response(verified.payloadBytes, {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
}

async function verifiedStaticSnapshot<TPayload>(
  result: RunResultEnvelope<TPayload>,
) {
  const payloadText = stableJsonSerialize(result.payload);
  const payloadBytes = new TextEncoder().encode(payloadText);
  const verifiedResult = {
    ...result,
    artifact: {
      ...result.artifact,
      sha256: await sha256Hex(payloadBytes),
      byteSize: payloadBytes.byteLength,
    },
  };
  return { result: verifiedResult, payloadBytes };
}

class DeferredTransport implements AnalysisTransport {
  readonly creation = deferred<RunRecord>();
  submission: RunSubmission | null = null;
  idempotencyKey: string | null = null;
  result: unknown = null;

  async getCapabilities(): Promise<ProjectCapabilities> {
    return {
      projectId: testManifest.projectId,
      projectName: "Test Dashboard",
      inputSchemaVersion: testManifest.inputSchemaVersion,
      inputSchemaHash: testInputSchemaHash,
      configHashAlgorithm: testManifest.configHashAlgorithm,
      acceptsRuns: true,
      defaultInputs: { lookback_days: 90 },
      defaultConfigHash: "2".repeat(64),
      inputs: [
        {
          key: "lookback_days",
          label: "분석 기간",
          type: "integer",
          required: true,
          default: 90,
          minimum: 20,
          maximum: 365,
          unit: "일",
          cliArgument: "--lookback-days",
          workflowInput: "lookback_days",
        },
      ],
      fallback: {
        defaultAllowed: false,
        analysisRunAllowFallback: false,
        scheduledOwnerOperationMayFallback: false,
        possibleWhen: "never",
        reason: "test",
        providerCanEnforceRejection: true,
      },
      provider: {
        name: "test",
        runCreationEnabled: true,
        executesHeavyAnalysisInApi: false,
        statusTracking: "native",
        resultBinding: "manifest-required",
      },
      endpoints: { createRun: "/v1/projects/test-dashboard/runs" },
      staticFallbackUrl: "https://example.test/test/latest.json",
    };
  }

  async createRun(
    _projectId: string,
    submission: RunSubmission,
    idempotencyKey: string,
  ) {
    this.submission = submission;
    this.idempotencyKey = idempotencyKey;
    return this.creation.promise;
  }

  async getRun(): Promise<RunRecord> {
    throw new Error("A published create response should not be polled.");
  }

  async getResult() {
    return this.result;
  }
}

class SwappedRunTransport implements AnalysisTransport {
  readonly initial: RunRecord;
  readonly swapped: RunRecord;
  resultRequested = false;

  constructor(initial: RunRecord, swapped: RunRecord) {
    this.initial = initial;
    this.swapped = swapped;
  }

  async getCapabilities(): Promise<ProjectCapabilities> {
    throw new Error("Capabilities are not used by this test.");
  }

  async createRun(): Promise<RunRecord> {
    return this.initial;
  }

  async getRun(): Promise<RunRecord> {
    return this.swapped;
  }

  async getResult(): Promise<unknown> {
    this.resultRequested = true;
    return null;
  }
}

describe("AnalysisSession", () => {
  it("keeps the official result while draft and pending state change", async () => {
    const transport = new DeferredTransport();
    const session = new AnalysisSession<{ value: number }>({
      manifest: testManifest,
      transport,
      parsePayload(value) {
        if (
          typeof value !== "object" ||
          value === null ||
          typeof (value as { value?: unknown }).value !== "number"
        ) {
          throw new Error("Invalid test payload.");
        }
        return value as { value: number };
      },
      createIdempotencyKey: () => "session-test-key",
    });
    const oldPair = pairFor(90, "run-old", "8".repeat(64));
    await bindVerifiedStaticSnapshot(session, oldPair.result);

    session.setAnalysisInput("lookback_days", 120);
    expect(session.getSnapshot()).toMatchObject({
      phase: "dirty",
      boundResult: { runId: "run-old" },
      appliedConfig: { effectiveInputs: { lookback_days: 90 } },
      draftConfig: { lookback_days: 120 },
    });

    const newPair = pairFor(120, "run-new", "9".repeat(64));
    transport.result = newPair.result;
    const submissionPromise = session.submit();
    await Promise.resolve();

    expect(session.getSnapshot()).toMatchObject({
      phase: "submitting",
      boundResult: { runId: "run-old" },
      appliedConfig: { effectiveInputs: { lookback_days: 90 } },
    });
    expect(transport.submission).toEqual({
      inputSchemaVersion: testManifest.inputSchemaVersion,
      inputs: { lookback_days: 120 },
      allowFallback: false,
    });
    expect(transport.idempotencyKey).toBe("session-test-key");

    transport.creation.resolve(newPair.run);
    await submissionPromise;
    expect(session.getSnapshot()).toMatchObject({
      phase: "ready",
      pendingRun: null,
      boundResult: {
        runId: "run-new",
        result: { payload: { value: 120 } },
      },
      appliedConfig: { effectiveInputs: { lookback_days: 120 } },
    });
  });

  it("retains the last bound result when a new run fails", async () => {
    const transport = new DeferredTransport();
    const session = new AnalysisSession({
      manifest: testManifest,
      transport,
      createIdempotencyKey: () => "session-failure-key",
    });
    const oldPair = pairFor(90, "run-old", "8".repeat(64));
    await bindVerifiedStaticSnapshot(session, oldPair.result);
    session.setAnalysisInput("lookback_days", 120);

    const submissionPromise = session.submit();
    transport.creation.reject(new Error("worker unavailable"));
    await submissionPromise;

    expect(session.getSnapshot()).toMatchObject({
      phase: "error",
      boundResult: { runId: "run-old" },
      appliedConfig: { effectiveInputs: { lookback_days: 90 } },
      error: { message: "worker unavailable" },
    });
  });

  it("does not create a run for display changes", async () => {
    const transport = new DeferredTransport();
    const session = new AnalysisSession({
      manifest: testManifest,
      transport,
      createIdempotencyKey: () => "display-test-key",
    });
    const oldPair = pairFor(90, "run-old", "8".repeat(64));
    await bindVerifiedStaticSnapshot(session, oldPair.result);
    session.setDisplayControl("visible_rows", 100);

    expect(transport.submission).toBeNull();
    expect(session.getSnapshot()).toMatchObject({
      phase: "ready",
      displayConfig: { visible_rows: 100 },
      boundResult: { runId: "run-old" },
      appliedConfig: { effectiveInputs: { lookback_days: 90 } },
    });
  });

  it("rejects tampered static artifact bytes and preserves the last verified result", async () => {
    const transport = new DeferredTransport();
    const session = new AnalysisSession<{ value: number }>({
      manifest: testManifest,
      transport,
    });
    const oldPair = pairFor(90, "run-old", "8".repeat(64));
    await bindVerifiedStaticSnapshot(session, oldPair.result);

    const tamperedPair = pairFor(120, "run-tampered", "9".repeat(64));
    const tamperedBytes = new TextEncoder().encode('{"value":999}');
    const result = await session.bindStaticSnapshot(
      tamperedPair.result,
      async () => new Response(tamperedBytes, { status: 200 }),
    );

    expect(result).toBeNull();
    expect(session.getSnapshot()).toMatchObject({
      phase: "error",
      boundResult: { runId: "run-old", result: { payload: { value: 90 } } },
      error: {
        message:
          "The static snapshot artifact bytes do not match their declared identity.",
      },
    });
  });

  it("does not let an older static fetch replace a newer verified snapshot", async () => {
    const transport = new DeferredTransport();
    const session = new AnalysisSession<{ value: number }>({
      manifest: testManifest,
      transport,
    });
    const oldSnapshot = await verifiedStaticSnapshot(
      pairFor(90, "run-old", "8".repeat(64)).result,
    );
    const newSnapshot = await verifiedStaticSnapshot(
      pairFor(120, "run-new", "9".repeat(64)).result,
    );
    const oldEnvelope = deferred<Response>();
    let oldArtifactRequests = 0;

    const firstLoad = session.loadStaticSnapshot(
      "https://example.test/results/old-envelope.json",
      async (input) => {
        if (String(input).endsWith("old-envelope.json")) {
          return oldEnvelope.promise;
        }
        oldArtifactRequests += 1;
        return new Response(oldSnapshot.payloadBytes, { status: 200 });
      },
    );
    const secondLoad = session.loadStaticSnapshot(
      "https://example.test/results/new-envelope.json",
      async (input) => {
        if (String(input).endsWith("new-envelope.json")) {
          return Response.json(newSnapshot.result);
        }
        return new Response(newSnapshot.payloadBytes, { status: 200 });
      },
    );

    await secondLoad;
    oldEnvelope.resolve(Response.json(oldSnapshot.result));
    await firstLoad;

    expect(oldArtifactRequests).toBe(0);
    expect(session.getSnapshot()).toMatchObject({
      phase: "ready",
      boundResult: {
        runId: "run-new",
        result: { payload: { value: 120 } },
      },
      error: null,
    });
  });

  it("rejects a different run identity returned while polling", async () => {
    const initialPair = pairFor(120, "run-created", "9".repeat(64));
    initialPair.run.status = "queued";
    const swappedPair = pairFor(120, "run-swapped", "9".repeat(64));
    const transport = new SwappedRunTransport(initialPair.run, swappedPair.run);
    const session = new AnalysisSession({
      manifest: testManifest,
      transport,
      polling: { intervalMs: 1, maxAttempts: 2 },
    });
    session.setAnalysisInput("lookback_days", 120);

    const result = await session.submit();

    expect(result).toBeNull();
    expect(transport.resultRequested).toBe(false);
    expect(session.getSnapshot()).toMatchObject({
      phase: "error",
      boundResult: null,
      error: {
        message: "The API changed immutable run identity while polling.",
      },
    });
  });

  it("rejects a static snapshot that claims an unapproved ignored input", async () => {
    const transport = new DeferredTransport();
    const session = new AnalysisSession<{ value: number }>({
      manifest: testManifest,
      transport,
    });
    const snapshot = await verifiedStaticSnapshot(
      pairFor(90, "run-static-fallback", "8".repeat(64)).result,
    );
    snapshot.result.ignoredInputs = ["lookback_days"];

    const result = await session.bindStaticSnapshot(
      snapshot.result,
      async () => new Response(snapshot.payloadBytes, { status: 200 }),
    );

    expect(result).toBeNull();
    expect(session.getSnapshot()).toMatchObject({
      phase: "error",
      boundResult: null,
    });
    expect(session.getSnapshot().error?.message).toContain(
      "Published results cannot ignore submitted analysis inputs.",
    );
  });
});
