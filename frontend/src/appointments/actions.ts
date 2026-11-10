import type { AppointmentStatus } from '../api/appointments'
import type { Role } from '../auth/AuthContext'

const canManage = (role: Role): boolean => role === 'admin' || role === 'receptionist'

const started = (startsAt: string, now: Date): boolean => now.getTime() >= Date.parse(startsAt)

/** "Agendar" en una franja libre: administración y recepción, profesional activo, franja no iniciada (P-1). */
export function slotActions(input: {
  role: Role
  professionalActive: boolean
  now: Date
  slot: { startsAt: string }
}): { book: boolean } {
  return {
    book:
      canManage(input.role) &&
      input.professionalActive &&
      !started(input.slot.startsAt, input.now),
  }
}

export interface AppointmentActions {
  cancel: boolean
  reschedule: boolean
  markAttendance: boolean
}

/** Qué acciones ofrece un turno según rol, estado y hora (DD-21 a DD-24, DD-64). `now` llega como dato. */
export function appointmentActions(input: {
  role: Role
  ownProfessionalId: string | null
  professionalActive: boolean
  now: Date
  appointment: {
    status: AppointmentStatus
    startsAt: string
    professionalId: string
    /** Pendiente de confirmación del paciente: solo se puede cancelar (DD-133). */
    pending?: boolean
  }
}): AppointmentActions {
  const { role, appointment, now } = input
  if (appointment.status !== 'scheduled') {
    return { cancel: false, reschedule: false, markAttendance: false }
  }
  if (appointment.pending === true) {
    return { cancel: canManage(role) && !started(appointment.startsAt, now), reschedule: false, markAttendance: false }
  }
  const begun = started(appointment.startsAt, now)
  const own = role !== 'dentist' || input.ownProfessionalId === appointment.professionalId
  return {
    cancel: canManage(role) && !begun,
    reschedule: canManage(role) && !begun && input.professionalActive,
    markAttendance: own && begun,
  }
}
