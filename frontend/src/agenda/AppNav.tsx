import { Link } from 'react-router'
import { ROLE_LABELS } from '../auth/AuthContext'
import { useAuth } from '../auth/useAuth'

/** Barra con la cuenta, el rol y los enlaces de la app; "Usuarios" solo para administración. */
export function AppNav() {
  const { user, logout } = useAuth()
  if (user === null) return null

  return (
    <nav className="app-nav" aria-label="Principal">
      <p>Hola, {user.full_name}</p>
      <p>{ROLE_LABELS[user.role]}</p>
      <div className="app-nav-links">
        <Link to="/pacientes">Pacientes</Link>
        <Link to="/profesionales">Profesionales</Link>
        {user.role === 'admin' ? <Link to="/usuarios">Usuarios</Link> : null}
        <button type="button" onClick={logout}>
          Salir
        </button>
      </div>
    </nav>
  )
}
