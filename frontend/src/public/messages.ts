import { ApiError } from '../api/users'

export const TOO_MANY_MESSAGE = 'Hizo muchos intentos. Espere un rato y vuelva a probar.'
export const BOOKING_NOT_POSSIBLE_MESSAGE = 'Verifique sus datos ingresados.'
export const SLOT_UNAVAILABLE_MESSAGE = 'Ese horario ya no está disponible. Elija otro.'
export const BOOKING_FAILED_MESSAGE = 'No pudimos registrar el turno. Pruebe de nuevo más tarde.'
export const CONFIRM_FAILED_MESSAGE = 'No pudimos confirmar el turno. Pruebe de nuevo más tarde.'
export const PROFESSIONALS_FAILED_MESSAGE = 'No pudimos cargar los profesionales. Pruebe de nuevo.'
export const TREATMENTS_FAILED_MESSAGE = 'No pudimos cargar los tratamientos. Pruebe de nuevo.'
export const TREATMENT_UNAVAILABLE_MESSAGE =
  'El tratamiento elegido ya no está disponible. Elija otro.'
export const NO_TREATMENTS_MESSAGE =
  'Este profesional no tiene tratamientos disponibles para reservar en línea. Elija otro o comuníquese con el consultorio.'
export const SLOTS_FAILED_MESSAGE = 'No pudimos cargar los horarios. Pruebe de nuevo.'
export const NO_PROFESSIONALS_MESSAGE =
  'Por ahora no hay profesionales disponibles para reservar en línea. Comuníquese con el consultorio.'
export const NO_SLOTS_MESSAGE = 'No hay horarios libres para este día. Pruebe con otro.'

const isTooMany = (error: unknown): boolean =>
  error instanceof ApiError && (error.status === 429 || error.code === 'TOO_MANY_REQUESTS')

/** Texto de un rechazo al reservar; ningún texto repite lo que escribió la persona. */
export function messageForBooking(error: unknown): string {
  if (isTooMany(error)) return TOO_MANY_MESSAGE
  if (error instanceof ApiError) {
    if (error.code === 'BOOKING_NOT_POSSIBLE') return BOOKING_NOT_POSSIBLE_MESSAGE
    if (error.code === 'SLOT_TAKEN' || error.code === 'SLOT_UNAVAILABLE') {
      return SLOT_UNAVAILABLE_MESSAGE
    }
    if (error.code === 'TREATMENT_NOT_AVAILABLE') return TREATMENT_UNAVAILABLE_MESSAGE
  }
  return BOOKING_FAILED_MESSAGE
}

/** Las franjas del día se recargan cuando la reserva perdió la franja. */
export function lostTheSlot(error: unknown): boolean {
  return error instanceof ApiError && (error.code === 'SLOT_TAKEN' || error.code === 'SLOT_UNAVAILABLE')
}

/** El tratamiento elegido dejó de poder reservarse: se vuelve a pedir la lista. */
export function lostTheTreatment(error: unknown): boolean {
  return error instanceof ApiError && error.code === 'TREATMENT_NOT_AVAILABLE'
}

export type ConfirmFailure = 'invalid' | 'retry'

/** Un enlace vencido, usado o inexistente es definitivo; todo lo demás se puede reintentar. */
export function confirmFailure(error: unknown): { kind: ConfirmFailure; message: string } {
  if (error instanceof ApiError && error.code === 'CONFIRMATION_LINK_INVALID') {
    return { kind: 'invalid', message: '' }
  }
  return {
    kind: 'retry',
    message: isTooMany(error) ? TOO_MANY_MESSAGE : CONFIRM_FAILED_MESSAGE,
  }
}
