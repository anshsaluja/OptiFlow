import type { Shipment } from './report';

export type ShipmentSort = 'units' | 'cost';

/**
 * Search route endpoints independently and sort without mutating the snapshot.
 * Stable route-ID tie breaks make the same report render reproducibly.
 */
export function selectShipments(
  shipments: readonly Shipment[],
  search: string,
  sortBy: ShipmentSort
): Shipment[] {
  const query = search.trim().toLocaleLowerCase();
  return shipments
    .filter((shipment) =>
      !query ||
      shipment.warehouseId.toLocaleLowerCase().includes(query) ||
      shipment.storeId.toLocaleLowerCase().includes(query)
    )
    .sort((a, b) => {
      const difference = sortBy === 'cost'
        ? b.transportCost - a.transportCost
        : b.units - a.units;
      return difference ||
        a.warehouseId.localeCompare(b.warehouseId) ||
        a.storeId.localeCompare(b.storeId);
    });
}
