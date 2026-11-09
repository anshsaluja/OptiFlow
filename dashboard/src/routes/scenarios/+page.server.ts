import { readFile } from 'node:fs/promises';
import { dirname, normalize, resolve } from 'node:path';
import { resolveSnapshotPath } from '$lib/server/snapshot-path';
import type { PageServerLoad } from './$types';
import { compareScenarios } from '$lib/scenarios';

/**
 * Manifest example:
 * { "baseline": "baseline.json", "scenarios": [
 *   { "id": "north-closed", "label": "North warehouse closed", "report": "north-closed.json" }
 * ] }
 * Paths are resolved relative to the manifest, never from browser input.
 */
export const load: PageServerLoad = async () => {
  const manifestPath = resolve(process.env.OPTIFLOW_SCENARIOS_PATH ?? '../output/scenarios/manifest.json');
  try {
    const manifest: unknown = JSON.parse(await readFile(manifestPath, 'utf8'));
    if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) throw new Error('Invalid scenario manifest');
    const data = manifest as Record<string, unknown>;
    if (typeof data.baseline !== 'string' || !Array.isArray(data.scenarios) || data.scenarios.length === 0 || data.scenarios.length > 30) {
      throw new Error('Manifest requires baseline and between 1 and 30 scenarios');
    }
    if (!data.baseline.trim()) throw new Error('Baseline report path must be nonempty');
    const ids = new Set<string>();
    // Normalize relative references so ./baseline.json cannot be reused as a scenario report.
    const reportPaths = new Set<string>([normalize(data.baseline.trim())]);
    for (const entry of data.scenarios) {
      if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw new Error('Invalid scenario entry');
      const row = entry as Record<string, unknown>;
      if (typeof row.id !== 'string' || !row.id.trim() || typeof row.label !== 'string' || !row.label.trim()) {
        throw new Error('Scenario id and label must be nonempty strings');
      }
      const id = row.id.trim();
      if (ids.has(id)) throw new Error(`Duplicate scenario id: ${id}`);
      ids.add(id);
      if (typeof row.report !== 'string' || !row.report.trim()) {
        throw new Error(`Scenario ${row.id} requires a nonempty report path`);
      }
      const normalizedReport = normalize(row.report.trim());
      if (reportPaths.has(normalizedReport)) throw new Error(`Duplicate scenario report path: ${row.report}`);
      reportPaths.add(normalizedReport);
    }
    const directory = dirname(manifestPath);
    const readSnapshot = async (file: unknown) => {
      return JSON.parse(await readFile(await resolveSnapshotPath(directory, file), 'utf8'));
    };
    const baseline = await readSnapshot(data.baseline);
    const snapshots = await Promise.all(data.scenarios.map(async (entry: unknown) => {
      if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw new Error('Invalid scenario entry');
      const row = entry as Record<string, unknown>;
      if (typeof row.id !== 'string' || typeof row.label !== 'string') throw new Error('Scenario id and label must be strings');
      return { id: row.id.trim(), label: row.label.trim(), report: await readSnapshot(row.report) };
    }));
    return { impacts: compareScenarios(baseline, snapshots), error: null };
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Unknown error';
    return { impacts: [], error: `Cannot load scenario comparisons: ${detail}` };
  }
};
