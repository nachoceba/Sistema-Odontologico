import type { Role } from '../auth/AuthContext'
import { apiFetch, type ApiFetchOptions } from './client'

/** Una cuenta tal como la devuelve la API al administrador (nunca trae contraseña ni hash). */
export interface ManagedUser {
  id: string
  email: string
  full_name: string
  role: Role
  active: boolean
  professional_id: string | null
}

export interface NewUserInput {
  email: string
  full_name: string
  role: Role
  password: string
  /** Solo para odontólogos; si se envía no puede ser vacío. */
  display_name?: string
  license_number?: string
}

export interface UserChanges {
  full_name?: string
  email?: string
  role?: Role
}

/** Rechazo de la API (4xx/5xx). `code` es el de `error.code`, o null (por ejemplo en un 422). */
export class ApiError extends Error {
  readonly status: number
  readonly code: string | null

  constructor(status: number, code: string | null, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

async function errorFrom(response: Response): Promise<ApiError> {
  let code: string | null = null
  let message = `Error ${String(response.status)}`
  try {
    const body = (await response.json()) as { error?: { code?: unknown; message?: unknown } }
    if (typeof body.error?.code === 'string') code = body.error.code
    if (typeof body.error?.message === 'string') message = body.error.message
  } catch {
    // Cuerpo vacío o que no es JSON: alcanza con el status.
  }
  return new ApiError(response.status, code, message)
}

export async function request(
  path: string,
  method: string,
  body?: unknown,
  options?: ApiFetchOptions,
): Promise<Response> {
  const init: RequestInit =
    body === undefined
      ? { method }
      : { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
  const response = await apiFetch(path, init, options)
  if (!response.ok) throw await errorFrom(response)
  return response
}

export async function listUsers(): Promise<ManagedUser[]> {
  const response = await request('/users', 'GET')
  return (await response.json()) as ManagedUser[]
}

export async function createUser(input: NewUserInput): Promise<ManagedUser> {
  const response = await request('/users', 'POST', input)
  return (await response.json()) as ManagedUser
}

export async function updateUser(id: string, changes: UserChanges): Promise<ManagedUser> {
  const response = await request(`/users/${id}`, 'PATCH', changes)
  return (await response.json()) as ManagedUser
}

export async function deactivateUser(id: string): Promise<ManagedUser> {
  const response = await request(`/users/${id}/deactivate`, 'POST')
  return (await response.json()) as ManagedUser
}

export async function reactivateUser(id: string): Promise<ManagedUser> {
  const response = await request(`/users/${id}/reactivate`, 'POST')
  return (await response.json()) as ManagedUser
}

export async function setPassword(id: string, password: string): Promise<void> {
  await request(`/users/${id}/password`, 'PUT', { password })
}
