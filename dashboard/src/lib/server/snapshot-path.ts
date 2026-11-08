import { realpath, stat } from 'node:fs/promises';
import { isAbsolute, relative, resolve, sep, win32 } from 'node:path';

/**
 * Resolve an existing snapshot under its manifest directory.
 * Rejects traversal, absolute paths (including Windows paths), and symlinks
 * that escape the directory after filesystem canonicalization.
 */
export async function resolveSnapshotPath(directory: string, candidate: unknown): Promise<string> {
  if (typeof candidate !== 'string' || !candidate.trim() || candidate.includes('\0') ||
      isAbsolute(candidate) || win32.isAbsolute(candidate) ||
      candidate.split(/[\\/]/).includes('..')) {
    throw new Error('Snapshot path must be a relative file inside the manifest directory');
  }
  const root = await realpath(directory);
  const target = await realpath(resolve(root, candidate));
  const offset = relative(root, target);
  if (!offset || offset === '..' || offset.startsWith('..' + sep) || isAbsolute(offset)) {
    throw new Error('Snapshot path must resolve to a file inside the manifest directory');
  }
  if (!candidate.toLowerCase().endsWith('.json')) {
    throw new Error('Snapshot must be a JSON file');
  }
  if (!(await stat(target)).isFile()) {
    throw new Error('Snapshot path must resolve to a regular file');
  }
  return target;
}
