import type { PropsWithChildren, ReactNode } from "react";
import { classNames } from "@quant-research/ui";

export interface ChartFrameProps extends PropsWithChildren {
  title: string;
  meta?: ReactNode;
  readout?: ReactNode;
  controls?: ReactNode;
  table?: ReactNode;
  className?: string;
}

export function ChartFrame({
  title,
  meta,
  readout,
  controls,
  table,
  className,
  children,
}: ChartFrameProps) {
  return (
    <section className={classNames("qr-chart-frame", className)}>
      <div className="qr-chart-frame__heading">
        <h3>{title}</h3>
        {meta ? <span>{meta}</span> : null}
      </div>
      {readout ? <div className="qr-chart-frame__readout">{readout}</div> : null}
      {controls ? <div className="qr-chart-frame__controls">{controls}</div> : null}
      <div className="qr-chart-frame__plot">{children}</div>
      {table ? (
        <details className="qr-chart-frame__data">
          <summary>정확값 표</summary>
          <div className="qr-chart-frame__table-scroll">{table}</div>
        </details>
      ) : null}
    </section>
  );
}

export interface ChartReadoutItem {
  label: string;
  value: ReactNode;
  tone?: "default" | "focal" | "muted";
}

export function ChartReadout({
  eyebrow,
  title,
  items,
}: {
  eyebrow?: string;
  title: ReactNode;
  items: readonly ChartReadoutItem[];
}) {
  return (
    <div className="qr-chart-readout">
      <div>
        {eyebrow ? <span className="qr-chart-readout__eyebrow">{eyebrow}</span> : null}
        <strong className="qr-chart-readout__title">{title}</strong>
      </div>
      <dl>
        {items.map((item) => (
          <div
            className={classNames(
              "qr-chart-readout__item",
              `qr-chart-readout__item--${item.tone ?? "default"}`,
            )}
            key={item.label}
          >
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
