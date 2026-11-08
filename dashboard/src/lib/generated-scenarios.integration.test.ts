import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { parseReport } from './report';
import { compareScenarios } from './scenarios';

// Set by Scala CI after the real OR-Tools generator has produced snapshots.
// Ordinary dashboard test runs skip this integration test when no outputs exist.
const directory = process.env.OPTIFLOW_SCENARIO_DIR;
describe.skipIf(!directory)('Scala-generated scenario snapshot contract', () => {
  it('loads every generated report through the dashboard parser and comparison engine', () => {
    const readJson = (filename: string): unknown =>
      JSON.parse(readFileSync(join(directory!, filename), 'utf8'));
    const manifest = readJson('manifest.json') as {
      baseline: string;
      scenarios: Array<{ id: string; label: string; report: string }>;
    };
    expect(manifest.scenarios.length).toBeGreaterThan(0);
    expect(manifest.scenarios.length).toBeLessThanOrEqual(30);
    const baseline = parseReport(readJson(manifest.baseline));
    const scenarios = manifest.scenarios.map(({ id, label, report }) => ({
      id, label, report: parseReport(readJson(report))
    }));
    const impacts = compareScenarios(baseline, scenarios);
    expect(impacts).toHaveLength(manifest.scenarios.length);
    expect(new Set(impacts.map((impact) => impact.id)).size).toBe(impacts.length);
    for (const impact of impacts) {
      expect(Number.isFinite(impact.costDelta)).toBe(true);
      expect(Number.isFinite(impact.shortageDelta)).toBe(true);
    }
  });
});
