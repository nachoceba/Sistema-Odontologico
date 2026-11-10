import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi } from '../test-utils'
import {
  bookAppointment,
  cancelAppointment,
  getAppointment,
  getDaySlots,
  listAppointments,
  recordAttendance,
  rescheduleAppointment,
  type Appointment,
  type AppointmentRecord,
  type Slot,
} from './appointments'
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
  origin: 'staff',
  pending_until: null,
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

const REGISTRO: AppointmentRecord = {
  id: 'a-1',
  patient_id: 'pac-1',
  professional_id: 'p-1',
  starts_at: '2026-11-09T13:00:00Z',
  ends_at: '2026-11-09T13:30:00Z',
  status: 'scheduled',
  cancel_reason: null,
  created_by: 'u-rec',
  origin: 'staff',
  pending_until: null,
}

function bodyOf(fetchMock: ReturnType<typeof mockApi>): unknown {
  const init = fetchMock.mock.calls[0]?.[1] as RequestInit
  return JSON.parse(init.body as string)
}

describe('cliente de turnos (escritura)', () => {
  it('bookAppointment envía paciente, profesional e inicio tal como vino de la franja', async () => {
    const fetchMock = mockApi({ 'POST /appointments': () => jsonResponse(REGISTRO, 201) })

    const result = await bookAppointment({
      patientId: 'pac-1',
      professionalId: 'p-1',
      startsAt: '2026-11-09T13:00:00Z',
    })

    expect(result).toEqual(REGISTRO)
    expect((fetchMock.mock.calls[0]?.[1] as RequestInit).method).toBe('POST')
    expect(bodyOf(fetchMock)).toEqual({
      patient_id: 'pac-1',
      professional_id: 'p-1',
      starts_at: '2026-11-09T13:00:00Z',
    })
  })

  it('cancelAppointment envía el motivo a la ruta del turno', async () => {
    const fetchMock = mockApi({
      'POST /appointments/a%201/cancel': () => jsonResponse({ ...REGISTRO, status: 'cancelled' }),
    })

    const result = await cancelAppointment('a 1', 'Avisó por teléfono')

    expect(result.status).toBe('cancelled')
    expect(bodyOf(fetchMock)).toEqual({ reason: 'Avisó por teléfono' })
  })

  it('rescheduleAppointment envía el nuevo inicio', async () => {
    const fetchMock = mockApi({
      'POST /appointments/a-1/reschedule': () => jsonResponse(REGISTRO),
    })

    await rescheduleAppointment('a-1', '2026-11-10T14:00:00Z')

    expect(bodyOf(fetchMock)).toEqual({ starts_at: '2026-11-10T14:00:00Z' })
  })

  it('recordAttendance envía completed o no_show', async () => {
    const fetchMock = mockApi({
      'POST /appointments/a-1/attendance': () => jsonResponse(REGISTRO),
    })

    await recordAttendance('a-1', 'completed')
    await recordAttendance('a-1', 'no_show')

    const bodies = fetchMock.mock.calls.map(
      (c) => JSON.parse((c[1] as RequestInit).body as string) as unknown,
    )
    expect(bodies).toEqual([{ status: 'completed' }, { status: 'no_show' }])
  })

  it('getAppointment pide el turno con su nombre y usa GET', async () => {
    const fetchMock = mockApi({ 'GET /appointments/a-1': () => jsonResponse(TURNO) })

    expect(await getAppointment('a-1')).toEqual(TURNO)
    expect((fetchMock.mock.calls[0]?.[1] as RequestInit).method).toBe('GET')
  })

  it('un 409 SLOT_TAKEN llega como ApiError con su código', async () => {
    mockApi({
      'POST /appointments': () =>
        jsonResponse({ error: { code: 'SLOT_TAKEN', message: 'Ocupado' } }, 409),
    })

    await expect(
      bookAppointment({ patientId: 'x', professionalId: 'p-1', startsAt: 'y' }),
    ).rejects.toMatchObject({ status: 409, code: 'SLOT_TAKEN' })
  })

  it('un 400 INSUFFICIENT_NOTICE conserva su código', async () => {
    mockApi({
      'POST /appointments/a-1/reschedule': () =>
        jsonResponse({ error: { code: 'INSUFFICIENT_NOTICE', message: 'Poco aviso' } }, 400),
    })

    await expect(rescheduleAppointment('a-1', 'z')).rejects.toMatchObject({
      status: 400,
      code: 'INSUFFICIENT_NOTICE',
    })
  })
})
