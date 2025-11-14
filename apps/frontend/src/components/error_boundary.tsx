import React from 'react'

type ErrorBoundaryState = { hasError: boolean; error?: Error }

export default class ErrorBoundary extends React.Component<{ children: React.ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Centralized place to log/report errors if needed
    // Using console.error intentionally for visibility; rule disabled at top level not needed
    console.error('ErrorBoundary caught an error', error, info)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="container py-5">
          <div className="alert alert-danger" role="alert">
            <h4 className="alert-heading">Something went wrong</h4>
            <p>Sorry, the page crashed. You can try again or reload the app.</p>
            {this.state.error && (
              <details className="mt-2 small">
                <summary>Error details</summary>
                <pre className="mb-0">{String(this.state.error?.message ?? this.state.error)}</pre>
              </details>
            )}
            <div className="mt-3 d-flex gap-2">
              <button className="btn btn-primary" onClick={this.handleReset}>Try again</button>
              <button className="btn btn-outline-secondary" onClick={() => window.location.reload()}>Reload</button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
