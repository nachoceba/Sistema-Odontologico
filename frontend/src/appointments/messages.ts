import { FORBIDDEN_MESSAGE } from '../api/client'
import { ApiError } from '../api/users'
import { formatDayLabel, formatLocalTime, localDateOf } from '../agenda/dates'
import { NETWORK_MESSAGE } from '../users/messages'

export const INVALID_DATA_MESSAGE = 'Revisá los datos ingresados'

export const BOOK_LABEL = 'Agendar'
export const BOOK_SUBMIT_LABEL = 'Agendar turno'
export const CANCEL_LABEL = 'Cancelar'
export const CANCEL_SUBMIT_LABEL = 'Cancelar turno'
export const RESCHEDULE_LABEL = 'Reprogramar'
export const RESCHEDULE_SUBMIT_LABEL = 'Reprogramar turno'
export const BACK_LABEL = 'Volver'
export const CLOSE_LABEL = 'Cerrar'
export const COMPLETED_LABEL = 'Atendido'
export const NO_SHOW_LABEL = 'Ausente'

export const CANCELLED_NOTICE = 'Turno cancelado'
export const ATTENDANCE_NOTICE = 'Asistencia registrada'
export const REASON_REQUIRED_MESSAGE = 'Escribí el motivo de la cancelación'
export const REASON_MAX_LENGTH = 500
export const NO_FREE_SLOTS_MESSAGE = 'No hay horarios libres este día'
export const ACCENT_NOTE =
  'La búsqueda distingue tildes: si el apellido lleva tilde, escribilo con tilde (por ejemplo, Pérez)'

const MESSAGE_BY_CODE: Record<string, string> = {
  SLOT_TAKEN: 'Ese horario se acaba de ocupar. Elegí otro horario',
  OUTSIDE_WORKING_HOURS: 'Ese horario está fuera del horario de atención del profesional',
  PROFESSIONAL_TIME_OFF: 'El profesional está de licencia ese día',
  INSUFFICIENT_NOTICE: 'Ese horario ya pasó o no respeta la anticipación mínima del consultorio',
  OFF_GRID: 'Ese horario no coincide con la grilla de turnos del profesional',
  PATIENT_INACTIVE:
    'El paciente está inactivo: reactivalo desde Pacientes para darle o moverle turnos',
  PROFESSIONAL_INACTIVE: 'El profesional está inactivo: no se le pueden dar ni mover turnos',
  PATIENT_DOUBLE_BOOKED: 'El paciente ya tiene otro turno en ese horario',
  ALREADY_STARTED: 'El turno ya empezó: no se puede cancelar ni reprogramar',
  CANCELLED_IS_FINAL: 'El turno ya estaba cancelado',
  ATTENDANCE_ALREADY_RECORDED: 'Este turno ya tiene la asistencia registrada',
  NOT_STARTED_YET: 'El turno todavía no empezó: la asistencia se marca desde su hora de inicio',
  RESCHEDULE_SAME_TIME: 'El turno ya está en ese horario',
  APPOINTMENT_NOT_FOUND: 'El turno ya no existe',
  PATIENT_NOT_FOUND: 'El paciente ya no existe',
  PROFESSIONAL_NOT_FOUND: 'El profesional ya no existe',
}

/** Texto de un rechazo al agendar, cancelar, reprogramar o marcar (spec de mensajes por código). */
export function messageForAppointmentError(error: unknown): string {
  if (!(error instanceof ApiError)) return NETWORK_MESSAGE
  const byCode = error.code === null ? undefined : MESSAGE_BY_CODE[error.code]
  if (byCode !== undefined) return byCode
  if (error.status === 403) return FORBIDDEN_MESSAGE
  if (error.status === 422) return INVALID_DATA_MESSAGE
  if (error.status >= 500) return NETWORK_MESSAGE
  return error.message
}

/** La agenda se vuelve a pedir después de un rechazo con código de la tabla (P-7). */
export function shouldReloadAfter(error: unknown): boolean {
  return error instanceof ApiError && error.code !== null && error.code in MESSAGE_BY_CODE
}

/** `Lun 09/11 10:00` para un instante UTC, en la zona del consultorio. */
export function dayAndTime(utcInstant: string): string {
  return `${formatDayLabel(localDateOf(utcInstant))} ${formatLocalTime(utcInstant)}`
}

export function bookedNotice(patientName: string, startsAt: string): string {
  return `Turno agendado: ${patientName}, ${dayAndTime(startsAt)}`
}

export function rescheduledNotice(startsAt: string): string {
  return `Turno reprogramado: ${dayAndTime(startsAt)}`
}

export function moveSummary(fromStartsAt: string, toStartsAt: string): string {
  return `Mover de ${dayAndTime(fromStartsAt)} a ${dayAndTime(toStartsAt)}`
}
