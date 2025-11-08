#!/usr/bin/env node
/*
  Simple flakiness heuristic for Vitest JSON output.
  Usage (CI): run vitest with --reporter=json > vitest-report.json then invoke this script.

  Heuristic:
    - Count tests with retries > 0 OR status == 'fail' then later overall exit 0 (indicates pass-after-retry when retry enabled).
    - If count >= threshold (default 2), emit GitHub Actions warning annotation.

  Environment variables:
    FLAKINESS_THRESHOLD (number, default 2)
    FLAKINESS_CHECK (set to '0' to disable)
*/
/* global process */
import fs from 'fs'

const disabled = process.env.FLAKINESS_CHECK === '0'
if (disabled) {
  console.log('[flakiness] check disabled via FLAKINESS_CHECK=0')
  process.exit(0)
}

const threshold = Number(process.env.FLAKINESS_THRESHOLD || 2)
const reportPath = 'vitest-report.json'
if (!fs.existsSync(reportPath)) {
  console.log('[flakiness] report file not found, skipping')
  process.exit(0)
}

let json
try {
  const raw = fs.readFileSync(reportPath, 'utf8')
  json = JSON.parse(raw)
} catch (e) {
  console.log('[flakiness] failed to parse vitest-report.json:', e.message)
  process.exit(0)
}

// Vitest JSON structure: { testResults: [ { assertionResults: [...], ... } ] }
let flakyCount = 0
const details = []
for (const file of json.testResults || []) {
  for (const t of file.assertionResults || []) {
    const retry = t.retry || 0
    const status = t.status
    if (retry > 0 || status === 'failed') {
      flakyCount++
      details.push(`${t.fullName || t.title} (status=${status}, retry=${retry})`)
    }
  }
}

if (flakyCount >= threshold) {
  const msg = `Flakiness detected: ${flakyCount} test(s) exceeded heuristic (threshold=${threshold}).\n${details.slice(0,10).join('\n')}`
  // GitHub Actions warning annotation
  console.log(`::warning file=apps/frontend/scripts/check-flakiness.mjs::${msg}`)
} else {
  console.log(`[flakiness] No significant flakiness (count=${flakyCount}, threshold=${threshold})`)
}