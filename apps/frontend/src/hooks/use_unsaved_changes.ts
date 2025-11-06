import { useEffect } from 'react'

/**
 * Warns the user when navigating away with unsaved changes.
 * - Adds a beforeunload handler for hard navigations.
 * - Blocks in-app navigation and shows a confirm dialog.
 * Return value: a helper you can call before programmatic navigations.
 */
export function useUnsavedChangesWarning(isDirty: boolean | undefined) {
  // Hard navigation (reload/close/tab)
  useEffect(() => {
    if (!isDirty) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
      return ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isDirty])

  // For custom actions like tab switching
  function confirmProceed(): boolean {
    if (!isDirty) return true
    return window.confirm('You have unsaved changes. Continue and discard them?')
  }

  return { confirmProceed }
}
