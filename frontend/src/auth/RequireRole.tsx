import { Link, Outlet } from 'react-router'
import { FORBIDDEN_MESSAGE } from '../api/client'
import type { Role } from './AuthContext'
import { useAuth } from './useAuth'

/** Deja pasar solo a los roles dados; a los demás les avisa sin cerrar la sesión ni llamar a la API. */
export default function RequireRole({ roles }: { roles: readonly Role[] }) {
  const { user } = useAuth()
  if (user !== null && roles.includes(user.role)) return <Outlet />

  return (
    <main className="page">
      <p role="alert">{FORBIDDEN_MESSAGE}</p>
      <Link to="/agenda">Volver a la agenda</Link>
    </main>
  )
}
