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
function close(a: number, b: number): boolean {
  return Math.abs(a - b) <= 1e-6 * Math.max(1, Math.abs(a), Math.abs(b));
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


  // Treat reports as untrusted input even when loaded from a local snapshot.
  // A report must describe a physically feasible shipment plan, not merely
  // reconcile aggregate totals.
  const nonnegativeInteger = (n: number, label: string) => {
    if (!Number.isSafeInteger(n) || n < 0) throw new Error(`Invalid ${label}: expected nonnegative integer`);
  };
  const nonnegativeMoney = (n: number, label: string) => {
    if (n < 0) throw new Error(`Invalid ${label}: expected nonnegative amount`);
  };
  nonnegativeMoney(report.shortagePenalty, 'shortagePenalty');
  if (report.shortagePenalty === 0) throw new Error('Shortage penalty must be positive');
  for (const key of ['totalDemand', 'fulfilledUnits', 'unfulfilledUnits'] as const)
    nonnegativeInteger(s[key], key);
  for (const key of ['optimizedCost', 'transportationCost', 'shortageCost', 'greedyCost'] as const)
    nonnegativeMoney(s[key], key);
  const unique = (ids: string[], label: string) => {
    if (ids.some((id) => !id.trim()) || new Set(ids).size !== ids.length)
      throw new Error(`Empty or duplicate ${label} IDs`);
  };
  unique(report.warehouses.map((w) => w.id), 'warehouse');
  unique(report.stores.map((store) => store.id), 'store');
  const warehouseIds = new Set(report.warehouses.map((w) => w.id));
  const storeIds = new Set(report.stores.map((store) => store.id));
  for (const w of report.warehouses) {
    nonnegativeInteger(w.inventory, 'warehouse.inventory');
    nonnegativeInteger(w.outboundCapacity, 'warehouse.outboundCapacity');
  }
  for (const store of report.stores) {
    nonnegativeInteger(store.demand, 'store.demand');
    nonnegativeInteger(store.unmet, 'store.unmet');
    if (store.unmet > store.demand) throw new Error('Store shortage exceeds demand');
  }
  const routes = new Set<string>();
  for (const shipment of report.shipments) {
    nonnegativeInteger(shipment.units, 'shipment.units');
    nonnegativeMoney(shipment.unitCost, 'shipment.unitCost');
    nonnegativeMoney(shipment.transportCost, 'shipment.transportCost');
    if (!warehouseIds.has(shipment.warehouseId) || !storeIds.has(shipment.storeId))
      throw new Error('Shipment references unknown warehouse or store');
    const routeKey = JSON.stringify([shipment.warehouseId, shipment.storeId]);
    if (routes.has(routeKey)) throw new Error('Duplicate shipment route');
    routes.add(routeKey);
    if (!close(shipment.transportCost, shipment.units * shipment.unitCost))
      throw new Error('Shipment transport cost mismatch');
  }
  if (s.fulfilledUnits + s.unfulfilledUnits !== s.totalDemand ||
      report.stores.reduce((n, store) => n + store.demand, 0) !== s.totalDemand ||
      report.shipments.reduce((n, shipment) => n + shipment.units, 0) !== s.fulfilledUnits) {
    throw new Error('Report totals do not reconcile');
  }
  for (const w of report.warehouses) {
    const outgoing = report.shipments.filter((x) => x.warehouseId === w.id)
      .reduce((sum, x) => sum + x.units, 0);
    if (outgoing > Math.min(w.inventory, w.outboundCapacity))
      throw new Error(`Warehouse ${w.id} exceeds available capacity`);
  }
  for (const store of report.stores) {
    const incoming = report.shipments.filter((x) => x.storeId === store.id)
      .reduce((sum, x) => sum + x.units, 0);
    if (incoming + store.unmet !== store.demand)
      throw new Error(`Store ${store.id} fulfillment mismatch`);
  }
  if (report.stores.reduce((sum, store) => sum + store.unmet, 0) !== s.unfulfilledUnits)
    throw new Error('Store shortages do not reconcile');
  if (!close(report.shipments.reduce((sum, x) => sum + x.transportCost, 0), s.transportationCost) ||
      !close(s.unfulfilledUnits * report.shortagePenalty, s.shortageCost) ||
      !close(s.transportationCost + s.shortageCost, s.optimizedCost) ||
      !close(s.greedyCost - s.optimizedCost, s.savingsVsGreedy))
    throw new Error('Cost breakdown does not reconcile');
  return report;
}
