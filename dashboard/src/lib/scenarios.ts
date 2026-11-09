import { parseReport, type AllocationReport } from './report';

export type ScenarioSnapshot = {
  id: string;
  label: string;
  report: AllocationReport;
};

export type ScenarioImpact = {
  id: string;
  label: string;
  costDelta: number;
  costDeltaPercent: number | null;
  demandDelta: number;
  fulfilledDelta: number;
  shortageDelta: number;
  transportDelta: number;
  shortagePenaltyDelta: number;
  fulfillmentRate: number | null;
  baselineFulfillmentRate: number | null;
};

/**
 * Compare independently optimized scenario snapshots against a common baseline.
 * No scenario is solved in the browser; all reports must come from the Scala engine.
 * Percentage changes are null when their denominator is zero.
 */
export function compareScenarios(
  baselineInput: unknown,
  scenarios: ReadonlyArray<{ id: string; label: string; report: unknown }>
): ScenarioImpact[] {
  const baseline = parseReport(baselineInput);
  const ids = new Set<string>();
  return scenarios.map(({ id, label, report: raw }) => {
    if (!id.trim() || !label.trim() || ids.has(id)) {
      throw new Error('Scenario IDs must be unique and scenario labels must be nonempty');
    }
    ids.add(id);
    const scenario = parseReport(raw);
    // Cost comparisons are only meaningful with the same shortage valuation.
    if (scenario.shortagePenalty !== baseline.shortagePenalty) {
      throw new Error(`Scenario ${id} uses a different shortage penalty`);
    }
    const base = baseline.summary;
    const next = scenario.summary;
    return {
      id,
      label,
      costDelta: next.optimizedCost - base.optimizedCost,
      costDeltaPercent: base.optimizedCost === 0 ? null :
        100 * (next.optimizedCost - base.optimizedCost) / base.optimizedCost,
      demandDelta: next.totalDemand - base.totalDemand,
      fulfilledDelta: next.fulfilledUnits - base.fulfilledUnits,
      shortageDelta: next.unfulfilledUnits - base.unfulfilledUnits,
      transportDelta: next.transportationCost - base.transportationCost,
      shortagePenaltyDelta: next.shortageCost - base.shortageCost,
      fulfillmentRate: next.totalDemand === 0 ? null : next.fulfilledUnits / next.totalDemand,
      baselineFulfillmentRate: base.totalDemand === 0 ? null : base.fulfilledUnits / base.totalDemand
    };
  }).sort((a, b) => b.costDelta - a.costDelta || a.id.localeCompare(b.id));
}
