#!/usr/bin/env node
/*
  Merge dependency freshness outputs from frontend (pnpm outdated --json)
  and backend (pip list --outdated --format=json under Poetry) into:
    - dependency-freshness.json
    - dependency-freshness.md

  Usage:
    node scripts/merge-dependency-freshness.mjs \
      --frontend outdated-frontend.json \
      --backend outdated-backend.json
*/
/* global process */
import fs from 'fs'
import path from 'path'

function parseArgs(argv) {
  const args = { frontend: 'outdated-frontend.json', backend: 'outdated-backend.json' }
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--frontend') args.frontend = argv[++i]
    if (argv[i] === '--backend') args.backend = argv[++i]
  }
  return args
}

function readJsonSafe(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')) } catch { return [] }
}

function normFrontend(item) {
  // pnpm outdated json typically has: name, current, wanted, latest, type
  return {
    name: item?.name ?? null,
    current: item?.current ?? null,
    wanted: item?.wanted ?? null,
    latest: item?.latest ?? null,
    type: item?.type ?? null,
  }
}

function normBackend(item) {
  // pip list --outdated --format=json has: name, version, latest_version, latest_filetype
  return {
    name: item?.name ?? null,
    current: item?.version ?? null,
    latest: item?.latest_version ?? null,
    filetype: item?.latest_filetype ?? null,
  }
}

function listMd(pkgs) {
  if (!pkgs?.length) return '_None_'
  const lines = pkgs
    .slice()
    .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    .slice(0, 20)
    .map(p => `- ${p.name}: ${p.current} → ${p.latest}`)
  return lines.join('\n')
}

const args = parseArgs(process.argv.slice(2))
const feRaw = readJsonSafe(args.frontend)
const beRaw = readJsonSafe(args.backend)
const fe = Array.isArray(feRaw) ? feRaw.map(normFrontend) : []
const be = Array.isArray(beRaw) ? beRaw.map(normBackend) : []

const out = {
  generatedAt: new Date().toISOString(),
  frontend: { manager: 'pnpm', count: fe.length, packages: fe },
  backend: { manager: 'pip', count: be.length, packages: be },
}

fs.writeFileSync(
  path.resolve('dependency-freshness.json'),
  JSON.stringify(out, null, 2),
  'utf8'
)

const md = []
md.push('# Dependency Freshness Report')
md.push('')
md.push(`Generated: ${out.generatedAt}`)
md.push('')
md.push('## Frontend (pnpm)')
md.push(`Outdated packages: ${out.frontend.count}`)
md.push(listMd(out.frontend.packages))
md.push('')
md.push('## Backend (pip)')
md.push(`Outdated packages: ${out.backend.count}`)
md.push(listMd(out.backend.packages))

fs.writeFileSync(path.resolve('dependency-freshness.md'), md.join('\n'), 'utf8')

console.log('[freshness] Wrote dependency-freshness.json and dependency-freshness.md')
