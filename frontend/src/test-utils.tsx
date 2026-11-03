import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { vi } from 'vitest'
import App from './App'

export const BASE = 'http://localhost:8000/api/v1'

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export const DENTIST = {
  id: 'u-1',
  email: 'dra.a@example.com',
  full_name: 'Dra. Ana Pérez',
  role: 'dentist',
  professional_id: 'p-1',
}

type Handler = (init: RequestInit | undefined) => Promise<Response> | Response

/** fetch simulado por ruta: `GET /health`, `POST /auth/login`, `GET /auth/me`. */
export function mockApi(handlers: Record<string, Handler>): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const raw = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    const url = raw.replace(BASE, '')
    const method = (init?.method ?? 'GET').toUpperCase()
    const handler = handlers[`${method} ${url}`]
    if (handler === undefined) return Promise.reject(new TypeError(`sin handler: ${method} ${url}`))
    return Promise.resolve(handler(init))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

export function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}
