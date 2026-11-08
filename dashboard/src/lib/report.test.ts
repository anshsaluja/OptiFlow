import { describe, expect, it } from 'vitest';
import { parseReport } from './report';

function valid() {
  return {
    schemaVersion: 1, status: 'OPTIMAL', shortagePenalty: 100,
    summary: { totalDemand: 8, fulfilledUnits: 5, unfulfilledUnits: 3,
      optimizedCost: 310, transportationCost: 10, shortageCost: 300,
      greedyCost: 315, savingsVsGreedy: 5 },
    warehouses: [{ id: 'W', inventory: 7, outboundCapacity: 5 }],
    stores: [{ id: 'S', demand: 8, unmet: 3 }],
    shipments: [{ warehouseId: 'W', storeId: 'S', units: 5, unitCost: 2, transportCost: 10 }]
  };
}

describe('allocation report integrity', () => {
  it('accepts a feasible allocation and reconciled costs', () => {
    expect(parseReport(valid()).summary.fulfilledUnits).toBe(5);
  });
  it('rejects warehouse capacity violations even if totals reconcile', () => {
    const input = valid();
    input.warehouses[0].outboundCapacity = 4;
    expect(() => parseReport(input)).toThrow(/capacity/);
  });
  it('rejects store-level fulfillment mismatches', () => {
    const input = valid();
    input.stores.push({ id: 'T', demand: 0, unmet: 0 });
    input.shipments[0].storeId = 'T';
    expect(() => parseReport(input)).toThrow(/fulfillment mismatch/);
  });
  it('rejects invented cost savings', () => {
    const input = valid();
    input.summary.savingsVsGreedy = 50;
    expect(() => parseReport(input)).toThrow(/Cost breakdown/);
  });
  it('rejects negative and fractional shipment units', () => {
    const input = valid();
    input.shipments[0].units = 4.5;
    expect(() => parseReport(input)).toThrow(/nonnegative integer/);
  });
  it('rejects shipments with unknown endpoints', () => {
    const input = valid();
    input.shipments[0].warehouseId = 'unknown';
    expect(() => parseReport(input)).toThrow(/unknown warehouse/);
  });
  it('rejects duplicated shipment routes', () => {
    const input = valid();
    input.shipments.push({ ...input.shipments[0], units: 0, transportCost: 0 });
    expect(() => parseReport(input)).toThrow(/Duplicate shipment route/);
  });
  it('rejects inconsistent shipment transport costs', () => {
    const input = valid();
    input.shipments[0].transportCost = 12;
    expect(() => parseReport(input)).toThrow(/transport cost mismatch/);
  });
});
