import {
  assessResultBinding,
  buildCanonicalAnalysisInputs,
  controlManifestSchema,
  jsonValueSchema,
  runRecordSchema,
  runResultEnvelopeSchema,
  runSubmissionSchema,
  splitControlDefaults,
  stableJsonSerialize,
  validateControlUpdate,
  verifyArtifactBytes,
  type ControlManifest,
  type InputMap,
  type JsonValue,
  type RunRecord,
  type RunResultEnvelope,
} from "@quant-research/contracts";
import {
  fetchArtifactBytes,
  fetchStaticSnapshot,
  type AnalysisTransport,
} from "./transport";

export type SessionPhase =
  | "idle"
  | "dirty"
  | "submitting"
  | "waiting"
  | "ready"
  | "error";

export interface AppliedConfig {
  inputSchemaVersion: string;
  inputSchemaHash: string;
  configHashAlgorithm: string;
  configHash: string;
  effectiveConfigHash: string;
  requestedInputs: InputMap;
  normalizedInputs: InputMap;
  effectiveInputs: InputMap;
  ignoredInputs: string[];
  allowFallback: boolean;
  fallbackUsed: boolean;
  fallbacks: RunResultEnvelope["fallbacks"];
}

export interface PendingRun {
  runId: string;
  configHash: string;
  inputSchemaVersion: string;
  status: RunRecord["status"];
  requestedInputs: InputMap;
  createdAt: string;
}

export interface BoundResult<TPayload> {
  runId: string;
  configHash: string;
  result: RunResultEnvelope<TPayload>;
}

export interface SessionError {
  code: string;
  message: string;
}

export interface AnalysisSessionState<TPayload> {
  phase: SessionPhase;
  draftConfig: Readonly<Record<string, JsonValue>>;
  displayConfig: Readonly<Record<string, JsonValue>>;
  resultSelectorConfig: Readonly<Record<string, JsonValue>>;
  appliedConfig: AppliedConfig | null;
  pendingRun: PendingRun | null;
  boundResult: BoundResult<TPayload> | null;
  error: SessionError | null;
}

export interface AnalysisSessionOptions<TPayload> {
  manifest: ControlManifest;
  transport: AnalysisTransport;
  parsePayload?: (input: unknown) => TPayload;
  polling?: {
    intervalMs?: number;
    maxAttempts?: number;
  };
  createIdempotencyKey?: () => string;
}

type Listener = () => void;

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, milliseconds);
  });
}

function errorFromUnknown(error: unknown): SessionError {
  if (error instanceof Error) {
    return { code: "analysis_session_error", message: error.message };
  }
  return {
    code: "analysis_session_error",
    message: "An unknown analysis session error occurred.",
  };
}

function isPending(status: RunRecord["status"]): boolean {
  return (
    status === "queued" ||
    status === "dispatched" ||
    status === "running" ||
    status === "validating"
  );
}

function statusRank(status: RunRecord["status"]): number {
  switch (status) {
    case "queued":
      return 0;
    case "dispatched":
      return 1;
    case "running":
      return 2;
    case "validating":
      return 3;
    case "published":
    case "failed":
    case "cancelled":
      return 4;
  }
}

export class AnalysisSession<TPayload = unknown> {
  readonly manifest: ControlManifest;

  private readonly transport: AnalysisTransport;
  private readonly parsePayload: (input: unknown) => TPayload;
  private readonly intervalMs: number;
  private readonly maxAttempts: number;
  private readonly createIdempotencyKey: () => string;
  private listeners = new Set<Listener>();
  private generation = 0;
  private state: AnalysisSessionState<TPayload>;

  constructor(options: AnalysisSessionOptions<TPayload>) {
    this.manifest = controlManifestSchema.parse(options.manifest);
    this.transport = options.transport;
    this.parsePayload =
      options.parsePayload ?? ((payload: unknown) => payload as TPayload);
    // Remote Python analyses can legitimately run for up to three hours.
    // Keep polling bounded, but do not turn a healthy long-running worker into
    // a client-side error after the former 90-second default.
    this.intervalMs = options.polling?.intervalMs ?? 5_000;
    this.maxAttempts = options.polling?.maxAttempts ?? 2_400;
    this.createIdempotencyKey =
      options.createIdempotencyKey ?? (() => globalThis.crypto.randomUUID());

    const defaults = splitControlDefaults(this.manifest);
    this.state = {
      phase: "idle",
      draftConfig: defaults.analysisValues,
      displayConfig: defaults.displayValues,
      resultSelectorConfig: defaults.resultSelectorValues,
      appliedConfig: null,
      pendingRun: null,
      boundResult: null,
      error: null,
    };
  }

  getSnapshot = (): AnalysisSessionState<TPayload> => this.state;

  subscribe = (listener: Listener): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  private publish(patch: Partial<AnalysisSessionState<TPayload>>): void {
    this.state = { ...this.state, ...patch };
    for (const listener of this.listeners) {
      listener();
    }
  }

  setAnalysisInput(controlId: string, value: JsonValue): void {
    const validated = validateControlUpdate(
      this.manifest,
      controlId,
      "analysis",
      value,
    );
    this.publish({
      phase: "dirty",
      draftConfig: { ...this.state.draftConfig, [controlId]: validated },
      error: null,
    });
  }

  setDisplayControl(controlId: string, value: JsonValue): void {
    const validated = validateControlUpdate(
      this.manifest,
      controlId,
      "display",
      value,
    );
    this.publish({
      displayConfig: { ...this.state.displayConfig, [controlId]: validated },
    });
  }

  setResultSelector(controlId: string, value: JsonValue): void {
    const validated = validateControlUpdate(
      this.manifest,
      controlId,
      "result_selector",
      value,
    );
    this.publish({
      resultSelectorConfig: {
        ...this.state.resultSelectorConfig,
        [controlId]: validated,
      },
    });
  }

  async submit(options: { allowFallback?: boolean } = {}): Promise<
    BoundResult<TPayload> | null
  > {
    const currentGeneration = ++this.generation;

    try {
      const inputs = buildCanonicalAnalysisInputs(
        this.manifest,
        this.state.draftConfig,
      );
      const submission = runSubmissionSchema.parse({
        inputSchemaVersion: this.manifest.inputSchemaVersion,
        inputs,
        allowFallback: options.allowFallback ?? false,
      });

      this.publish({
        phase: "submitting",
        pendingRun: null,
        error: null,
      });

      let run = runRecordSchema.parse(
        await this.transport.createRun(
          this.manifest.projectId,
          submission,
          this.createIdempotencyKey(),
        ),
      );
      this.assertRunMatchesSubmission(submission, run);
      const createdRun = run;

      if (currentGeneration !== this.generation) {
        return null;
      }

      this.publish({
        phase: "waiting",
        pendingRun: this.pendingRunFromRecord(run),
      });

      let attempts = 0;
      while (isPending(run.status)) {
        if (attempts >= this.maxAttempts) {
          throw new Error("The analysis run did not finish before the polling limit.");
        }
        attempts += 1;
        await delay(this.intervalMs);
        const polledRun = runRecordSchema.parse(
          await this.transport.getRun(createdRun.runId),
        );
        this.assertRunMatchesSubmission(submission, polledRun, createdRun, run);
        run = polledRun;

        if (currentGeneration !== this.generation) {
          return null;
        }
        this.publish({ pendingRun: this.pendingRunFromRecord(run) });
      }

      if (run.status !== "published") {
        throw new Error(
          run.errorMessage ?? `The analysis run ended with status: ${run.status}`,
        );
      }

      const rawResult = await this.transport.getResult(createdRun.runId);
      const assessment = await assessResultBinding<TPayload>(run, rawResult);
      if (!assessment.accepted) {
        throw new Error(assessment.message);
      }

      const result: RunResultEnvelope<TPayload> = {
        ...assessment.result,
        payload: this.parsePayload(assessment.result.payload),
      };
      const boundResult = {
        runId: result.runId,
        configHash: result.configHash,
        result,
      };

      if (currentGeneration !== this.generation) {
        return null;
      }
      this.publish({
        phase: "ready",
        appliedConfig: this.appliedConfigFromResult(result),
        pendingRun: null,
        boundResult,
        error: null,
      });
      return boundResult;
    } catch (error) {
      if (currentGeneration === this.generation) {
        this.publish({
          phase: "error",
          pendingRun: null,
          error: errorFromUnknown(error),
        });
      }
      return null;
    }
  }

  async bindStaticSnapshot(
    input: unknown,
    fetcher: typeof fetch = fetch,
  ): Promise<BoundResult<TPayload> | null> {
    const currentGeneration = ++this.generation;
    try {
      const envelope = runResultEnvelopeSchema.parse(input);
      if (
        envelope.projectId !== this.manifest.projectId ||
        envelope.inputSchemaVersion !== this.manifest.inputSchemaVersion
      ) {
        throw new Error("The static snapshot contract does not match this project.");
      }
      if (
        this.manifest.inputSchemaHash &&
        envelope.inputSchemaHash !== this.manifest.inputSchemaHash
      ) {
        throw new Error("The static snapshot uses a different input schema.");
      }
      if (envelope.configHashAlgorithm !== this.manifest.configHashAlgorithm) {
        throw new Error("The static snapshot uses a different config hash algorithm.");
      }
      const artifactBytes = await fetchArtifactBytes(envelope.artifact, fetcher);
      if (!(await verifyArtifactBytes(artifactBytes, envelope.artifact))) {
        throw new Error("The static snapshot artifact bytes do not match their declared identity.");
      }
      let artifactPayload: unknown;
      try {
        artifactPayload = JSON.parse(
          new TextDecoder("utf-8", { fatal: true }).decode(artifactBytes),
        );
      } catch {
        throw new Error("The static snapshot artifact is not valid UTF-8 JSON.");
      }
      const verifiedPayload = jsonValueSchema.parse(artifactPayload);
      const envelopePayload = jsonValueSchema.parse(envelope.payload);
      if (
        stableJsonSerialize(verifiedPayload) !==
        stableJsonSerialize(envelopePayload)
      ) {
        throw new Error("The static snapshot payload does not match the verified artifact.");
      }

      const staticRun = runRecordSchema.parse({
        ...envelope,
        provider: "static-snapshot",
        replayed: true,
        createdAt: envelope.calculatedAt,
        updatedAt: envelope.calculatedAt,
      });
      this.assertRunMatchesSubmission(
        runSubmissionSchema.parse({
          inputSchemaVersion: envelope.inputSchemaVersion,
          inputs: envelope.requestedInputs,
          allowFallback: envelope.allowFallback,
        }),
        staticRun,
      );
      const assessment = await assessResultBinding<TPayload>(staticRun, envelope);
      if (!assessment.accepted) {
        throw new Error(assessment.message);
      }

      const result: RunResultEnvelope<TPayload> = {
        ...assessment.result,
        payload: this.parsePayload(verifiedPayload),
      };
      const boundResult = {
        runId: result.runId,
        configHash: result.configHash,
        result,
      };

      if (currentGeneration !== this.generation) {
        return null;
      }
      this.publish({
        phase: "ready",
        draftConfig: this.analysisValuesFromEffectiveInputs(result.effectiveInputs),
        appliedConfig: this.appliedConfigFromResult(result),
        pendingRun: null,
        boundResult,
        error: null,
      });
      return boundResult;
    } catch (error) {
      if (currentGeneration === this.generation) {
        this.publish({
          phase: "error",
          pendingRun: null,
          error: errorFromUnknown(error),
        });
      }
      return null;
    }
  }

  async loadStaticSnapshot(
    url: string,
    fetcher?: typeof fetch,
  ): Promise<BoundResult<TPayload> | null> {
    const currentGeneration = ++this.generation;
    try {
      const resolvedFetcher = fetcher ?? fetch;
      const snapshot = await fetchStaticSnapshot(url, resolvedFetcher);
      if (currentGeneration !== this.generation) {
        return null;
      }
      return this.bindStaticSnapshot(
        snapshot,
        resolvedFetcher,
      );
    } catch (error) {
      if (currentGeneration === this.generation) {
        this.publish({
          phase: "error",
          error: errorFromUnknown(error),
          pendingRun: null,
        });
      }
      return null;
    }
  }

  cancelLocalWait(): void {
    this.generation += 1;
    this.publish({
      phase: this.state.boundResult ? "ready" : "idle",
      pendingRun: null,
      error: null,
    });
  }

  private assertRunMatchesSubmission(
    submission: ReturnType<typeof runSubmissionSchema.parse>,
    run: RunRecord,
    createdRun?: RunRecord,
    previousRun?: RunRecord,
  ): void {
    if (run.projectId !== this.manifest.projectId) {
      throw new Error("The API returned a run for a different project.");
    }
    if (run.inputSchemaVersion !== this.manifest.inputSchemaVersion) {
      throw new Error("The API returned a run for a different input schema.");
    }
    if (
      this.manifest.inputSchemaHash &&
      run.inputSchemaHash !== this.manifest.inputSchemaHash
    ) {
      throw new Error("The API returned a different input schema hash.");
    }
    if (run.configHashAlgorithm !== this.manifest.configHashAlgorithm) {
      throw new Error("The API returned a different config hash algorithm.");
    }
    if (
      stableJsonSerialize(run.requestedInputs) !==
      stableJsonSerialize(submission.inputs)
    ) {
      throw new Error("The API changed requested inputs before recording the run.");
    }
    this.assertAnalysisInputShape(run.requestedInputs, "requested");
    this.assertAnalysisInputShape(run.normalizedInputs, "normalized");
    this.assertAnalysisInputShape(run.effectiveInputs, "effective");
    if (run.allowFallback !== submission.allowFallback) {
      throw new Error("The API changed fallback consent for the run.");
    }
    if (
      !submission.allowFallback &&
      (run.fallbackUsed || run.fallbacks.length > 0 || run.ignoredInputs.length > 0)
    ) {
      throw new Error("The API applied an unapproved fallback or ignored an input.");
    }
    if (
      !submission.allowFallback &&
      run.effectiveConfigHash !== run.configHash
    ) {
      throw new Error("The API changed effective inputs without fallback consent.");
    }
    if (
      createdRun &&
      (run.runId !== createdRun.runId ||
        run.configHash !== createdRun.configHash ||
        run.projectId !== createdRun.projectId ||
        run.provider !== createdRun.provider ||
        run.createdAt !== createdRun.createdAt)
    ) {
      throw new Error("The API changed immutable run identity while polling.");
    }
    if (
      previousRun &&
      statusRank(run.status) < statusRank(previousRun.status)
    ) {
      throw new Error("The API regressed the run status while polling.");
    }
  }

  private assertAnalysisInputShape(inputs: InputMap, label: string): void {
    const controls = this.manifest.controls.filter(
      (control) => control.controlKind === "analysis",
    );
    const expectedKeys = controls
      .map((control) => control.transportKey)
      .sort();
    const observedKeys = Object.keys(inputs).sort();
    if (stableJsonSerialize(observedKeys) !== stableJsonSerialize(expectedKeys)) {
      throw new Error(
        `The ${label} inputs do not exactly match the analysis control registry.`,
      );
    }
    for (const control of controls) {
      const value = inputs[control.transportKey];
      if (value === undefined) {
        throw new Error(
          `The ${label} inputs omit ${control.transportKey}.`,
        );
      }
      validateControlUpdate(
        this.manifest,
        control.id,
        "analysis",
        value,
      );
    }
  }

  private pendingRunFromRecord(run: RunRecord): PendingRun {
    return {
      runId: run.runId,
      configHash: run.configHash,
      inputSchemaVersion: run.inputSchemaVersion,
      status: run.status,
      requestedInputs: run.requestedInputs,
      createdAt: run.createdAt,
    };
  }

  private appliedConfigFromResult(
    result: RunResultEnvelope<TPayload>,
  ): AppliedConfig {
    return {
      inputSchemaVersion: result.inputSchemaVersion,
      inputSchemaHash: result.inputSchemaHash,
      configHashAlgorithm: result.configHashAlgorithm,
      configHash: result.configHash,
      effectiveConfigHash: result.effectiveConfigHash,
      requestedInputs: result.requestedInputs,
      normalizedInputs: result.normalizedInputs,
      effectiveInputs: result.effectiveInputs,
      ignoredInputs: result.ignoredInputs,
      allowFallback: result.allowFallback,
      fallbackUsed: result.fallbackUsed,
      fallbacks: result.fallbacks,
    };
  }

  private analysisValuesFromEffectiveInputs(
    effectiveInputs: InputMap,
  ): Record<string, JsonValue> {
    const values: Record<string, JsonValue> = {};
    for (const control of this.manifest.controls) {
      if (control.controlKind !== "analysis") {
        continue;
      }
      const value = effectiveInputs[control.transportKey];
      if (value === undefined) {
        throw new Error(
          `The snapshot does not include analysis input: ${control.transportKey}`,
        );
      }
      values[control.id] = validateControlUpdate(
        this.manifest,
        control.id,
        "analysis",
        value,
      );
    }
    return values;
  }
}
