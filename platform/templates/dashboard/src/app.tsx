import { useState } from "react";
import { AccessibleLineChart } from "@quant-research/charts";
import type { JsonValue } from "@quant-research/contracts";
import { DashboardShell } from "@quant-research/shell";
import {
  ControlPanel,
  MetricCard,
  SectionHeading,
  StatusStrip,
} from "@quant-research/ui";
import { dashboardDefinition as definition } from "./dashboard-definition";

export function App() {
  const [draftValues, setDraftValues] = useState<Record<string, JsonValue>>({
    example_analysis_input: 1,
  });
  const [displayValues, setDisplayValues] = useState<Record<string, JsonValue>>({
    visible_rows: 20,
  });

  return (
    <DashboardShell
      currentProject={definition.projectId}
      eyebrow={definition.eyebrow}
      operationsDetails={
        <p>
          프로젝트의 실제 공급자·생성 시각·fallback·자동화 링크를 이 한 곳에
          연결합니다.
        </p>
      }
      supportingCopy={definition.supportingCopy}
      title={definition.title}
    >
      <StatusStrip
        items={[
          { label: "상태", value: "검증 완료", tone: "positive" },
          { label: "데이터 기준일", value: definition.dataAsOf },
        ]}
      />

      <section className="template-section">
        <SectionHeading eyebrow="Primary result" title="핵심 결과" />
        <div className="template-metrics">
          <MetricCard
            label={definition.resultLabel}
            meta={definition.resultMeta}
            tone="primary"
            value={definition.resultValue}
          />
        </div>
      </section>

      <section className="template-section">
        <SectionHeading eyebrow="Chart" title={definition.chartTitle} />
        <AccessibleLineChart
          initialSeriesId={definition.series[0]?.id}
          meta={definition.chartMeta}
          points={definition.points}
          series={definition.series}
          title={definition.chartTitle}
        />
      </section>

      <section className="template-section">
        <SectionHeading eyebrow="Controls" title="화면·분석 설정" />
        <ControlPanel
          appliedValues={{ example_analysis_input: 1 }}
          displayValues={displayValues}
          draftValues={draftValues}
          manifest={definition.controls}
          onAnalysisChange={(id, value) =>
            setDraftValues((current) => ({ ...current, [id]: value }))
          }
          onDisplayChange={(id, value) =>
            setDisplayValues((current) => ({ ...current, [id]: value }))
          }
          onSubmit={() => undefined}
        />
      </section>
    </DashboardShell>
  );
}
