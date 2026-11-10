import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, readToken, saveToken } from './auth/session'
import { turno } from './agenda/fixtures'
import { DRA, installAgendaApi } from './agenda/testApi'
import { BASE, DENTIST, jsonResponse, mockApi, renderApp } from './test-utils'

const HEALTH_URL = `${BASE}/health`
const LOGIN_OK = {
  access_token: 'tok-1',
  token_type: 'bearer',
  expires_in: 1800,
  user: DENTIST,
}

function fillAndSubmit(email: string, password: string) {
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: email } })
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: password } })
  fireEvent.click(screen.getByRole('button', { name: 'Ingresar' }))
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
  window.sessionStorage.clear()
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('pantalla de login: estado de la API (frontend-shell)', () => {
  it('muestra el nombre del sistema y "API disponible" si /health responde ok', async () => {
    const fetchMock = mockApi({ 'GET /health': () => jsonResponse({ status: 'ok' }) })

    renderApp('/login')

    expect(screen.getByRole('heading', { name: 'Sistema Odontológico' })).toBeInTheDocument()
    expect(await screen.findByText('API disponible')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(HEALTH_URL)
  })

  it('muestra "Verificando…" mientras la respuesta no llega', () => {
    mockApi({ 'GET /health': () => new Promise<Response>(() => undefined) })

    renderApp('/login')

    expect(screen.getByText('Verificando…')).toBeInTheDocument()
  })

  it('muestra "API no disponible" ante un error de red', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    renderApp('/login')

    expect(await screen.findByText('API no disponible')).toBeInTheDocument()
  })

  it('muestra "API no disponible" si /health responde 500', async () => {
    mockApi({ 'GET /health': () => jsonResponse({ detail: 'x' }, 500) })

    renderApp('/login')

    expect(await screen.findByText('API no disponible')).toBeInTheDocument()
  })

  it('muestra "API no disponible" si responde 200 con otro cuerpo', async () => {
    mockApi({ 'GET /health': () => jsonResponse({ status: 'degraded' }) })

    renderApp('/login')

    expect(await screen.findByText('API no disponible')).toBeInTheDocument()
  })

  it('pide configurar la URL y no hace ninguna solicitud si falta VITE_API_URL', () => {
    vi.stubEnv('VITE_API_URL', '')
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    renderApp('/login')

    expect(screen.getByText('Falta configurar la URL de la API')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('pantalla de login: ingreso', () => {
  it('login correcto guarda el token y navega a /agenda', async () => {
    const fetchMock = mockApi({
      'GET /health': () => jsonResponse({ status: 'ok' }),
      'POST /auth/login': () => jsonResponse(LOGIN_OK),
    })
    renderApp('/login')

    fillAndSubmit('dra.a@example.com', 'clave-ficticia')

    expect(await screen.findByText('Hola, Dra. Ana Pérez')).toBeInTheDocument()
    expect(readToken()).toBe('tok-1')
    const loginCall = fetchMock.mock.calls.find((call) => String(call[0]).endsWith('/auth/login'))
    const init = loginCall?.[1] as RequestInit
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({
      email: 'dra.a@example.com',
      password: 'clave-ficticia',
    })
    expect(new Headers(init.headers).has('Authorization')).toBe(false)
  })

  it('no guarda la contraseña en ningún almacenamiento', async () => {
    mockApi({
      'GET /health': () => jsonResponse({ status: 'ok' }),
      'POST /auth/login': () => jsonResponse(LOGIN_OK),
    })
    renderApp('/login')

    fillAndSubmit('dra.a@example.com', 'clave-ficticia')
    await screen.findByText('Hola, Dra. Ana Pérez')

    expect(JSON.stringify({ ...window.sessionStorage })).not.toContain('clave-ficticia')
    expect(JSON.stringify({ ...window.localStorage })).not.toContain('clave-ficticia')
  })

  it('401 muestra "Email o contraseña incorrectos", conserva el email y queda en /login', async () => {
    mockApi({
      'GET /health': () => jsonResponse({ status: 'ok' }),
      'POST /auth/login': () =>
        jsonResponse({ error: { code: 'INVALID_CREDENTIALS', message: 'x' } }, 401),
    })
    renderApp('/login')

    fillAndSubmit('dra.a@example.com', 'mala')

    expect(await screen.findByRole('alert')).toHaveTextContent('Email o contraseña incorrectos')
    expect(screen.getByLabelText('Email')).toHaveValue('dra.a@example.com')
    expect(readToken()).toBeNull()
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeEnabled()
  })

  it('un error de red muestra "No se pudo conectar con el servidor"', async () => {
    mockApi({
      'GET /health': () => jsonResponse({ status: 'ok' }),
      'POST /auth/login': () => Promise.reject(new TypeError('Failed to fetch')),
    })
    renderApp('/login')

    fillAndSubmit('dra.a@example.com', 'clave')

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })

  it('un 500 muestra "No se pudo conectar con el servidor"', async () => {
    mockApi({
      'GET /health': () => jsonResponse({ status: 'ok' }),
      'POST /auth/login': () => jsonResponse({ error: { code: 'INTERNAL_ERROR' } }, 500),
    })
    renderApp('/login')

    fillAndSubmit('dra.a@example.com', 'clave')

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })

  it('un doble clic envía una sola solicitud de login y deshabilita el botón', async () => {
    let release: (response: Response) => void = () => undefined
    const pending = new Promise<Response>((resolve) => {
      release = resolve
    })
    const fetchMock = mockApi({
      'GET /health': () => jsonResponse({ status: 'ok' }),
      'POST /auth/login': () => pending,
    })
    renderApp('/login')
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'clave' } })
    const button = screen.getByRole('button', { name: 'Ingresar' })

    fireEvent.click(button)
    fireEvent.click(button)
    fireEvent.submit(button.closest('form') as HTMLFormElement)

    expect(button).toBeDisabled()
    const logins = fetchMock.mock.calls.filter((call) => String(call[0]).endsWith('/auth/login'))
    expect(logins).toHaveLength(1)

    release(jsonResponse({ error: {} }, 401))
    await waitFor(() => {
      expect(button).toBeEnabled()
    })
  })
})

describe('rutas protegidas', () => {
  const me = () => jsonResponse(DENTIST)

  it('sin sesión, /agenda lleva a /login', async () => {
    mockApi({ 'GET /health': () => jsonResponse({ status: 'ok' }) })

    renderApp('/agenda')

    expect(await screen.findByRole('button', { name: 'Ingresar' })).toBeInTheDocument()
  })

  it('con sesión, /agenda muestra el nombre y el rol (llamando a /auth/me con el token)', async () => {
    saveToken('tok-1')
    const fetchMock = mockApi({ 'GET /auth/me': me })

    renderApp('/agenda')

    expect(await screen.findByText('Hola, Dra. Ana Pérez')).toBeInTheDocument()
    expect(screen.getByText('Odontólogo')).toBeInTheDocument()
    const meCall = fetchMock.mock.calls.find((call) => String(call[0]).endsWith('/auth/me'))
    const headers = new Headers((meCall?.[1] as RequestInit).headers)
    expect(headers.get('Authorization')).toBe('Bearer tok-1')
  })

  it('con sesión en la agenda, la odontóloga ve su agenda de hoy con nombre y rol en la barra', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-11-09T15:00:00Z'))
    saveToken('tok-1')
    const api = installAgendaApi({
      me: DENTIST,
      professionals: [DRA],
      appointments: [turno(10, 0, 10, 30)],
      timeOff: [],
      conflicts: [],
    })

    renderApp('/agenda')

    expect(await screen.findByText('10:00–10:30 Perez, Juan')).toBeInTheDocument()
    expect(screen.getByText('Hola, Dra. Ana Pérez')).toBeInTheDocument()
    expect(screen.getByText('Odontólogo')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Lun 09/11' })).toBeInTheDocument()
    expect(api.calls).toContain('GET /professionals/p-1/slots?date=2026-11-09')
    vi.useRealTimers()
  })

  it('muestra el rol de recepción con su nombre', async () => {
    saveToken('tok-1')
    mockApi({
      'GET /auth/me': () => jsonResponse({ ...DENTIST, role: 'receptionist', professional_id: null }),
    })

    renderApp('/agenda')

    expect(await screen.findByText('Recepción')).toBeInTheDocument()
  })

  it('con sesión, /login lleva a /agenda', async () => {
    saveToken('tok-1')
    mockApi({ 'GET /auth/me': me, 'GET /health': () => jsonResponse({ status: 'ok' }) })

    renderApp('/login')

    expect(await screen.findByText('Hola, Dra. Ana Pérez')).toBeInTheDocument()
  })

  it('una ruta inexistente lleva a /agenda con sesión', async () => {
    saveToken('tok-1')
    mockApi({ 'GET /auth/me': me })

    renderApp('/no-existe')

    expect(await screen.findByText('Hola, Dra. Ana Pérez')).toBeInTheDocument()
  })

  it('una ruta inexistente lleva a /login sin sesión', async () => {
    mockApi({ 'GET /health': () => jsonResponse({ status: 'ok' }) })

    renderApp('/no-existe')

    expect(await screen.findByRole('button', { name: 'Ingresar' })).toBeInTheDocument()
  })

  it('un 401 en /auth/me borra el token y vuelve a /login con el aviso', async () => {
    saveToken('vencido')
    mockApi({
      'GET /auth/me': () => jsonResponse({ error: { code: 'NOT_AUTHENTICATED' } }, 401),
      'GET /health': () => jsonResponse({ status: 'ok' }),
    })

    renderApp('/agenda')

    expect(await screen.findByRole('alert')).toHaveTextContent('Tu sesión terminó. Volvé a ingresar')
    expect(readToken()).toBeNull()
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeInTheDocument()
  })

  it('"Salir" borra el token y deja al usuario en /login', async () => {
    saveToken('tok-1')
    mockApi({ 'GET /auth/me': me, 'GET /health': () => jsonResponse({ status: 'ok' }) })
    renderApp('/agenda')
    await screen.findByText('Hola, Dra. Ana Pérez')

    fireEvent.click(screen.getByRole('button', { name: 'Salir' }))

    expect(await screen.findByRole('button', { name: 'Ingresar' })).toBeInTheDocument()
    expect(readToken()).toBeNull()
    expect(screen.queryByText('Tu sesión terminó. Volvé a ingresar')).not.toBeInTheDocument()
  })

  it('un error de red al recargar con token no deja la pantalla en blanco', async () => {
    saveToken('tok-1')
    mockApi({
      'GET /auth/me': () => Promise.reject(new TypeError('Failed to fetch')),
      'GET /health': () => jsonResponse({ status: 'ok' }),
    })

    renderApp('/agenda')

    expect(await screen.findByRole('button', { name: 'Ingresar' })).toBeInTheDocument()
  })
})

describe('páginas públicas de turnos: fuera de la sesión (frontend-auth, P-8)', () => {
  const PROFESIONALES = [{ id: 'p-1', display_name: 'Dra. A' }]

  it('sin sesión, /turnos muestra la reserva y no redirige a /login', async () => {
    mockApi({ 'GET /public/professionals': () => jsonResponse(PROFESIONALES) })

    renderApp('/turnos')

    expect(await screen.findByRole('heading', { name: 'Reservar un turno' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Dra. A' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Contraseña')).not.toBeInTheDocument()
  })

  it('con un token guardado y /auth/me sin responder, /turnos no queda en "Cargando…"', async () => {
    saveToken('tok-rec')
    const fetchMock = mockApi({
      'GET /public/professionals': () => jsonResponse(PROFESIONALES),
      'GET /auth/me': () => new Promise<Response>(() => undefined),
    })

    renderApp('/turnos')

    expect(await screen.findByRole('heading', { name: 'Reservar un turno' })).toBeInTheDocument()
    const paths = fetchMock.mock.calls.map((call) => String(call[0]))
    expect(paths.some((path) => path.endsWith('/auth/me'))).toBe(false)
  })

  it('con sesión de recepción abierta, ningún pedido de /turnos lleva Authorization', async () => {
    saveToken('tok-rec')
    const fetchMock = mockApi({ 'GET /public/professionals': () => jsonResponse(PROFESIONALES) })

    renderApp('/turnos')

    await screen.findByRole('button', { name: 'Dra. A' })
    for (const call of fetchMock.mock.calls) {
      const init = call[1] as RequestInit | undefined
      expect(new Headers(init?.headers).has('Authorization')).toBe(false)
    }
    expect(readToken()).toBe('tok-rec')
  })

  it('/turnos/confirmar#token=abc muestra la confirmación sin sesión y sin hacer pedidos', async () => {
    const fetchMock = mockApi({})

    renderApp('/turnos/confirmar#token=abc')

    expect(await screen.findByRole('heading', { name: 'Confirmar su turno' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirmar mi turno' })).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('una ruta inexistente sigue llevando a /login sin sesión', async () => {
    mockApi({ 'GET /health': () => jsonResponse({ status: 'ok' }) })

    renderApp('/turnos/otra-cosa')

    expect(await screen.findByLabelText('Contraseña')).toBeInTheDocument()
  })
})
