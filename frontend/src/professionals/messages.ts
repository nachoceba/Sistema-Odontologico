import { ApiError } from '../api/users'
import { messageForError as baseMessageForError } from '../users/messages'

export const NAME_REQUIRED_MESSAGE = 'El nombre a mostrar es obligatorio'
export const DATES_REQUIRED_MESSAGE = 'Completá las fechas de inicio y de fin'
export const END_BEFORE_START_MESSAGE = 'La fecha de fin no puede ser anterior a la de inicio'
export const NO_FILE_MESSAGE = 'No tenés una ficha de profesional asociada'
export const CONFLICTS_MESSAGE =
  'Estos turnos quedaron fuera del nuevo horario. Recepción debe reprogramarlos o cancelarlos.'
export const HOURS_SAVED_MESSAGE = 'Horario guardado'
export const HOURS_INCOMPLETE_MESSAGE = 'Completá el inicio y el fin de todos los tramos'
export const CONFIRM_DELETE_MESSAGE = '¿Borrar esta licencia?'
export const PROFESSIONAL_GONE_CODE = 'PROFESSIONAL_NOT_FOUND'

const MESSAGE_BY_CODE: Record<string, string> = {
  PROFESSIONAL_NOT_FOUND: 'El profesional ya no existe',
  TIME_OFF_NOT_FOUND: 'La licencia ya no existe',
  INVALID_TIME_OFF: END_BEFORE_START_MESSAGE,
}

/** Texto para mostrar ante un fallo de la API; INVALID_WORKING_HOURS usa el mensaje de la API. */
export function messageForError(error: unknown): string {
  if (error instanceof ApiError && error.code !== null) {
    if (error.code === 'INVALID_WORKING_HOURS') return error.message
    const byCode = MESSAGE_BY_CODE[error.code]
    if (byCode !== undefined) return byCode
  }
  return baseMessageForError(error)
}
