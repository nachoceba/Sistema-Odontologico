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
const MORNING = { weekday: 0, start_time: '09:00', end_time: '13:00' }
const AFTERNOON = { weekday: 0, start_time: '14:00', end_time: '18:00' }
const CONFLICT = {
  appointment_id: 'a-1',
  patient_id: 'pac-1',
  professional_id: 'p-1',
  starts_at: '2026-10-05T19:00:00Z',
  ends_at: '2026-10-05T19:30:00Z',
  reason: 'OUTSIDE_WORKING_HOURS',
}

function setup(
  put: () => Promise<Response> | Response,
  initial: (typeof MORNING)[] = [],
) {
  saveToken('tok-admin')
  return mockApi({
    'GET /auth/me': () => jsonResponse(ADMIN),
    'GET /professionals': () => jsonResponse([DRA]),
    'GET /professionals/p-1/working-hours': () => jsonResponse({ blocks: initial }),
    'GET /professionals/p-1/time-off': () => jsonResponse([]),
    'GET /professionals/p-1/treatments': () => jsonResponse([]),
    'GET /treatments': () => jsonResponse([]),
    'PUT /professionals/p-1/working-hours': put,
  })
}

function putBody(fetchMock: ReturnType<typeof vi.fn>): unknown {
  const call = fetchMock.mock.calls.find(
    (c) => (c[1] as RequestInit | undefined)?.method === 'PUT',
  ) as [string, RequestInit]
  return JSON.parse(call[1].body as string)
}

function setTime(label: string, value: string) {
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
})

describe('editor del horario semanal', () => {
  it('guarda dos tramos el lunes enviando la semana completa y avisa "Horario guardado"', async () => {
    const fetchMock = setup(() => jsonResponse({ blocks: [MORNING, AFTERNOON], conflicts: [] }))
    renderApp('/profesionales')
    await screen.findByRole('heading', { name: 'Dra. Ana Álvarez' })

    fireEvent.click(await screen.findByRole('button', { name: 'Agregar tramo el lunes' }))
    fireEvent.click(screen.getByRole('button', { name: 'Agregar tramo el lunes' }))
    setTime('Lunes, tramo 1, inicio', '09:00')
    setTime('Lunes, tramo 1, fin', '13:00')
    setTime('Lunes, tramo 2, inicio', '14:00')
    setTime('Lunes, tramo 2, fin', '18:00')
    fireEvent.click(screen.getByRole('button', { name: 'Guardar horario' }))

    expect(await screen.findByText('Horario guardado')).toBeInTheDocument()
    expect(putBody(fetchMock)).toEqual({ blocks: [MORNING, AFTERNOON] })
    expect(screen.getByLabelText('Lunes, tramo 2, fin')).toHaveValue('18:00')
    expect(screen.queryByText(/quedaron fuera del nuevo horario/)).not.toBeInTheDocument()
  })

  it('quita un tramo antes de guardar', async () => {
    const fetchMock = setup(() => jsonResponse({ blocks: [AFTERNOON], conflicts: [] }), [
      MORNING,
      AFTERNOON,
    ])
    renderApp('/profesionales')
    await screen.findByLabelText('Lunes, tramo 2, inicio')

    fireEvent.click(screen.getByRole('button', { name: 'Quitar tramo 1 del lunes' }))
    fireEvent.click(screen.getByRole('button', { name: 'Guardar horario' }))

    await screen.findByText('Horario guardado')
    expect(putBody(fetchMock)).toEqual({ blocks: [AFTERNOON] })
  })

  it('muestra la superposición junto al lunes y conserva lo escrito', async () => {
    setup(
      () =>
        jsonResponse(
          { error: { code: 'INVALID_WORKING_HOURS', message: 'Los tramos 1 y 2 se superponen.' } },
          400,
        ),
      [MORNING, { weekday: 0, start_time: '12:00', end_time: '15:00' }],
    )
    renderApp('/profesionales')
    await screen.findByLabelText('Lunes, tramo 2, inicio')

    fireEvent.click(screen.getByRole('button', { name: 'Guardar horario' }))

    const monday = await screen.findByRole('group', { name: 'Lunes' })
    expect(await within(monday).findByRole('alert')).toHaveTextContent(
      'Los tramos 1 y 2 se superponen.',
    )
    expect(screen.getByLabelText('Lunes, tramo 2, inicio')).toHaveValue('12:00')
    expect(screen.queryByText('Horario guardado')).not.toBeInTheDocument()
  })

  it('lista los turnos en conflicto con su fecha y hora local', async () => {
    setup(() => jsonResponse({ blocks: [MORNING], conflicts: [CONFLICT] }), [MORNING])
    renderApp('/profesionales')
    await screen.findByLabelText('Lunes, tramo 1, inicio')

    fireEvent.click(screen.getByRole('button', { name: 'Guardar horario' }))

    await waitFor(() => {
      expect(
        screen.getByText(
          'Estos turnos quedaron fuera del nuevo horario. Recepción debe reprogramarlos o cancelarlos.',
        ),
      ).toBeInTheDocument()
    })
    expect(screen.getByText('lun 05/10 16:00')).toBeInTheDocument()
    expect(screen.queryByText('Horario guardado')).not.toBeInTheDocument()
  })

  it('con un 403 avisa que no tiene permiso y no pierde el horario escrito', async () => {
    setup(() => jsonResponse({ error: { code: 'FORBIDDEN', message: 'x' } }, 403), [MORNING])
    renderApp('/profesionales')
    await screen.findByLabelText('Lunes, tramo 1, inicio')

    setTime('Lunes, tramo 1, fin', '12:00')
    fireEvent.click(screen.getByRole('button', { name: 'Guardar horario' }))

    expect(await screen.findByText('No tenés permiso para esta acción')).toBeInTheDocument()
    expect(screen.getByLabelText('Lunes, tramo 1, fin')).toHaveValue('12:00')
  })
})
