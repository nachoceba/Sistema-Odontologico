import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi } from '../test-utils'
import {
  addTimeOff,
  deleteTimeOff,
  getProfessional,
  getWorkingHours,
  listConflicts,
  listProfessionals,
  listTimeOff,
  replaceWorkingHours,
  updateProfessional,
  type Conflict,
  type Professional,
} from './professionals'
import { ApiError } from './users'

const DRA: Professional = {
  id: 'p-1',
  display_name: 'Dra. Ana Álvarez',
  license_number: 'MAT-0001',
  active: true,
}
const CONFLICT: Conflict = {
  appointment_id: 'a-1',
  patient_id: 'pac-1',
  professional_id: 'p-1',
  starts_at: '2026-10-05T19:00:00Z',
  ends_at: '2026-10-05T19:30:00Z',
  reason: 'OUTSIDE_WORKING_HOURS',
}
const MONDAY = { weekday: 0, start_time: '09:00', end_time: '13:00' }

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  saveToken('tok-admin')
})

afterEach(() => {
  clearToken()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

function lastCall(fetchMock: ReturnType<typeof vi.fn>): { url: string; init: RequestInit } {
  const call = fetchMock.mock.calls.at(-1) as [string, RequestInit]
  return { url: call[0], init: call[1] }
}

describe('cliente de la API de profesionales', () => {
  it('listProfessionals y getProfessional piden GET con el token', async () => {
    const fetchMock = mockApi({
      'GET /professionals': () => jsonResponse([DRA]),
      'GET /professionals/p-1': () => jsonResponse(DRA),
    })

    expect(await listProfessionals()).toEqual([DRA])
    expect(await getProfessional('p-1')).toEqual(DRA)
    const { init } = lastCall(fetchMock)
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer tok-admin')
  })

  it('updateProfessional envía PATCH solo con los campos pedidos y permite borrar la matrícula', async () => {
    const fetchMock = mockApi({
      'PATCH /professionals/p-1': () => jsonResponse({ ...DRA, license_number: null }),
    })

    const updated = await updateProfessional('p-1', { license_number: null })

    expect(updated.license_number).toBeNull()
    const { init } = lastCall(fetchMock)
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body as string)).toEqual({ license_number: null })
  })

  it('getWorkingHours devuelve la lista de tramos', async () => {
    mockApi({ 'GET /professionals/p-1/working-hours': () => jsonResponse({ blocks: [MONDAY] }) })

    expect(await getWorkingHours('p-1')).toEqual([MONDAY])
  })

  it('replaceWorkingHours envía PUT con la semana completa y devuelve tramos y conflictos', async () => {
    const fetchMock = mockApi({
      'PUT /professionals/p-1/working-hours': () =>
        jsonResponse({ blocks: [MONDAY], conflicts: [CONFLICT] }),
    })

    const saved = await replaceWorkingHours('p-1', [MONDAY])

    expect(saved).toEqual({ blocks: [MONDAY], conflicts: [CONFLICT] })
    const { init } = lastCall(fetchMock)
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body as string)).toEqual({ blocks: [MONDAY] })
  })

  it('listTimeOff y listConflicts leen las listas', async () => {
    const entry = { id: 't-1', starts_on: '2026-10-12', ends_on: '2026-10-16', reason: null }
    mockApi({
      'GET /professionals/p-1/time-off': () => jsonResponse([entry]),
      'GET /professionals/p-1/conflicts': () => jsonResponse([CONFLICT]),
    })

    expect(await listTimeOff('p-1')).toEqual([entry])
    expect(await listConflicts('p-1')).toEqual([CONFLICT])
  })

  it('addTimeOff envía POST y devuelve la licencia con los conflictos', async () => {
    const entry = { id: 't-2', starts_on: '2026-10-12', ends_on: '2026-10-16', reason: 'Congreso' }
    const fetchMock = mockApi({
      'POST /professionals/p-1/time-off': () =>
        jsonResponse({ time_off: entry, conflicts: [] }, 201),
    })

    const saved = await addTimeOff('p-1', {
      starts_on: '2026-10-12',
      ends_on: '2026-10-16',
      reason: 'Congreso',
    })

    expect(saved).toEqual({ time_off: entry, conflicts: [] })
    expect(JSON.parse(lastCall(fetchMock).init.body as string)).toEqual({
      starts_on: '2026-10-12',
      ends_on: '2026-10-16',
      reason: 'Congreso',
    })
  })

  it('deleteTimeOff acepta el 204 sin cuerpo', async () => {
    const fetchMock = mockApi({
      'DELETE /professionals/p-1/time-off/t-1': () => new Response(null, { status: 204 }),
    })

    await expect(deleteTimeOff('p-1', 't-1')).resolves.toBeUndefined()
    expect(lastCall(fetchMock).init.method).toBe('DELETE')
  })

  it('un rechazo de la API sale como ApiError con el error.code', async () => {
    mockApi({
      'PUT /professionals/p-1/working-hours': () =>
        jsonResponse(
          { error: { code: 'INVALID_WORKING_HOURS', message: 'Los tramos 1 y 2 se superponen.' } },
          400,
        ),
    })

    const failure = replaceWorkingHours('p-1', [MONDAY]).catch((error: unknown) => error)

    const error = await failure
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 400,
      code: 'INVALID_WORKING_HOURS',
      message: 'Los tramos 1 y 2 se superponen.',
    })
  })
})
