// @vitest-environment jsdom
import { cleanup, render, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { SharedNavigation } from "@quant-research/shell";
import { ThemeProvider } from "@quant-research/ui";

afterEach(cleanup);

it("renders Regime in shared navigation and moves the active page to it", () => {
  const { getByRole, rerender } = render(
    <ThemeProvider>
      <SharedNavigation currentProject="hub" />
    </ThemeProvider>,
  );
  const navigation = getByRole("navigation", { name: "프로젝트" });
  const links = within(navigation).getAllByRole("link");
  expect(links.map((link) => link.textContent)).toEqual([
    "Hub", "Fear & Greed", "Momentum", "DRAM", "Best Factor", "ETF", "SOX", "Regime",
  ]);
  const regime = within(navigation).getByRole("link", { name: "Regime" });
  expect(regime.getAttribute("href")).toBe("https://sonchanggi.github.io/regime/");
  expect(regime.getAttribute("aria-current")).toBeNull();

  rerender(
    <ThemeProvider>
      <SharedNavigation currentProject="regime" />
    </ThemeProvider>,
  );
  expect(within(navigation).getAllByRole("link", { current: "page" })).toEqual([regime]);
  expect(within(navigation).getByRole("link", { name: "Hub" }).getAttribute("aria-current")).toBeNull();
});
