import { NavLink } from 'react-router'
import { ROLE_LABELS } from '../auth/AuthContext'
import { useAuth } from '../auth/useAuth'
import { ToothMark } from '../ui/ToothMark'

/** Barra con la cuenta, el rol y los enlaces de la app; "Usuarios" solo para administración. */
export function AppNav() {
  const { user, logout } = useAuth()
  if (user === null) return null

  return (
    <nav className="app-nav" aria-label="Principal">
      <span className="app-brand">
        <ToothMark />
        Sistema Odontológico
      </span>
      <p>Hola, {user.full_name}</p>
      <p>{ROLE_LABELS[user.role]}</p>
      <div className="app-nav-links">
        <NavLink to="/agenda">Agenda</NavLink>
        <NavLink to="/pacientes">Pacientes</NavLink>
        <NavLink to="/profesionales">Profesionales</NavLink>
        {user.role === 'admin' ? <NavLink to="/tratamientos">Tratamientos</NavLink> : null}
        {user.role === 'admin' ? <NavLink to="/usuarios">Usuarios</NavLink> : null}
        <button type="button" onClick={logout}>
          Salir
        </button>
      </div>
    </nav>
  )
}
