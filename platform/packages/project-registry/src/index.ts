export const canonicalProjectRegistry = [
  {
    id: "hub",
    label: "Hub",
    url: "https://sonchanggi.github.io/quant-dashboard/",
  },
  {
    id: "fear-greed",
    label: "Fear & Greed",
    url: "https://sonchanggi.github.io/fearNgreed/",
  },
  {
    id: "momentum",
    label: "Momentum",
    url: "https://sonchanggi.github.io/momentum-factor-lab/",
  },
  {
    id: "dram",
    label: "DRAM",
    url: "https://sonchanggi.github.io/dram-price/",
  },
  {
    id: "best-factor",
    label: "Best Factor",
    url: "https://sonchanggi.github.io/best-factor/",
  },
  {
    id: "etf",
    label: "ETF",
    url: "https://sonchanggi.github.io/etf-tracking/",
  },
  {
    id: "sox",
    label: "SOX",
    url: "https://sonchanggi.github.io/sox/",
  },
] as const;

export type ProjectId = (typeof canonicalProjectRegistry)[number]["id"];
export type ProjectRegistryEntry = (typeof canonicalProjectRegistry)[number];

/**
 * Existing public summary ids are protected data contracts. Keep translation
 * here instead of rewriting generated JSON to match navigation/API ids.
 */
export const publicSummaryProjectIds = {
  "fear-greed": "fearngreed",
  momentum: "momentum",
  dram: "dram",
  "best-factor": "best",
  etf: "etf",
  sox: "sox",
} as const satisfies Partial<Record<ProjectId, string>>;

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
  if (!canonicalProjectRegistry.some((project) => project.id === currentId)) {
    throw new RangeError(`Unknown project id: ${currentId}`);
  }
  return canonicalProjectRegistry.map((project) => ({
    ...project,
    current: project.id === currentId,
  }));
}

export function getProject(currentId: ProjectId): ProjectRegistryEntry {
  const project = canonicalProjectRegistry.find(
    (candidate) => candidate.id === currentId,
  );
  if (!project) {
    throw new RangeError(`Unknown project id: ${currentId}`);
  }
  return project;
}
