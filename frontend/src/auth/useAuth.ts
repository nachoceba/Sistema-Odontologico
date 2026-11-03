import { useContext } from 'react'
import { AuthContext, type AuthState } from './AuthContext'

export function useAuth(): AuthState {
  const state = useContext(AuthContext)
  if (state === null) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return state
}
