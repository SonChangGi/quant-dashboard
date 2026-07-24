import type { ControlManifest } from "@quant-research/contracts";
import type { LineChartPoint, LineSeries } from "@quant-research/charts";
import type { ProjectId } from "@quant-research/project-registry";
import type { RetainedVisibleCopy } from "@quant-research/ui";

export interface DashboardDefinition {
  projectId: ProjectId;
  eyebrow: string;
  title: string;
  supportingCopy?: RetainedVisibleCopy;
  dataAsOf: string;
  resultLabel: string;
  resultValue: string;
  resultMeta: string;
  chartTitle: string;
  chartMeta: string;
  points: readonly LineChartPoint[];
  series: readonly LineSeries[];
  controls: ControlManifest;
}

/**
 * Replace only this view-model with a project's validated result adapter.
 * Do not place collection, analysis, ranking, or strategy calculations here.
 */
export const dashboardDefinition: DashboardDefinition = {
  projectId: "hub",
  eyebrow: "Research dashboard",
  title: "프로젝트 제목",
  dataAsOf: "2026-07-23",
  resultLabel: "대표 결과",
  resultValue: "검증된 값",
  resultMeta: "기준일 2026-07-23",
  chartTitle: "핵심 시계열",
  chartMeta: "단위",
  points: [
    { x: "07.20", values: { result: 98, benchmark: 100 } },
    { x: "07.21", values: { result: 101, benchmark: 101 } },
    { x: "07.22", values: { result: 103, benchmark: 101.5 } },
    { x: "07.23", values: { result: 104, benchmark: 102 } },
  ],
  series: [
    {
      id: "result",
      label: "핵심 계열",
      color: "var(--qr-chart-focal)",
      unit: "pt",
    },
    {
      id: "benchmark",
      label: "비교 계열",
      color: "var(--qr-chart-benchmark)",
      unit: "pt",
    },
  ],
  controls: {
    schemaVersion: 1,
    projectId: "template-dashboard",
    inputSchemaVersion: "template-dashboard/v1",
    inputSchemaHash: "7".repeat(64),
    configHashAlgorithm: "replace-with-worker-algorithm",
    controls: [
      {
        id: "visible_rows",
        label: "표시 행",
        controlKind: "display",
        valueType: "number",
        defaultValue: 20,
        defaultSource: "html-constant",
        unit: "행",
        minimum: 5,
        maximum: 100,
        step: 5,
      },
      {
        id: "example_analysis_input",
        label: "분석 입력 예시",
        controlKind: "analysis",
        valueType: "number",
        defaultValue: 1,
        defaultSource: "current-result",
        minimum: 0,
        maximum: 10,
        step: 1,
        transportKey: "example_analysis_input",
        pythonParameter: "--example-analysis-input",
        resultEvidencePath: "metadata.effectiveInputs.example_analysis_input",
      },
    ],
  },
};
