import {
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type PropsWithChildren,
  type ReactNode,
} from "react";
import type {
  ControlDefinition,
  ControlManifest,
  JsonValue,
} from "@quant-research/contracts";
import { classNames } from "./class-names";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "default" | "compact" | "icon";
}

export function Button({
  className,
  variant = "secondary",
  size = "default",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      className={classNames(
        "qr-button",
        `qr-button--${variant}`,
        `qr-button--${size}`,
        className,
      )}
      type={type}
      {...props}
    />
  );
}

export function Card({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={classNames("qr-card", className)} {...props} />;
}

export interface MetricCardProps {
  label: string;
  value: ReactNode;
  meta?: ReactNode;
  tone?: "neutral" | "primary" | "positive" | "warning" | "negative";
}

export function MetricCard({
  label,
  value,
  meta,
  tone = "neutral",
}: MetricCardProps) {
  return (
    <Card className={classNames("qr-metric", `qr-metric--${tone}`)}>
      <span className="qr-metric__label">{label}</span>
      <strong className="qr-metric__value">{value}</strong>
      {meta ? <span className="qr-metric__meta">{meta}</span> : null}
    </Card>
  );
}

export interface StatusItem {
  label: string;
  value: ReactNode;
  tone?: "neutral" | "positive" | "warning" | "negative";
}

export function StatusStrip({ items }: { items: readonly StatusItem[] }) {
  return (
    <dl className="qr-status-strip" aria-label="현재 상태">
      {items.map((item) => (
        <div className="qr-status-strip__item" key={item.label}>
          <dt>{item.label}</dt>
          <dd
            className={classNames(
              "qr-status-strip__value",
              item.tone && `qr-status-strip__value--${item.tone}`,
            )}
          >
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export const retainedVisibleCopyIntents = [
  "dynamic-result",
  "interpretation-guardrail",
  "nonstandard-action",
  "required-disclosure",
] as const;

export type RetainedVisibleCopyIntent =
  (typeof retainedVisibleCopyIntents)[number];

/**
 * Visible supporting prose is opt-in. Project code owns the copy id, exact
 * wording, and concrete reason; shared packages never keep project copy.
 */
export interface RetainedVisibleCopy {
  copyId: string;
  text: string;
  intent: RetainedVisibleCopyIntent;
  reason: string;
}

export interface SupportingCopyProps {
  copy: RetainedVisibleCopy;
  role: "hero-support" | "section-support" | "chart-instructions";
}

export function SupportingCopy({ copy, role }: SupportingCopyProps) {
  return (
    <p
      data-copy-id={copy.copyId}
      data-copy-intent={copy.intent}
      data-copy-reason={copy.reason}
      data-copy-role={role}
    >
      {copy.text}
    </p>
  );
}

export interface DisclosureProps extends PropsWithChildren {
  summary: ReactNode;
  defaultOpen?: boolean;
  className?: string;
}

export function Disclosure({
  summary,
  defaultOpen = false,
  className,
  children,
}: DisclosureProps) {
  return (
    <details
      className={classNames("qr-disclosure", className)}
      open={defaultOpen || undefined}
    >
      <summary>{summary}</summary>
      <div className="qr-disclosure__body">{children}</div>
    </details>
  );
}

interface ControlFieldProps {
  control: ControlDefinition;
  value: JsonValue;
  disabled?: boolean;
  onChange: (value: JsonValue) => void;
}

function ControlField({
  control,
  value,
  disabled,
  onChange,
}: ControlFieldProps) {
  const inputId = `qr-control-${control.id}`;
  const common = {
    id: inputId,
    disabled,
    name: control.id,
  };

  let field: ReactNode;
  if (control.options && control.valueType === "string") {
    field = (
      <select
        {...common}
        value={typeof value === "string" ? value : ""}
        onChange={(event) => onChange(event.currentTarget.value)}
      >
        {control.options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  } else if (control.valueType === "boolean") {
    field = (
      <input
        {...common}
        checked={value === true}
        className="qr-control__checkbox"
        onChange={(event) => onChange(event.currentTarget.checked)}
        type="checkbox"
      />
    );
  } else if (control.valueType === "number") {
    field = (
      <input
        {...common}
        max={control.maximum}
        min={control.minimum}
        onChange={(event) => onChange(event.currentTarget.valueAsNumber)}
        step={control.step}
        type="number"
        value={typeof value === "number" ? value : ""}
      />
    );
  } else if (control.valueType === "string-array") {
    field = (
      <input
        {...common}
        onChange={(event) =>
          onChange(
            event.currentTarget.value
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
          )
        }
        type="text"
        value={Array.isArray(value) ? value.join(", ") : ""}
      />
    );
  } else {
    field = (
      <input
        {...common}
        onChange={(event) => onChange(event.currentTarget.value)}
        type="text"
        value={typeof value === "string" ? value : ""}
      />
    );
  }

  return (
    <div className="qr-control">
      <label htmlFor={inputId}>
        {control.label}
        {control.unit ? <span className="qr-control__unit">{control.unit}</span> : null}
      </label>
      {field}
    </div>
  );
}

export interface ControlPanelProps {
  manifest: ControlManifest;
  draftValues: Readonly<Record<string, JsonValue>>;
  appliedValues?: Readonly<Record<string, JsonValue>>;
  displayValues: Readonly<Record<string, JsonValue>>;
  selectorValues?: Readonly<Record<string, JsonValue>>;
  busy?: boolean;
  canSubmit?: boolean;
  submitLabel?: string;
  phaseLabel?: string;
  onAnalysisChange: (controlId: string, value: JsonValue) => void;
  onDisplayChange: (controlId: string, value: JsonValue) => void;
  onResultSelectorChange?: (controlId: string, value: JsonValue) => void;
  onSubmit: () => void;
}

export function ControlPanel({
  manifest,
  draftValues,
  appliedValues = {},
  displayValues,
  selectorValues = {},
  busy,
  canSubmit = false,
  submitLabel,
  phaseLabel,
  onAnalysisChange,
  onDisplayChange,
  onResultSelectorChange,
  onSubmit,
}: ControlPanelProps) {
  const displayControls = manifest.controls.filter(
    (control) => control.controlKind === "display",
  );
  const selectorControls = manifest.controls.filter(
    (control) => control.controlKind === "result_selector",
  );
  const analysisControls = manifest.controls.filter(
    (control) => control.controlKind === "analysis",
  );
  const appliedSummary = analysisControls
    .map((control) => {
      const value = appliedValues[control.id];
      if (value === undefined) return null;
      const formatted = Array.isArray(value) ? value.join(", ") : String(value);
      return `${control.label} ${formatted}${control.unit ?? ""}`;
    })
    .filter((value): value is string => value !== null)
    .join(" · ");

  return (
    <div className="qr-control-panel">
      {displayControls.length > 0 ? (
        <section aria-labelledby="qr-display-controls-title">
          <div className="qr-control-panel__heading">
            <div>
              <span className="qr-eyebrow">Display</span>
              <h3 id="qr-display-controls-title">화면 표시</h3>
            </div>
          </div>
          <div className="qr-control-grid">
            {displayControls.map((control) => (
              <ControlField
                control={control}
                key={control.id}
                onChange={(value) => onDisplayChange(control.id, value)}
                value={displayValues[control.id] ?? control.defaultValue}
              />
            ))}
          </div>
        </section>
      ) : null}

      {selectorControls.length > 0 ? (
        <section aria-labelledby="qr-result-selectors-title">
          <div className="qr-control-panel__heading">
            <div>
              <span className="qr-eyebrow">Saved results</span>
              <h3 id="qr-result-selectors-title">저장 결과 선택</h3>
            </div>
          </div>
          <div className="qr-control-grid">
            {selectorControls.map((control) => (
              <ControlField
                control={control}
                key={control.id}
                onChange={(value) =>
                  onResultSelectorChange?.(control.id, value)
                }
                value={selectorValues[control.id] ?? control.defaultValue}
              />
            ))}
          </div>
        </section>
      ) : null}

      {analysisControls.length > 0 ? (
        <Disclosure
          className="qr-analysis-controls"
          summary={
            <span className="qr-control-panel__summary">
              <span>
                <span className="qr-eyebrow">Analysis inputs</span>
                <strong>분석 입력값</strong>
                <small className="qr-control-panel__applied">
                  현재 적용 · {appliedSummary || "결과 없음"}
                </small>
              </span>
              <span className="qr-control-panel__count">
                {analysisControls.length}개
              </span>
            </span>
          }
        >
          <div className="qr-control-grid">
            {analysisControls.map((control) => (
              <ControlField
                control={control}
                disabled={busy}
                key={control.id}
                onChange={(value) => onAnalysisChange(control.id, value)}
                value={draftValues[control.id] ?? control.defaultValue}
              />
            ))}
          </div>
          <div className="qr-control-panel__actions">
            {phaseLabel ? (
              <span aria-live="polite" className="qr-control-panel__phase">
                {phaseLabel}
              </span>
            ) : (
              <span />
            )}
            <Button
              disabled={busy || !canSubmit}
              onClick={onSubmit}
              variant="primary"
            >
              {busy
                ? "분석 실행 중"
                : submitLabel ?? (canSubmit ? "새 분석 실행" : "분석 API 연결 필요")}
            </Button>
          </div>
        </Disclosure>
      ) : null}
    </div>
  );
}

export interface SectionHeadingProps {
  eyebrow?: string;
  title: string;
  supportingCopy?: RetainedVisibleCopy;
  action?: ReactNode;
}

export function SectionHeading({
  eyebrow,
  title,
  supportingCopy,
  action,
}: SectionHeadingProps) {
  return (
    <div className="qr-section-heading">
      <div>
        {eyebrow ? <span className="qr-eyebrow">{eyebrow}</span> : null}
        <h2>{title}</h2>
        {supportingCopy ? (
          <SupportingCopy copy={supportingCopy} role="section-support" />
        ) : null}
      </div>
      {action ? <div className="qr-section-heading__action">{action}</div> : null}
    </div>
  );
}
