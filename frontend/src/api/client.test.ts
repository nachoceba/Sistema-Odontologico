import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, readToken, saveToken } from '../auth/session'
import { apiFetch, messageForStatus, onSessionExpired } from './client'

const BASE = 'http://localhost:8000/api/v1'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function headersOf(fetchMock: ReturnType<typeof vi.fn>): Headers {
  const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined
  return new Headers(init?.headers)
}

describe('apiFetch', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_URL', BASE)
    clearToken()
    window.sessionStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('agrega Authorization: Bearer cuando hay token', async () => {
    saveToken('tok-1')
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await apiFetch('/auth/me')

    expect(fetchMock.mock.calls[0]?.[0]).toBe(`${BASE}/auth/me`)
    expect(headersOf(fetchMock).get('Authorization')).toBe('Bearer tok-1')
  })

  it('no agrega Authorization si no hay token', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await apiFetch('/auth/me')

    expect(headersOf(fetchMock).has('Authorization')).toBe(false)
  })

  it('no agrega el token al login ni al health aunque haya sesión', async () => {
    saveToken('tok-1')
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await apiFetch('/auth/login', { method: 'POST' }, { auth: false })
    expect(headersOf(fetchMock).has('Authorization')).toBe(false)

    fetchMock.mockClear()
    await apiFetch('/health', undefined, { auth: false })
    expect(headersOf(fetchMock).has('Authorization')).toBe(false)
  })

  it('ante 401 borra la sesión y avisa una vez', async () => {
    saveToken('tok-1')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ error: {} }, 401)))
    const listener = vi.fn()
    const off = onSessionExpired(listener)

    const response = await apiFetch('/auth/me')
    off()

    expect(response.status).toBe(401)
    expect(readToken()).toBeNull()
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('ante 401 de una llamada sin auth (login) no borra ni avisa', async () => {
    saveToken('tok-1')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ error: {} }, 401)))
    const listener = vi.fn()
    const off = onSessionExpired(listener)

    await apiFetch('/auth/login', { method: 'POST' }, { auth: false })
    off()

    expect(readToken()).toBe('tok-1')
    expect(listener).not.toHaveBeenCalled()
  })

  it('ante 403 conserva la sesión y no avisa', async () => {
    saveToken('tok-1')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ error: {} }, 403)))
    const listener = vi.fn()
    const off = onSessionExpired(listener)

    const response = await apiFetch('/algo')
    off()

    expect(response.status).toBe(403)
    expect(readToken()).toBe('tok-1')
    expect(listener).not.toHaveBeenCalled()
  })

  it('falla de forma clara si VITE_API_URL no está configurada', async () => {
    vi.stubEnv('VITE_API_URL', '')
    vi.stubGlobal('fetch', vi.fn())

    await expect(apiFetch('/auth/me')).rejects.toThrow('API no configurada')
  })
})

describe('messageForStatus', () => {
  it('traduce 401 y 403 a los avisos de la spec', () => {
    expect(messageForStatus(401)).toBe('Tu sesión terminó. Volvé a ingresar')
    expect(messageForStatus(403)).toBe('No tenés permiso para esta acción')
  })

  it('devuelve null para otros estados', () => {
    expect(messageForStatus(200)).toBeNull()
    expect(messageForStatus(500)).toBeNull()
  })
})
