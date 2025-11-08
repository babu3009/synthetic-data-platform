import '@testing-library/jest-dom'
import { server } from './mocks/server'
// Polyfill ResizeObserver for libraries like recharts in JSDOM
class ResizeObserverMock {
		observe() {}
		unobserve() {}
		disconnect() {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverMock }).ResizeObserver = ResizeObserverMock

// Prefer MSW for request handling. If MSW isn't used in a test, ensure fetch/XHR are no-ops to avoid
// accidental external calls from third-party libs. Tests that need network behavior should use MSW
// handlers and override this global behavior as needed.
if (!(globalThis as { fetch?: unknown }).fetch) {
	(globalThis as { fetch?: typeof fetch }).fetch = (async () => new Response('', { status: 200 })) as unknown as typeof fetch
}

if (!(globalThis as { XMLHttpRequest?: unknown }).XMLHttpRequest) {
	// Minimal XHR shim that completes asynchronously with 200; MSW will normally intercept network calls
	class MinimalXHR {
		onload: ((this: MinimalXHR, ev: Event) => void) | null = null
		onerror: ((this: MinimalXHR, ev: Event) => void) | null = null
		onreadystatechange: ((this: MinimalXHR, ev: Event) => void) | null = null
		readyState = 0
		status = 0
		responseText = ''
		response: unknown = ''
		withCredentials = false
		timeout = 0

		open(_method: string, _url: string, _async = true) {
			this.readyState = 1
			this.onreadystatechange && this.onreadystatechange(new Event('readystatechange'))
		}
		setRequestHeader(_name: string, _value: string) {}
		abort() {}
		send(_body?: Document | BodyInit | null) {
			setTimeout(() => {
				this.readyState = 4
				this.status = 200
				this.responseText = ''
				this.response = ''
				this.onreadystatechange && this.onreadystatechange(new Event('readystatechange'))
				this.onload && this.onload(new Event('load'))
			}, 0)
		}
	}
		(globalThis as { XMLHttpRequest?: unknown }).XMLHttpRequest = MinimalXHR as unknown
}

	// Start MSW server for all tests
	declare const beforeAll: (fn: () => void) => void
	declare const afterEach: (fn: () => void) => void
	declare const afterAll: (fn: () => void) => void

	beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
	afterEach(() => server.resetHandlers())
	afterAll(() => server.close())