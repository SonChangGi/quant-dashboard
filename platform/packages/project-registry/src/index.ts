import { sharedNavigationFallback } from "./navigation.generated";

export { sharedNavigationFallback };
export const canonicalProjectRegistry = [
  { ...sharedNavigationFallback.brand, label: "Hub" },
  ...sharedNavigationFallback.projects,
] as const;

export type NavigationProjectId = (typeof canonicalProjectRegistry)[number]["id"];
/** Legacy calculation/API ids remain distinct from visible navigation. */
export type ProjectId = NavigationProjectId | "momentum" | "best-factor";
export type ProjectRegistryEntry = (typeof canonicalProjectRegistry)[number];
export function normalizeNavigationId(id: string): string { return id === "momentum" ? "factor" : id; }

/**
 * Existing public summary ids are protected data contracts. Keep translation
 * here instead of rewriting generated JSON to match navigation/API ids.
 * Regime uses its own weekly-regime-result-v5 contract, not a summary id.
 */
export const publicSummaryProjectIds = {
  "fear-greed": "fearngreed",
  momentum: "momentum",
  dram: "dram",
  "best-factor": "best",
  etf: "etf",
  sox: "sox",
} as const satisfies Partial<Record<ProjectId, string>>;

/** Summary-contract dashboards only; navigation registration is broader. */
export type CompletedDashboardId = keyof typeof publicSummaryProjectIds;

export function getPublicSummaryProjectId(
  projectId: CompletedDashboardId,
): string {
  return publicSummaryProjectIds[projectId];
}

export type NavigationEntry = ProjectRegistryEntry & {
  current: boolean;
};

export function getCanonicalNavigation(currentId: ProjectId): NavigationEntry[] {
  if (!canonicalProjectRegistry.some((project) => project.id === normalizeNavigationId(currentId))) {
    throw new RangeError(`Unknown project id: ${currentId}`);
  }
  return canonicalProjectRegistry.map((project) => ({
    ...project,
    current: project.id === normalizeNavigationId(currentId),
  }));
}

export function getProject(currentId: ProjectId): ProjectRegistryEntry {
  const project = canonicalProjectRegistry.find(
    (candidate) => candidate.id === normalizeNavigationId(currentId),
  );
  if (!project) {
    throw new RangeError(`Unknown project id: ${currentId}`);
  }
  return project;
}

/** Explicit local integration contract; public summaries retain their own schemas. */
export const integratedMomentumContract = {
  projectId: "momentum",
  inputSchemaVersion: "momentum-integrated/v1",
  resultSchemaVersion: "integrated-factor/v1",
  strategyTypes: ["monthly_selection", "fixed_factor_experiment"],
  retiredProjectId: "best-factor",
  acceptsLegacyBestInputs: false,
} as const;

export function getLocalIntegratedNavigation(origin: string) {
  const base = new URL(origin);
  if (base.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(base.hostname)
      || base.username || base.password || base.search || base.hash || base.pathname !== "/") {
    throw new RangeError("Integrated runtime must be a loopback HTTP origin");
  }
  return canonicalProjectRegistry.map(project => ({
    ...project,
    url: project.id === "factor" ? base.href : project.id === "hub" ? new URL("hub/", base).href : project.url,
  }));
}
