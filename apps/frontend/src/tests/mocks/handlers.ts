import { rest } from 'msw'

// Basic handlers to prevent real network calls; expand per API needs
export const handlers = [
  // Explicit health check handler to silence unhandled request warnings
  rest.get('http://localhost:8000/health', (_req, res, ctx) => {
    return res(ctx.status(200), ctx.json({ status: 'ok' }))
  }),
  // Relative path variant (in case code calls just /health without origin)
  rest.get('/health', (_req, res, ctx) => {
    return res(ctx.status(200), ctx.json({ status: 'ok' }))
  }),
  rest.get('/api/:path*', (_req, res, ctx) => res(ctx.status(200), ctx.json({}))),
  rest.post('/api/:path*', (_req, res, ctx) => res(ctx.status(200), ctx.json({}))),
]
