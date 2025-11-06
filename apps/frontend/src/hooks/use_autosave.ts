import { useEffect, useRef } from 'react'

type SaveFn = () => Promise<void> | void

export function useAutosave(deps: React.DependencyList, save: SaveFn, delayMs: number, onSaved?: () => void) {
  const timer = useRef<number | null>(null)

  useEffect(() => {
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(async () => {
      try {
        await save()
        onSaved?.()
      } catch (_) {
        // autosave is best-effort
      }
    }, delayMs)
    return () => {
      if (timer.current) window.clearTimeout(timer.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
