import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi } from '../test-utils'
import {
  createPatient,
  deactivatePatient,
  deletePatient,
  getPatient,
  reactivatePatient,
  searchPatients,
  updatePatient,
  type Patient,
} from './patients'
import { ApiError } from './users'

const JUAN: Patient = {
  id: 'pac-1',
  first_name: 'Juan',
  last_name: 'Pérez',
  document_number: '30111222',
  email: 'juan@example.com',
  phone: '011-5550-0001',
  birth_date: null,
  active: true,
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

function lastCall(fetchMock: ReturnType<typeof vi.fn>): { url: string; init: RequestInit } {
  const call = fetchMock.mock.calls.at(-1) as [string, RequestInit]
  return { url: call[0], init: call[1] }
}

describe('cliente de la API de pacientes', () => {
  it('searchPatients pide GET con q codificado e include_inactive solo cuando se pide', async () => {
    const fetchMock = mockApi({
      'GET /patients?q=p%C3%A9r': () => jsonResponse({ items: [JUAN], truncated: false }),
      'GET /patients?include_inactive=true': () => jsonResponse({ items: [JUAN], truncated: true }),
      'GET /patients': () => jsonResponse({ items: [], truncated: false }),
    })

    expect(await searchPatients({ q: 'pér' })).toEqual({ items: [JUAN], truncated: false })
    expect(lastCall(fetchMock).url).toBe(`${BASE}/patients?q=p%C3%A9r`)
    expect(new Headers(lastCall(fetchMock).init.headers).get('Authorization')).toBe(
      'Bearer tok-rec',
    )

    expect((await searchPatients({ includeInactive: true })).truncated).toBe(true)
    expect(lastCall(fetchMock).url).toBe(`${BASE}/patients?include_inactive=true`)

    await searchPatients({ q: '   ' })
    expect(lastCall(fetchMock).url).toBe(`${BASE}/patients`)
  })

  it('getPatient lee la ficha', async () => {
    mockApi({ 'GET /patients/pac-1': () => jsonResponse(JUAN) })
    expect(await getPatient('pac-1')).toEqual(JUAN)
  })

  it('createPatient envía POST con el cuerpo y devuelve la ficha', async () => {
    const fetchMock = mockApi({ 'POST /patients': () => jsonResponse(JUAN, 201) })
    const input = {
      first_name: 'Juan',
      last_name: 'Pérez',
      document_number: '30.111.222',
      email: 'juan@example.com',
    }

    expect(await createPatient(input)).toEqual(JUAN)
    const { init } = lastCall(fetchMock)
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual(input)
  })

  it('updatePatient envía PATCH y permite borrar el teléfono con null', async () => {
    const fetchMock = mockApi({
      'PATCH /patients/pac-1': () => jsonResponse({ ...JUAN, phone: null }),
    })

    const updated = await updatePatient('pac-1', { phone: null })

    expect(updated.phone).toBeNull()
    const { init } = lastCall(fetchMock)
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body as string)).toEqual({ phone: null })
  })

  it('deactivatePatient devuelve la ficha y los turnos futuros', async () => {
    const appointment = {
      id: 'a-1',
      professional_id: 'p-1',
      starts_at: '2026-11-05T13:00:00Z',
      ends_at: '2026-11-05T13:30:00Z',
      status: 'scheduled',
    }
    const fetchMock = mockApi({
      'POST /patients/pac-1/deactivate': () =>
        jsonResponse({
          patient: { ...JUAN, active: false },
          upcoming_appointments: [appointment],
        }),
    })

    const result = await deactivatePatient('pac-1')

    expect(result.patient.active).toBe(false)
    expect(result.upcoming_appointments).toEqual([appointment])
    expect(lastCall(fetchMock).init.method).toBe('POST')
  })

  it('reactivatePatient envía POST y devuelve la ficha activa', async () => {
    mockApi({ 'POST /patients/pac-1/reactivate': () => jsonResponse(JUAN) })
    expect((await reactivatePatient('pac-1')).active).toBe(true)
  })

  it('deletePatient acepta el 204 sin cuerpo', async () => {
    const fetchMock = mockApi({
      'DELETE /patients/pac-1': () => new Response(null, { status: 204 }),
    })

    await expect(deletePatient('pac-1')).resolves.toBeUndefined()
    expect(lastCall(fetchMock).init.method).toBe('DELETE')
  })

  it('un rechazo de la API lleva el status y error.code', async () => {
    mockApi({
      'POST /patients': () =>
        jsonResponse({ error: { code: 'DOCUMENT_TAKEN', message: 'Ya existe' } }, 409),
      'DELETE /patients/pac-1': () =>
        jsonResponse({ error: { code: 'PATIENT_HAS_APPOINTMENTS', message: 'Tiene turnos' } }, 409),
    })

    const created = createPatient({
      first_name: 'A',
      last_name: 'B',
      document_number: '30111222',
      email: 'a@b.com',
    })
    await expect(created).rejects.toMatchObject({ status: 409, code: 'DOCUMENT_TAKEN' })
    await expect(created).rejects.toBeInstanceOf(ApiError)
    await expect(deletePatient('pac-1')).rejects.toMatchObject({
      status: 409,
      code: 'PATIENT_HAS_APPOINTMENTS',
    })
  })
})
