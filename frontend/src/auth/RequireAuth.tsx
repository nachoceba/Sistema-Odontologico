import { Navigate, Outlet } from 'react-router'
import { useAuth } from './useAuth'

/** Deja pasar solo con sesión; sin ella lleva a /login (RN-AU-01). */
export default function RequireAuth() {
  const { status } = useAuth()
  return status === 'authenticated' ? <Outlet /> : <Navigate to="/login" replace />
}
