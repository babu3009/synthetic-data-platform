import '@testing-library/jest-dom'
// Polyfill ResizeObserver for libraries like recharts in JSDOM
class ResizeObserverMock {
	observe() {}
	unobserve() {}
	disconnect() {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverMock }).ResizeObserver = ResizeObserverMock