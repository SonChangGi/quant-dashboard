// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ControlPanel } from "@quant-research/ui";
import { testManifest } from "./fixtures";

afterEach(cleanup);

describe("ControlPanel", () => {
  it("keeps analysis inputs collapsed and summarizes applied values", () => {
    const { container } = render(
      <ControlPanel
        appliedValues={{ lookback_days: 90 }}
        displayValues={{ visible_rows: 20 }}
        draftValues={{ lookback_days: 120 }}
        manifest={testManifest}
        onAnalysisChange={vi.fn()}
        onDisplayChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    const details = container.querySelector(".qr-analysis-controls");
    expect(details?.hasAttribute("open")).toBe(false);
    expect(screen.getByText(/현재 적용 · 분석 기간 90일/)).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "분석 API 연결 필요" }).hasAttribute("disabled"),
    ).toBe(true);
  });
});
