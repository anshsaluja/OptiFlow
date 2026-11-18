import { describe, expect, it } from 'vitest';
import { explainScenarioImpact } from './scenario-insights';

const impact = (changes: Partial<Parameters<typeof explainScenarioImpact>[0]> = {}) => ({
  demandDelta: 0, shortageDelta: 0, costDelta: 0, transportDelta: 0,
  shortagePenaltyDelta: 0, fulfillmentRateDeltaPoints: 0, ...changes
});

describe('scenario risk interpretation', () => {
  it('distinguishes demand-driven shortages from disruption shortages', () => {
    expect(explainScenarioImpact(impact({ demandDelta: 10, shortageDelta: 4, costDelta: 400 }))).toMatch(/Demand growth/);
    expect(explainScenarioImpact(impact({ shortageDelta: 4, costDelta: 400 }))).toMatch(/Disruption/);
  });
  it('identifies cost-only transport changes and no-impact closures', () => {
    expect(explainScenarioImpact(impact({ costDelta: 20, transportDelta: 20 }))).toMatch(/transport spend/);
    expect(explainScenarioImpact(impact())).toMatch(/No measured/);
  });
  it('distinguishes service recovery and cost savings', () => {
    expect(explainScenarioImpact(impact({ shortageDelta: -2, costDelta: -100 }))).toMatch(/Fewer unmet/);
    expect(explainScenarioImpact(impact({ costDelta: -5 }))).toMatch(/Lower total cost/);
  });
});
