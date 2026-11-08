import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import type { PageServerLoad } from './$types';
import { parseReport } from '$lib/report';

export const load: PageServerLoad = async () => {
  // Never accept a browser-supplied file path. This is a local snapshot viewer.
  const reportPath = resolve(process.env.OPTIFLOW_REPORT_PATH ?? '../output/allocation.json');
  try {
    const report = parseReport(JSON.parse(await readFile(reportPath, 'utf8')));
    return { report, error: null };
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Unknown error';
    return { report: null, error: `Cannot load allocation snapshot: ${detail}. Generate it with the Scala exporter first.` };
  }
};
