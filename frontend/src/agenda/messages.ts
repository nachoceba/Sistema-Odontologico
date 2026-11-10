import type { AppointmentOrigin, AppointmentStatus } from '../api/appointments'
import type { ConflictReason } from '../api/professionals'

export const PENDING_LABEL = 'Pendiente de confirmación'
export const ONLINE_LABEL = 'Online'
export const FREE_LABEL = 'Libre'
export const BUSY_LABEL = 'Ocupado'
export const OUTSIDE_LABEL = 'Fuera de horario'
export const NO_HOURS_MESSAGE = 'Sin atención este día'
export const NO_PROFESSIONALS_MESSAGE = 'Todavía no hay profesionales cargados'
export const INACTIVE_PROFESSIONAL_MESSAGE =
  'Profesional inactivo: no se le pueden dar turnos nuevos'

export const STATUS_LABELS: Record<AppointmentStatus, string> = {
  scheduled: 'Agendado',
  completed: 'Atendido',
  no_show: 'Ausente',
  cancelled: 'Cancelado',
}

export const CONFLICT_LABELS: Record<ConflictReason, string> = {
  OUTSIDE_WORKING_HOURS: 'En conflicto: fuera del horario',
  TIME_OFF: 'En conflicto: en licencia',
}

/** Etiqueta de origen por texto: pendiente de confirmación, o reserva online ya confirmada (DD-133). */
export function originLabel(item: {
  origin: AppointmentOrigin
  pendingUntil: string | null
}): string | null {
  if (item.pendingUntil !== null) return PENDING_LABEL
  return item.origin === 'online' ? ONLINE_LABEL : null
}

export function leaveLabel(reason: string | null): string {
  return reason === null || reason === '' ? 'Licencia' : `Licencia: ${reason}`
}
