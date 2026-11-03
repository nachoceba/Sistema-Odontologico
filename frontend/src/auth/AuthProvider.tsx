import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { apiFetch, onSessionExpired, SESSION_ENDED_MESSAGE } from '../api/client'
import {
  AuthContext,
  type AuthState,
  type LoginResult,
  type Role,
  type SessionStatus,
  type User,
} from './AuthContext'
import { clearToken, readToken, saveToken } from './session'

const ROLES: readonly string[] = ['admin', 'receptionist', 'dentist']

function parseUser(value: unknown): User | null {
  if (typeof value !== 'object' || value === null) return null
  const v = value as Record<string, unknown>
  if (
    typeof v.id !== 'string' ||
    typeof v.email !== 'string' ||
    typeof v.full_name !== 'string' ||
    typeof v.role !== 'string' ||
    !ROLES.includes(v.role)
  ) {
    return null
  }
  const professional = typeof v.professional_id === 'string' ? v.professional_id : null
  return {
    id: v.id,
    email: v.email,
    full_name: v.full_name,
    role: v.role as Role,
    professional_id: professional,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>(() =>
    readToken() === null ? 'anonymous' : 'loading',
  )
  const [user, setUser] = useState<User | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  // Un 401 de cualquier llamada protegida termina la sesión (el cliente ya borró el token).
  useEffect(
    () =>
      onSessionExpired(() => {
        setUser(null)
        setStatus('anonymous')
        setNotice(SESSION_ENDED_MESSAGE)
      }),
    [],
  )

  // Al cargar con un token guardado se pide /auth/me: el JWT no se decodifica en el navegador.
  useEffect(() => {
    if (readToken() === null) return
    let active = true
    apiFetch('/auth/me')
      .then(async (response) => {
        const me = response.ok ? parseUser(await response.json()) : null
        if (!active) return
        setUser(me)
        setStatus(me === null ? 'anonymous' : 'authenticated')
      })
      .catch(() => {
        if (!active) return
        setUser(null)
        setStatus('anonymous')
      })
    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (email: string, password: string): Promise<LoginResult> => {
    try {
      const response = await apiFetch(
        '/auth/login',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        },
        { auth: false },
      )
      if (response.status === 401) return 'invalid'
      if (!response.ok) return 'unavailable'
      const body = (await response.json()) as { access_token?: unknown; user?: unknown }
      const loggedIn = parseUser(body.user)
      if (typeof body.access_token !== 'string' || loggedIn === null) return 'unavailable'
      saveToken(body.access_token)
      setUser(loggedIn)
      setNotice(null)
      setStatus('authenticated')
      return 'ok'
    } catch {
      return 'unavailable'
    }
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
    setNotice(null)
    setStatus('anonymous')
  }, [])

  const value = useMemo<AuthState>(
    () => ({ status, user, notice, login, logout }),
    [status, user, notice, login, logout],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
