#!/usr/bin/env node
// svg2png.mjs — render a logo SVG to PNG using vendored resvg-wasm.
//
// Zero-install: vendored resvg-wasm binary + bindings, no package manager, no
// network. Runs unchanged under node / bun / deno.
//
//   node scripts/svg2png.mjs <input.svg> <output.png> [width]
//
// Fonts: logos are either pure vector (icons), have their text converted to
// <path>, or use widely-available system fonts (Helvetica, Arial, Georgia…).
// No fonts are vendored. If the SVG references a <text> font family, this
// script scans the OS font directories and feeds the matching face to resvg
// as a buffer — resvg-wasm's own loadSystemFonts does not resolve families by
// name in this build, so the bytes must be supplied explicitly. An unresolved
// family is reported on stderr, never silently dropped.

import { initWasm, Resvg } from './resvg.mjs';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const HERE = path.dirname(new URL(import.meta.url).pathname);
const DEFAULT_WIDTH = 512;
const FONT_EXT = /\.(ttf|otf|ttc)$/i;

const GENERIC = new Set([
  'serif', 'sans-serif', 'monospace', 'cursive', 'fantasy', 'math', 'emoji',
  'system-ui', 'ui-monospace', 'ui-serif', 'ui-sans-serif', 'ui-rounded',
  '-apple-system', 'blinkmacsystemfont',
]);

const SYSTEM_FONT_DIRS = {
  darwin: [
    '/System/Library/Fonts', '/System/Library/Fonts/Supplemental',
    '/Library/Fonts', path.join(os.homedir(), 'Library/Fonts'),
  ],
  linux: [
    '/usr/share/fonts', '/usr/local/share/fonts',
    path.join(os.homedir(), '.local/share/fonts'), path.join(os.homedir(), '.fonts'),
  ],
  win32: ['C:\\Windows\\Fonts'],
}[process.platform] ?? [];

const norm = (s) => s.toLowerCase().replace(/['"]/g, '').replace(/[\s_-]+/g, '');
const log = (msg) => process.stderr.write(`[fonts] ${msg}\n`);

// Collect the first (intent-carrying) family of every font-family stack.
function referencedFamilies(svg) {
  const fams = new Map(); // norm -> display name
  for (const m of svg.matchAll(/font-family="([^"]+)"/g)) {
    const first = m[1].split(',')[0].trim().replace(/^['"]|['"]$/g, '');
    const n = norm(first);
    if (!n || GENERIC.has(first.toLowerCase().trim()) || GENERIC.has(n)) continue;
    if (!fams.has(n)) fams.set(n, first);
  }
  return fams;
}

async function listFontFiles(dir, depth = 2) {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory() && depth > 0) out.push(...(await listFontFiles(p, depth - 1)));
    else if (entry.isFile() && FONT_EXT.test(entry.name)) out.push(p);
  }
  return out;
}

const matchesFamily = (filePath, famNorm) =>
  norm(path.basename(filePath).replace(FONT_EXT, '')).includes(famNorm);

async function resolveSystemFonts(svg) {
  const fams = referencedFamilies(svg);
  if (!fams.size) return []; // pure icon / text-as-path — no fonts needed

  const buffers = [];
  for (const [famNorm, name] of fams) {
    let hits = [];
    for (const dir of SYSTEM_FONT_DIRS) {
      hits.push(...(await listFontFiles(dir)).filter((f) => matchesFamily(f, famNorm)));
    }
    if (hits.length) {
      for (const f of hits.slice(0, 4)) buffers.push(await readFile(f));
      log(`${name} ← system (${hits.length} file${hits.length > 1 ? 's' : ''})`);
    } else {
      log(`WARN: "${name}" not found on system — text in this family will not render. ` +
          `Use a common system font (Helvetica/Arial/Georgia) or convert text to <path>.`);
    }
  }
  return buffers;
}

// ---------- main ----------

const [, , input, output, widthArg] = process.argv;
if (!input || !output) {
  console.error('usage: node scripts/svg2png.mjs <input.svg> <output.png> [width]');
  process.exit(1);
}

await initWasm(await readFile(path.join(HERE, 'index_bg.wasm')));
const svg = await readFile(input, 'utf8');
const fontBuffers = await resolveSystemFonts(svg);

const resvg = new Resvg(svg, {
  fitTo: { mode: 'width', value: Number(widthArg) || DEFAULT_WIDTH },
  font: { fontBuffers, loadSystemFonts: false },
});
const png = resvg.render().asPng();
await writeFile(output, png);
console.log(`${output} (${(png.length / 1024).toFixed(0)}KB)`);
