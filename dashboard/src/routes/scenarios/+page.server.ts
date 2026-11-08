import { readFile } from 'node:fs/promises';
import { dirname, isAbsolute, resolve } from 'node:path';
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
    if (typeof data.baseline !== 'string' || !Array.isArray(data.scenarios) || data.scenarios.length > 30) {
      throw new Error('Manifest requires baseline and up to 30 scenarios');
    }
    const directory = dirname(manifestPath);
    const readSnapshot = async (file: unknown) => {
      if (typeof file !== 'string' || !file || isAbsolute(file) || file.split(/[\\/]/).includes('..')) {
        throw new Error('Snapshot paths must be relative to the manifest directory');
      }
      return JSON.parse(await readFile(resolve(directory, file), 'utf8'));
    };
    const baseline = await readSnapshot(data.baseline);
    const snapshots = await Promise.all(data.scenarios.map(async (entry: unknown) => {
      if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw new Error('Invalid scenario entry');
      const row = entry as Record<string, unknown>;
      if (typeof row.id !== 'string' || typeof row.label !== 'string') throw new Error('Scenario id and label must be strings');
      return { id: row.id, label: row.label, report: await readSnapshot(row.report) };
    }));
    return { impacts: compareScenarios(baseline, snapshots), error: null };
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Unknown error';
    return { impacts: [], error: `Cannot load scenario comparisons: ${detail}` };
  }
};
