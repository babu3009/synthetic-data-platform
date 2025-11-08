#!/usr/bin/env node
/**
 * Aggregate SLO-ish metrics from existing CI artifacts.
 * Inputs (optional if missing):
 *  - frontend coverage summary JSON
 *  - backend coverage XML
 *  - flakiness trend JSON
 *  - test-duration-trend.json
 *  - cache-efficiency.json
 *  - dependency-freshness.json
 *  - trivy-results.sarif (security)
 *  - image-sizes.json
 * Output: slo-dashboard.json + slo-dashboard.md
 */
import fs from 'fs';
import path from 'path';

function readJSON(p){
  try { return JSON.parse(fs.readFileSync(p,'utf8')); } catch { return null; }
}
function readText(p){
  try { return fs.readFileSync(p,'utf8'); } catch { return null; }
}
function parseBackendCoverage(xml){
  if(!xml) return null;
  try {
    // Simple attribute extraction from cobertura root element: <coverage line-rate="0.89" branch-rate="0.77" ...>
    const mLine = xml.match(/line-rate\s*=\s*"([0-9.]+)"/);
    const mBranch = xml.match(/branch-rate\s*=\s*"([0-9.]+)"/);
    const line = mLine ? Number(mLine[1]) * 100 : null;
    const branch = mBranch ? Number(mBranch[1]) * 100 : null;
    return { lines: isFinite(line) ? line : null, branches: isFinite(branch) ? branch : null };
  } catch { return null; }
}

// Discover artifact paths heuristically
const args = process.argv.slice(2);
let outJson = 'slo-dashboard.json';
let outMd = 'slo-dashboard.md';
for (let i=0;i<args.length;i++) {
  if(args[i] === '--out-json') outJson = args[++i];
  if(args[i] === '--out-md') outMd = args[++i];
}

const artifactsRoot = path.resolve('artifacts');
function find(...segments){ return path.join(...segments); }

const frontendCoverage = readJSON(find(artifactsRoot,'frontend','coverage','coverage-summary.json'));
const backendCoverageXml = readText(find(artifactsRoot,'backend','coverage.xml'));
const backendCoverage = parseBackendCoverage(backendCoverageXml);
const flakinessTrend = readJSON(find(artifactsRoot,'flaky','flakiness-trend.json'));
const durationTrend = readJSON(find(artifactsRoot,'duration','test-duration-trend.json'));
const cacheEfficiency = readJSON(find(artifactsRoot,'cache','cache-efficiency.json'));
const depFreshness = readJSON(find(artifactsRoot,'freshness','dependency-freshness.json'));
let trivySarif = readJSON(find(artifactsRoot,'security','trivy-results.sarif'));
const imageSizes = readJSON(find(artifactsRoot,'images','image-sizes.json'));

function summarizeSecurity(sarif){
  if(!sarif) return { critical:0, high:0 };
  try {
    const results = sarif.runs?.flatMap(r=>r.results||[])||[];
    return {
      critical: results.filter(r=>r.level==='error').length,
      high: results.filter(r=>r.level==='warning').length,
    };
  } catch { return { critical:0, high:0 }; }
}

const securitySummary = summarizeSecurity(trivySarif);
const now = new Date().toISOString();

const out = {
  generatedAt: now,
  coverage: {
    frontend: frontendCoverage?.total ? {
      lines: frontendCoverage.total.lines?.pct ?? null,
      statements: frontendCoverage.total.statements?.pct ?? null,
      functions: frontendCoverage.total.functions?.pct ?? null,
      branches: frontendCoverage.total.branches?.pct ?? null,
    } : null,
    backend: backendCoverage || null,
  },
  flakiness: flakinessTrend ? {
    flakyCount: flakinessTrend.flakyCount ?? null,
    rate: flakinessTrend.rate ?? null,
  } : null,
  testDuration: durationTrend ? {
    maxMs: durationTrend.topOverall?.[0]?.durationMs ?? null,
    slowTests: durationTrend.topOverall?.length ?? 0,
  } : null,
  cache: cacheEfficiency || null,
  dependencies: depFreshness ? {
    frontendOutdated: depFreshness.frontend?.count ?? null,
    backendOutdated: depFreshness.backend?.count ?? null,
  } : null,
  security: securitySummary,
  images: imageSizes || null,
};

fs.writeFileSync(outJson, JSON.stringify(out,null,2),'utf8');

function fmt(n){ return (n==null||Number.isNaN(n))? 'n/a' : (typeof n==='number'? n.toFixed(2): String(n)); }

let md = [];
md.push(`# SLO Dashboard`);
md.push(`Generated: ${now}`);
md.push('');
md.push('## Coverage');
md.push(`- Frontend lines: ${fmt(out.coverage.frontend?.lines)}`);
md.push(`- Backend lines: ${fmt(out.coverage.backend?.lines)}`);
md.push('');
md.push('## Flakiness');
md.push(`- Flaky tests: ${fmt(out.flakiness?.flakyCount)}`);
md.push(`- Rate: ${fmt(out.flakiness?.rate)}`);
md.push('');
md.push('## Test Duration');
md.push(`- Max duration ms: ${fmt(out.testDuration?.maxMs)}`);
md.push(`- Slow tests listed: ${fmt(out.testDuration?.slowTests)}`);
md.push('');
md.push('## Cache Efficiency');
md.push(`- Frontend cache: ${out.cache?.frontend?.cacheHit ?? 'n/a'}`);
md.push(`- Backend cache: ${out.cache?.backend?.cacheHit ?? 'n/a'}`);
md.push('');
md.push('## Dependency Freshness');
md.push(`- Frontend outdated: ${fmt(out.dependencies?.frontendOutdated)}`);
md.push(`- Backend outdated: ${fmt(out.dependencies?.backendOutdated)}`);
md.push('');
md.push('## Security');
md.push(`- Critical vulns: ${out.security.critical}`);
md.push(`- High vulns: ${out.security.high}`);
md.push('');
if(out.images){
  md.push('## Image Sizes');
  md.push(`- Backend: ${out.images.backend?.sizeHuman ?? 'n/a'}`);
  md.push(`- Frontend: ${out.images.frontend?.sizeHuman ?? 'n/a'}`);
}
fs.writeFileSync(outMd, md.join('\n'),'utf8');
console.log(md.slice(0,30).join('\n'));
