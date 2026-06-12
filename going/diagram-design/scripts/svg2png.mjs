#!/usr/bin/env node
// svg2png.mjs — render a diagram-design SVG to PNG.
//
// Zero-install: vendored resvg-wasm + OFL fonts, no package manager, no network
// for skill-generated diagrams. Runs unchanged under node / bun / deno.
//
//   node scripts/svg2png.mjs <input.svg> <output.png> [width]
//
// Font resolution ladder (see docs/svg2png-font-pipeline.md):
//   T1 vendored fonts → T2 disk cache → T3 system fonts → T4 Google Fonts
// Every degraded resolution is reported on stderr — never a silent drop.

import { initWasm, Resvg } from './resvg.mjs';
import { readFile, writeFile, readdir, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const HERE = path.dirname(new URL(import.meta.url).pathname);
const FONT_DIR = path.join(HERE, 'fonts');
const CACHE_DIR = path.join(os.homedir(), '.cache', 'diagram-fonts');
const DEFAULT_WIDTH = 2160;
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

// Broad-coverage safety net for CJK glyph fallback. Used in place, never cached
// or redistributed (system faces are not OFL).
const CJK_NET = {
  darwin: [
    '/System/Library/Fonts/PingFang.ttc',
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/STHeiti Light.ttc',
  ],
  linux: [
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
  ],
  win32: ['C:\\Windows\\Fonts\\msyh.ttc', 'C:\\Windows\\Fonts\\simsun.ttc'],
}[process.platform] ?? [];

const norm = (s) => s.toLowerCase().replace(/['"]/g, '').replace(/[\s_-]+/g, '');
const log = (msg) => process.stderr.write(`[fonts] ${msg}\n`);

// ---------- scanner ----------

function scan(svg) {
  // name -> { name, axes: css2 axis spec from @import (or null), weights: Set }
  const specs = new Map();

  // 1. Google Fonts @import URLs are the authoritative family+weight declaration.
  //    XML-unescape first: SVG writes & as &amp;.
  const css = svg.replace(/&amp;/g, '&');
  for (const m of css.matchAll(/fonts\.googleapis\.com\/css2\?([^'")\s]+)/g)) {
    for (const fam of new URLSearchParams(m[1]).getAll('family')) {
      const [rawName, axes] = fam.split(':');
      const name = rawName.replace(/\+/g, ' ').trim();
      specs.set(norm(name), { name, axes: axes ?? null, weights: new Set() });
    }
  }

  // 2. Attribute sweep — union in families the @import does not cover.
  //    Only the first family of each stack carries intent; the rest are fallbacks.
  // 400 is always requested: text without a font-weight attribute renders at 400.
  const weights = new Set([
    '400',
    ...[...svg.matchAll(/font-weight="(\d+)"/g)].map((m) => m[1]),
  ]);
  for (const m of svg.matchAll(/font-family="([^"]+)"/g)) {
    const first = m[1].split(',')[0].trim().replace(/^['"]|['"]$/g, '');
    const n = norm(first);
    if (!n || GENERIC.has(first.toLowerCase().trim()) || GENERIC.has(n)) continue;
    if (!specs.has(n)) specs.set(n, { name: first, axes: null, weights });
  }

  const hasCJK =
    /[　-ヿ㐀-䶿一-鿿豈-﫿＀-￯]/.test(svg);
  return { specs, hasCJK };
}

// ---------- resolver tiers ----------

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

function matchesFamily(filePath, famNorm) {
  return norm(path.basename(filePath).replace(FONT_EXT, '')).includes(famNorm);
}

async function fetchCss2(famParam) {
  // Legacy UA makes the css2 endpoint serve per-weight static ttf URLs
  // instead of woff2 (which fontdb cannot parse).
  const res = await fetch(`https://fonts.googleapis.com/css2?family=${famParam}`, {
    headers: { 'User-Agent': 'curl/7.0' },
  });
  return res.ok ? res.text() : null;
}

async function googleDownload(spec, famNorm) {
  const base = spec.name.replace(/ /g, '+');
  const axisSpec =
    spec.axes ??
    (spec.weights.size ? `wght@${[...spec.weights].sort().join(';')}` : null);
  const css =
    (axisSpec && (await fetchCss2(`${base}:${axisSpec}`))) ?? (await fetchCss2(base));
  if (!css) throw new Error('css2 request failed');

  const urls = [...css.matchAll(/url\((https:[^)]+\.(?:ttf|otf))\)/g)].map((m) => m[1]);
  if (!urls.length) throw new Error('no ttf/otf sources in css2 response');

  const famCache = path.join(CACHE_DIR, famNorm);
  await mkdir(famCache, { recursive: true });
  return Promise.all(
    urls.map(async (url) => {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`download failed: ${url}`);
      const bytes = new Uint8Array(await res.arrayBuffer());
      // Keep the versioned path segments (/lora/v37/X.ttf) — pinned forever.
      const name = new URL(url).pathname.split('/').slice(-2).join('-');
      await writeFile(path.join(famCache, name), bytes);
      return bytes;
    }),
  );
}

async function resolveFonts({ specs, hasCJK }) {
  const buffers = [];

  // T1: vendored fonts are the skill's own defaults — always loaded.
  const vendorFiles = await listFontFiles(FONT_DIR, 0);
  if (!vendorFiles.length) {
    throw new Error(`vendored fonts missing at ${FONT_DIR} — broken install`);
  }
  for (const f of vendorFiles) buffers.push(await readFile(f));

  for (const [famNorm, spec] of specs) {
    if (vendorFiles.some((f) => matchesFamily(f, famNorm))) {
      log(`${spec.name} ← vendor`);
      continue;
    }

    const famCache = path.join(CACHE_DIR, famNorm);
    const cached = await listFontFiles(famCache, 0);
    if (cached.length) {
      for (const f of cached) buffers.push(await readFile(f));
      log(`${spec.name} ← cache`);
      continue;
    }

    let sysHits = [];
    for (const dir of SYSTEM_FONT_DIRS) {
      sysHits.push(...(await listFontFiles(dir)).filter((f) => matchesFamily(f, famNorm)));
    }
    if (sysHits.length) {
      for (const f of sysHits.slice(0, 6)) buffers.push(await readFile(f));
      log(`${spec.name} ← system (${sysHits.length} file${sysHits.length > 1 ? 's' : ''})`);
      continue;
    }

    try {
      const downloaded = await googleDownload(spec, famNorm);
      buffers.push(...downloaded);
      log(`${spec.name} ← google fonts (${downloaded.length} weights, cached)`);
    } catch (e) {
      log(`WARN: "${spec.name}" unresolved (${e.message}) — falling back to Geist`);
    }
  }

  if (hasCJK) {
    const net = CJK_NET.find((p) => existsSync(p));
    if (net) {
      buffers.push(await readFile(net));
      // Fallback granularity is the whole text chunk: a mixed CJK/Latin label
      // renders entirely in this font, not just its CJK characters.
      log(`CJK safety net ← ${path.basename(net)} (mixed-script labels render wholly in it)`);
    } else {
      log('WARN: CJK text present but no CJK font found — glyphs will be missing');
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
const fontBuffers = await resolveFonts(scan(svg));

const resvg = new Resvg(svg, {
  fitTo: { mode: 'width', value: Number(widthArg) || DEFAULT_WIDTH },
  font: {
    fontBuffers,
    loadSystemFonts: false,
    defaultFontFamily: 'Geist',
    serifFamily: 'Instrument Serif',
    sansSerifFamily: 'Geist',
    monospaceFamily: 'Geist Mono',
  },
});
const png = resvg.render().asPng();
await writeFile(output, png);
console.log(`${output} (${(png.length / 1024).toFixed(0)}KB)`);
