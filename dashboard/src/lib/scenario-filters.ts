import type { ScenarioImpact } from './scenarios';

export type ImpactFilter = 'all' | 'worse' | 'savings';

/**
 * Filter already-ranked optimizer results without changing their relative order.
 * A zero-cost scenario belongs only in the "all" view.
 */
export function filterScenarioImpacts(
  impacts: readonly ScenarioImpact[],
  search: string,
  filter: ImpactFilter
): ScenarioImpact[] {
  const query = search.trim().toLocaleLowerCase();
  return impacts.filter((impact) => {
    const matchesSearch = !query ||
      impact.id.toLocaleLowerCase().includes(query) ||
      impact.label.toLocaleLowerCase().includes(query);
    const matchesCost = filter === 'all' ||
      (filter === 'worse' && impact.costDelta > 0) ||
      (filter === 'savings' && impact.costDelta < 0);
    return matchesSearch && matchesCost;
  });
}

export type ScenarioSort = 'cost' | 'shortage' | 'service';

/** Rank disruption impacts without mutating source snapshots.
 * Missing service-rate comparisons sort last, not as the worst disruption.
 * Stable ID tie-breaking keeps the ranking reproducible across report runs.
 */
export function sortScenarioImpacts(
  impacts: readonly ScenarioImpact[],
  sortBy: ScenarioSort
): ScenarioImpact[] {
  return [...impacts].sort((a, b) => {
    if (sortBy === 'shortage') return b.shortageDelta - a.shortageDelta || a.id.localeCompare(b.id);
    if (sortBy === 'service') {
      const aRate = a.fulfillmentRateDeltaPoints;
      const bRate = b.fulfillmentRateDeltaPoints;
      if (aRate === null && bRate !== null) return 1;
      if (bRate === null && aRate !== null) return -1;
      if (aRate !== null && bRate !== null && aRate !== bRate) return aRate - bRate;
      return a.id.localeCompare(b.id);
    }
    return b.costDelta - a.costDelta || a.id.localeCompare(b.id);
  });
}
