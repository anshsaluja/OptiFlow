import { describe, expect, it } from 'vitest';
import { filterScenarioImpacts, sortScenarioImpacts } from './scenario-filters';
import type { ScenarioImpact } from './scenarios';

const scenario = (id: string, label: string, costDelta: number): ScenarioImpact => ({
  id, label, costDelta, costDeltaPercent: null, fulfilledDelta: 0,
  demandDelta: 0, shortageDelta: 0, transportDelta: 0, shortagePenaltyDelta: 0,
  fulfillmentRate: null, baselineFulfillmentRate: null, fulfillmentRateDeltaPoints: null
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

describe('sortScenarioImpacts', () => {
  const impacts = [
    { ...scenario('z', 'Z', 20), shortageDelta: 4, fulfillmentRateDeltaPoints: -3 },
    { ...scenario('b', 'B', 20), shortageDelta: 8, fulfillmentRateDeltaPoints: null },
    { ...scenario('a', 'A', -5), shortageDelta: 8, fulfillmentRateDeltaPoints: -7 },
    { ...scenario('c', 'C', 0), shortageDelta: 0, fulfillmentRateDeltaPoints: null }
  ];
  it('ranks cost descending with deterministic ID ties', () => {
    expect(sortScenarioImpacts(impacts, 'cost').map((s) => s.id)).toEqual(['b', 'z', 'c', 'a']);
  });
  it('ranks additional shortage descending with deterministic ID ties', () => {
    expect(sortScenarioImpacts(impacts, 'shortage').map((s) => s.id)).toEqual(['a', 'b', 'z', 'c']);
  });
  it('ranks service decline first and missing service comparisons last', () => {
    expect(sortScenarioImpacts(impacts, 'service').map((s) => s.id)).toEqual(['a', 'z', 'b', 'c']);
  });
  it('does not mutate inputs and handles empty results', () => {
    const before = impacts.map((s) => s.id);
    sortScenarioImpacts(impacts, 'service');
    expect(impacts.map((s) => s.id)).toEqual(before);
    expect(sortScenarioImpacts([], 'cost')).toEqual([]);
  });
});
