import {
  artifactIdentitySchema,
  projectCapabilitiesSchema,
  runRecordSchema,
  runSubmissionSchema,
  type ArtifactIdentity,
  type ProjectCapabilities,
  type RunRecord,
  type RunSubmission,
} from "@quant-research/contracts";

export interface AnalysisTransport {
  getCapabilities(projectId: string): Promise<ProjectCapabilities>;
  createRun(
    projectId: string,
    submission: RunSubmission,
    idempotencyKey: string,
  ): Promise<RunRecord>;
  getRun(runId: string): Promise<RunRecord>;
  getResult(runId: string): Promise<unknown>;
}

export interface HttpAnalysisTransportOptions {
  baseUrl: string;
  fetcher?: typeof fetch;
  getAccessToken?: () => string | null | Promise<string | null>;
}

function assertSecureUrl(value: string): URL {
  const url = new URL(value);
  const local =
    url.hostname === "localhost" ||
    url.hostname === "127.0.0.1" ||
    url.hostname === "[::1]";
  if (url.protocol !== "https:" && !(local && url.protocol === "http:")) {
    throw new Error("Remote data URLs must use HTTPS.");
  }
  return url;
}

async function responseJson(response: Response): Promise<unknown> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `Analysis API request failed (${response.status})${detail ? `: ${detail}` : ""}`,
    );
  }
  return response.json() as Promise<unknown>;
}

export function createHttpAnalysisTransport(
  options: HttpAnalysisTransportOptions,
): AnalysisTransport {
  const fetcher = options.fetcher ?? fetch;
  const parsedBaseUrl = assertSecureUrl(options.baseUrl);
  if (
    parsedBaseUrl.username ||
    parsedBaseUrl.password ||
    parsedBaseUrl.search ||
    parsedBaseUrl.hash
  ) {
    throw new Error("The analysis API base URL cannot contain credentials, a query, or a fragment.");
  }
  const baseUrl = parsedBaseUrl.toString().replace(/\/$/, "");

  async function headers(includeJson = false): Promise<Headers> {
    const value = new Headers();
    value.set("accept", "application/json");
    if (includeJson) {
      value.set("content-type", "application/json");
    }
    const token = await options.getAccessToken?.();
    if (token) {
      value.set("authorization", `Bearer ${token}`);
    }
    return value;
  }

  return {
    async getCapabilities(projectId) {
      const response = await fetcher(
        `${baseUrl}/v1/projects/${encodeURIComponent(projectId)}/capabilities`,
        { headers: await headers() },
      );
      return projectCapabilitiesSchema.parse(await responseJson(response));
    },

    async createRun(projectId, submissionInput, idempotencyKey) {
      const submission = runSubmissionSchema.parse(submissionInput);
      const requestHeaders = await headers(true);
      requestHeaders.set("idempotency-key", idempotencyKey);
      const response = await fetcher(
        `${baseUrl}/v1/projects/${encodeURIComponent(projectId)}/runs`,
        {
          method: "POST",
          headers: requestHeaders,
          body: JSON.stringify(submission),
        },
      );
      return runRecordSchema.parse(await responseJson(response));
    },

    async getRun(runId) {
      const response = await fetcher(
        `${baseUrl}/v1/runs/${encodeURIComponent(runId)}`,
        { headers: await headers() },
      );
      return runRecordSchema.parse(await responseJson(response));
    },

    async getResult(runId) {
      const response = await fetcher(
        `${baseUrl}/v1/runs/${encodeURIComponent(runId)}/result`,
        { headers: await headers() },
      );
      return responseJson(response);
    },
  };
}

export async function fetchStaticSnapshot(
  url: string,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const safeUrl = assertSecureUrl(url);
  const response = await fetcher(safeUrl, {
    headers: { accept: "application/json" },
  });
  return responseJson(response);
}

export async function fetchArtifactBytes(
  artifactInput: ArtifactIdentity,
  fetcher: typeof fetch = fetch,
): Promise<Uint8Array> {
  const artifact = artifactIdentitySchema.parse(artifactInput);
  const safeUrl = assertSecureUrl(artifact.url);
  const response = await fetcher(safeUrl, {
    headers: { accept: "application/json, application/octet-stream" },
  });
  if (!response.ok) {
    throw new Error(`Artifact request failed (${response.status}).`);
  }
  return new Uint8Array(await response.arrayBuffer());
}
