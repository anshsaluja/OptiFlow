import { describe, expect, it } from 'vitest';
import { filterScenarioImpacts } from './scenario-filters';
import type { ScenarioImpact } from './scenarios';

const scenario = (id: string, label: string, costDelta: number): ScenarioImpact => ({
  id, label, costDelta, costDeltaPercent: null, fulfilledDelta: 0,
  shortageDelta: 0, transportDelta: 0, shortagePenaltyDelta: 0,
  fulfillmentRate: null, baselineFulfillmentRate: null
});

const ranked = [
  scenario('north-closed', 'North warehouse closed', 120),
  scenario('demand-spike', 'Demand spike', 40),
  scenario('unchanged', 'Unchanged baseline', 0),
  scenario('routing-win', 'Cheaper routing', -25)
];

describe('filterScenarioImpacts', () => {
  it('preserves the optimizer ranking for all scenarios', () => {
    expect(filterScenarioImpacts(ranked, '', 'all').map((s) => s.id))
      .toEqual(ranked.map((s) => s.id));
  });

  it('searches both IDs and labels case-insensitively and trims whitespace', () => {
    expect(filterScenarioImpacts(ranked, '  NORTH  ', 'all').map((s) => s.id))
      .toEqual(['north-closed']);
    expect(filterScenarioImpacts(ranked, 'ROUTING-WIN', 'all').map((s) => s.id))
      .toEqual(['routing-win']);
  });

  it('separates cost increases and savings, excluding zero from both', () => {
    expect(filterScenarioImpacts(ranked, '', 'worse').map((s) => s.id))
      .toEqual(['north-closed', 'demand-spike']);
    expect(filterScenarioImpacts(ranked, '', 'savings').map((s) => s.id))
      .toEqual(['routing-win']);
  });

  it('combines search and cost filter without mutating source results', () => {
    const original = ranked.map((s) => s.id);
    expect(filterScenarioImpacts(ranked, 'north', 'savings')).toEqual([]);
    expect(ranked.map((s) => s.id)).toEqual(original);
  });

  it('handles empty inputs and searches with no matches', () => {
    expect(filterScenarioImpacts([], '', 'all')).toEqual([]);
    expect(filterScenarioImpacts(ranked, 'nonexistent', 'all')).toEqual([]);
  });
});
