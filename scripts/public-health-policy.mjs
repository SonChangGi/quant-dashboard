export const TRANSPORT_HARD_FAILURE_PROJECT_THRESHOLD = 2;

const OPERATIONAL_WARNING_STATES = new Set([
  'degraded',
  'stale',
  'demo',
  'unavailable',
  'ruin',
  'partial',
  'warning',
  'blocked',
  'error',
]);

export function operationalFindingsFor(projectId, summary = {}) {
  const findings = [];
  const state = firstString(summary?.meta?.statusState, summary?.state);
  const assessment = summary.healthAssessment;
  if (state === 'degraded' && !summary.scatterError && !summary.priceError && !summary.trendError
      && ((projectId === 'fearngreed' && assessment?.kind === 'provenance')
        || (projectId === 'regime' && assessment?.kind === 'model_quality'))
      && typeof assessment.detail === 'string' && assessment.detail.trim()) {
    return [{ project: projectId, category: assessment.kind, severity: 'transient',
      message: assessment.detail, upstreamState: state,
      upstreamReasons: uniqueStrings(summary?.meta?.degradedReasons) }];
  }

  if (OPERATIONAL_WARNING_STATES.has(state)) {
    findings.push({
      project: projectId,
      category: 'operation',
      severity: 'transient',
      message: `${projectId} upstream state is ${state}`,
    });
  }

  const degradedReasons = uniqueStrings(summary?.meta?.degradedReasons);
  if (degradedReasons.length) {
    findings.push({
      project: projectId,
      category: 'operation',
      severity: 'transient',
      message: `${projectId} degraded reasons: ${degradedReasons.join(',')}`,
    });
  }

  return findings;
}

export function transportEscalation(projectIds, projectCount) {
  const affectedProjects = uniqueStrings(projectIds);
  if (affectedProjects.length < TRANSPORT_HARD_FAILURE_PROJECT_THRESHOLD) return null;
  return {
    project: 'hub',
    category: 'observability',
    severity: 'hard',
    message: (
      `${affectedProjects.length}/${projectCount} public projects are unobservable; `
      + `hard threshold is ${TRANSPORT_HARD_FAILURE_PROJECT_THRESHOLD}`
    ),
    affectedProjects,
  };
}

function uniqueStrings(...values) {
  return [...new Set(
    values
      .flatMap((value) => Array.isArray(value) ? value : [value])
      .filter((value) => typeof value === 'string' && value.trim())
      .map((value) => value.trim()),
  )];
}

function firstString(...values) {
  return values.find((value) => typeof value === 'string' && value.trim())?.trim() || '';
}
