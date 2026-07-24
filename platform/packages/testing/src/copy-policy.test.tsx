// @vitest-environment jsdom
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { PageHeader } from "@quant-research/shell";
import {
  SectionHeading,
  retainedVisibleCopyIntents,
} from "@quant-research/ui";

afterEach(cleanup);

describe("visible supporting copy contract", () => {
  it("renders no hero or section supporting prose by default", () => {
    const { container } = render(
      <>
        <PageHeader title="핵심 결과" />
        <SectionHeading title="상세 결과" />
      </>,
    );

    expect(container.querySelector(".qr-page-header__copy > p")).toBeNull();
    expect(container.querySelector(".qr-section-heading p")).toBeNull();
    expect(container.querySelectorAll("[data-copy-role]")).toHaveLength(0);
  });

  it("requires project-owned id, intent, and reason for retained prose", () => {
    const { container } = render(
      <PageHeader
        supportingCopy={{
          copyId: "example-market-close-status",
          text: "현재 데이터는 장 마감 전 잠정치입니다.",
          intent: "interpretation-guardrail",
          reason:
            "확정 종가로 오해하면 현재 결과의 시간 기준을 잘못 판단하게 됩니다.",
        }}
        title="핵심 결과"
      />,
    );

    const copy = container.querySelector("[data-copy-role='hero-support']");
    expect(copy?.textContent).toBe("현재 데이터는 장 마감 전 잠정치입니다.");
    expect(copy?.getAttribute("data-copy-id")).toBe(
      "example-market-close-status",
    );
    expect(copy?.getAttribute("data-copy-intent")).toBe(
      "interpretation-guardrail",
    );
    expect(copy?.getAttribute("data-copy-reason")).toContain("확정 종가");
  });

  it("keeps the shared intent vocabulary closed", () => {
    expect(retainedVisibleCopyIntents).toEqual([
      "dynamic-result",
      "interpretation-guardrail",
      "nonstandard-action",
      "required-disclosure",
    ]);
  });
});
