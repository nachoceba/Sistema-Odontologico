import { useEffect, useRef, useState } from 'react'

export type Remote<T> = { status: 'loading' } | { status: 'error' } | { status: 'ready'; data: T }

/**
 * Pide un dato cuando cambia `key` o `reloadKey`. Una respuesta vieja se descarta si mientras
 * tanto cambió la clave. Con `key` nulo no pide nada y queda en "loading".
 */
export function useRemote<T>(
  key: string | null,
  load: () => Promise<T>,
  reloadKey: number,
): Remote<T> {
  const requestKey = `${key ?? ''}|${String(reloadKey)}`
  const [result, setResult] = useState<{ key: string; state: Remote<T> } | null>(null)
  const loadRef = useRef(load)

  useEffect(() => {
    loadRef.current = load
  })

  useEffect(() => {
    if (key === null) return
    let active = true
    loadRef.current().then(
      (data) => {
        if (active) setResult({ key: requestKey, state: { status: 'ready', data } })
      },
      () => {
        if (active) setResult({ key: requestKey, state: { status: 'error' } })
      },
    )
    return () => {
      active = false
    }
  }, [key, requestKey])

  return result?.key === requestKey ? result.state : { status: 'loading' }
}
