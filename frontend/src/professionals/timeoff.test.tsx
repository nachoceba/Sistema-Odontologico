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
const OLD = { id: 't-1', starts_on: '2026-09-01', ends_on: '2026-09-03', reason: null }
const NEW = { id: 't-2', starts_on: '2026-10-12', ends_on: '2026-10-16', reason: 'Congreso' }
const CONFLICT = {
  appointment_id: 'a-1',
  patient_id: 'pac-1',
  professional_id: 'p-1',
  starts_at: '2026-10-14T12:00:00Z',
  ends_at: '2026-10-14T12:30:00Z',
  reason: 'TIME_OFF',
}

function setup(extra: Record<string, () => Promise<Response> | Response> = {}) {
  saveToken('tok-admin')
  return mockApi({
    'GET /auth/me': () => jsonResponse(ADMIN),
    'GET /professionals': () => jsonResponse([DRA]),
    'GET /professionals/p-1/working-hours': () => jsonResponse({ blocks: [] }),
    'GET /professionals/p-1/time-off': () => jsonResponse([OLD]),
    ...extra,
  })
}

function callsWith(fetchMock: ReturnType<typeof vi.fn>, method: string) {
  return fetchMock.mock.calls.filter(
    (c) => ((c[1] as RequestInit | undefined)?.method ?? 'GET') === method,
  )
}

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
  window.sessionStorage.clear()
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('licencias en pantalla', () => {
  it('lista las licencias con fechas DD/MM/AAAA y "Sin motivo"', async () => {
    setup()

    renderApp('/profesionales')

    expect(await screen.findByText('01/09/2026 al 03/09/2026')).toBeInTheDocument()
    expect(screen.getByText('Sin motivo')).toBeInTheDocument()
  })

  it('agrega una licencia con motivo y aparece en el listado', async () => {
    const fetchMock = setup({
      'POST /professionals/p-1/time-off': () =>
        jsonResponse({ time_off: NEW, conflicts: [] }, 201),
    })
    renderApp('/profesionales')
    await screen.findByText('01/09/2026 al 03/09/2026')

    fill('Desde', '2026-10-12')
    fill('Hasta', '2026-10-16')
    fill('Motivo (opcional)', 'Congreso')
    fireEvent.click(screen.getByRole('button', { name: 'Agregar licencia' }))

    expect(await screen.findByText('12/10/2026 al 16/10/2026')).toBeInTheDocument()
    expect(screen.getByText('Congreso')).toBeInTheDocument()
    const [post] = callsWith(fetchMock, 'POST') as [[string, RequestInit]]
    expect(JSON.parse(post[1].body as string)).toEqual({
      starts_on: '2026-10-12',
      ends_on: '2026-10-16',
      reason: 'Congreso',
    })
  })

  it('con fechas invertidas avisa y no envía ningún pedido', async () => {
    const fetchMock = setup()
    renderApp('/profesionales')
    await screen.findByText('01/09/2026 al 03/09/2026')

    fill('Desde', '2026-10-16')
    fill('Hasta', '2026-10-12')
    fireEvent.click(screen.getByRole('button', { name: 'Agregar licencia' }))

    expect(
      await screen.findByText('La fecha de fin no puede ser anterior a la de inicio'),
    ).toBeInTheDocument()
    expect(callsWith(fetchMock, 'POST')).toHaveLength(0)
  })

  it('con las fechas vacías pide completarlas sin llamar a la API', async () => {
    const fetchMock = setup()
    renderApp('/profesionales')
    await screen.findByText('01/09/2026 al 03/09/2026')

    fireEvent.click(screen.getByRole('button', { name: 'Agregar licencia' }))

    expect(await screen.findByText('Completá las fechas de inicio y de fin')).toBeInTheDocument()
    expect(callsWith(fetchMock, 'POST')).toHaveLength(0)
  })

  it('tras agregar muestra los conflictos con el mismo aviso que el horario', async () => {
    setup({
      'POST /professionals/p-1/time-off': () =>
        jsonResponse({ time_off: NEW, conflicts: [CONFLICT] }, 201),
    })
    renderApp('/profesionales')
    await screen.findByText('01/09/2026 al 03/09/2026')

    fill('Desde', '2026-10-12')
    fill('Hasta', '2026-10-16')
    fireEvent.click(screen.getByRole('button', { name: 'Agregar licencia' }))

    expect(
      await screen.findByText(
        'Estos turnos quedaron fuera del nuevo horario. Recepción debe reprogramarlos o cancelarlos.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('mié 14/10 09:00')).toBeInTheDocument()
  })

  it('cancelar la confirmación no envía ningún pedido y deja la licencia', async () => {
    const fetchMock = setup()
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderApp('/profesionales')
    await screen.findByText('01/09/2026 al 03/09/2026')

    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))

    expect(confirm).toHaveBeenCalledWith('¿Borrar esta licencia?')
    expect(callsWith(fetchMock, 'DELETE')).toHaveLength(0)
    expect(screen.getByText('01/09/2026 al 03/09/2026')).toBeInTheDocument()
  })

  it('confirmar el borrado la quita del listado', async () => {
    const fetchMock = setup({
      'DELETE /professionals/p-1/time-off/t-1': () => new Response(null, { status: 204 }),
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderApp('/profesionales')
    const entry = (await screen.findByText('01/09/2026 al 03/09/2026')).closest('li') as HTMLElement

    fireEvent.click(within(entry).getByRole('button', { name: 'Borrar' }))

    await waitFor(() => {
      expect(screen.queryByText('01/09/2026 al 03/09/2026')).not.toBeInTheDocument()
    })
    expect(callsWith(fetchMock, 'DELETE')).toHaveLength(1)
  })

  it('si la licencia ya no existe avisa y la saca del listado', async () => {
    setup({
      'DELETE /professionals/p-1/time-off/t-1': () =>
        jsonResponse({ error: { code: 'TIME_OFF_NOT_FOUND', message: 'x' } }, 404),
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderApp('/profesionales')
    await screen.findByText('01/09/2026 al 03/09/2026')

    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))

    expect(await screen.findByText('La licencia ya no existe')).toBeInTheDocument()
  })
})
