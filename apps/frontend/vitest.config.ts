import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/tests/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      lines: 80,
      functions: 80,
      branches: 70,
      statements: 80,
      exclude: [
        'src/tests/**',
        'src/**/*.d.ts'
      ]
    }
  },
})