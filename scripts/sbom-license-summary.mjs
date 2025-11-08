#!/usr/bin/env node
/*
  Parse one or more SPDX JSON SBOM files and produce a license summary.
  Usage:
    node scripts/sbom-license-summary.mjs --out sbom-licenses.md sbom1.spdx.json sbom2.spdx.json
*/
import fs from 'fs'
import path from 'path'

function readJson(p) {
  try {
    return JSON.parse(fs.readFileSync(p, 'utf-8'))
  } catch (e) {
    return null
  }
}

function collectLicenses(spdx) {
  const counts = new Map()
  const pkgs = spdx?.packages || []
  for (const p of pkgs) {
    const candidates = []
    if (p.licenseConcluded && typeof p.licenseConcluded === 'string') candidates.push(p.licenseConcluded)
    if (p.licenseDeclared && typeof p.licenseDeclared === 'string') candidates.push(p.licenseDeclared)
    // SPDX expressions may include AND/OR; split on whitespace and operators to approximate
    for (const c of candidates) {
      const parts = c.split(/\s+|\(|\)|AND|OR|WITH|\+/i).map(s => s.trim()).filter(Boolean)
      for (const part of parts) {
        const key = part.toUpperCase()
        counts.set(key, (counts.get(key) || 0) + 1)
      }
    }
  }
  return counts
}

function main() {
  const args = process.argv.slice(2)
  let outIdx = args.indexOf('--out')
  let outPath = outIdx !== -1 ? args[outIdx + 1] : 'sbom-license-summary.md'
  const files = args.filter(a => !a.startsWith('--') && !a.endsWith('.md'))
  const summaries = []
  const grand = new Map()
  for (const f of files) {
    const spdx = readJson(f)
    if (!spdx) continue
    const counts = collectLicenses(spdx)
    // merge to grand
    for (const [k, v] of counts) grand.set(k, (grand.get(k) || 0) + v)
    summaries.push({ file: f, counts })
  }
  let md = []
  md.push('# License Summary from SBOMs')
  md.push('')
  const ts = new Date().toISOString()
  md.push(`Generated: ${ts}`)
  md.push('')
  function topN(map, n = 15) {
    return [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, n)
  }
  if (summaries.length > 1) {
    md.push('## Aggregate (all SBOMs)')
    const agg = topN(grand)
    if (agg.length) {
      for (const [lic, cnt] of agg) md.push(`- ${lic}: ${cnt}`)
    } else {
      md.push('_No licenses found_')
    }
    md.push('')
  }
  for (const s of summaries) {
    md.push(`## ${path.basename(s.file)}`)
    const t = topN(s.counts)
    if (t.length) {
      for (const [lic, cnt] of t) md.push(`- ${lic}: ${cnt}`)
    } else {
      md.push('_No licenses found_')
    }
    md.push('')
  }
  fs.writeFileSync(outPath, md.join('\n'))
  console.log(`[sbom] license summary written to ${outPath}`)
}

main()
