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
    "Fear & Greed", "Factor", "DRAM", "ETF", "SOX", "Regime", "News", "SPO", "알파 하우스",
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
  expect(getByRole("link", { name: "Quant Research Hub" }).getAttribute("aria-current")).toBeNull();
});

it("uses the shared validated runtime while React owns its links", async () => {
  const menu = {
    schemaVersion: "quant-navigation/v1" as const,
    brand: {id: "hub", label: "Quant Research Hub", url: "https://sonchanggi.github.io/quant-dashboard/"},
    projects: [{id:"factor",label:"Factor",url:"https://sonchanggi.github.io/factor/"},{id:"regime",label:"Regime",url:"https://sonchanggi.github.io/regime/"}],
  };
  window.QuantNavigationV1 = {getMenu: () => menu, getLinks: () => []};
  const {getByRole} = render(<ThemeProvider><SharedNavigation currentProject="momentum" /></ThemeProvider>);
  const navigation = getByRole("navigation", {name:"프로젝트"});
  expect(within(navigation).getAllByRole("link").map(link=>link.textContent)).toEqual(["Factor","Regime"]);
  expect(within(navigation).getByRole("link",{name:"Factor"}).getAttribute("aria-current")).toBe("page");
  expect(navigation.closest('[data-quant-navigation-managed="react"]')).not.toBeNull();
  delete window.QuantNavigationV1;
});
