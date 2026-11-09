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

});
