import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    if (entry.name === 'node_modules' || entry.name === 'dist' || entry.name === 'scripts') continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await walk(path));
    else if (/\.(jsx?|mjs)$/.test(entry.name)) files.push(path);
  }
  return files;
}

const files = await walk(fileURLToPath(new URL('..', import.meta.url)));
for (const file of files) {
  const source = await readFile(file, 'utf8');
  if (/window\.kisanHarness|from ['"](?:\.\.\/)+(?:backend|agent)/.test(source)) throw new Error(`standalone browser boundary violation: ${file}`);
}
console.log(`standalone lint: ${files.length} files checked`);
