#!/usr/bin/env node
/**
 * Compute test ordering snapshot and drift between current and previous.
 * Inputs:
 *  --vitest <path to vitest-report.json>
 *  --pytest <path to pytest-junit.xml>
 *  --previous <previous snapshot json> (optional)
 * Outputs:
 *  --out-snapshot <path>
 *  --out-md <path>
 */
import fs from 'fs';

function readJSON(p){ try { return p && fs.existsSync(p) ? JSON.parse(fs.readFileSync(p,'utf8')) : null; } catch { return null; } }
function readText(p){ try { return p && fs.existsSync(p) ? fs.readFileSync(p,'utf8') : null; } catch { return null; } }

const args = process.argv.slice(2);
function arg(name, def){ const i = args.indexOf(name); return i>=0 ? args[i+1] : def; }
const vitestPath = arg('--vitest');
const pytestPath = arg('--pytest');
const prevPath = arg('--previous');
const outSnap = arg('--out-snapshot','test-ordering-snapshot.json');
const outMd = arg('--out-md','test-ordering-drift.md');

// Extract a stable list of test IDs in execution order
function vitestOrder(json){
  if(!json) return [];
  // Some formats have testResults; others nested by suites
  const results = json.testResults || [];
  const ids = [];
  for (const file of results){
    const filePath = file.name || file.testFilePath || file.file || '';
    const assertions = file.assertionResults || [];
    for(const a of assertions){
      const title = Array.isArray(a.ancestorTitles) && a.ancestorTitles.length
        ? `${a.ancestorTitles.join(' > ')} > ${a.title}`
        : a.title;
      ids.push(`${filePath}::${title}`);
    }
  }
  return ids;
}

function pytestOrder(xml){
  if(!xml) return [];
  try {
    // Extract <testcase ...> attributes with a simple regex; robust enough for CI snapshots
    const re = /<testcase\b([^>]*)>/g;
    const attrs = (s,k) => {
      const m = s.match(new RegExp(`${k}\\s*=\\s*"([^"]*)"`));
      return m ? m[1] : '';
    };
    const out = [];
    let m;
    while ((m = re.exec(xml)) !== null) {
      const part = m[1] || '';
      const cls = attrs(part,'classname');
      const name = attrs(part,'name');
      const file = attrs(part,'file');
      if (name) out.push(`${file || cls}::${name}`);
    }
    return out;
  } catch { return []; }
}

const vitestJson = readJSON(vitestPath);
const pytestXml = readText(pytestPath);
const current = {
  vitest: vitestOrder(vitestJson),
  pytest: pytestOrder(pytestXml),
};

function diff(prev, cur){
  const prevArr = prev || [];
  const curArr = cur || [];
  const min = Math.min(prevArr.length, curArr.length);
  let posDiff = 0;
  const moved = [];
  const indexPrev = new Map(prevArr.map((id,idx)=>[id, idx]));
  curArr.forEach((id, idx) => {
    const p = indexPrev.has(id) ? indexPrev.get(id) : null;
    if (p!=null && p !== idx) { posDiff++; if(moved.length<20) moved.push({id, from:p, to:idx}); }
  });
  return { count: posDiff, examples: moved };
}

const previous = readJSON(prevPath) || { vitest: [], pytest: [] };
const snapshot = {
  generatedAt: new Date().toISOString(),
  totals: {
    vitest: current.vitest.length,
    pytest: current.pytest.length,
    total: current.vitest.length + current.pytest.length,
  },
  current,
  previous: { vitest: previous.vitest || [], pytest: previous.pytest || [] },
  drift: {
    vitest: diff(previous.vitest, current.vitest),
    pytest: diff(previous.pytest, current.pytest),
    count: (diff(previous.vitest, current.vitest).count + diff(previous.pytest, current.pytest).count),
  }
};

fs.writeFileSync(outSnap, JSON.stringify(snapshot,null,2),'utf8');

let md = [];
md.push('# Test Ordering Drift');
md.push(`Generated: ${snapshot.generatedAt}`);
md.push('');
md.push(`- Vitest tests: ${snapshot.totals.vitest}`);
md.push(`- Pytest tests: ${snapshot.totals.pytest}`);
md.push(`- Total tests: ${snapshot.totals.total}`);
md.push('');
md.push(`- Reordered (Vitest): ${snapshot.drift.vitest.count}`);
md.push(`- Reordered (Pytest): ${snapshot.drift.pytest.count}`);
md.push(`- Reordered (Total): ${snapshot.drift.count}`);
md.push('');
if (snapshot.drift.vitest.examples.length){
  md.push('Examples (Vitest):');
  for(const ex of snapshot.drift.vitest.examples){ md.push(`- ${ex.id} (${ex.from} -> ${ex.to})`); }
}
if (snapshot.drift.pytest.examples.length){
  md.push('Examples (Pytest):');
  for(const ex of snapshot.drift.pytest.examples){ md.push(`- ${ex.id} (${ex.from} -> ${ex.to})`); }
}
fs.writeFileSync(outMd, md.join('\n'),'utf8');
console.log(md.slice(0,30).join('\n'));
