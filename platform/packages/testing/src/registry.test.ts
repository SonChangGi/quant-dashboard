import { describe, expect, expectTypeOf, it } from "vitest";
import {
  canonicalProjectRegistry,
  getCanonicalNavigation,
  getProject,
  publicSummaryProjectIds,
  type CompletedDashboardId,
  type ProjectId,
} from "@quant-research/project-registry";

describe("canonical project registry", () => {
  it("keeps the shared public labels and URLs in the approved order", () => {
    expect(canonicalProjectRegistry.map(row => row.id)).toEqual(["hub","factor","dram","etf","sox","fear-greed","regime","news","investment-journal","observatory"]);
    expect(getProject("investment-journal").url).toBe("https://invest.changgi-son.chatgpt.site/");
    expect(getProject("factor").label).toBe("Factor");
    expect(getProject("factor").url).toBe("https://sonchanggi.github.io/factor/");
    expect(canonicalProjectRegistry.some(row => String(row.id) === "best-factor")).toBe(false);
  });

  it("marks exactly one project as current", () => {
    const navigation = getCanonicalNavigation("factor");
    expect(navigation.filter((item) => item.current)).toEqual([
      expect.objectContaining({ id: "factor" }),
    ]);
  });

  it("keeps platform ids separate from protected public summary ids", () => {
    expect(publicSummaryProjectIds).toEqual({
      "fear-greed": "fearngreed",
      momentum: "momentum",
      dram: "dram",
      etf: "etf",
      sox: "sox",
    });
  });

  it("supports Regime navigation without inventing a public summary contract", () => {
    expect(getProject("regime")).toEqual({
      id: "regime",
      label: "Regime",
      url: "https://sonchanggi.github.io/regime/",
    });
    expect(getCanonicalNavigation("regime").filter((item) => item.current)).toEqual([
      expect.objectContaining({ id: "regime" }),
    ]);
    expect(publicSummaryProjectIds).not.toHaveProperty("regime");
    expectTypeOf<Extract<ProjectId, "regime">>().toEqualTypeOf<"regime">();
    expectTypeOf<Extract<ProjectId, "best-factor">>().toEqualTypeOf<never>();
    expectTypeOf<Extract<CompletedDashboardId, "best-factor">>().toEqualTypeOf<never>();
    expectTypeOf<Extract<CompletedDashboardId, "regime">>().toEqualTypeOf<never>();
  });
});
