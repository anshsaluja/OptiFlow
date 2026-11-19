import { describe, expect, it } from 'vitest';
import type { ScenarioImpact } from './scenarios';
import { summarizeScenarioCosts } from './scenario-summary';

const impact = (id: string, costDelta: number): ScenarioImpact => ({
  id, label: id, costDelta, costDeltaPercent: null,
  demandDelta: 0, fulfilledDelta: 0, shortageDelta: 0,
  transportDelta: 0, shortagePenaltyDelta: 0,
  fulfillmentRate: null, baselineFulfillmentRate: null,
  fulfillmentRateDeltaPoints: null
});

describe('Scenario Lab cost summary', () => {
  it('selects the largest increase and the greatest saving independently', () => {
    const result = summarizeScenarioCosts([impact('small', 3), impact('saving', -20), impact('large', 12), impact('less', -4)]);
    expect(result.highestCostIncrease?.id).toBe('large');
    expect(result.greatestCostSaving?.id).toBe('saving');
  });

  it('reports savings without claiming an increase', () => {
    const result = summarizeScenarioCosts([impact('unchanged', 0), impact('saved', -7)]);
    expect(result.highestCostIncrease).toBeNull();
    expect(result.greatestCostSaving?.costDelta).toBe(-7);
  });

  it('reports neither for zero-only or empty scenarios', () => {
    expect(summarizeScenarioCosts([impact('zero', 0)])).toEqual({
      highestCostIncrease: null, greatestCostSaving: null
    });
    expect(summarizeScenarioCosts([])).toEqual({
      highestCostIncrease: null, greatestCostSaving: null
    });
  });

  it('resolves equal deltas by ID regardless of input order', () => {
    const values = [impact('z', 10), impact('b', -8), impact('a', 10), impact('a-saving', -8)];
    for (const items of [values, [...values].reverse()]) {
      const result = summarizeScenarioCosts(items);
      expect(result.highestCostIncrease?.id).toBe('a');
      expect(result.greatestCostSaving?.id).toBe('a-saving');
    }
  });

  it('does not mutate scenario inputs', () => {
    const values = Object.freeze([Object.freeze(impact('worse', 3)), Object.freeze(impact('better', -2))]);
    summarizeScenarioCosts(values);
    expect(values.map((value) => value.id)).toEqual(['worse', 'better']);
  });
});
