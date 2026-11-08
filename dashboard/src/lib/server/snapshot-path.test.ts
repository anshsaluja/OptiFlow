import { afterEach, describe, expect, it } from 'vitest';
import { mkdtemp, mkdir, rm, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { resolveSnapshotPath } from './snapshot-path';

const directories: string[] = [];
async function fixture() {
  const root = await mkdtemp(join(tmpdir(), 'optiflow-snapshots-'));
  directories.push(root);
  const snapshots = join(root, 'snapshots');
  const outside = join(root, 'outside');
  await mkdir(snapshots);
  await mkdir(outside);
  await writeFile(join(snapshots, 'baseline.json'), '{}');
  await writeFile(join(outside, 'secret.json'), '{}');
  return { snapshots, outside };
}
afterEach(async () => {
  await Promise.all(directories.splice(0).map(path => rm(path, { recursive: true, force: true })));
});
describe('resolveSnapshotPath', () => {
  it('accepts existing files inside the manifest directory', async () => {
    const { snapshots } = await fixture();
    expect(await resolveSnapshotPath(snapshots, 'baseline.json')).toBe(join(snapshots, 'baseline.json'));
  });
  it('rejects parent traversal and absolute paths', async () => {
    const { snapshots, outside } = await fixture();
    await expect(resolveSnapshotPath(snapshots, '../outside/secret.json')).rejects.toThrow();
    await expect(resolveSnapshotPath(snapshots, join(outside, 'secret.json'))).rejects.toThrow();
    await expect(resolveSnapshotPath(snapshots, 'C:\\outside\\secret.json')).rejects.toThrow();
  });
  it('rejects symlinks escaping the snapshot directory', async () => {
    const { snapshots, outside } = await fixture();
    await symlink(join(outside, 'secret.json'), join(snapshots, 'escape.json'));
    await expect(resolveSnapshotPath(snapshots, 'escape.json')).rejects.toThrow(/inside the manifest/);
  });
  it('rejects NUL bytes, non-JSON files, and directory targets', async () => {
    const { snapshots } = await fixture();
    await writeFile(join(snapshots, 'notes.txt'), 'not a snapshot');
    await mkdir(join(snapshots, 'folder.json'));
    await expect(resolveSnapshotPath(snapshots, 'baseline.json' + String.fromCharCode(0) + '.txt')).rejects.toThrow();
    await expect(resolveSnapshotPath(snapshots, 'notes.txt')).rejects.toThrow(/JSON file/);
    await expect(resolveSnapshotPath(snapshots, 'folder.json')).rejects.toThrow(/regular file/);
  });
  it('rejects missing, blank, and non-string snapshot paths', async () => {
    const { snapshots } = await fixture();
    await expect(resolveSnapshotPath(snapshots, 'missing.json')).rejects.toThrow();
    await expect(resolveSnapshotPath(snapshots, '')).rejects.toThrow();
    await expect(resolveSnapshotPath(snapshots, null)).rejects.toThrow();
  });
});
