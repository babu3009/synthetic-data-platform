#!/usr/bin/env node
/*
  Generate a flakiness snapshot from vitest-report.json.
  Output: flakiness-trend.json (single run snapshot) with timestamp, flakyCount, tests array.
*/
/* global process */
import fs from 'fs'
const reportPath = 'vitest-report.json'
if (!fs.existsSync(reportPath)) {
  console.log('[flakiness-trend] vitest-report.json not found, skipping')
  process.exit(0)
}
let data
try { data = JSON.parse(fs.readFileSync(reportPath,'utf8')) } catch (e) {
  console.log('[flakiness-trend] invalid JSON, skipping:', e.message)
  process.exit(0)
}
let flakyCount = 0
const tests = []
for (const file of data.testResults || []) {
  for (const t of file.assertionResults || []) {
    const retry = t.retry || 0
    const status = t.status
    if (retry > 0 || status === 'failed') {
      flakyCount++
      tests.push({ title: t.fullName || t.title, status, retry })
    }
  }
}
const snapshot = {
  timestamp: new Date().toISOString(),
  flakyCount,
  tests
}
fs.writeFileSync('flakiness-trend.json', JSON.stringify(snapshot, null, 2))
console.log(`[flakiness-trend] snapshot written (flakyCount=${flakyCount})`)