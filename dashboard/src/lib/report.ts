export type Warehouse = { id: string; inventory: number; outboundCapacity: number };
export type Store = { id: string; demand: number; unmet: number };
export type Shipment = { warehouseId: string; storeId: string; units: number; unitCost: number; transportCost: number };
export type Summary = {
  totalDemand: number; fulfilledUnits: number; unfulfilledUnits: number;
  optimizedCost: number; transportationCost: number; shortageCost: number;
  greedyCost: number; savingsVsGreedy: number;
};
export type AllocationReport = {
  schemaVersion: 1; status: string; shortagePenalty: number;
  summary: Summary; warehouses: Warehouse[]; stores: Store[]; shipments: Shipment[];
};

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Expected JSON object');
  return value as Record<string, unknown>;
}
function number(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error(`Invalid ${label}`);
  return value;
}
function text(value: unknown, label: string): string {
  if (typeof value !== 'string') throw new Error(`Invalid ${label}`);
  return value;
}
function array<T>(value: unknown, label: string, convert: (v: Record<string, unknown>) => T): T[] {
  if (!Array.isArray(value)) throw new Error(`Invalid ${label}`);
  return value.map((entry) => convert(object(entry)));
}
export function parseReport(raw: unknown): AllocationReport {
  const value = object(raw);
  if (value.schemaVersion !== 1) throw new Error('Unsupported report schema version');
  const summary = object(value.summary);
  const report: AllocationReport = {
    schemaVersion: 1,
    status: text(value.status, 'status'),
    shortagePenalty: number(value.shortagePenalty, 'shortagePenalty'),
    summary: {
      totalDemand: number(summary.totalDemand, 'totalDemand'),
      fulfilledUnits: number(summary.fulfilledUnits, 'fulfilledUnits'),
      unfulfilledUnits: number(summary.unfulfilledUnits, 'unfulfilledUnits'),
      optimizedCost: number(summary.optimizedCost, 'optimizedCost'),
      transportationCost: number(summary.transportationCost, 'transportationCost'),
      shortageCost: number(summary.shortageCost, 'shortageCost'),
      greedyCost: number(summary.greedyCost, 'greedyCost'),
      savingsVsGreedy: number(summary.savingsVsGreedy, 'savingsVsGreedy')
    },
    warehouses: array(value.warehouses, 'warehouses', (w) => ({
      id: text(w.id, 'warehouse.id'), inventory: number(w.inventory, 'inventory'),
      outboundCapacity: number(w.outboundCapacity, 'outboundCapacity')
    })),
    stores: array(value.stores, 'stores', (s) => ({
      id: text(s.id, 'store.id'), demand: number(s.demand, 'demand'), unmet: number(s.unmet, 'unmet')
    })),
    shipments: array(value.shipments, 'shipments', (s) => ({
      warehouseId: text(s.warehouseId, 'shipment.warehouseId'),
      storeId: text(s.storeId, 'shipment.storeId'), units: number(s.units, 'units'),
      unitCost: number(s.unitCost, 'unitCost'), transportCost: number(s.transportCost, 'transportCost')
    }))
  };
  const s = report.summary;
  if (s.fulfilledUnits + s.unfulfilledUnits !== s.totalDemand ||
      report.stores.reduce((n, store) => n + store.demand, 0) !== s.totalDemand ||
      report.shipments.reduce((n, shipment) => n + shipment.units, 0) !== s.fulfilledUnits) {
    throw new Error('Report totals do not reconcile');
  }
  return report;
}
