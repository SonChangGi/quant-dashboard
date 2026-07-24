// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { AccessibleLineChart } from "@quant-research/charts";

const points = [
  { x: "2026-07-22", values: { alpha: 1, beta: 2, gamma: 3 } },
  { x: "2026-07-23", values: { alpha: 2, beta: 3, gamma: 4 } },
];

afterEach(cleanup);

describe("AccessibleLineChart", () => {
  it("can move from an empty state to data without changing hook order", () => {
    const view = render(
      <AccessibleLineChart points={[]} series={[]} title="테스트 차트" />,
    );
    expect(screen.getByText("관측 없음")).toBeTruthy();
    expect(() =>
      view.rerender(
        <AccessibleLineChart
          points={points}
          series={[{ id: "alpha", label: "Alpha", color: "#3182f6" }]}
          title="테스트 차트"
        />,
      ),
    ).not.toThrow();
    const chart = screen.getByRole("group", { name: /좌우 방향키/ });
    expect(chart.getAttribute("aria-keyshortcuts")).toBe(
      "ArrowLeft ArrowRight Home End",
    );
    fireEvent.keyDown(chart, { key: "ArrowLeft" });
    expect(
      view.container.querySelector(".qr-chart-readout__title")?.textContent,
    ).toBe("2026-07-22");
  });

  it("recovers when the pinned series disappears", async () => {
    const view = render(
      <AccessibleLineChart
        initialSeriesId="alpha"
        points={points}
        series={[
          { id: "alpha", label: "Alpha", color: "#3182f6" },
          { id: "beta", label: "Beta", color: "#8b95a1" },
        ]}
        title="동적 계열"
      />,
    );
    expect(screen.getByRole("button", { name: "Alpha" }).getAttribute("aria-pressed")).toBe(
      "true",
    );
    view.rerender(
      <AccessibleLineChart
        points={points}
        series={[{ id: "gamma", label: "Gamma", color: "#1687a7" }]}
        title="동적 계열"
      />,
    );
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Gamma" }).getAttribute("aria-pressed"),
      ).toBe("true");
    });
  });

  it("rejects mixed units on one y-axis", () => {
    expect(() =>
      render(
        <AccessibleLineChart
          points={points}
          series={[
            { id: "alpha", label: "Alpha", color: "#3182f6", unit: "%" },
            { id: "beta", label: "Beta", color: "#8b95a1", unit: "원" },
          ]}
          title="혼합 단위"
        />,
      ),
    ).toThrow(/different units/);
  });
});
