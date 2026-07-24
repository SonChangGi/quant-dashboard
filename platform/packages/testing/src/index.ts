import type {
  RunRecord,
  RunSubmission,
  RunResultEnvelope,
} from "@quant-research/contracts";

export interface RecordedRun<TPayload = unknown> {
  projectId: string;
  idempotencyKey: string;
  submission: RunSubmission;
  record: RunRecord;
  result: RunResultEnvelope<TPayload>;
}

export function assertResultIdentity<TPayload>(
  previous: RunResultEnvelope<TPayload>,
  next: RunResultEnvelope<TPayload>,
): void {
  if (previous.runId !== next.runId) {
    throw new Error(`run_id changed: ${previous.runId} → ${next.runId}`);
  }
  if (previous.configHash !== next.configHash) {
    throw new Error("config_hash changed.");
  }
  if (previous.dataAsOf !== next.dataAsOf) {
    throw new Error(`data_as_of changed: ${previous.dataAsOf} → ${next.dataAsOf}`);
  }
  if (JSON.stringify(previous.payload) !== JSON.stringify(next.payload)) {
    throw new Error("The protected result payload changed.");
  }
}

export * from "./fixtures";
