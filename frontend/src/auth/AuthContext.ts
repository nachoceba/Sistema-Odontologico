import { createContext } from 'react'

export type Role = 'admin' | 'receptionist' | 'dentist'

export interface User {
  id: string
  email: string
  full_name: string
  role: Role
  professional_id: string | null
}

export type SessionStatus = 'loading' | 'authenticated' | 'anonymous'

/** ok; invalid = 401 (credenciales); unavailable = red caída o error del servidor. */
export type LoginResult = 'ok' | 'invalid' | 'unavailable'

export interface AuthState {
  status: SessionStatus
  user: User | null
  /** Aviso para mostrar en /login (por ejemplo, la sesión terminó). */
  notice: string | null
  login: (email: string, password: string) => Promise<LoginResult>
  logout: () => void
}

export const ROLE_LABELS: Record<Role, string> = {
  admin: 'Administrador',
  receptionist: 'Recepción',
  dentist: 'Odontólogo',
}

export const AuthContext = createContext<AuthState | null>(null)
