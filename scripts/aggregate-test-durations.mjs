#!/usr/bin/env node
/*
  Aggregate test durations from frontend (Vitest JSON) and backend (Pytest JUnit)
  Usage:
    node scripts/aggregate-test-durations.mjs \
      --vitest frontend-artifacts/vitest-report.json \
      --pytest backend-artifacts/pytest-junit.xml

  Outputs:
    - test-duration-trend.json (machine-readable snapshot)
    - test-duration-trend.md (human-readable summary)
*/
/* global process */
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

function parseArgs(argv) {
  const args = { vitest: null, pytest: null }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a === '--vitest') args.vitest = argv[++i]
    if (a === '--pytest') args.pytest = argv[++i]
  }
  return args
}

function readJsonSafe(p) {
  try {
    const raw = fs.readFileSync(p, 'utf8')
    // In case stdout had extra noise, try to extract first JSON object
    try { return JSON.parse(raw) } catch {
      const start = raw.indexOf('{')
      if (start !== -1) {
        let depth = 0, inStr = false, esc = false
        for (let i = start; i < raw.length; i++) {
          const ch = raw[i]
          if (inStr) {
            if (esc) esc = false
            else if (ch === '\\') esc = true
            else if (ch === '"') inStr = false
          } else {
            if (ch === '"') inStr = true
            else if (ch === '{') depth++
            else if (ch === '}') { depth--; if (depth === 0) return JSON.parse(raw.slice(start, i+1)) }
          }
        }
      }
    }
  } catch {}
  return null
}

function parseVitestDurations(json) {
  const out = []
  if (!json) return out
  const results = json.testResults || []
  for (const file of results) {
    const filePath = file.name || file.file || 'unknown'
    const assertions = file.assertionResults || []
    for (const t of assertions) {
      const title = t.fullName || t.title || 'unnamed'
      const duration = typeof t.duration === 'number' ? t.duration : 0
      out.push({ source: 'frontend', name: title, file: filePath, durationMs: duration })
    }
  }
  return out
}

function parsePytestJunit(xmlText) {
  const out = []
  if (!xmlText) return out
  // Simple regex-based extraction to avoid extra deps
  const testcaseRe = /<testcase\b[^>]*>/g
  let m
  while ((m = testcaseRe.exec(xmlText))) {
    const tag = m[0]
    const name = /name="([^"]+)"/.exec(tag)?.[1] || 'unnamed'
    const classname = /classname="([^"]+)"/.exec(tag)?.[1] || 'unknown'
    const timeStr = /time="([^"]+)"/.exec(tag)?.[1] || '0'
    const seconds = parseFloat(timeStr)
    const durationMs = isNaN(seconds) ? 0 : Math.round(seconds * 1000)
    out.push({ source: 'backend', name, classname, durationMs })
  }
  return out
}

function topN(arr, n) {
  return [...arr].sort((a,b) => b.durationMs - a.durationMs).slice(0, n)
}

const args = parseArgs(process.argv.slice(2))
if (!args.vitest || !args.pytest) {
  console.error('Usage: --vitest <vitest-report.json> --pytest <pytest-junit.xml>')
  process.exit(1)
}

const vitestJson = readJsonSafe(args.vitest)
const pytestXml = fs.existsSync(args.pytest) ? fs.readFileSync(args.pytest, 'utf8') : ''

const fe = parseVitestDurations(vitestJson)
const be = parsePytestJunit(pytestXml)

const out = {
  generatedAt: new Date().toISOString(),
  frontend: { totalTests: fe.length, topSlow: topN(fe, 10) },
  backend: { totalTests: be.length, topSlow: topN(be, 10) },
  topOverall: topN([...fe, ...be], 10)
}

const jsonPath = path.resolve('test-duration-trend.json')
fs.writeFileSync(jsonPath, JSON.stringify(out, null, 2), 'utf8')

function mdList(items, mapFn) {
  if (!items.length) return '_None_'
  return items.map(mapFn).join('\n')
}

const md = []
md.push('# Test Duration Summary')
md.push('')
md.push(`Generated: ${out.generatedAt}`)
md.push('')
md.push('## Frontend (Vitest): Top Slow Tests')
md.push(mdList(out.frontend.topSlow, t => `- ${t.durationMs} ms — ${t.name} (${t.file})`))
md.push('')
md.push('## Backend (Pytest): Top Slow Tests')
md.push(mdList(out.backend.topSlow, t => `- ${t.durationMs} ms — ${t.name} (${t.classname})`))
md.push('')
md.push('## Overall: Top Slow Tests')
md.push(mdList(out.topOverall, t => `- ${t.durationMs} ms — ${t.name} (${t.source === 'frontend' ? t.file : t.classname})`))

const mdPath = path.resolve('test-duration-trend.md')
fs.writeFileSync(mdPath, md.join('\n'), 'utf8')

console.log(`[duration] Wrote ${jsonPath} and ${mdPath}`)
