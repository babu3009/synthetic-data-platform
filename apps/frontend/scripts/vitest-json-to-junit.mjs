#!/usr/bin/env node
/*
  Transform Vitest JSON reporter output (vitest-report.json) into a basic JUnit XML (junit.xml)
  Location: apps/frontend/scripts/

  Usage:
    node apps/frontend/scripts/vitest-json-to-junit.mjs

  Output:
    junit.xml in current working directory (apps/frontend)

  Notes:
    - Minimal schema, enough for most CI analytics tools
    - Aggregates all tests into a single <testsuite name="vitest">
*/
/* global process */
import fs from 'fs'
import path from 'path'

const reportPath = path.resolve('vitest-report.json')
const outputPath = path.resolve('junit.xml')

if (!fs.existsSync(reportPath)) {
  console.error('[junit] vitest-report.json not found, skipping transform')
  process.exit(0)
}

// Read file and tolerate trailing non-JSON output (e.g., coverage text appended to stdout)
const raw = fs.readFileSync(reportPath, 'utf8')
function extractFirstJsonObject(str) {
  const start = str.indexOf('{')
  if (start === -1) return null
  let depth = 0
  let inStr = false
  let esc = false
  for (let i = start; i < str.length; i++) {
    const ch = str[i]
    if (inStr) {
      if (esc) {
        esc = false
      } else if (ch === '\\') {
        esc = true
      } else if (ch === '"') {
        inStr = false
      }
      continue
    }
    if (ch === '"') {
      inStr = true
      continue
    }
    if (ch === '{') depth++
    if (ch === '}') {
      depth--
      if (depth === 0) {
        return str.slice(start, i + 1)
      }
    }
  }
  return null
}

let json
let parsed = null
try {
  parsed = JSON.parse(raw)
} catch {
  const firstObj = extractFirstJsonObject(raw)
  if (firstObj) {
    try {
      parsed = JSON.parse(firstObj)
    } catch (e2) {
      console.error('[junit] Failed to parse extracted JSON:', e2.message)
    }
  }
}
if (!parsed) {
  console.error('[junit] Failed to parse vitest-report.json: trailing output present and extraction failed')
  process.exit(1)
}
json = parsed

const testResults = json.testResults || []
let totalTests = 0
let totalFailures = 0
const casesXml = []

for (const file of testResults) {
  const filePath = file.name || file.file || 'unknown'
  for (const t of file.assertionResults || []) {
    totalTests++
    const status = t.status
    const title = t.fullName || t.title || 'unnamed'
    const classname = filePath.replace(/\\/g, '/').replace(/^.*apps\/frontend\//, '')
    const safeTitle = title.replace(/&/g, '&amp;').replace(/</g, '&lt;')
    if (status === 'failed') {
      totalFailures++
      const failureMsg = (t.failureMessages || []).join('\n').replace(/&/g, '&amp;').replace(/</g, '&lt;')
      casesXml.push(`    <testcase classname="${classname}" name="${safeTitle}" time="0"><failure message="failure">${failureMsg}</failure></testcase>`)      
    } else {
      casesXml.push(`    <testcase classname="${classname}" name="${safeTitle}" time="0" />`)
    }
  }
}

const suiteAttrs = `name="vitest" tests="${totalTests}" failures="${totalFailures}" time="0"`
const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<testsuites>\n  <testsuite ${suiteAttrs}>\n${casesXml.join('\n')}\n  </testsuite>\n</testsuites>\n`

fs.writeFileSync(outputPath, xml, 'utf8')
console.log(`[junit] Wrote ${outputPath} (tests=${totalTests}, failures=${totalFailures})`)