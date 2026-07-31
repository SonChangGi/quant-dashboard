# Capability: interactive chart

Apply this rail when a chart supports hover, tap, focus, selection, zoom,
comparison, or a time-range control.

- Derive rendering and hit-testing from the same domain, scale, plot bounds, and
  data ordering.
- For SVG, convert client coordinates through the current screen CTM rather than
  mixing CSS pixels and viewBox coordinates.
- When both states exist, keep hover preview distinct from pinned/selected state.
- Provide exact values outside crowded plot regions and avoid overlays covering
  important marks.
- Select representative boundary, data-shape, input-method, and viewport checks
  from interactions the chart actually supports. First, middle, or last points,
  irregular dates, gaps, pointer/touch/focus, resize, scroll/zoom, and keyboard
  traversal are examples, not a universal checklist.
- A period/input change must bind the displayed chart to the corresponding
  applied result, not merely relabel the axis.
