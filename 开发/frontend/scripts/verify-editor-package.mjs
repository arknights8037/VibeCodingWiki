import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const packagePath = resolve('vendor/my-notebook-vue-block-editor-0.1.0.tgz');
const checksumPath = `${packagePath}.sha256`;
const [archive, expectedRaw] = await Promise.all([readFile(packagePath), readFile(checksumPath, 'utf8')]);
const actual = createHash('sha256').update(archive).digest('hex');
const expected = expectedRaw.trim().split(/\s+/)[0];
if (!/^[a-f0-9]{64}$/i.test(expected) || actual !== expected.toLowerCase()) {
  throw new Error(`local editor package checksum mismatch: expected ${expected}, got ${actual}`);
}
console.log(`verified @my-notebook/vue-block-editor local archive (${actual})`);
