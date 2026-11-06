import { describe, expect, it } from 'vitest'
import { ApiError } from '../api/users'
import {
  bookedNotice,
  messageForAppointmentError,
  moveSummary,
  rescheduledNotice,
  shouldReloadAfter,
} from './messages'

const CODES: [string, string][] = [
  ['SLOT_TAKEN', 'Ese horario se acaba de ocupar. Elegí otro horario'],
  ['OUTSIDE_WORKING_HOURS', 'Ese horario está fuera del horario de atención del profesional'],
  ['PROFESSIONAL_TIME_OFF', 'El profesional está de licencia ese día'],
  [
    'INSUFFICIENT_NOTICE',
    'Ese horario ya pasó o no respeta la anticipación mínima del consultorio',
  ],
  ['OFF_GRID', 'Ese horario no coincide con la grilla de turnos del profesional'],
  [
    'PATIENT_INACTIVE',
    'El paciente está inactivo: reactivalo desde Pacientes para darle o moverle turnos',
  ],
  ['PROFESSIONAL_INACTIVE', 'El profesional está inactivo: no se le pueden dar ni mover turnos'],
  ['PATIENT_DOUBLE_BOOKED', 'El paciente ya tiene otro turno en ese horario'],
  ['ALREADY_STARTED', 'El turno ya empezó: no se puede cancelar ni reprogramar'],
  ['CANCELLED_IS_FINAL', 'El turno ya estaba cancelado'],
  ['ATTENDANCE_ALREADY_RECORDED', 'Este turno ya tiene la asistencia registrada'],
  [
    'NOT_STARTED_YET',
    'El turno todavía no empezó: la asistencia se marca desde su hora de inicio',
  ],
  ['RESCHEDULE_SAME_TIME', 'El turno ya está en ese horario'],
  ['APPOINTMENT_NOT_FOUND', 'El turno ya no existe'],
  ['PATIENT_NOT_FOUND', 'El paciente ya no existe'],
  ['PROFESSIONAL_NOT_FOUND', 'El profesional ya no existe'],
]

describe('messageForAppointmentError', () => {
  it.each(CODES)('%s -> texto de la spec', (code, text) => {
    expect(messageForAppointmentError(new ApiError(409, code, 'x'))).toBe(text)
  })

  it('403 -> sin permiso', () => {
    expect(messageForAppointmentError(new ApiError(403, 'FORBIDDEN', 'x'))).toBe(
      'No tenés permiso para esta acción',
    )
  })

  it('422 -> revisá los datos', () => {
    expect(messageForAppointmentError(new ApiError(422, null, 'x'))).toBe(
      'Revisá los datos ingresados',
    )
  })

  it('red caída y 500 -> sin conexión', () => {
    expect(messageForAppointmentError(new TypeError('failed'))).toBe(
      'No se pudo conectar con el servidor',
    )
    expect(messageForAppointmentError(new ApiError(500, null, 'boom'))).toBe(
      'No se pudo conectar con el servidor',
    )
  })

  it('código desconocido -> el mensaje de la API', () => {
    expect(
      messageForAppointmentError(new ApiError(409, 'OTRO', 'No se pudo completar la operación')),
    ).toBe('No se pudo completar la operación')
  })
})

describe('shouldReloadAfter', () => {
  it('verdadero para todo código de la tabla', () => {
    for (const [code] of CODES) expect(shouldReloadAfter(new ApiError(409, code, 'x'))).toBe(true)
  })

  it('falso para red, 403 y 422', () => {
    expect(shouldReloadAfter(new TypeError('failed'))).toBe(false)
    expect(shouldReloadAfter(new ApiError(403, 'FORBIDDEN', 'x'))).toBe(false)
    expect(shouldReloadAfter(new ApiError(422, null, 'x'))).toBe(false)
  })
})

describe('textos de éxito', () => {
  it('turno agendado con nombre, día y hora local', () => {
    expect(bookedNotice('Perez, Juan', '2026-11-09T13:00:00Z')).toBe(
      'Turno agendado: Perez, Juan, Lun 09/11 10:00. Se enviará la confirmación por email al paciente.',
    )
    expect(bookedNotice('Ruiz, Laura', '2026-11-10T14:30:00Z')).toBe(
      'Turno agendado: Ruiz, Laura, Mar 10/11 11:30. Se enviará la confirmación por email al paciente.',
    )
  })

  it('reprogramado y resumen del movimiento', () => {
    expect(rescheduledNotice('2026-11-10T14:00:00Z')).toBe(
      'Turno reprogramado: Mar 10/11 11:00. Se enviará la confirmación por email al paciente.',
    )
    expect(moveSummary('2026-11-09T13:00:00Z', '2026-11-10T14:00:00Z')).toBe(
      'Mover de Lun 09/11 10:00 a Mar 10/11 11:00',
    )
  })

  it('los avisos no incluyen ningún email', () => {
    expect(bookedNotice('Perez, Juan', '2026-11-09T13:00:00Z')).not.toContain('@')
    expect(rescheduledNotice('2026-11-09T13:00:00Z')).not.toContain('@')
  })

  it('el día sale en la zona del consultorio aunque el instante UTC sea del día siguiente', () => {
    expect(rescheduledNotice('2026-11-10T01:30:00Z')).toBe(
      'Turno reprogramado: Lun 09/11 22:30. Se enviará la confirmación por email al paciente.',
    )
  })
})
