/* eslint-disable react-refresh/only-export-components */
import React from 'react'

export interface ToastItem { id: string; kind: 'success'|'error'|'info'; message: string; ts: number }
interface ToastContextValue {
  toasts: ToastItem[]
  push: (kind: ToastItem['kind'], message: string) => void
  dismiss: (id: string) => void
}

export const ToastContext = React.createContext<ToastContextValue | undefined>(undefined)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = React.useState<ToastItem[]>([])
  
  const push = React.useCallback((kind: ToastItem['kind'], message: string) => {
    const id = crypto.randomUUID()
    setToasts(t => [...t, { id, kind, message, ts: Date.now() }])
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setToasts(t => t.filter(x => x.id !== id))
    }, 5000)
  }, [])
  
  const dismiss = React.useCallback((id: string) => {
    setToasts(t => t.filter(x => x.id !== id))
  }, [])
  return (
    <ToastContext.Provider value={{ toasts, push, dismiss }}>
      {children}
      <div className="toast-container position-fixed top-0 end-0 p-3 toast-z">
        {toasts.map(t => (
          <div key={t.id} className={`toast show mb-2 border-${t.kind==='error'?'danger':t.kind==='success'?'success':'secondary'}`}> 
            <div className="toast-header">
              <strong className="me-auto text-capitalize">{t.kind}</strong>
              <button type="button" className="btn-close" onClick={() => dismiss(t.id)} aria-label="Close" />
            </div>
            <div className="toast-body">{t.message}</div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// Hook moved to hooks/use_toasts.ts to improve Fast Refresh behavior
