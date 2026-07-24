import { describe, expect, it } from "vitest";
import {
  canonicalProjectRegistry,
  getCanonicalNavigation,
  publicSummaryProjectIds,
} from "@quant-research/project-registry";

describe("canonical project registry", () => {
  it("keeps all 11 labels and URLs in the approved order", () => {
    expect(canonicalProjectRegistry).toEqual([
      { id: "hub", label: "Hub", url: "https://sonchanggi.github.io/quant-dashboard/" },
      { id: "fear-greed", label: "Fear & Greed", url: "https://sonchanggi.github.io/fearNgreed/" },
      { id: "momentum", label: "Momentum", url: "https://sonchanggi.github.io/momentum-factor-lab/" },
      { id: "dram", label: "DRAM", url: "https://sonchanggi.github.io/dram-price/" },
      { id: "best-factor", label: "Best Factor", url: "https://sonchanggi.github.io/best-factor/" },
      { id: "etf", label: "ETF", url: "https://sonchanggi.github.io/etf-tracking/" },
      { id: "sox", label: "SOX", url: "https://sonchanggi.github.io/sox/" },
      { id: "risk-score", label: "Risk Score", url: "https://sonchanggi.github.io/quant-dashboard/risk-score/" },
      { id: "port", label: "Port", url: "https://sonchanggi.github.io/port/" },
      { id: "valuation", label: "Valuation", url: "https://sonchanggi.github.io/valuation/" },
      { id: "kelly", label: "Kelly", url: "https://sonchanggi.github.io/kelly/" },
    ]);
  });

  it("marks exactly one project as current", () => {
    const navigation = getCanonicalNavigation("best-factor");
    expect(navigation.filter((item) => item.current)).toEqual([
      expect.objectContaining({ id: "best-factor" }),
    ]);
  });

  it("keeps platform ids separate from protected public summary ids", () => {
    expect(publicSummaryProjectIds).toEqual({
      "fear-greed": "fearngreed",
      momentum: "momentum",
      dram: "dram",
      "best-factor": "best",
      etf: "etf",
      sox: "sox",
    });
  });
});
