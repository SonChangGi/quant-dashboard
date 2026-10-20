import { describe, expect, it } from "vitest";
import { canonicalProjectRegistry, getLocalIntegratedNavigation, integratedMomentumContract } from "../../project-registry/src/index";

describe("explicit local factor integration", () => {
  it("retires Best only locally and preserves other project URLs", () => {
    const local = getLocalIntegratedNavigation("http://127.0.0.1:50073");
    expect(local.map(project => project.id)).not.toContain("best-factor");
    expect(local.find(project => project.id === "momentum")?.url).toBe("http://127.0.0.1:50073/");
    expect(local.find(project => project.id === "news")?.url).toBe(canonicalProjectRegistry.find(project => project.id === "news")?.url);
    expect(canonicalProjectRegistry.some(project => project.id === "best-factor")).toBe(true);
    expect(integratedMomentumContract.acceptsLegacyBestInputs).toBe(false);
    expect(integratedMomentumContract.resultSchemaVersion).toBe("integrated-factor/v1");
  });
  it("rejects public hosts and paths", () => {
    for (const value of ["https://example.com/", "http://localhost:50073/path", "http://user:pw@localhost:50073/"]) {
      expect(() => getLocalIntegratedNavigation(value)).toThrow();
    }
  });
});
