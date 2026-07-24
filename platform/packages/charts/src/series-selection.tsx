import { useEffect, useMemo, useState } from "react";
import { Button, classNames } from "@quant-research/ui";

export interface SeriesOption {
  id: string;
  label: string;
  color: string;
}

export interface SeriesSelection {
  pinnedId: string;
  previewId: string | null;
  activeId: string;
  pin: (id: string) => void;
  preview: (id: string | null) => void;
}

export function useSeriesSelection(
  series: readonly SeriesOption[],
  initialId?: string,
): SeriesSelection {
  const fallback =
    initialId && series.some((item) => item.id === initialId)
      ? initialId
      : series[0]?.id;
  if (!fallback) {
    throw new Error("Series selection requires at least one series.");
  }
  const [pinnedId, setPinnedId] = useState(fallback);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const validIds = useMemo(() => new Set(series.map((item) => item.id)), [series]);
  const effectivePinnedId = validIds.has(pinnedId) ? pinnedId : fallback;
  const effectivePreviewId =
    previewId !== null && validIds.has(previewId) ? previewId : null;

  useEffect(() => {
    if (!validIds.has(pinnedId)) {
      setPinnedId(fallback);
    }
    if (previewId !== null && !validIds.has(previewId)) {
      setPreviewId(null);
    }
  }, [fallback, pinnedId, previewId, validIds]);

  return {
    pinnedId: effectivePinnedId,
    previewId: effectivePreviewId,
    activeId: effectivePreviewId ?? effectivePinnedId,
    pin(id) {
      if (!validIds.has(id)) {
        throw new RangeError(`Unknown series: ${id}`);
      }
      setPinnedId(id);
      setPreviewId(null);
    },
    preview(id) {
      if (id !== null && !validIds.has(id)) {
        throw new RangeError(`Unknown series: ${id}`);
      }
      setPreviewId(id);
    },
  };
}

export function SeriesPicker({
  series,
  selection,
}: {
  series: readonly SeriesOption[];
  selection: SeriesSelection;
}) {
  return (
    <div aria-label="차트 계열" className="qr-series-picker" role="toolbar">
      {series.map((item) => {
        const active = selection.activeId === item.id;
        const pinned = selection.pinnedId === item.id;
        return (
          <Button
            aria-pressed={pinned}
            className={classNames(
              "qr-series-picker__button",
              active && "qr-series-picker__button--active",
            )}
            key={item.id}
            onBlur={() => selection.preview(null)}
            onClick={() => selection.pin(item.id)}
            onFocus={() => selection.preview(item.id)}
            onMouseEnter={() => selection.preview(item.id)}
            onMouseLeave={() => selection.preview(null)}
            size="compact"
            style={{ "--qr-series-color": item.color } as React.CSSProperties}
            variant="ghost"
          >
            <span aria-hidden="true" className="qr-series-picker__swatch" />
            {item.label}
          </Button>
        );
      })}
    </div>
  );
}
