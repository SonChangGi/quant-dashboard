import {
  useEffect,
  useMemo,
  useState,
  type KeyboardEvent,
  type PointerEvent,
} from "react";
import { ChartFrame, ChartReadout } from "./chart-frame";
import {
  SeriesPicker,
  useSeriesSelection,
  type SeriesOption,
} from "./series-selection";

export interface LineChartPoint {
  x: string;
  values: Readonly<Record<string, number | null>>;
}

export interface LineSeries extends SeriesOption {
  unit?: string;
  format?: (value: number) => string;
}

export interface AccessibleLineChartProps {
  title: string;
  meta?: string;
  points: readonly LineChartPoint[];
  series: readonly LineSeries[];
  initialSeriesId?: string;
  valueLabel?: string;
}

const WIDTH = 960;
const HEIGHT = 360;
const MARGIN = { top: 22, right: 24, bottom: 42, left: 62 } as const;

function defaultFormat(value: number): string {
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 2,
  }).format(value);
}

function getBounds(
  points: readonly LineChartPoint[],
  series: readonly LineSeries[],
): [number, number] {
  const values = points.flatMap((point) =>
    series.flatMap((item) => {
      const value = point.values[item.id];
      return typeof value === "number" && Number.isFinite(value) ? [value] : [];
    }),
  );
  if (values.length === 0) {
    return [0, 1];
  }
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  if (minimum === maximum) {
    const padding = Math.abs(minimum) * 0.05 || 1;
    return [minimum - padding, maximum + padding];
  }
  const padding = (maximum - minimum) * 0.08;
  return [minimum - padding, maximum + padding];
}

function buildPath(
  points: readonly LineChartPoint[],
  seriesId: string,
  xScale: (index: number) => number,
  yScale: (value: number) => number,
): string {
  let path = "";
  let drawing = false;
  points.forEach((point, index) => {
    const value = point.values[seriesId];
    if (typeof value !== "number" || !Number.isFinite(value)) {
      drawing = false;
      return;
    }
    path += `${drawing ? "L" : "M"}${xScale(index).toFixed(2)},${yScale(value).toFixed(2)} `;
    drawing = true;
  });
  return path.trim();
}

export function AccessibleLineChart({
  ...props
}: AccessibleLineChartProps) {
  const units = new Set(
    props.series
      .map((item) => item.unit)
      .filter((unit): unit is string => Boolean(unit)),
  );
  if (units.size > 1) {
    throw new Error(
      "Series with different units must be rendered in separate chart facets.",
    );
  }
  if (props.points.length === 0 || props.series.length === 0) {
    return (
      <ChartFrame meta={props.meta} title={props.title}>
        <div className="qr-chart-empty">관측 없음</div>
      </ChartFrame>
    );
  }
  return <NonEmptyAccessibleLineChart {...props} />;
}

function NonEmptyAccessibleLineChart({
  title,
  meta,
  points,
  series,
  initialSeriesId,
  valueLabel = "값",
}: AccessibleLineChartProps) {
  const selection = useSeriesSelection(series, initialSeriesId);
  const [selectedIndex, setSelectedIndex] = useState(points.length - 1);
  useEffect(() => {
    setSelectedIndex((current) => Math.min(current, points.length - 1));
  }, [points.length]);

  const [minimum, maximum] = useMemo(
    () => getBounds(points, series),
    [points, series],
  );
  const plotWidth = WIDTH - MARGIN.left - MARGIN.right;
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
  const xScale = (index: number) =>
    MARGIN.left +
    (points.length === 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth);
  const yScale = (value: number) =>
    MARGIN.top + ((maximum - value) / (maximum - minimum)) * plotHeight;
  const selectedPoint = points[selectedIndex] ?? points[points.length - 1]!;
  const selectedSeries =
    series.find((item) => item.id === selection.activeId) ?? series[0]!;
  const selectedValue = selectedPoint.values[selectedSeries.id];

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    let next = selectedIndex;
    if (event.key === "ArrowLeft") next -= 1;
    else if (event.key === "ArrowRight") next += 1;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = points.length - 1;
    else return;
    event.preventDefault();
    setSelectedIndex(Math.max(0, Math.min(points.length - 1, next)));
  }

  function onPointerMove(event: PointerEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const viewX = ((event.clientX - rect.left) / rect.width) * WIDTH;
    const ratio = (viewX - MARGIN.left) / plotWidth;
    setSelectedIndex(
      Math.max(0, Math.min(points.length - 1, Math.round(ratio * (points.length - 1)))),
    );
  }

  const gridTicks = Array.from({ length: 5 }, (_, index) => {
    const ratio = index / 4;
    return {
      value: maximum - ratio * (maximum - minimum),
      y: MARGIN.top + ratio * plotHeight,
    };
  });

  const readout = (
    <ChartReadout
      eyebrow="선택 관측"
      items={[
        {
          label: selectedSeries.label,
          tone: "focal",
          value:
            typeof selectedValue === "number"
              ? `${(selectedSeries.format ?? defaultFormat)(selectedValue)}${selectedSeries.unit ?? ""}`
              : "관측 없음",
        },
      ]}
      title={selectedPoint.x}
    />
  );

  const table = (
    <table className="qr-chart-table">
      <thead>
        <tr>
          <th scope="col">관측</th>
          {series.map((item) => (
            <th key={item.id} scope="col">
              {item.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {points.map((point) => (
          <tr key={point.x}>
            <th scope="row">{point.x}</th>
            {series.map((item) => {
              const value = point.values[item.id];
              return (
                <td key={item.id}>
                  {typeof value === "number"
                    ? `${(item.format ?? defaultFormat)(value)}${item.unit ?? ""}`
                    : "—"}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );

  return (
    <ChartFrame
      controls={<SeriesPicker selection={selection} series={series} />}
      meta={meta}
      readout={readout}
      table={table}
      title={title}
    >
      <div
        aria-keyshortcuts="ArrowLeft ArrowRight Home End"
        aria-label={`${title}. 좌우 방향키로 관측을 이동합니다.`}
        className="qr-line-chart"
        onKeyDown={onKeyDown}
        role="group"
        tabIndex={0}
      >
        <svg
          aria-hidden="true"
          onPointerMove={onPointerMove}
          preserveAspectRatio="xMidYMid meet"
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        >
          {gridTicks.map((tick) => (
            <g key={tick.y}>
              <line
                className="qr-line-chart__grid"
                x1={MARGIN.left}
                x2={WIDTH - MARGIN.right}
                y1={tick.y}
                y2={tick.y}
              />
              <text
                className="qr-line-chart__axis-label"
                textAnchor="end"
                x={MARGIN.left - 10}
                y={tick.y + 4}
              >
                {defaultFormat(tick.value)}
              </text>
            </g>
          ))}
          <line
            className="qr-line-chart__axis"
            x1={MARGIN.left}
            x2={WIDTH - MARGIN.right}
            y1={HEIGHT - MARGIN.bottom}
            y2={HEIGHT - MARGIN.bottom}
          />
          {series.map((item) => {
            const active = item.id === selection.activeId;
            return (
              <path
                className={
                  active
                    ? "qr-line-chart__series qr-line-chart__series--active"
                    : "qr-line-chart__series qr-line-chart__series--context"
                }
                d={buildPath(points, item.id, xScale, yScale)}
                key={item.id}
                stroke={item.color}
              />
            );
          })}
          <line
            className="qr-line-chart__guide"
            x1={xScale(selectedIndex)}
            x2={xScale(selectedIndex)}
            y1={MARGIN.top}
            y2={HEIGHT - MARGIN.bottom}
          />
          {series.map((item) => {
            const value = selectedPoint.values[item.id];
            if (typeof value !== "number") return null;
            const active = item.id === selection.activeId;
            return (
              <g key={item.id}>
                {active ? (
                  <circle
                    className="qr-line-chart__halo"
                    cx={xScale(selectedIndex)}
                    cy={yScale(value)}
                    r="8"
                  />
                ) : null}
                <circle
                  className={
                    active
                      ? "qr-line-chart__point qr-line-chart__point--active"
                      : "qr-line-chart__point"
                  }
                  cx={xScale(selectedIndex)}
                  cy={yScale(value)}
                  fill={item.color}
                  r={active ? 4.5 : 2.5}
                />
              </g>
            );
          })}
          <text
            className="qr-line-chart__x-label"
            textAnchor="middle"
            x={xScale(selectedIndex)}
            y={HEIGHT - 13}
          >
            {selectedPoint.x}
          </text>
          <text
            className="qr-line-chart__axis-title"
            textAnchor="start"
            x={MARGIN.left}
            y={14}
          >
            {valueLabel}
          </text>
        </svg>
      </div>
    </ChartFrame>
  );
}
