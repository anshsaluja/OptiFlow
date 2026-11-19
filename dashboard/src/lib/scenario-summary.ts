import type { ScenarioImpact } from './scenarios';

export type ScenarioCostSummary = {
  highestCostIncrease: ScenarioImpact | null;
  greatestCostSaving: ScenarioImpact | null;
};

/**
 * Select the most costly disruption and greatest saving across ALL scenarios,
 * independently of search filters and table sorting. A zero delta is neither.
 * Ties use canonical scenario IDs so the result does not depend on input order.
 */
export function summarizeScenarioCosts(impacts: readonly ScenarioImpact[]): ScenarioCostSummary {
  let highestCostIncrease: ScenarioImpact | null = null;
  let greatestCostSaving: ScenarioImpact | null = null;
  for (const impact of impacts) {
    if (impact.costDelta > 0 && (
      highestCostIncrease === null ||
      impact.costDelta > highestCostIncrease.costDelta ||
      (impact.costDelta === highestCostIncrease.costDelta && impact.id < highestCostIncrease.id)
    )) highestCostIncrease = impact;
    if (impact.costDelta < 0 && (
      greatestCostSaving === null ||
      impact.costDelta < greatestCostSaving.costDelta ||
      (impact.costDelta === greatestCostSaving.costDelta && impact.id < greatestCostSaving.id)
    )) greatestCostSaving = impact;
  }
  return { highestCostIncrease, greatestCostSaving };
}
