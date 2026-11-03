import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const HEALTH_URL = 'http://localhost:8000/api/v1/health'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('App', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_URL', 'http://localhost:8000/api/v1')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('muestra el nombre del sistema y "API disponible" si /health responde ok', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: 'ok' }))
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    expect(screen.getByRole('heading', { name: 'Sistema Odontológico' })).toBeInTheDocument()
    expect(await screen.findByText('API disponible')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(HEALTH_URL)
  })

  it('muestra "Verificando…" mientras la respuesta no llega', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise<Response>(() => undefined)))

    render(<App />)

    expect(screen.getByText('Verificando…')).toBeInTheDocument()
  })

  it('muestra "API no disponible" ante un error de red', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    render(<App />)

    expect(await screen.findByText('API no disponible')).toBeInTheDocument()
  })

  it('muestra "API no disponible" si /health responde 500', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'x' }, 500)))

    render(<App />)

    expect(await screen.findByText('API no disponible')).toBeInTheDocument()
  })

  it('muestra "API no disponible" si responde 200 con otro cuerpo', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ status: 'degraded' })))

    render(<App />)

    expect(await screen.findByText('API no disponible')).toBeInTheDocument()
  })

  it('pide configurar la URL y no hace ninguna solicitud si falta VITE_API_URL', () => {
    vi.stubEnv('VITE_API_URL', '')
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    expect(screen.getByText('Falta configurar la URL de la API')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
