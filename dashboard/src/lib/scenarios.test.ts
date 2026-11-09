import { describe, expect, it } from 'vitest';
import { compareScenarios } from './scenarios';

function report(demand = 8, fulfilled = 5, unitCost = 2, penalty = 100) {
  const unmet = demand - fulfilled;
  const transportationCost = fulfilled * unitCost;
  const optimizedCost = transportationCost + unmet * penalty;
  return {
    schemaVersion: 1, status: 'OPTIMAL', shortagePenalty: penalty,
    summary: {
      totalDemand: demand, fulfilledUnits: fulfilled, unfulfilledUnits: unmet,
      optimizedCost, transportationCost, shortageCost: unmet * penalty,
      greedyCost: optimizedCost + 5, savingsVsGreedy: 5
    },
    warehouses: [{ id: 'W', inventory: 10, outboundCapacity: 10 }],
    stores: [{ id: 'S', demand, unmet }],
    shipments: [{ warehouseId: 'W', storeId: 'S', units: fulfilled,
      unitCost, transportCost: transportationCost }]
  };
}

describe('scenario comparison', () => {
  it('computes cost, transport, shortage and fulfillment deltas', () => {
    const [impact] = compareScenarios(report(), [
      { id: 'closure', label: 'Warehouse closure', report: report(8, 3) }
    ]);
    expect(impact.costDelta).toBe(196);
    expect(impact.shortageDelta).toBe(2);
    expect(impact.demandDelta).toBe(0);
    expect(impact.fulfilledDelta).toBe(-2);
    expect(impact.transportDelta).toBe(-4);
    expect(impact.shortagePenaltyDelta).toBe(200);
    expect(impact.fulfillmentRate).toBe(3 / 8);
  });

  it('ranks the highest additional cost first and breaks ties by id', () => {
    const impacts = compareScenarios(report(), [
      { id: 'z', label: 'Z', report: report(8, 4) },
      { id: 'b', label: 'B', report: report(8, 3) },
      { id: 'a', label: 'A', report: report(8, 3) }
    ]);
    expect(impacts.map((s) => s.id)).toEqual(['a', 'b', 'z']);
  });

  it('rejects incompatible penalty valuations', () => {
    expect(() => compareScenarios(report(), [
      { id: 'x', label: 'Different penalty', report: report(8, 5, 2, 200) }
    ])).toThrow(/different shortage penalty/);
  });

  it('rejects duplicate IDs and malformed scenario allocations', () => {
    expect(() => compareScenarios(report(), [
      { id: 'x', label: 'One', report: report() },
      { id: 'x', label: 'Two', report: report() }
    ])).toThrow(/unique/);
    const broken = report();
    broken.summary.optimizedCost += 10;
    expect(() => compareScenarios(report(), [
      { id: 'bad', label: 'Bad', report: broken }
    ])).toThrow(/Cost breakdown/);
  });

  it('uses null percentages for zero-denominator baselines', () => {
    const [impact] = compareScenarios(report(0, 0), [
      { id: 'demand', label: 'Demand surge', report: report(2, 1) }
    ]);
    expect(impact.costDeltaPercent).toBeNull();
    expect(impact.baselineFulfillmentRate).toBeNull();
    expect(impact.fulfillmentRate).toBe(0.5);
    expect(impact.demandDelta).toBe(2);
    expect(impact.fulfilledDelta).toBe(1);
    expect(impact.shortageDelta).toBe(1);
  });
});
