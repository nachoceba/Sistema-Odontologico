import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Treatment } from '../api/treatments'
import { clearToken, saveToken } from '../auth/session'
import { BASE, DENTIST, jsonResponse, mockApi, renderApp } from '../test-utils'

const ADMIN = {
  id: 'u-admin',
  email: 'admin@example.com',
  full_name: 'Admin Demo',
  role: 'admin',
  professional_id: null,
}
const RECEPTIONIST = { ...ADMIN, id: 'u-rec', full_name: 'Rec Demo', role: 'receptionist' }

const DRA = { id: 'p-1', display_name: 'Dra. Ana Álvarez', license_number: 'MAT-0001', active: true }
const DR_B = { id: 'p-2', display_name: 'Dr. Bruno Benítez', license_number: null, active: true }

const CONSULTA: Treatment = { id: 't-1', name: 'Consulta', active: true }
const EXTRACCION: Treatment = { id: 't-3', name: 'Extracción', active: true }
const BLANQUEAMIENTO: Treatment = { id: 't-4', name: 'Blanqueamiento', active: false }
const CATALOG = [BLANQUEAMIENTO, CONSULTA, EXTRACCION]

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
  window.sessionStorage.clear()
  saveToken('tok')
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

function api(me: object, assigned: Treatment[], extra: Record<string, () => Response> = {}) {
  return mockApi({
    'GET /auth/me': () => jsonResponse(me),
    'GET /professionals': () => jsonResponse([DRA, DR_B]),
    'GET /professionals/p-1/working-hours': () => jsonResponse({ blocks: [] }),
    'GET /professionals/p-1/time-off': () => jsonResponse([]),
    'GET /professionals/p-1/treatments': () => jsonResponse(assigned),
    'GET /treatments': () => jsonResponse(CATALOG),
    ...extra,
  })
}

async function openDra() {
  renderApp('/profesionales')
  fireEvent.click(await screen.findByRole('button', { name: 'Ver a Dra. Ana Álvarez' }))
  return screen.findByRole('region', { name: 'Tratamientos que ofrece' })
}

describe('ficha del profesional: tratamientos que ofrece', () => {
  it('el administrador ve todo el catálogo con casillas y los inactivos marcados', async () => {
    api(ADMIN, [CONSULTA])

    const section = await openDra()

    const boxes = await within(section).findAllByRole('checkbox')
    expect(boxes.map((b) => (b as HTMLInputElement).checked)).toEqual([false, true, false])
    expect(within(section).getByLabelText(/Blanqueamiento/)).toBeInTheDocument()
    expect(within(section).getByText('Inactivo')).toBeInTheDocument()
    expect(within(section).getByRole('button', { name: 'Guardar tratamientos' })).toBeInTheDocument()
  })

  it('marcar Extracción y guardar reemplaza la asignación con un PUT', async () => {
    const fetchMock = api(ADMIN, [CONSULTA], {
      'PUT /professionals/p-1/treatments': () => jsonResponse([CONSULTA, EXTRACCION]),
    })
    const section = await openDra()

    fireEvent.click(await within(section).findByLabelText('Extracción'))
    fireEvent.click(within(section).getByRole('button', { name: 'Guardar tratamientos' }))

    expect(await within(section).findByRole('status')).toHaveTextContent('Tratamientos guardados')
    const put = fetchMock.mock.calls.find(
      (c) => (c[1] as RequestInit | undefined)?.method === 'PUT',
    )
    expect(JSON.parse((put?.[1] as RequestInit).body as string)).toEqual({
      treatment_ids: ['t-1', 't-3'],
    })
  })

  it('un doble clic en guardar envía un solo PUT', async () => {
    const fetchMock = api(ADMIN, [CONSULTA], {
      'PUT /professionals/p-1/treatments': () => jsonResponse([CONSULTA]),
    })
    const section = await openDra()
    const save = await within(section).findByRole('button', { name: 'Guardar tratamientos' })

    fireEvent.click(save)
    fireEvent.click(save)

    await within(section).findByRole('status')
    const puts = fetchMock.mock.calls.filter(
      (c) => (c[1] as RequestInit | undefined)?.method === 'PUT',
    )
    expect(puts).toHaveLength(1)
  })

  it('si el guardado falla muestra el error y deja las casillas como estaban', async () => {
    api(ADMIN, [CONSULTA], { 'PUT /professionals/p-1/treatments': () => jsonResponse({}, 500) })
    const section = await openDra()

    fireEvent.click(await within(section).findByLabelText('Extracción'))
    fireEvent.click(within(section).getByRole('button', { name: 'Guardar tratamientos' }))

    expect(await within(section).findByRole('alert')).toHaveTextContent('No se pudo conectar')
    expect(within(section).getByLabelText('Extracción')).toBeChecked()
  })

  it('un profesional sin tratamientos activos muestra el aviso', async () => {
    api(ADMIN, [BLANQUEAMIENTO])
    const section = await openDra()

    expect(
      await within(section).findByText(
        'Sin tratamientos activos: no se le pueden dar turnos nuevos.',
      ),
    ).toBeInTheDocument()
  })

  it('la recepción ve la lista de solo lectura, sin casillas ni botón y sin pedir el catálogo', async () => {
    const fetchMock = api(RECEPTIONIST, [CONSULTA, EXTRACCION])
    const section = await openDra()

    expect(await within(section).findByText('Consulta')).toBeInTheDocument()
    expect(within(section).getByText('Extracción')).toBeInTheDocument()
    expect(within(section).queryByRole('checkbox')).not.toBeInTheDocument()
    expect(within(section).queryByRole('button')).not.toBeInTheDocument()
    expect(fetchMock.mock.calls.some((c) => String(c[0]).endsWith('/treatments') && !String(c[0]).includes('professionals'))).toBe(false)
  })

  it('el odontólogo ve su propia ficha en solo lectura', async () => {
    api(DENTIST, [CONSULTA], {
      'GET /professionals': () => jsonResponse([DRA]),
    })

    renderApp('/profesionales')
    const section = await screen.findByRole('region', { name: 'Tratamientos que ofrece' })

    expect(await within(section).findByText('Consulta')).toBeInTheDocument()
    expect(within(section).queryByRole('button')).not.toBeInTheDocument()
  })

  it('una asignación vacía de solo lectura dice que no tiene tratamientos', async () => {
    api(RECEPTIONIST, [])
    const section = await openDra()

    await waitFor(() => {
      expect(
        within(section).getByText('Sin tratamientos activos: no se le pueden dar turnos nuevos.'),
      ).toBeInTheDocument()
    })
  })
})
