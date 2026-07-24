import {
  controlManifestSchema,
  inputMapSchema,
  jsonValueSchema,
  type ControlDefinition,
  type ControlKind,
  type ControlManifest,
  type InputMap,
  type JsonValue,
} from "./schemas";

export type ControlValues = Readonly<Record<string, JsonValue>>;

function validateControlValue(
  control: ControlDefinition,
  value: JsonValue,
): JsonValue {
  switch (control.valueType) {
    case "number": {
      if (typeof value !== "number" || !Number.isFinite(value)) {
        throw new TypeError(`${control.id} must be a finite number.`);
      }
      if (control.minimum !== undefined && value < control.minimum) {
        throw new RangeError(`${control.id} must be at least ${control.minimum}.`);
      }
      if (control.maximum !== undefined && value > control.maximum) {
        throw new RangeError(`${control.id} must be at most ${control.maximum}.`);
      }
      return Object.is(value, -0) ? 0 : value;
    }
    case "boolean":
      if (typeof value !== "boolean") {
        throw new TypeError(`${control.id} must be a boolean.`);
      }
      return value;
    case "string":
      if (typeof value !== "string") {
        throw new TypeError(`${control.id} must be a string.`);
      }
      if (
        control.options &&
        !control.options.some((option) => option.value === value)
      ) {
        throw new RangeError(`${control.id} is not an allowed option.`);
      }
      return value;
    case "string-array":
      if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
        throw new TypeError(`${control.id} must be an array of strings.`);
      }
      return [...value];
  }
}

export function splitControlDefaults(manifestInput: ControlManifest): {
  analysisValues: Record<string, JsonValue>;
  displayValues: Record<string, JsonValue>;
  resultSelectorValues: Record<string, JsonValue>;
  operationValues: Record<string, JsonValue>;
} {
  const manifest = controlManifestSchema.parse(manifestInput);
  const analysisValues: Record<string, JsonValue> = {};
  const displayValues: Record<string, JsonValue> = {};
  const resultSelectorValues: Record<string, JsonValue> = {};
  const operationValues: Record<string, JsonValue> = {};

  for (const control of manifest.controls) {
    const validated = validateControlValue(control, control.defaultValue);
    switch (control.controlKind) {
      case "analysis":
        analysisValues[control.id] = validated;
        break;
      case "display":
        displayValues[control.id] = validated;
        break;
      case "result_selector":
        resultSelectorValues[control.id] = validated;
        break;
      case "operation":
        operationValues[control.id] = validated;
        break;
    }
  }

  return {
    analysisValues,
    displayValues,
    resultSelectorValues,
    operationValues,
  };
}

export function validateControlUpdate(
  manifestInput: ControlManifest,
  controlId: string,
  expectedKind: ControlKind,
  value: JsonValue,
): JsonValue {
  const manifest = controlManifestSchema.parse(manifestInput);
  const control = manifest.controls.find((candidate) => candidate.id === controlId);
  if (!control) {
    throw new RangeError(`Unknown control: ${controlId}`);
  }
  if (control.controlKind !== expectedKind) {
    throw new TypeError(
      `${controlId} is ${control.controlKind}, not ${expectedKind}.`,
    );
  }
  return validateControlValue(control, value);
}

export function buildCanonicalAnalysisInputs(
  manifestInput: ControlManifest,
  values: ControlValues,
): InputMap {
  const manifest = controlManifestSchema.parse(manifestInput);
  const inputs: Record<string, JsonValue> = {};
  const analysisControls = manifest.controls
    .filter((control) => control.controlKind === "analysis")
    .sort((left, right) => left.transportKey.localeCompare(right.transportKey));

  for (const control of analysisControls) {
    const value = values[control.id] ?? control.defaultValue;
    inputs[control.transportKey] = validateControlValue(control, value);
  }
  return inputMapSchema.parse(inputs);
}

function sortJson(value: JsonValue): JsonValue {
  if (Array.isArray(value)) {
    return value.map(sortJson);
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, child]) => [key, sortJson(child)]),
    );
  }
  return value;
}

export function stableJsonSerialize(value: unknown): string {
  return JSON.stringify(sortJson(jsonValueSchema.parse(value)));
}

export async function sha256Hex(value: string | Uint8Array): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new Error("Web Crypto is required to create a SHA-256 digest.");
  }
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value;
  const digestBytes = Uint8Array.from(bytes);
  const digest = await globalThis.crypto.subtle.digest(
    "SHA-256",
    digestBytes.buffer,
  );
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

export const supportedClientHashAlgorithm = "js-stable-json-v1" as const;
export type ClientHashAlgorithm = typeof supportedClientHashAlgorithm;

/**
 * Optional fingerprint for projects that explicitly adopt js-stable-json-v1.
 * It is never a substitute for a server-issued configHash. Existing Python
 * schemas such as best-factor-python-json-v1 serialize typed floats differently.
 */
export async function hashCanonicalInputsForAlgorithm(
  inputs: InputMap,
  algorithm: ClientHashAlgorithm,
): Promise<{ algorithm: ClientHashAlgorithm; digest: string }> {
  if (algorithm !== supportedClientHashAlgorithm) {
    throw new Error(`Unsupported client hash algorithm: ${String(algorithm)}`);
  }
  const parsed = inputMapSchema.parse(inputs);
  return {
    algorithm,
    digest: await sha256Hex(stableJsonSerialize(parsed)),
  };
}
