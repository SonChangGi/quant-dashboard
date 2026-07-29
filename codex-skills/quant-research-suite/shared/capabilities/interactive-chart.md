# Capability: interactive chart

Activate when a chart supports hover, tap, focus, selection, zoom, comparison,
or a time-range control.

- Derive rendering and hit-testing from the same domain, scale, plot bounds, and
  data ordering.
- For SVG, convert client coordinates through the current screen CTM rather than
  mixing CSS pixels and viewBox coordinates.
- Keep hover preview distinct from pinned/selected state.
- Provide exact values outside crowded plot regions and avoid overlays covering
  important marks.
- Verify first, middle, and last points; irregular dates; gaps; direct tap;
  resize; scroll/zoom; keyboard traversal; and touch targets.
- A period/input change must bind the displayed chart to the corresponding
  applied result, not merely relabel the axis.

Evidence gate: `chart_interaction`.
