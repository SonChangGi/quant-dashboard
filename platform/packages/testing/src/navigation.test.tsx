// @vitest-environment jsdom
import { cleanup, render, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { SharedNavigation } from "@quant-research/shell";
import { ThemeProvider } from "@quant-research/ui";

afterEach(cleanup);

it("marks Fear & Greed as the active page in shared navigation", () => {
  const { getByRole, rerender } = render(
    <ThemeProvider>
      <SharedNavigation currentProject="hub" />
    </ThemeProvider>,
  );
  const navigation = getByRole("navigation", { name: "프로젝트" });
  const links = within(navigation).getAllByRole("link");
  expect(links.map((link) => link.textContent)).toEqual([
    "Factor", "DRAM", "ETF", "SOX", "Fear & Greed", "News", "투자일지", "알파 하우스",
  ]);
  const fear = within(navigation).getByRole("link", { name: "Fear & Greed" });
  expect(fear.getAttribute("href")).toBe("https://sonchanggi.github.io/fearNgreed/");
  expect(fear.getAttribute("aria-current")).toBeNull();

  rerender(
    <ThemeProvider>
      <SharedNavigation currentProject="fear-greed" />
    </ThemeProvider>,
  );
  expect(within(navigation).getAllByRole("link", { current: "page" })).toEqual([fear]);
  expect(getByRole("link", { name: "Quant Research Hub" }).getAttribute("aria-current")).toBeNull();
});

it("uses the shared validated runtime while React owns its links", async () => {
  const menu = {
    schemaVersion: "quant-navigation/v1" as const,
    brand: {id: "hub", label: "Quant Research Hub", url: "https://sonchanggi.github.io/quant-dashboard/"},
    projects: [{id:"factor",label:"Factor",url:"https://sonchanggi.github.io/factor/"},{id:"fear-greed",label:"Fear & Greed",url:"https://sonchanggi.github.io/fearNgreed/"}],
  };
  window.QuantNavigationV1 = {getMenu: () => menu, getLinks: () => []};
  const {getByRole} = render(<ThemeProvider><SharedNavigation currentProject="momentum" /></ThemeProvider>);
  const navigation = getByRole("navigation", {name:"프로젝트"});
  expect(within(navigation).getAllByRole("link").map(link=>link.textContent)).toEqual(["Factor","Fear & Greed"]);
  expect(within(navigation).getByRole("link",{name:"Factor"}).getAttribute("aria-current")).toBe("page");
  expect(navigation.closest('[data-quant-navigation-managed="react"]')).not.toBeNull();
  delete window.QuantNavigationV1;
});
