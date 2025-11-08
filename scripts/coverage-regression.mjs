#!/usr/bin/env node
// Compare frontend coverage against a previous snapshot and print a markdown summary
// Usage: node scripts/coverage-regression.mjs --current apps/frontend/coverage/coverage-summary.json --previous prev-coverage.json --out coverage-regression.md

import fs from 'node:fs';
import path from 'node:path';

function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf-8')); } catch { return null; }
}

function pct(v) { return v == null ? null : Number(v); }

function extractTotals(obj) {
  const t = obj?.total || {};
  return {
    lines: pct(t.lines?.pct),
    statements: pct(t.statements?.pct),
    functions: pct(t.functions?.pct),
    branches: pct(t.branches?.pct),
  };
}

function formatDelta(a, b) {
  if (a == null || b == null) return 'n/a';
  const d = (a - b);
  const sign = d > 0 ? '+' : '';
  return `${sign}${d.toFixed(2)}%`;
}

function run(args) {
  const current = args['--current'] || 'apps/frontend/coverage/coverage-summary.json';
  const previous = args['--previous'] || '';
  const out = args['--out'] || 'coverage-regression.md';
  const cur = readJson(current);
  const prev = previous ? readJson(previous) : null;
  if (!cur) {
    console.error('Current coverage summary not found:', current);
    process.exit(0);
  }
  const c = extractTotals(cur);
  const p = prev ? extractTotals(prev) : null;

  const lines = [];
  lines.push('# Coverage Regression Summary');
  lines.push('');
  lines.push(`Current: lines ${c.lines ?? 'n/a'}%, statements ${c.statements ?? 'n/a'}%, functions ${c.functions ?? 'n/a'}%, branches ${c.branches ?? 'n/a'}%`);
  if (p) {
    lines.push(`Delta: lines ${formatDelta(c.lines, p.lines)}, statements ${formatDelta(c.statements, p.statements)}, functions ${formatDelta(c.functions, p.functions)}, branches ${formatDelta(c.branches, p.branches)}`);
  } else {
    lines.push('Delta: previous snapshot not available.');
  }

  fs.writeFileSync(out, lines.join('\n'), 'utf-8');
  console.log(`Wrote ${out}`);
}

const argv = process.argv.slice(2);
const args = {};
for (let i = 0; i < argv.length; i += 2) {
  args[argv[i]] = argv[i + 1];
}
run(args);
