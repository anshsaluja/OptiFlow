import { describe, expect, it } from 'vitest';
import type { Shipment } from './report';
import { selectShipments } from './shipment-view';

const routes: Shipment[] = [
  { warehouseId: 'WH-B', storeId: 'ST-2', units: 8, unitCost: 2, transportCost: 16 },
  { warehouseId: 'WH-A', storeId: 'ST-1', units: 8, unitCost: 5, transportCost: 40 },
  { warehouseId: 'WH-C', storeId: 'ST-3', units: 3, unitCost: 20, transportCost: 60 }
];

describe('selectShipments', () => {
  it('sorts by units with deterministic route tie breaks', () => {
    expect(selectShipments(routes, '', 'units').map((s) => s.warehouseId))
      .toEqual(['WH-A', 'WH-B', 'WH-C']);
  });

  it('sorts by total transportation cost', () => {
    expect(selectShipments(routes, '', 'cost').map((s) => s.warehouseId))
      .toEqual(['WH-C', 'WH-A', 'WH-B']);
  });

  it('searches either endpoint ignoring case and outer whitespace', () => {
    expect(selectShipments(routes, '  st-2  ', 'units').map((s) => s.warehouseId))
      .toEqual(['WH-B']);
    expect(selectShipments(routes, 'wh-c', 'units').map((s) => s.storeId))
      .toEqual(['ST-3']);
    expect(selectShipments(routes, 'missing', 'units')).toEqual([]);
  });

  it('does not mutate the input array or its shipments', () => {
    const frozen = Object.freeze(routes.map((route) => Object.freeze({ ...route })));
    selectShipments(frozen, '', 'cost');
    expect(frozen.map((route) => route.warehouseId))
      .toEqual(['WH-B', 'WH-A', 'WH-C']);
  });

  it('breaks exact numeric ties by both endpoint IDs', () => {
    const tied = [
      { ...routes[0], warehouseId: 'WH-A', storeId: 'ST-Z' },
      { ...routes[0], warehouseId: 'WH-A', storeId: 'ST-A' }
    ];
    expect(selectShipments(tied, '', 'cost').map((s) => s.storeId))
      .toEqual(['ST-A', 'ST-Z']);
  });
});
