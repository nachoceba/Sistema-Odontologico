import { apiUrl } from '../config'
import { clearToken, readToken } from '../auth/session'

export const SESSION_ENDED_MESSAGE = 'Tu sesión terminó. Volvé a ingresar'
export const FORBIDDEN_MESSAGE = 'No tenés permiso para esta acción'

type ExpiredListener = () => void
const listeners = new Set<ExpiredListener>()

/** Suscribe un aviso para cuando la API rechaza la sesión (401). Devuelve la baja. */
export function onSessionExpired(listener: ExpiredListener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export interface ApiFetchOptions {
  /** false para el login y el health: no se envía el token ni un 401 cierra la sesión. */
  auth?: boolean
}

/** Llamada a la API con el token en `Authorization: Bearer`. 401 borra la sesión; 403 la conserva. */
export async function apiFetch(
  path: string,
  init: RequestInit = {},
  { auth = true }: ApiFetchOptions = {},
): Promise<Response> {
  const url = apiUrl(path)
  if (url === null) throw new Error('API no configurada')

  const headers = new Headers(init.headers)
  const token = auth ? readToken() : null
  if (token !== null) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(url, { ...init, headers })
  if (auth && response.status === 401) {
    clearToken()
    listeners.forEach((listener) => {
      listener()
    })
  }
  return response
}

/** Aviso para mostrar según el estado HTTP, o null si no corresponde ninguno. */
export function messageForStatus(status: number): string | null {
  if (status === 401) return SESSION_ENDED_MESSAGE
  if (status === 403) return FORBIDDEN_MESSAGE
  return null
}
