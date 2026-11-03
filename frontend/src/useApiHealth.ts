import { useEffect, useState } from 'react'
import { apiUrl } from './config'

export type ApiHealth = 'unconfigured' | 'checking' | 'up' | 'down'

async function checkHealth(url: string): Promise<boolean> {
  try {
    const response = await fetch(url)
    if (!response.ok) return false
    const body = (await response.json()) as { status?: unknown }
    return body.status === 'ok'
  } catch {
    return false
  }
}

/** Consulta GET /health una vez al montar y devuelve el estado de la API. */
export function useApiHealth(): ApiHealth {
  const url = apiUrl('/health')
  const [state, setState] = useState<ApiHealth>(url === null ? 'unconfigured' : 'checking')

  useEffect(() => {
    if (url === null) return
    let active = true
    void checkHealth(url).then((ok) => {
      if (active) setState(ok ? 'up' : 'down')
    })
    return () => {
      active = false
    }
  }, [url])

  return state
}
