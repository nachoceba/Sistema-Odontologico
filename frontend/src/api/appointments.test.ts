import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi } from '../test-utils'
import { getDaySlots, listAppointments, type Appointment, type Slot } from './appointments'
import { ApiError } from './users'

const TURNO: Appointment = {
  id: 'a-1',
  patient_id: 'pac-1',
  patient_first_name: 'Juan',
  patient_last_name: 'Perez',
  professional_id: 'p-1',
  starts_at: '2026-11-09T13:00:00Z',
  ends_at: '2026-11-09T13:30:00Z',
  status: 'scheduled',
  cancel_reason: null,
  created_by: 'u-rec',
}
const FRANJA: Slot = {
  starts_at: '2026-11-09T12:00:00Z',
  ends_at: '2026-11-09T12:30:00Z',
  status: 'FREE',
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  saveToken('tok-rec')
})

afterEach(() => {
  clearToken()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('cliente de turnos (solo lectura)', () => {
  it('listAppointments pide por profesional y rango con los parámetros codificados', async () => {
    const fetchMock = mockApi({
      'GET /appointments?professional_id=p%201&from=2026-11-09T03%3A00%3A00Z&to=2026-11-16T03%3A00%3A00Z':
        () => jsonResponse([TURNO]),
    })

    const result = await listAppointments('p 1', '2026-11-09T03:00:00Z', '2026-11-16T03:00:00Z')

    expect(result).toEqual([TURNO])
    expect((fetchMock.mock.calls[0]?.[1] as RequestInit).method).toBe('GET')
  })

  it('getDaySlots pide las franjas de una fecha', async () => {
    mockApi({ 'GET /professionals/p-2/slots?date=2026-11-10': () => jsonResponse([FRANJA]) })

    expect(await getDaySlots('p-2', '2026-11-10')).toEqual([FRANJA])
  })

  it('un 403 llega como ApiError con su código', async () => {
    mockApi({
      'GET /professionals/p-2/slots?date=2026-11-10': () =>
        jsonResponse({ error: { code: 'FORBIDDEN', message: 'No tenés permiso' } }, 403),
    })

    await expect(getDaySlots('p-2', '2026-11-10')).rejects.toMatchObject({
      status: 403,
      code: 'FORBIDDEN',
    })
    await expect(getDaySlots('p-2', '2026-11-10')).rejects.toBeInstanceOf(ApiError)
  })
})
