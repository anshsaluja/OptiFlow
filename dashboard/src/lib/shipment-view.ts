import type { Shipment } from './report';

export type ShipmentSort = 'units' | 'cost';

/**
 * Match every whitespace-separated term against either route endpoint.
 * Sort without mutating the source snapshot, with deterministic ID tie breaks.
 */
export function selectShipments(
  shipments: readonly Shipment[],
  search: string,
  sortBy: ShipmentSort
): Shipment[] {
  const terms = search.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return shipments
    .filter((shipment) => {
      const warehouse = shipment.warehouseId.toLowerCase();
      const store = shipment.storeId.toLowerCase();
      return terms.every((term) => warehouse.includes(term) || store.includes(term));
    })
    .sort((a, b) => {
      const difference = sortBy === 'cost'
        ? b.transportCost - a.transportCost
        : b.units - a.units;
      return difference ||
        a.warehouseId.localeCompare(b.warehouseId) ||
        a.storeId.localeCompare(b.storeId);
    });
}
