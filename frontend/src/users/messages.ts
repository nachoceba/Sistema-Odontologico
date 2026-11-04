import { FORBIDDEN_MESSAGE } from '../api/client'
import { ApiError } from '../api/users'
import type { Role } from '../auth/AuthContext'

/** Nombres de los roles en la pantalla de usuarios. */
export const USER_ROLE_LABELS: Record<Role, string> = {
  admin: 'Administrador',
  receptionist: 'Recepción',
  dentist: 'Odontólogo/a',
}

export const ROLES: readonly Role[] = ['admin', 'receptionist', 'dentist']

export const NETWORK_MESSAGE = 'No se pudo conectar con el servidor'
export const INVALID_DATA_MESSAGE = 'Revisá los datos: hay campos inválidos'
export const USER_GONE_CODE = 'USER_NOT_FOUND'

const MESSAGE_BY_CODE: Record<string, string> = {
  EMAIL_TAKEN: 'Ya existe un usuario con ese email',
  ROLE_CHANGE_NOT_ALLOWED: 'No se puede cambiar el rol de un odontólogo',
  SELF_MODIFICATION_NOT_ALLOWED: 'No podés desactivar ni cambiar el rol de tu propia cuenta',
  USER_NOT_FOUND: 'El usuario ya no existe',
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
