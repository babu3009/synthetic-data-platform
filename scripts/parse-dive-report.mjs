#!/usr/bin/env node
/*
  Parse Dive JSON reports and produce a concise markdown summary.
  Usage:
    node scripts/parse-dive-report.mjs --backend dive-backend.json --frontend dive-frontend.json --out dive-summary.md
*/
import fs from 'fs'

function read(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf-8')) } catch { return null }
}

function summarize(img, label) {
  if (!img) return { label, efficiency: null, layers: [] }
  const efficiency = img?.image?.efficiency ?? null
  const layers = (img?.image?.layers || []).map(l => ({
    sizeBytes: l?.sizeBytes || 0,
    wastedBytes: l?.wastedBytes || 0,
    command: l?.command || ''
  }))
  layers.sort((a,b) => b.sizeBytes - a.sizeBytes)
  return { label, efficiency, layers: layers.slice(0, 5) }
}

function human(n) {
  let x = Number(n || 0)
  for (const u of ['B','KB','MB','GB','TB']) {
    if (x < 1024 || u === 'TB') return `${x.toFixed(1)} ${u}`
    x /= 1024
  }
}

const args = process.argv.slice(2)
const getArg = (k, d=null) => {
  const i = args.indexOf(k); return i !== -1 ? args[i+1] : d
}
const outPath = getArg('--out', 'dive-summary.md')
const backend = read(getArg('--backend'))
const frontend = read(getArg('--frontend'))

const sections = []
for (const s of [ summarize(backend, 'Backend'), summarize(frontend, 'Frontend') ]) {
  sections.push(`## ${s.label}`)
  if (s.efficiency != null) sections.push(`Efficiency: ${(s.efficiency * 100).toFixed(1)}%`)
  if (!s.layers.length) { sections.push('_No layer data_'); sections.push(''); continue }
  sections.push('Top 5 largest layers:')
  for (const l of s.layers) {
    sections.push(`- ${human(l.sizeBytes)} (wasted: ${human(l.wastedBytes)}) — ${l.command?.slice(0, 80)}`)
  }
  sections.push('')
}

const md = [ '# Image Layer Analysis', '', ...sections ]
fs.writeFileSync(outPath, md.join('\n'))
console.log(`[dive] Wrote ${outPath}`)
