import { act, fireEvent, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi, renderApp } from '../test-utils'

const RECEPTIONIST = {
  id: 'u-rec',
  email: 'recepcion@example.com',
  full_name: 'Rec Demo',
  role: 'receptionist',
  professional_id: null,
}
const JUAN = {
  id: 'pac-1',
  first_name: 'Juan',
  last_name: 'Pérez',
  document_number: '30111222',
  email: 'juan@example.com',
  phone: '011-5550-0001',
  birth_date: null,
  active: true,
}
const ANA = {
  ...JUAN,
  id: 'pac-2',
  first_name: 'Ana',
  last_name: 'Gómez',
  active: false,
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
  window.sessionStorage.clear()
  saveToken('tok')
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

function patientCalls(fetchMock: ReturnType<typeof vi.fn>): string[] {
  return fetchMock.mock.calls
    .map((call) => String(call[0]).replace(BASE, ''))
    .filter((url) => url.startsWith('/patients'))
}

describe('búsqueda y tabla de pacientes', () => {
  it('muestra "Cargando…" hasta que llega la lista', async () => {
    let release: (response: Response) => void = () => undefined
    const pending = new Promise<Response>((resolve) => {
      release = resolve
    })
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => pending,
    })

    renderApp('/pacientes')

    await screen.findByRole('heading', { name: 'Pacientes' })
    expect(screen.getByText('Cargando…')).toBeInTheDocument()
    expect(screen.queryByText('Pérez, Juan')).not.toBeInTheDocument()
    await act(async () => {
      release(jsonResponse({ items: [JUAN], truncated: false }))
      await pending
    })
    expect(await screen.findByText('Pérez, Juan')).toBeInTheDocument()
    expect(screen.queryByText('Cargando…')).not.toBeInTheDocument()
  })

  it('escribir pide la búsqueda una sola vez, 300 ms después de la última tecla', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN, ANA], truncated: false }),
      'GET /patients?q=p%C3%A9r': () => jsonResponse({ items: [JUAN], truncated: false }),
    })
    renderApp('/pacientes')
    expect(await screen.findByText('Gómez, Ana')).toBeInTheDocument()
    const box = screen.getByRole('searchbox', { name: 'Buscar paciente' })

    for (const text of ['p', 'pé', 'pér']) {
      fireEvent.change(box, { target: { value: text } })
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100)
      })
    }
    expect(patientCalls(fetchMock)).toEqual(['/patients'])

    await act(async () => {
      await vi.advanceTimersByTimeAsync(250)
    })

    expect(patientCalls(fetchMock)).toEqual(['/patients', '/patients?q=p%C3%A9r'])
    expect(await screen.findByText('Pérez, Juan')).toBeInTheDocument()
    expect(screen.queryByText('Gómez, Ana')).not.toBeInTheDocument()
  })

  it('"Incluir inactivos" suma a Ana con el estado Inactivo', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
      'GET /patients?include_inactive=true': () =>
        jsonResponse({ items: [ANA, JUAN], truncated: false }),
    })
    renderApp('/pacientes')
    await screen.findByText('Pérez, Juan')

    fireEvent.click(screen.getByRole('checkbox', { name: 'Incluir inactivos' }))

    const ana = (await screen.findByText('Gómez, Ana')).closest('tr')
    expect(ana).toHaveTextContent('Inactivo')
    expect(screen.getByText('Pérez, Juan').closest('tr')).toHaveTextContent('Activo')
  })

  it('con truncated avisa que hay más resultados', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: true }),
    })

    renderApp('/pacientes')

    expect(await screen.findByText('Hay más resultados: afiná la búsqueda')).toBeInTheDocument()
  })

  it('sin coincidencias dice "No se encontraron pacientes" y no dibuja la tabla', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [], truncated: false }),
    })

    renderApp('/pacientes')

    expect(await screen.findByText('No se encontraron pacientes')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText('Hay más resultados: afiná la búsqueda')).not.toBeInTheDocument()
  })

  it('ante un error de red muestra el aviso de conexión', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => {
        throw new TypeError('Failed to fetch')
      },
    })

    renderApp('/pacientes')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudo conectar con el servidor',
    )
  })

  it('ante un 500 muestra el aviso de conexión', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ error: { code: 'INTERNAL_ERROR', message: 'x' } }, 500),
    })

    renderApp('/pacientes')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudo conectar con el servidor',
    )
  })
})

describe('tabla de pacientes en pantallas angostas (P-8)', () => {
  it('está dentro de una región con nombre "Pacientes", enfocable y desplazable', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN, ANA], truncated: false }),
    })
    renderApp('/pacientes')

    const region = await screen.findByRole('region', { name: 'Pacientes' })

    expect(region).toHaveAttribute('tabindex', '0')
    expect(region).toHaveClass('table-scroll')
    expect(region.querySelector('table')).toHaveClass('data-table')
  })

  it('sin pacientes no hay tabla ni región', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [], truncated: false }),
    })
    renderApp('/pacientes')

    await screen.findByText('No se encontraron pacientes')

    expect(screen.queryByRole('region', { name: 'Pacientes' })).not.toBeInTheDocument()
  })
})
