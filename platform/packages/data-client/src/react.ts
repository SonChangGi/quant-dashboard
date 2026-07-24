import { useSyncExternalStore } from "react";
import {
  AnalysisSession,
  type AnalysisSessionState,
} from "./session";

export function useAnalysisSession<TPayload>(
  session: AnalysisSession<TPayload>,
): AnalysisSessionState<TPayload> {
  return useSyncExternalStore(
    session.subscribe,
    session.getSnapshot,
    session.getSnapshot,
  );
}
