#!/usr/bin/env node
/*
  Placeholder performance script.
  Simulates collecting latency metrics; replace with real load/perf tooling later (e.g., k6, Locust, Artillery).
  Outputs performance-results.json.
*/
/* global process */
import fs from 'fs'

function simulateMetric(name) {
  // deterministic pseudo-metric for placeholder
  return {
    name,
    p50_ms: 40 + Math.random() * 10,
    p95_ms: 80 + Math.random() * 20,
    p99_ms: 100 + Math.random() * 30,
    samples: 100
  }
}

const metrics = [
  simulateMetric('frontend_render'),
  simulateMetric('api_list_entities'),
  simulateMetric('api_create_entity')
]

const report = {
  timestamp: new Date().toISOString(),
  environment: process.env.PERF_ENV || 'placeholder',
  metrics
}

fs.writeFileSync('performance-results.json', JSON.stringify(report, null, 2))
console.log('[perf] performance-results.json written')