import { describe, expect, it, vi } from "vitest";
import {
  createHttpAnalysisTransport,
  fetchArtifactBytes,
  fetchStaticSnapshot,
} from "@quant-research/data-client";
import {
  createPublishedPair,
  testInputSchemaHash,
  testManifest,
} from "./fixtures";

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

describe("HTTP analysis transport", () => {
  it("uses the project-scoped POST and common run GET routes", async () => {
    const pair = createPublishedPair(
      { lookback_days: 90 },
      { value: 90 },
    );
    const capabilities = {
      projectId: testManifest.projectId,
      projectName: "Test Dashboard",
      inputSchemaVersion: testManifest.inputSchemaVersion,
      inputSchemaHash: testInputSchemaHash,
      configHashAlgorithm: testManifest.configHashAlgorithm,
      acceptsRuns: true,
      defaultInputs: { lookback_days: 90 },
      defaultConfigHash: pair.run.configHash,
      inputs: [
        {
          key: "lookback_days",
          label: "분석 기간",
          type: "integer",
          required: true,
          default: 90,
          choices: null,
          minimum: 20,
          maximum: 365,
          exclusiveMinimum: 19,
          exclusiveMaximum: null,
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
      endpoints: {
        createRun: "/v1/projects/test-dashboard/runs",
        status: "/v1/runs/{runId}",
        result: "/v1/runs/{runId}/result",
      },
      staticFallbackUrl: "https://example.test/test/latest.json",
    };
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    const fetcher = vi.fn(async (input: URL | RequestInfo, init?: RequestInit) => {
      const url = String(input);
      calls.push({ url, init });
      if (url.endsWith("/capabilities")) return jsonResponse(capabilities);
      if (url.endsWith("/runs") && init?.method === "POST") {
        return jsonResponse(pair.run);
      }
      if (url.endsWith("/result")) return jsonResponse(pair.result);
      return jsonResponse(pair.run);
    }) as unknown as typeof fetch;
    const transport = createHttpAnalysisTransport({
      baseUrl: "https://api.example.test/",
      fetcher,
    });

    const parsedCapabilities = await transport.getCapabilities(testManifest.projectId);
    await transport.createRun(
      testManifest.projectId,
      {
        inputSchemaVersion: testManifest.inputSchemaVersion,
        inputs: { lookback_days: 90 },
        allowFallback: false,
      },
      "idempotency-test-key",
    );
    await transport.getRun(pair.run.runId);
    await transport.getResult(pair.run.runId);

    expect(calls.map((call) => call.url)).toEqual([
      "https://api.example.test/v1/projects/test-dashboard/capabilities",
      "https://api.example.test/v1/projects/test-dashboard/runs",
      `https://api.example.test/v1/runs/${pair.run.runId}`,
      `https://api.example.test/v1/runs/${pair.run.runId}/result`,
    ]);
    const postHeaders = calls[1]?.init?.headers as Headers;
    expect(postHeaders.get("idempotency-key")).toBe("idempotency-test-key");
    expect(JSON.parse(String(calls[1]?.init?.body))).toEqual({
      inputSchemaVersion: testManifest.inputSchemaVersion,
      inputs: { lookback_days: 90 },
      allowFallback: false,
    });
    expect(parsedCapabilities.inputs[0]).toMatchObject({
      exclusiveMinimum: 19,
      exclusiveMaximum: null,
    });
  });

  it("rejects insecure remote snapshot and artifact URLs", async () => {
    const fetcher = vi.fn() as unknown as typeof fetch;
    await expect(
      fetchStaticSnapshot("http://example.test/result.json", fetcher),
    ).rejects.toThrow(/HTTPS/);
    await expect(
      fetchArtifactBytes(
        {
          url: "http://example.test/result.json",
          sha256: "3".repeat(64),
          byteSize: 10,
          contractVersion: "test/v1",
        },
        fetcher,
      ),
    ).rejects.toThrow(/HTTPS/);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("rejects an insecure or credential-bearing control API before reading a token", () => {
    const getAccessToken = vi.fn(() => "owner-secret");
    expect(() =>
      createHttpAnalysisTransport({
        baseUrl: "http://api.example.test",
        getAccessToken,
      }),
    ).toThrow(/HTTPS/);
    expect(() =>
      createHttpAnalysisTransport({
        baseUrl: "https://owner-secret@api.example.test",
        getAccessToken,
      }),
    ).toThrow(/credentials/);
    expect(getAccessToken).not.toHaveBeenCalled();
  });
});
