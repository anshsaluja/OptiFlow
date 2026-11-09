import { afterEach, describe, expect, it } from 'vitest';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { load } from './+page.server';

const originalPath = process.env.OPTIFLOW_SCENARIOS_PATH;
const directories: string[] = [];

afterEach(async () => {
  if (originalPath === undefined) delete process.env.OPTIFLOW_SCENARIOS_PATH;
  else process.env.OPTIFLOW_SCENARIOS_PATH = originalPath;
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true, force: true })));
});

async function loadManifest(manifest: unknown) {
  const directory = await mkdtemp(join(tmpdir(), 'optiflow-scenarios-'));
  directories.push(directory);
  process.env.OPTIFLOW_SCENARIOS_PATH = join(directory, 'manifest.json');
  await writeFile(process.env.OPTIFLOW_SCENARIOS_PATH, JSON.stringify(manifest));
  // Invalid manifests must fail before reading baseline or scenario report files.
  return await load({} as Parameters<typeof load>[0]) as { impacts: unknown[]; error: string | null };
}

describe('scenario page manifest validation', () => {
  it('rejects empty scenario lists before reading snapshots', async () => {
    const result = await loadManifest({ baseline: 'baseline.json', scenarios: [] });
    expect(result.impacts).toEqual([]);
    expect(result.error).toMatch(/between 1 and 30 scenarios/);
  });

  it('rejects duplicate scenario IDs before reading snapshots', async () => {
    const result = await loadManifest({
      baseline: 'baseline.json',
      scenarios: [
        { id: 'closure', label: 'North closed', report: 'one.json' },
        { id: 'closure', label: 'South closed', report: 'two.json' }
      ]
    });
    expect(result.impacts).toEqual([]);
    expect(result.error).toMatch(/Duplicate scenario id: closure/);
  });

  it('rejects missing or whitespace-only identifiers and labels', async () => {
    for (const row of [
      { id: '', label: 'Closed', report: 'one.json' },
      { id: '  ', label: 'Closed', report: 'one.json' },
      { id: 'closure', label: ' ', report: 'one.json' },
      { id: 42, label: 'Closed', report: 'one.json' }
    ]) {
      const result = await loadManifest({ baseline: 'baseline.json', scenarios: [row] });
      expect(result.impacts).toEqual([]);
      expect(result.error).toMatch(/id and label must be nonempty strings/);
    }
  });

  it('rejects malformed scenario entries and oversized manifests', async () => {
    for (const scenarios of [
      [null],
      ['closure'],
      Array.from({ length: 31 }, (_, index) => ({
        id: String(index), label: 'Scenario', report: 'scenario.json'
      }))
    ]) {
      const result = await loadManifest({ baseline: 'baseline.json', scenarios });
      expect(result.impacts).toEqual([]);
      expect(result.error).toMatch(/Invalid scenario entry|between 1 and 30 scenarios/);
    }
  });
  it('rejects missing report paths before opening snapshot files', async () => {
    for (const report of ['', '  ', null, 42]) {
      const result = await loadManifest({
        baseline: 'baseline.json',
        scenarios: [{ id: 'closure', label: 'Warehouse closed', report }]
      });
      expect(result.impacts).toEqual([]);
      expect(result.error).toMatch(/requires a nonempty report path/);
    }
  });

  it('rejects blank baseline paths', async () => {
    const result = await loadManifest({
      baseline: '  ',
      scenarios: [{ id: 'closure', label: 'Warehouse closed', report: 'closure.json' }]
    });
    expect(result.impacts).toEqual([]);
    expect(result.error).toMatch(/Baseline report path must be nonempty/);
  });

  it('rejects reports reused by baseline or another scenario', async () => {
    for (const scenarios of [
      [{ id: 'closure', label: 'Warehouse closed', report: 'baseline.json' }],
      [
        { id: 'closure', label: 'Warehouse closed', report: 'shared.json' },
        { id: 'delay', label: 'Route delayed', report: 'shared.json' }
      ]
    ]) {
      const result = await loadManifest({ baseline: 'baseline.json', scenarios });
      expect(result.impacts).toEqual([]);
      expect(result.error).toMatch(/Duplicate scenario report path/);
    }
  });


  it('loads real report-shaped files and ranks disruption cost impacts', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'optiflow-scenarios-valid-'));
    directories.push(directory);
    process.env.OPTIFLOW_SCENARIOS_PATH = join(directory, 'manifest.json');

    const report = (fulfilled: number) => {
      const demand = 8;
      const unmet = demand - fulfilled;
      const transportationCost = fulfilled * 2;
      const shortageCost = unmet * 100;
      const optimizedCost = transportationCost + shortageCost;
      return {
        schemaVersion: 1, status: 'OPTIMAL', shortagePenalty: 100,
        summary: {
          totalDemand: demand, fulfilledUnits: fulfilled, unfulfilledUnits: unmet,
          optimizedCost, transportationCost, shortageCost,
          greedyCost: optimizedCost + 5, savingsVsGreedy: 5
        },
        warehouses: [{ id: 'W', inventory: 10, outboundCapacity: 10 }],
        stores: [{ id: 'S', demand, unmet }],
        shipments: [{ warehouseId: 'W', storeId: 'S', units: fulfilled,
          unitCost: 2, transportCost: transportationCost }]
      };
    };

    await Promise.all([
      writeFile(join(directory, 'manifest.json'), JSON.stringify({
        baseline: 'baseline.json',
        scenarios: [
          { id: 'minor', label: 'Minor disruption', report: 'minor.json' },
          { id: 'major', label: 'Major disruption', report: 'major.json' }
        ]
      })),
      writeFile(join(directory, 'baseline.json'), JSON.stringify(report(5))),
      writeFile(join(directory, 'minor.json'), JSON.stringify(report(4))),
      writeFile(join(directory, 'major.json'), JSON.stringify(report(2)))
    ]);

    const result = await load({} as Parameters<typeof load>[0]);
    expect(result.error).toBeNull();
    expect(result.impacts.map((impact) => impact.id)).toEqual(['major', 'minor']);
    expect(result.impacts[0]).toMatchObject({
      costDelta: 294, fulfilledDelta: -3, shortageDelta: 3,
      transportDelta: -6, shortagePenaltyDelta: 300
    });
    expect(result.impacts[1].costDelta).toBe(98);
  });
});
