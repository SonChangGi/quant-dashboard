import { useEffect, useMemo } from "react";
import { AccessibleLineChart } from "@quant-research/charts";
import {
  AnalysisSession,
  useAnalysisSession,
} from "@quant-research/data-client";
import { DashboardShell } from "@quant-research/shell";
import {
  ControlPanel,
  MetricCard,
  SectionHeading,
  StatusStrip,
} from "@quant-research/ui";
import {
  ReferenceTransport,
  createReferenceStaticSnapshot,
  referenceManifest,
  referencePayloadSchema,
} from "./contracts";
import { stableJsonSerialize } from "@quant-research/contracts";

function phaseLabel(phase: string): string {
  switch (phase) {
    case "dirty":
      return "변경한 입력은 아직 결과에 적용되지 않았습니다.";
    case "submitting":
    case "waiting":
      return "새 실행 결과를 확인하고 있습니다.";
    case "error":
      return "새 결과를 적용하지 못했습니다.";
    case "ready":
      return "검증된 결과";
    default:
      return "저장 결과 불러오는 중";
  }
}

export function App() {
  const session = useMemo(
    () =>
      new AnalysisSession({
        manifest: referenceManifest,
        transport: new ReferenceTransport(),
        parsePayload: (value) => referencePayloadSchema.parse(value),
        polling: { intervalMs: 10, maxAttempts: 5 },
      }),
    [],
  );
  const state = useAnalysisSession(session);

  useEffect(() => {
    let active = true;
    void createReferenceStaticSnapshot().then((snapshot) => {
      if (!active) return;
      const payloadBytes = new TextEncoder().encode(
        stableJsonSerialize(snapshot.payload),
      );
      void session.bindStaticSnapshot(
        snapshot,
        async () =>
          new Response(payloadBytes, {
            status: 200,
            headers: { "content-type": "application/json" },
          }),
      );
    });
    return () => {
      active = false;
      session.cancelLocalWait();
    };
  }, [session]);

  const payload = state.boundResult?.result.payload;
  const visibleRows =
    typeof state.displayConfig.visible_rows === "number"
      ? state.displayConfig.visible_rows
      : 8;
  const points = payload?.points.slice(-visibleRows) ?? [];
  const result = state.boundResult?.result;
  const busy = state.phase === "submitting" || state.phase === "waiting";

  return (
    <DashboardShell
      currentProject="hub"
      eyebrow="Platform reference"
      operationsDetails={
        <dl className="reference-operations">
          <div>
            <dt>입력 schema</dt>
            <dd>{referenceManifest.inputSchemaVersion}</dd>
          </div>
          <div>
            <dt>hash algorithm</dt>
            <dd>{referenceManifest.configHashAlgorithm}</dd>
          </div>
          <div>
            <dt>정적 fallback</dt>
            <dd>검증된 envelope만 채택</dd>
          </div>
        </dl>
      }
      title="Frontend Contract Reference"
    >
      <StatusStrip
        items={[
          {
            label: "상태",
            value: state.error ? "새 실행 실패 · 이전 결과 유지" : phaseLabel(state.phase),
            tone: state.error ? "negative" : "positive",
          },
          {
            label: "데이터 기준일",
            value: result?.dataAsOf ?? "확인 중",
          },
          {
            label: "현재 run",
            value: result?.runId ?? "없음",
          },
          {
            label: "config hash",
            value: result ? `${result.configHash.slice(0, 10)}…` : "없음",
          },
        ]}
      />

      <section className="reference-section">
        <SectionHeading eyebrow="Primary result" title="현재 결합된 결과" />
        <div className="reference-metrics">
          <MetricCard
            label="결론"
            meta={
              result?.dataIdentity.source === "static-snapshot"
                ? "저장 snapshot"
                : "새 실행"
            }
            tone="primary"
            value={payload?.headline ?? "결과 확인 중"}
          />
          <MetricCard
            label="참조 점수"
            meta={result?.dataAsOf}
            value={payload ? payload.score.toFixed(1) : "—"}
          />
          <MetricCard
            label="적용 분석 기간"
            meta="effectiveInputs"
            value={
              typeof state.appliedConfig?.effectiveInputs.lookback_days === "number"
                ? `${state.appliedConfig.effectiveInputs.lookback_days}일`
                : "—"
            }
          />
        </div>
      </section>

      <section className="reference-section">
        <SectionHeading
          eyebrow="Chart interaction"
          title="plot 밖 정확값과 계열 강조"
        />
        <AccessibleLineChart
          initialSeriesId="focal"
          meta={`${points.length}개 관측`}
          points={points}
          series={[
            {
              id: "focal",
              label: "선택 계열",
              color: "var(--qr-chart-focal)",
            },
            {
              id: "benchmark",
              label: "비교 계열",
              color: "var(--qr-chart-benchmark)",
            },
          ]}
          title="계약 참조 시계열"
          valueLabel="참조값"
        />
      </section>

      <section className="reference-section">
        <SectionHeading
          eyebrow="Control registry"
          title="화면 상태와 분석 상태"
        />
        <ControlPanel
          appliedValues={Object.fromEntries(
            referenceManifest.controls
              .filter((control) => control.controlKind === "analysis")
              .flatMap((control) => {
                const value =
                  state.appliedConfig?.effectiveInputs[control.transportKey];
                return value === undefined ? [] : [[control.id, value]];
              }),
          )}
          busy={busy}
          canSubmit
          displayValues={state.displayConfig}
          draftValues={state.draftConfig}
          manifest={referenceManifest}
          onAnalysisChange={(id, value) => session.setAnalysisInput(id, value)}
          onDisplayChange={(id, value) => session.setDisplayControl(id, value)}
          onSubmit={() => void session.submit()}
          phaseLabel={state.error?.message ?? phaseLabel(state.phase)}
          submitLabel="새 분석 실행"
        />
      </section>
    </DashboardShell>
  );
}
