import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  assessResultBinding,
  buildCanonicalAnalysisInputs,
  hashCanonicalInputsForAlgorithm,
  sha256Hex,
  runRecordSchema,
  runResultEnvelopeSchema,
} from "@quant-research/contracts";
import {
  createPublishedPair,
  testArtifactHash,
  testManifest,
} from "./fixtures";

describe("analysis input canonicalization", () => {
  it("is deterministic for an explicitly adopted client algorithm", async () => {
    const left = await hashCanonicalInputsForAlgorithm(
      { beta: 2, alpha: 1 },
      "js-stable-json-v1",
    );
    const right = await hashCanonicalInputsForAlgorithm(
      { alpha: 1, beta: 2 },
      "js-stable-json-v1",
    );
    expect(left).toEqual(right);
    expect(left.algorithm).toBe("js-stable-json-v1");
    expect(left.digest).toMatch(/^[a-f0-9]{64}$/);
  });

  it("excludes display, result selector, and operation values", () => {
    const baseline = buildCanonicalAnalysisInputs(testManifest, {
      lookback_days: 90,
      visible_rows: 20,
      saved_result: "latest",
      force_refresh: false,
    });
    const changedDisplay = buildCanonicalAnalysisInputs(testManifest, {
      lookback_days: 90,
      visible_rows: 100,
      saved_result: "another",
      force_refresh: true,
    });
    expect(changedDisplay).toEqual(baseline);
    expect(changedDisplay).toEqual({ lookback_days: 90 });
  });
});

describe("published result binding", () => {
  it("accepts only a complete matching identity", async () => {
    const { run, result } = createPublishedPair(
      { lookback_days: 90 },
      { headline: "ready" },
    );
    await expect(assessResultBinding(run, result)).resolves.toEqual({
      accepted: true,
      result,
    });
  });

  it("rejects artifact and input-audit mismatches", async () => {
    const { run, result } = createPublishedPair(
      { lookback_days: 90 },
      { headline: "ready" },
    );
    const artifactMismatch = {
      ...result,
      artifact: { ...result.artifact, sha256: "4".repeat(64) },
    };
    await expect(assessResultBinding(run, artifactMismatch)).resolves.toMatchObject({
      accepted: false,
      reason: "artifact-mismatch",
    });

    const inputMismatch = {
      ...result,
      normalizedInputs: { lookback_days: 91 },
    };
    await expect(assessResultBinding(run, inputMismatch)).resolves.toMatchObject({
      accepted: false,
      reason: "config-mismatch",
    });
  });

  it("fails closed when a published result ignored an input", () => {
    const { result } = createPublishedPair(
      { lookback_days: 90 },
      { headline: "ready" },
    );
    expect(
      runResultEnvelopeSchema.safeParse({
        ...result,
        ignoredInputs: ["lookback_days"],
      }).success,
    ).toBe(false);
  });

  it("uses the server-issued Fear and Greed hash without browser recomputation", async () => {
    const fixtureUrl = new URL(
      "../../../fixtures/contracts/fear-greed-v1.json",
      import.meta.url,
    );
    const fixtureSource = await readFile(fileURLToPath(fixtureUrl), "utf8");
    const fixture = JSON.parse(fixtureSource) as {
      projectId: string;
      inputSchemaVersion: string;
      inputSchemaHash: string;
      inputs: Record<string, unknown>;
      configHashAlgorithm: string;
      defaultConfigHash: string;
    };
    const common = {
      projectId: fixture.projectId,
      runId: "fear-golden-run",
      status: "published" as const,
      inputSchemaVersion: fixture.inputSchemaVersion,
      inputSchemaHash: fixture.inputSchemaHash,
      configHashAlgorithm: fixture.configHashAlgorithm,
      configHash: fixture.defaultConfigHash,
      effectiveConfigHash: fixture.defaultConfigHash,
      requestedInputs: fixture.inputs,
      normalizedInputs: fixture.inputs,
      effectiveInputs: fixture.inputs,
      ignoredInputs: [],
      allowFallback: false,
      fallbackUsed: false,
      fallbacks: [],
      dataAsOf: "2026-07-23",
      calculatedAt: "2026-07-24T00:00:00.000Z",
      codeVersion: "fear-fixture-v1",
      dataIdentity: {
        source: "frontend-test-fixture/fear-greed-v1",
        sourceHash: await sha256Hex(fixtureSource),
        dataAsOf: "2026-07-23",
      },
      artifact: {
        url: "https://sonchanggi.github.io/fearNgreed/data/result.json",
        sha256: testArtifactHash,
        byteSize: 2048,
        contractVersion: "fear-greed/result-v1",
      },
    };
    const run = runRecordSchema.parse({
      ...common,
      provider: "github-actions",
      replayed: true,
      createdAt: "2026-07-24T00:00:00.000Z",
      updatedAt: "2026-07-24T00:00:00.000Z",
    });
    const result = runResultEnvelopeSchema.parse({
      ...common,
      payload: { fixture: true },
    });

    expect(fixture.defaultConfigHash).toBe(
      "cf8d60da8b6ad43c6849c553b953302721857cfccd1f0d49973f032bada922db",
    );
    await expect(assessResultBinding(run, result)).resolves.toMatchObject({
      accepted: true,
    });
  });
});
