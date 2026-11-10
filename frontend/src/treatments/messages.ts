import { FORBIDDEN_MESSAGE } from '../api/client'
import { ApiError } from '../api/users'
import { INVALID_DATA_MESSAGE, NETWORK_MESSAGE } from '../users/messages'

export const EMPTY_CATALOG_MESSAGE = 'Todavía no hay tratamientos.'
export const DEACTIVATE_WARNING =
  'Los turnos que ya lo tienen no cambian. No se va a poder elegir en turnos nuevos.'
export const NAME_TAKEN_MESSAGE = 'Ya existe un tratamiento con ese nombre.'
export const GONE_MESSAGE = 'El tratamiento ya no existe'
export const NO_ACTIVE_ASSIGNED_MESSAGE =
  'Sin tratamientos activos: no se le pueden dar turnos nuevos.'

const MESSAGE_BY_CODE: Record<string, string> = {
  TREATMENT_NAME_TAKEN: NAME_TAKEN_MESSAGE,
  TREATMENT_NOT_FOUND: GONE_MESSAGE,
}

/** Texto para mostrar ante un fallo de la API de tratamientos; red caída y 5xx dan el aviso de conexión. */
export function messageForTreatmentError(error: unknown): string {
  if (!(error instanceof ApiError)) return NETWORK_MESSAGE
  const byCode = error.code === null ? undefined : MESSAGE_BY_CODE[error.code]
  if (byCode !== undefined) return byCode
  if (error.status === 422) return INVALID_DATA_MESSAGE
  if (error.status === 403) return FORBIDDEN_MESSAGE
  return NETWORK_MESSAGE
}
