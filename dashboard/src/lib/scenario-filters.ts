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
