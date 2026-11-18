import type { ScenarioImpact } from './scenarios';

/** Explain observed optimizer output, without inferring unmeasured operational causes. */
export function explainScenarioImpact(impact: Pick<ScenarioImpact,
  'demandDelta' | 'shortageDelta' | 'costDelta' | 'transportDelta' | 'shortagePenaltyDelta' | 'fulfillmentRateDeltaPoints'>): string {
  if (impact.shortageDelta > 0) {
    if (impact.demandDelta > 0) return 'Demand growth increases unmet units; review capacity.';
    return 'Disruption increases unmet units; service is at risk.';
  }
  if (impact.shortageDelta < 0) return 'Fewer unmet units than baseline; service improves.';
  if (impact.costDelta === 0) return 'No measured cost or shortage impact in this dataset.';
  if (impact.costDelta > 0) {
    return impact.transportDelta > 0
      ? 'Higher transport spend without additional shortages.'
      : 'Higher total cost without additional shortages.';
  }
  return 'Lower total cost with no additional shortages.';
}
