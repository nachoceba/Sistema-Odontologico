import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi, renderApp } from '../test-utils'

const ADMIN = {
  id: 'u-admin',
  email: 'admin@example.com',
  full_name: 'Admin Demo',
  role: 'admin',
  professional_id: null,
}
const DRA = { id: 'p-1', display_name: 'Dra. Ana Álvarez', license_number: 'MAT-0001', active: true }
const DR_B = { id: 'p-2', display_name: 'Dr. Bruno Benítez', license_number: null, active: false }

function setup(extra: Record<string, () => Promise<Response> | Response> = {}) {
  saveToken('tok-admin')
  return mockApi({
    'GET /auth/me': () => jsonResponse(ADMIN),
    'GET /professionals': () => jsonResponse([DRA, DR_B]),
    'GET /professionals/p-1/working-hours': () => jsonResponse({ blocks: [] }),
    'GET /professionals/p-1/time-off': () => jsonResponse([]),
    'GET /professionals/p-1/treatments': () => jsonResponse([]),
    'GET /treatments': () => jsonResponse([]),
    ...extra,
  })
}

async function openDra() {
  fireEvent.click(await screen.findByRole('button', { name: 'Ver a Dra. Ana Álvarez' }))
  return screen.findByRole('button', { name: 'Editar ficha' })
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

describe('listado y edición de la ficha', () => {
  it('muestra "Cargando…" mientras espera y marca la ficha inactiva', async () => {
    setup()

    renderApp('/profesionales')

    expect(screen.getAllByText('Cargando…').length).toBeGreaterThan(0)
    const rowB = (await screen.findByText('Dr. Bruno Benítez')).closest('tr') as HTMLElement
    expect(within(rowB).getByText('Inactivo')).toBeInTheDocument()
    const rowA = screen.getByText('Dra. Ana Álvarez').closest('tr') as HTMLElement
    expect(within(rowA).getByText('Activo')).toBeInTheDocument()
    expect(within(rowA).getByText('MAT-0001')).toBeInTheDocument()
  })

  it('ante un error de red muestra el aviso de conexión', async () => {
    saveToken('tok-admin')
    mockApi({
      'GET /auth/me': () => jsonResponse(ADMIN),
      'GET /professionals': () => Promise.reject(new TypeError('sin red')),
    })

    renderApp('/profesionales')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudo conectar con el servidor',
    )
  })

  it('con un nombre vacío muestra el error y no envía ningún pedido', async () => {
    const fetchMock = setup()
    renderApp('/profesionales')
    fireEvent.click(await openDra())

    fireEvent.change(screen.getByLabelText('Nombre a mostrar'), { target: { value: '   ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar ficha' }))

    expect(await screen.findByText('El nombre a mostrar es obligatorio')).toBeInTheDocument()
    const patches = fetchMock.mock.calls.filter(
      (c) => ((c[1] as RequestInit | undefined)?.method ?? 'GET') === 'PATCH',
    )
    expect(patches).toHaveLength(0)
  })

  it('guarda el nombre y la matrícula y los muestra', async () => {
    const fetchMock = setup({
      'PATCH /professionals/p-1': () =>
        jsonResponse({ ...DRA, display_name: 'Dra. Ana Pérez', license_number: null }),
    })
    renderApp('/profesionales')
    fireEvent.click(await openDra())

    fireEvent.change(screen.getByLabelText('Nombre a mostrar'), {
      target: { value: 'Dra. Ana Pérez' },
    })
    fireEvent.change(screen.getByLabelText('Matrícula'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar ficha' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Dra. Ana Pérez' })).toBeInTheDocument()
    })
    const call = fetchMock.mock.calls.find(
      (c) => (c[1] as RequestInit | undefined)?.method === 'PATCH',
    ) as [string, RequestInit]
    expect(JSON.parse(call[1].body as string)).toEqual({
      display_name: 'Dra. Ana Pérez',
      license_number: null,
    })
    expect(screen.queryByLabelText('Nombre a mostrar')).not.toBeInTheDocument()
  })

  it('si la API rechaza el cambio muestra el aviso y deja el formulario abierto', async () => {
    setup({
      'PATCH /professionals/p-1': () =>
        jsonResponse({ error: { code: 'FORBIDDEN', message: 'x' } }, 403),
    })
    renderApp('/profesionales')
    fireEvent.click(await openDra())

    fireEvent.click(screen.getByRole('button', { name: 'Guardar ficha' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No tenés permiso para esta acción')
    expect(screen.getByLabelText('Nombre a mostrar')).toBeInTheDocument()
  })
})

describe('tabla de profesionales en pantallas angostas (P-8)', () => {
  it('está dentro de una región con nombre "Profesionales", enfocable y desplazable', async () => {
    setup()
    renderApp('/profesionales')

    const region = await screen.findByRole('region', { name: 'Profesionales' })

    expect(region).toHaveAttribute('tabindex', '0')
    expect(region).toHaveClass('table-scroll')
    expect(within(region).getByRole('table')).toHaveClass('data-table')
  })
})
