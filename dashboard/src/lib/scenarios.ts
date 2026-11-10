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
  fulfillmentRateDeltaPoints: number | null;
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
    // Enforce the same canonical identity for direct callers and manifest-loaded scenarios.
    const normalizedId = id.trim();
    const normalizedLabel = label.trim();
    if (!normalizedId || !normalizedLabel || ids.has(normalizedId)) {
      throw new Error('Scenario IDs must be unique and scenario labels must be nonempty');
    }
    ids.add(normalizedId);
    const scenario = parseReport(raw);
    // Cost comparisons are only meaningful with the same shortage valuation.
    if (scenario.shortagePenalty !== baseline.shortagePenalty) {
      throw new Error(`Scenario ${normalizedId} uses a different shortage penalty`);
    }
    const base = baseline.summary;
    const next = scenario.summary;
    const costDelta = next.optimizedCost - base.optimizedCost;
    const rawCostDeltaPercent = base.optimizedCost === 0 ? null :
      (costDelta / base.optimizedCost) * 100;
    // Divide before multiplying to preserve representable percentages for large
    // finite costs; genuinely unrepresentable changes remain null.
    const costDeltaPercent = rawCostDeltaPercent !== null && Number.isFinite(rawCostDeltaPercent)
      ? rawCostDeltaPercent : null;
    return {
      id: normalizedId,
      label: normalizedLabel,
      costDelta,
      costDeltaPercent,
      demandDelta: next.totalDemand - base.totalDemand,
      fulfilledDelta: next.fulfilledUnits - base.fulfilledUnits,
      shortageDelta: next.unfulfilledUnits - base.unfulfilledUnits,
      transportDelta: next.transportationCost - base.transportationCost,
      shortagePenaltyDelta: next.shortageCost - base.shortageCost,
      fulfillmentRate: next.totalDemand === 0 ? null : next.fulfilledUnits / next.totalDemand,
      baselineFulfillmentRate: base.totalDemand === 0 ? null : base.fulfilledUnits / base.totalDemand,
      // Percentage-point change is meaningful only when both periods have demand.
      fulfillmentRateDeltaPoints: base.totalDemand === 0 || next.totalDemand === 0
        ? null : 100 * (next.fulfilledUnits / next.totalDemand - base.fulfilledUnits / base.totalDemand)
    };
  }).sort((a, b) => b.costDelta - a.costDelta || a.id.localeCompare(b.id));
}
