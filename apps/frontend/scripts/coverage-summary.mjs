#!/usr/bin/env node
/*
  Emit a Markdown coverage summary to stdout based on coverage/coverage-summary.json.
  Intended usage in GitHub Actions:
    node apps/frontend/scripts/coverage-summary.mjs >> $GITHUB_STEP_SUMMARY
*/
/* global process */
import fs from 'fs'
import path from 'path'

const summaryPath = path.resolve('coverage', 'coverage-summary.json')
if (!fs.existsSync(summaryPath)) {
  console.log('## Frontend coverage summary')
  console.log('Coverage summary file not found. Was coverage enabled?')
  process.exit(0)
}

let data
try {
  data = JSON.parse(fs.readFileSync(summaryPath, 'utf8'))
} catch (e) {
  console.log('## Frontend coverage summary')
  console.log('Failed to parse coverage-summary.json:', e.message)
  process.exit(0)
}

const total = data.total || {}
const section = (k) => (total[k] && typeof total[k].pct === 'number' ? `${total[k].pct.toFixed(2)}%` : 'n/a')

console.log('## Frontend coverage summary')
console.log('')
console.log(`- Lines: ${section('lines')}`)
console.log(`- Statements: ${section('statements')}`)
console.log(`- Functions: ${section('functions')}`)
console.log(`- Branches: ${section('branches')}`)

// Top 5 least-covered files by lines
const fileEntries = Object.entries(data).filter(([k]) => k !== 'total')
  .map(([file, metrics]) => ({ file, pct: (metrics.lines && metrics.lines.pct) || 0 }))
  .sort((a, b) => a.pct - b.pct)
  .slice(0, 5)

if (fileEntries.length) {
  console.log('')
  console.log('### Least-covered files (by lines)')
  for (const { file, pct } of fileEntries) {
    console.log(`- ${file}: ${pct.toFixed(2)}%`)
  }
}