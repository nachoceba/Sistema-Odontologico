import { FORBIDDEN_MESSAGE } from '../api/client'
import { ApiError } from '../api/users'
import { NETWORK_MESSAGE } from '../users/messages'

export const TRUNCATED_MESSAGE = 'Hay más resultados: afiná la búsqueda'
export const EMPTY_MESSAGE = 'No se encontraron pacientes'
export const DOCUMENT_TAKEN_MESSAGE = 'Ya existe un paciente con ese documento'
export const INVALID_DATA_MESSAGE = 'Revisá los datos ingresados'
export const FUTURE_BIRTH_DATE_MESSAGE = 'La fecha de nacimiento no puede ser futura'
export const HAS_APPOINTMENTS_MESSAGE = 'No se puede borrar: tiene turnos. Desactivalo en su lugar'
export const PATIENT_GONE_MESSAGE = 'El paciente ya no existe'
export const PATIENT_GONE_CODE = 'PATIENT_NOT_FOUND'
export const REQUIRED_MESSAGE = 'Este dato es obligatorio'

const MESSAGE_BY_CODE: Record<string, string> = {
  DOCUMENT_TAKEN: DOCUMENT_TAKEN_MESSAGE,
  PATIENT_HAS_APPOINTMENTS: HAS_APPOINTMENTS_MESSAGE,
  INVALID_PATIENT_DATA: FUTURE_BIRTH_DATE_MESSAGE,
  PATIENT_NOT_FOUND: PATIENT_GONE_MESSAGE,
}

/** Texto para mostrar ante un fallo de la API; red caída y 5xx dan el aviso de conexión. */
export function messageForError(error: unknown): string {
  if (!(error instanceof ApiError)) return NETWORK_MESSAGE
  const byCode = error.code === null ? undefined : MESSAGE_BY_CODE[error.code]
  if (byCode !== undefined) return byCode
  if (error.status === 422) return INVALID_DATA_MESSAGE
  if (error.status === 403) return FORBIDDEN_MESSAGE
  return NETWORK_MESSAGE
}

/** `Pérez, Juan` */
export function listName(patient: { first_name: string; last_name: string }): string {
  return `${patient.last_name}, ${patient.first_name}`
}
