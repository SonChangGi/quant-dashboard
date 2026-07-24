import { z } from "zod";

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

export const jsonValueSchema: z.ZodType<JsonValue> = z.lazy(() =>
  z.union([
    z.string(),
    z.number().finite(),
    z.boolean(),
    z.null(),
    z.array(jsonValueSchema),
    z.record(jsonValueSchema),
  ]),
);

export const inputMapSchema = z.record(jsonValueSchema);
export type InputMap = z.infer<typeof inputMapSchema>;

export const controlKindSchema = z.enum([
  "display",
  "result_selector",
  "analysis",
  "operation",
]);
export type ControlKind = z.infer<typeof controlKindSchema>;

export const controlValueTypeSchema = z.enum([
  "string",
  "number",
  "boolean",
  "string-array",
]);

const controlBaseSchema = z.object({
  id: z.string().regex(/^[a-z][a-z0-9_]*$/),
  label: z.string().min(1),
  valueType: controlValueTypeSchema,
  defaultValue: jsonValueSchema,
  defaultSource: z.enum(["html-constant", "current-result", "saved-setting"]),
  unit: z.string().min(1).optional(),
  minimum: z.number().finite().optional(),
  maximum: z.number().finite().optional(),
  step: z.number().positive().optional(),
  options: z
    .array(
      z.object({
        value: z.string(),
        label: z.string().min(1),
      }),
    )
    .min(1)
    .optional(),
});

export const analysisControlDefinitionSchema = controlBaseSchema.extend({
  controlKind: z.literal("analysis"),
  transportKey: z.string().min(1),
  pythonParameter: z.string().min(1),
  noOpCondition: z.string().min(1).optional(),
  resultEvidencePath: z.string().min(1),
});

export const displayControlDefinitionSchema = controlBaseSchema.extend({
  controlKind: z.literal("display"),
});

export const resultSelectorControlDefinitionSchema = controlBaseSchema.extend({
  controlKind: z.literal("result_selector"),
  resultIdentityKey: z.string().min(1),
});

export const operationControlDefinitionSchema = controlBaseSchema.extend({
  controlKind: z.literal("operation"),
  operationKey: z.string().min(1),
  requiresAuthentication: z.literal(true),
});

export const controlDefinitionSchema = z.discriminatedUnion("controlKind", [
  displayControlDefinitionSchema,
  resultSelectorControlDefinitionSchema,
  analysisControlDefinitionSchema,
  operationControlDefinitionSchema,
]);

export type AnalysisControlDefinition = z.infer<
  typeof analysisControlDefinitionSchema
>;
export type DisplayControlDefinition = z.infer<
  typeof displayControlDefinitionSchema
>;
export type ResultSelectorControlDefinition = z.infer<
  typeof resultSelectorControlDefinitionSchema
>;
export type OperationControlDefinition = z.infer<
  typeof operationControlDefinitionSchema
>;
export type ControlDefinition = z.infer<typeof controlDefinitionSchema>;

export const controlManifestSchema = z
  .object({
    schemaVersion: z.literal(1),
    projectId: z.string().regex(/^[a-z][a-z0-9-]*$/),
    inputSchemaVersion: z.string().regex(/^[a-z][a-z0-9-]*\/v[1-9][0-9]*$/),
    inputSchemaHash: z.string().regex(/^[a-f0-9]{64}$/).optional(),
    configHashAlgorithm: z.string().min(1),
    controls: z.array(controlDefinitionSchema),
  })
  .superRefine((manifest, context) => {
    const ids = new Set<string>();
    const transportKeys = new Set<string>();
    const pythonParameters = new Set<string>();

    for (const control of manifest.controls) {
      if (ids.has(control.id)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Duplicate control id: ${control.id}`,
          path: ["controls"],
        });
      }
      ids.add(control.id);

      if (control.controlKind === "analysis") {
        if (transportKeys.has(control.transportKey)) {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Duplicate transport key: ${control.transportKey}`,
            path: ["controls"],
          });
        }
        if (pythonParameters.has(control.pythonParameter)) {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Duplicate Python parameter: ${control.pythonParameter}`,
            path: ["controls"],
          });
        }
        transportKeys.add(control.transportKey);
        pythonParameters.add(control.pythonParameter);
      }
    }
  });

export type ControlManifest = z.infer<typeof controlManifestSchema>;

export const runSubmissionSchema = z.object({
  inputSchemaVersion: z.string().min(1),
  inputs: inputMapSchema,
  allowFallback: z.boolean(),
});
export type RunSubmission = z.infer<typeof runSubmissionSchema>;

export const projectCapabilitiesSchema = z.object({
  projectId: z.string().regex(/^[a-z][a-z0-9-]*$/),
  projectName: z.string().min(1),
  inputSchemaVersion: z.string().min(1),
  inputSchemaHash: z.string().regex(/^[a-f0-9]{64}$/),
  configHashAlgorithm: z.string().min(1),
  acceptsRuns: z.boolean(),
  defaultInputs: inputMapSchema,
  defaultConfigHash: z.string().regex(/^[a-f0-9]{64}$/),
  inputs: z.array(
    z.object({
      key: z.string().min(1),
      label: z.string().min(1),
      type: z.enum(["enum", "integer", "number", "string-list"]),
      required: z.boolean(),
      default: jsonValueSchema,
      choices: z.array(z.string()).nullable().optional(),
      minimum: z.number().nullable().optional(),
      maximum: z.number().nullable().optional(),
      exclusiveMinimum: z.number().nullable().optional(),
      exclusiveMaximum: z.number().nullable().optional(),
      unit: z.string().nullable().optional(),
      cliArgument: z.string().min(1),
      workflowInput: z.string().min(1),
    }),
  ),
  fallback: z.object({
    defaultAllowed: z.boolean(),
    analysisRunAllowFallback: z.boolean(),
    scheduledOwnerOperationMayFallback: z.boolean(),
    possibleWhen: z.string().min(1),
    reason: z.string().min(1),
    providerCanEnforceRejection: z.boolean(),
  }),
  provider: z.object({
    name: z.string().min(1),
    runCreationEnabled: z.boolean(),
    executesHeavyAnalysisInApi: z.boolean(),
    statusTracking: z.enum(["native", "adapter-required", "disabled"]),
    resultBinding: z.enum(["manifest-required", "disabled"]),
  }),
  endpoints: z.record(z.string().min(1)),
  staticFallbackUrl: z.string().url(),
});
export type ProjectCapabilities = z.infer<typeof projectCapabilitiesSchema>;

export const runStatusSchema = z.enum([
  "queued",
  "dispatched",
  "running",
  "validating",
  "published",
  "failed",
  "cancelled",
]);
export type RunStatus = z.infer<typeof runStatusSchema>;

export const artifactIdentitySchema = z.object({
  url: z.string().url(),
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
  byteSize: z.number().int().nonnegative(),
  contractVersion: z.string().min(1),
});
export type ArtifactIdentity = z.infer<typeof artifactIdentitySchema>;

export const dataIdentitySchema = z.object({
  source: z.string().min(1),
  sourceHash: z.string().regex(/^[a-f0-9]{8,128}$/),
  dataAsOf: z.string().min(1),
});
export type DataIdentity = z.infer<typeof dataIdentitySchema>;

export const fallbackRecordSchema = z.object({
  input: z.string().min(1),
  code: z.string().min(1),
  requested: jsonValueSchema,
  effective: jsonValueSchema,
  reason: z.string().min(1),
});
export type FallbackRecord = z.infer<typeof fallbackRecordSchema>;

const runIdentityFields = {
  projectId: z.string().regex(/^[a-z][a-z0-9-]*$/),
  runId: z.string().min(1),
  inputSchemaVersion: z.string().min(1),
  inputSchemaHash: z.string().regex(/^[a-f0-9]{64}$/),
  configHashAlgorithm: z.string().min(1),
  configHash: z.string().regex(/^[a-f0-9]{64}$/),
  effectiveConfigHash: z.string().regex(/^[a-f0-9]{64}$/),
  requestedInputs: inputMapSchema,
  normalizedInputs: inputMapSchema,
  effectiveInputs: inputMapSchema,
  ignoredInputs: z.array(z.string().min(1)),
  allowFallback: z.boolean(),
  fallbackUsed: z.boolean(),
  fallbackReason: z.string().min(1).optional(),
  fallbacks: z.array(fallbackRecordSchema),
};

function stableValue(value: JsonValue): string {
  if (Array.isArray(value)) {
    return `[${value.map(stableValue).join(",")}]`;
  }
  if (value !== null && typeof value === "object") {
    return `{${Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, child]) => `${JSON.stringify(key)}:${stableValue(child)}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function validateFallbackEvidence(
  value: {
    requestedInputs: InputMap;
    effectiveInputs: InputMap;
    allowFallback: boolean;
    fallbackUsed: boolean;
    fallbacks: FallbackRecord[];
  },
  context: z.RefinementCtx,
): void {
  if (value.fallbackUsed !== (value.fallbacks.length > 0)) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "fallbackUsed must match whether fallback records exist.",
      path: ["fallbackUsed"],
    });
  }
  if (
    "configHash" in value &&
    "effectiveConfigHash" in value &&
    !value.fallbackUsed &&
    value.configHash !== value.effectiveConfigHash
  ) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "configHash and effectiveConfigHash must match without fallback.",
      path: ["effectiveConfigHash"],
    });
  }
  if (value.fallbackUsed && !value.allowFallback) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      message: "A fallback cannot be used when allowFallback is false.",
      path: ["fallbackUsed"],
    });
  }

  const inputKeys = new Set([
    ...Object.keys(value.requestedInputs),
    ...Object.keys(value.effectiveInputs),
  ]);
  for (const key of inputKeys) {
    const requested = value.requestedInputs[key];
    const effective = value.effectiveInputs[key];
    if (
      requested !== undefined &&
      effective !== undefined &&
      stableValue(requested) === stableValue(effective)
    ) {
      continue;
    }
    if (!value.fallbacks.some((fallback) => fallback.input === key)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: `Input difference requires fallback evidence: ${key}`,
        path: ["fallbacks"],
      });
    }
  }
}

export const runRecordSchema = z
  .object({
    ...runIdentityFields,
    status: runStatusSchema,
    provider: z.string().min(1),
    providerRunId: z.string().min(1).optional(),
    replayed: z.boolean(),
    createdAt: z.string().datetime(),
    updatedAt: z.string().datetime(),
    dataAsOf: z.string().min(1).optional(),
    calculatedAt: z.string().datetime().optional(),
    codeVersion: z.string().min(1).optional(),
    dataIdentity: dataIdentitySchema.optional(),
    artifact: artifactIdentitySchema.optional(),
    errorCode: z.string().min(1).optional(),
    errorMessage: z.string().min(1).optional(),
  })
  .superRefine((run, context) => {
    if (
      run.status === "published" &&
      (!run.dataAsOf ||
        !run.calculatedAt ||
        !run.codeVersion ||
        !run.dataIdentity ||
        !run.artifact)
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Published runs require complete data, code, and artifact identity.",
      });
    }
    if (run.status === "published" && run.ignoredInputs.length > 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Published results cannot ignore submitted analysis inputs.",
        path: ["ignoredInputs"],
      });
    }
    validateFallbackEvidence(run, context);
  });
export type RunRecord = z.infer<typeof runRecordSchema>;

export const runResultEnvelopeSchema = z
  .object({
    ...runIdentityFields,
    status: z.literal("published"),
    dataAsOf: z.string().min(1),
    calculatedAt: z.string().datetime(),
    codeVersion: z.string().min(1),
    dataIdentity: dataIdentitySchema,
    artifact: artifactIdentitySchema,
    payload: z.unknown(),
  })
  .superRefine((result, context) => {
    if (result.dataIdentity.dataAsOf !== result.dataAsOf) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "dataIdentity.dataAsOf must match dataAsOf.",
        path: ["dataIdentity", "dataAsOf"],
      });
    }
    if (result.ignoredInputs.length > 0) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Published results cannot ignore submitted analysis inputs.",
        path: ["ignoredInputs"],
      });
    }
    validateFallbackEvidence(result, context);
  });

export interface RunResultEnvelope<TPayload = unknown>
  extends Omit<z.infer<typeof runResultEnvelopeSchema>, "payload"> {
  payload: TPayload;
}

export function parseRunResultEnvelope<TPayload>(
  input: unknown,
  payloadSchema: z.ZodType<TPayload>,
): RunResultEnvelope<TPayload> {
  const envelope = runResultEnvelopeSchema.parse(input);
  return {
    ...envelope,
    payload: payloadSchema.parse(envelope.payload),
  };
}
