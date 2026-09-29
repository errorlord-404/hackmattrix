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
    else files.push(path);
  }
  return files;
}

for (const file of await walk(fileURLToPath(new URL('..', import.meta.url)))) {
  if (!/\.(jsx?|mjs|html|css|json)$/.test(file)) continue;
  const source = await readFile(file, 'utf8');
  if (source.includes('window.kisanHarness') || source.includes('OPENAI_API_KEY') || source.includes('ANTHROPIC_API_KEY')) throw new Error(`browser secret or Electron bridge found: ${file}`);
}
console.log('browser standalone boundary: PASS');
