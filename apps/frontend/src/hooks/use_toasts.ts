import React from 'react'
import { ToastContext } from '../state/toast_context'

export function useToasts() {
  const ctx = React.useContext(ToastContext)
  if (!ctx) throw new Error('useToasts must be used within ToastProvider')
  return ctx
}
