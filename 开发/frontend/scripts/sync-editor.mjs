import { mkdirSync, readdirSync, copyFileSync } from 'node:fs';
import { join } from 'node:path';
function copyDirectory(source, target) {
  mkdirSync(target, { recursive: true });
  for (const entry of readdirSync(source, { withFileTypes: true })) {
    const from = join(source, entry.name), to = join(target, entry.name);
    if (entry.isDirectory()) copyDirectory(from, to);
    else copyFileSync(from, to);
  }
}
copyDirectory('node_modules/vditor/dist', 'public/vendor/vditor/dist');
