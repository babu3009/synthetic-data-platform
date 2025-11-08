import '@testing-library/jest-dom'
import { server } from './mocks/server'
import type { ReactNode } from 'react'
import { vi } from 'vitest'
// Silence specific noisy warnings that are expected due to library versions:
// - ReactDOMTestUtils.act deprecation (triggered internally by @testing-library/react v13)
// - React Router future flag advisory messages
const originalWarn = console.warn
const originalError = console.error
console.warn = (...args: unknown[]) => {
	const first = args[0]
	if (typeof first === 'string') {
		if (first.includes('ReactDOMTestUtils.act is deprecated')) return
		if (first.includes('React Router Future Flag Warning')) return
	}
	return originalWarn(...args as [unknown, ...unknown[]])
}
console.error = (...args: unknown[]) => {
	const first = args[0]
	if (typeof first === 'string') {
		if (first.includes('ReactDOMTestUtils.act is deprecated')) return
	}
	return originalError(...args as [unknown, ...unknown[]])
}

// Mock react-transition-group to eliminate asynchronous mount/unmount cycles that trigger
// act() warnings in tests (react-bootstrap relies on these for Modal/Collapse/Fade).
// By rendering children immediately, we keep behavior assertions focused on visual state
// without needing manual act wrapping for transitions.
vi.mock('react-transition-group', () => {
	const Transition = ({ children }: { children: ReactNode }) =>
		(typeof children === 'function' ? ((children as unknown as (s?: boolean) => JSX.Element)(true)) : (children as JSX.Element))
	const CSSTransition = ({ children }: { children: ReactNode }) =>
		(typeof children === 'function' ? ((children as unknown as (s?: boolean) => JSX.Element)(true)) : (children as JSX.Element))
	return { Transition, CSSTransition }
})

vi.mock('react-transition-group/Transition', () => {
	return {
		default: ({ children }: { children: ReactNode }) =>
			(typeof children === 'function' ? ((children as unknown as (s?: boolean) => JSX.Element)(true)) : (children as JSX.Element)),
	}
})
vi.mock('react-transition-group/CSSTransition', () => {
	return {
		default: ({ children }: { children: ReactNode }) =>
			(typeof children === 'function' ? ((children as unknown as (s?: boolean) => JSX.Element)(true)) : (children as JSX.Element)),
	}
})
vi.mock('react-transition-group/cjs/Transition', () => {
	return {
		default: ({ children }: { children: ReactNode }) =>
			(typeof children === 'function' ? ((children as unknown as (s?: boolean) => JSX.Element)(true)) : (children as JSX.Element)),
	}
})
vi.mock('react-transition-group/cjs/CSSTransition', () => {
	return {
		default: ({ children }: { children: ReactNode }) =>
			(typeof children === 'function' ? ((children as unknown as (s?: boolean) => JSX.Element)(true)) : (children as JSX.Element)),
	}
})

// Mock @restart/ui and react-bootstrap Transition wrappers to short-circuit animations
vi.mock('@restart/ui/Transition', () => {
	return {
		default: ({ children }: { children: ReactNode }) =>
			(typeof children === 'function' ? ((children as unknown as (s?: boolean) => JSX.Element)(true)) : (children as JSX.Element)),
	}
})
vi.mock('@restart/ui/NoopTransition', () => {
	return {
		default: ({ children }: { children: ReactNode }) =>
			(typeof children === 'function' ? ((children as unknown as (s?: boolean) => JSX.Element)(true)) : (children as JSX.Element)),
	}
})
vi.mock('react-bootstrap/esm/TransitionWrapper', () => {
	return {
		default: ({ children }: { children: ReactNode | ((show: boolean) => ReactNode) }) =>
			(typeof children === 'function'
				? ((children as unknown as (show?: boolean) => ReactNode)(true) as JSX.Element)
				: (children as JSX.Element)),
	}
})
vi.mock('react-bootstrap/cjs/TransitionWrapper', () => {
	return {
		default: ({ children }: { children: ReactNode | ((show: boolean) => ReactNode) }) =>
			(typeof children === 'function'
				? ((children as unknown as (show?: boolean) => ReactNode)(true) as JSX.Element)
				: (children as JSX.Element)),
	}
})

// Simplify @restart/ui Modal behavior (focus trap/portal/measurements often trigger act warnings)
vi.mock('@restart/ui/Modal', () => {
	return {
		default: ({ children }: { children: ReactNode }) => (children as JSX.Element),
	}
})
vi.mock('@restart/ui/cjs/Modal', () => {
	return {
		default: ({ children }: { children: ReactNode }) => (children as JSX.Element),
	}
})
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